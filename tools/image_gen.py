"""Generation d'images NVIDIA pour Tony."""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

from core.config import reglage
from core.registre import outil

MODEL = "black-forest-labs/flux.2-klein-4b"
HOSTED_URL = "https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b"


def _racine_sortie() -> Path:
    try:
        from core.project_store import store
        project = store().active
        if project:
            path = Path(project.path) / "output" / "images"
        else:
            path = Path(__file__).resolve().parent.parent / "generated"
    except Exception:
        path = Path(__file__).resolve().parent.parent / "generated"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _extract_base64(payload: dict) -> str | None:
    artifacts = payload.get("artifacts") or []
    if artifacts and isinstance(artifacts[0], dict) and artifacts[0].get("base64"):
        return artifacts[0]["base64"]
    data = payload.get("data") or []
    if data and isinstance(data[0], dict) and data[0].get("b64_json"):
        return data[0]["b64_json"]
    return None


def _post(url: str, key: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


@outil(
    nom="generer_image",
    description=(
        "Genere une image a partir d'une description utilisateur. A utiliser quand "
        "l'utilisateur demande de creer, generer, dessiner ou produire une image. "
        "Retourne le chemin du fichier genere. Ne dis jamais que la generation est "
        "impossible si cet outil est disponible."
    ),
    parametres={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Description detaillee de l'image a generer."},
            "nom_fichier": {"type": "string", "description": "Nom de fichier facultatif, sans chemin."},
        },
        "required": ["prompt"],
    },
    lent=True,
    phrase_attente="Je genere l'image.",
)
def generer_image(prompt: str, nom_fichier: str = "") -> str:
    key = os.getenv("NVIDIA_API_KEY") or reglage("nvidia.cle", "")
    if not key:
        return "La cle NVIDIA n'est pas configuree."

    model = reglage("nvidia.image_modele", MODEL)
    url = reglage("nvidia.image_url", HOSTED_URL)

    # FLUX.2-klein accepte un payload beaucoup plus petit que les anciens NIM.
    # Les champs mode/height/width/samples envoyes auparavant pouvaient etre
    # rejetes par la validation de l'API catalogue (422 extra_forbidden selon
    # la version du service). Prompt + seed + steps est le contrat generation.
    payload = {"prompt": prompt, "seed": 0, "steps": 4}
    try:
        result = _post(url, key, payload)
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(exc)
        # Fallback utile si NVIDIA change temporairement le schema du hosted
        # endpoint : le contrat generation documente aussi le mode explicite.
        if exc.code == 422:
            try:
                result = _post(url, key, {"mode": "Image Generation", "prompt": prompt, "seed": 0, "steps": 4})
            except urllib.error.HTTPError as exc2:
                try:
                    detail2 = exc2.read().decode("utf-8", errors="replace")
                except Exception:
                    detail2 = str(exc2)
                return f"Generation d'image NVIDIA echouee : HTTP {exc2.code}: {detail2[:500]}"
            except Exception as exc2:
                return f"Generation d'image NVIDIA echouee : {type(exc2).__name__}: {exc2}"
        else:
            return f"Generation d'image NVIDIA echouee : HTTP {exc.code}: {detail[:500]}"
    except Exception as exc:
        return f"Generation d'image NVIDIA echouee : {type(exc).__name__}: {exc}"

    b64 = _extract_base64(result)
    if not b64:
        return "NVIDIA n'a retourne aucune image exploitable."

    try:
        data = base64.b64decode(b64)
        safe_name = Path(nom_fichier).name if nom_fichier else ""
        if not safe_name or safe_name in (".", ".."):
            safe_name = f"tony_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        if Path(safe_name).suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            safe_name += ".png"
        output = _racine_sortie() / safe_name
        output.write_bytes(data)
        try:
            import project_hud
            project_hud.image_gen(str(output), prompt)
        except Exception:
            try:
                import hud
                hud.image_gen(str(output), prompt)
            except Exception:
                pass
        return f'Image generee avec {model} : {output}'
    except Exception as exc:
        return f"Image NVIDIA recue mais impossible a enregistrer : {type(exc).__name__}: {exc}"
