"""Generation d'images NVIDIA pour Tony.

Utilise l'API OpenAI-compatible Visual GenAI de NVIDIA et FLUX.2 Klein 4B.
L'image est sauvegardee dans le workspace du projet actif quand il existe,
sinon dans generated/."""
from __future__ import annotations

import base64
from datetime import datetime
from pathlib import Path

from core.config import reglage
from core.registre import outil


MODEL = "black-forest-labs/flux.2-klein-4b"


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
    try:
        import os
        from openai import OpenAI
    except ImportError:
        return "La generation d'image necessite le paquet openai."

    key = os.getenv("NVIDIA_API_KEY") or reglage("nvidia.cle", "")
    if not key:
        return "La cle NVIDIA n'est pas configuree."

    base_url = reglage("nvidia.base_url", "https://integrate.api.nvidia.com/v1").rstrip("/")
    model = reglage("nvidia.image_modele", MODEL)
    try:
        client = OpenAI(api_key=key, base_url=base_url, timeout=180.0)
        response = client.images.generate(
            model=model,
            prompt=prompt,
            n=1,
            response_format="b64_json",
        )
        b64 = response.data[0].b64_json
        if not b64:
            return "NVIDIA n'a retourne aucune image."
        data = base64.b64decode(b64)

        safe_name = Path(nom_fichier).name if nom_fichier else ""
        if not safe_name or safe_name in (".", ".."):
            safe_name = f"tony_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        if Path(safe_name).suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            safe_name += ".png"
        output = _racine_sortie() / safe_name
        output.write_bytes(data)

        try:
            from core import hud
        except Exception:
            hud = None
        if hud is not None:
            try:
                hud.image_gen(str(output), prompt)
            except Exception:
                pass
        return f'Image generee avec {model} : {output}'
    except Exception as exc:
        return f"Generation d'image NVIDIA echouee : {type(exc).__name__}: {exc}"
