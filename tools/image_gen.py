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
    """Accepte les deux formats NVIDIA: hosted API (artifacts) et NIM OpenAI."""
    artifacts = payload.get("artifacts") or []
    if artifacts and isinstance(artifacts[0], dict) and artifacts[0].get("base64"):
        return artifacts[0]["base64"]
    data = payload.get("data") or []
    if data and isinstance(data[0], dict) and data[0].get("b64_json"):
        return data[0]["b64_json"]
    return None


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
    # L'API catalogue NVIDIA utilise un endpoint /genai distinct du endpoint
    # OpenAI-compatible /v1/chat/completions. L'ancien appel client.images.generate
    # sur integrate.api.nvidia.com pouvait donc renvoyer 404.
    url = reglage("nvidia.image_url", HOSTED_URL)
    payload = {
        "mode": "Image Generation",
        "prompt": prompt,
        "height": 1024,
        "width": 1024,
        "samples": 1,
        "seed": 0,
        "steps": 4,
    }
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

    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
        b64 = _extract_base64(result)
        if not b64:
            return "NVIDIA n'a retourne aucune image exploitable."
        data = base64.b64decode(b64)

        safe_name = Path(nom_fichier).name if nom_fichier else ""
        if not safe_name or safe_name in (".", ".."):
            safe_name = f"tony_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        if Path(safe_name).suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            safe_name += ".png"
        output = _racine_sortie() / safe_name
        output.write_bytes(data)

        try:
            import hud
            hud.image_gen(str(output), prompt)
        except Exception:
            pass
        return f'Image generee avec {model} : {output}'
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", errors="replace")
        except Exception:
            detail = str(exc)
        return f"Generation d'image NVIDIA echouee : HTTP {exc.code}: {detail[:500]}"
    except Exception as exc:
        return f"Generation d'image NVIDIA echouee : {type(exc).__name__}: {exc}"
