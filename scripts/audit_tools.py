"""Audit statique et non destructif du registre des outils Jarvis.

Usage:
    uv run python scripts/audit_tools.py

Le script ne lance PAS les actions réelles (pas de Spotify, mail, navigateur,
lampe, appel, etc.). Il vérifie que chaque outil est correctement découvert,
que son schéma est exploitable par le contrat LLM commun, que sa signature
Python reste cohérente avec son schéma, et que le provider NVIDIA peut
sérialiser tous les tools au format OpenAI function calling.
"""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

# Permet de lancer le script depuis la racine avec `uv run python scripts/...`.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import registre


def _check_schema(schema: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(schema, dict):
        return ["schema absent ou non-dict"]
    if schema.get("type") != "object":
        errors.append("schema.type != object")
    if not isinstance(schema.get("properties", {}), dict):
        errors.append("schema.properties n'est pas un objet")
    required = schema.get("required", [])
    if required is not None and not isinstance(required, list):
        errors.append("schema.required n'est pas une liste")
    return errors


def _check_signature(outil) -> list[str]:
    errors: list[str] = []
    try:
        sig = inspect.signature(outil.fonction)
    except (TypeError, ValueError) as exc:
        return [f"signature illisible: {exc}"]

    props = outil.parametres.get("properties", {})
    for name, param in sig.parameters.items():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        if name not in props and param.default is param.empty:
            errors.append(f"argument requis '{name}' absent du schema")

    required = set(outil.parametres.get("required", []) or [])
    for name in required:
        if name not in sig.parameters:
            errors.append(f"schema.required contient '{name}', absent de la fonction")
    return errors


def main() -> int:
    registre.charger_outils()
    outils = registre.tous()
    if not outils:
        print("FAIL: aucun outil découvert dans tools/")
        return 1

    # Import tardif : le test reste utile même si le provider NVIDIA n'est pas
    # configuré. On teste uniquement la conversion des schemas, jamais un appel API.
    from core.llm import NvidiaProvider

    total = len(outils)
    passed = skipped = failed = 0
    print(f"Jarvis tool audit — {total} outils découverts\n")

    for outil in sorted(outils, key=lambda x: x.nom):
        errors = _check_schema(outil.parametres)
        errors.extend(_check_signature(outil))

        try:
            converted = NvidiaProvider._outils([
                {
                    "name": outil.nom,
                    "description": outil.description,
                    "input_schema": outil.parametres,
                }
            ])
            json.dumps(converted, ensure_ascii=False)
            if not converted or converted[0]["function"]["name"] != outil.nom:
                errors.append("conversion OpenAI invalide")
        except Exception as exc:
            errors.append(f"conversion NVIDIA impossible: {exc}")

        flags = []
        if outil.confirmation:
            flags.append("confirmation")
        if outil.lent:
            flags.append("lent")
        if outil.mcp_expose:
            flags.append("MCP")
        meta = ", ".join(flags) if flags else "normal"

        if errors:
            failed += 1
            print(f"🔴 FAIL  {outil.nom:32} [{meta}]")
            for error in errors:
                print(f"       - {error}")
        elif outil.confirmation or outil.lent:
            skipped += 1
            print(f"🟡 READY {outil.nom:32} [{meta}] (pas d'exécution réelle)")
        else:
            passed += 1
            print(f"🟢 PASS  {outil.nom:32} [{meta}]")

    print("\nRésumé")
    print(f"  🟢 structure valide : {passed}")
    print(f"  🟡 valide mais action protégée/lente : {skipped}")
    print(f"  🔴 problèmes : {failed}")
    print("\nAucune action réelle n'a été exécutée.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
