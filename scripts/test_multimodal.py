"""Smoke tests that do not spend NVIDIA quota.

Run: uv run python scripts/test_multimodal.py
"""
from core import registre

registre.charger_outils()
noms = {o.nom for o in registre.tous()}
required = {"capture_screen", "generer_image", "creer_projet", "lancer_agent"}
missing = required - noms
if missing:
    raise SystemExit(f"FAIL: tools manquants: {sorted(missing)}")

from core.llm import NvidiaProvider
provider = NvidiaProvider()
messages = [{
    "role": "user",
    "content": [{"type": "text", "text": "Analyse cette image."}, {
        "type": "image", "source": {"media_type": "image/jpeg", "data": "ZmFrZQ=="}
    }],
}]
translated = provider._traduire("test", messages, vision=True)
assert provider._contient_image(translated), "Image non convertie en image_url"
assert translated[-1]["content"][1]["type"] == "image_url"
print("OK: capture_screen + generer_image + project/agent tools + routing image")
