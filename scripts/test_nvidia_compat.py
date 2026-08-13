"""Smoke test du contrat LLM commun avec NVIDIA.

Teste le provider NVIDIA comme Ollama :
1) reponse texte ;
2) tool call ;
3) conversion vers Bloc/Reponse interne.

Usage:
    uv run python scripts/test_nvidia_compat.py
"""

import os
import sys

# Permet l'import depuis la racine du projet quand le script est lance directement.
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.llm import NvidiaProvider


TOOL = {
    "name": "lancer_application",
    "description": "Lance une application du PC.",
    "input_schema": {
        "type": "object",
        "properties": {"nom": {"type": "string"}},
        "required": ["nom"],
    },
}


SYSTEM = (
    "Tu es Tony, un assistant vocal. "
    "Pour lancer une application, utilise le tool fourni."
)


def main():
    provider = NvidiaProvider()
    print(f"Modele: {provider.modele}")
    print(f"Base URL: {provider.base_url}")
    print(f"Vision: {getattr(provider, 'vision', False)}")

    if not provider.disponible():
        raise SystemExit(
            "NVIDIA non configure. Definis NVIDIA_API_KEY avant de lancer le test."
        )

    print("\n1/2 Test texte...")
    rep = provider.repondre(
        SYSTEM,
        [{"role": "user", "content": "Dis simplement bonjour."}],
        [],
    )
    print("STOP =", rep.stop_reason)
    print("CONTENT =", [(b.type, b.text) for b in rep.content])

    print("\n2/2 Test tool calling...")
    rep = provider.repondre(
        SYSTEM,
        [{"role": "user", "content": "Lance Spotify."}],
        [TOOL],
    )
    calls = [b for b in rep.content if b.type == "tool_use"]
    print("STOP =", rep.stop_reason)
    print(
        "TOOL CALLS =",
        [(b.name, b.input) for b in calls],
    )

    if not calls:
        raise SystemExit("ECHEC: aucun tool call recu.")
    if calls[0].name != "lancer_application":
        raise SystemExit(f"ECHEC: mauvais outil: {calls[0].name}")

    print("OK: contrat NVIDIA compatible avec le registre de tools.")


if __name__ == "__main__":
    main()
