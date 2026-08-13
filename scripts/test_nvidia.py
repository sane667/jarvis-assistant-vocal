"""Smoke-test NVIDIA NIM without starting the whole voice assistant.

Usage (PowerShell):
    $env:NVIDIA_API_KEY = "..."
    uv run python scripts/test_nvidia.py

The script checks a normal response and a simple tool call. It never executes
an actual Jarvis tool; it only verifies that the model emits the expected call.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.llm import NvidiaProvider


TOOLS = [
    {
        "name": "lancer_application",
        "description": "Lance une application du PC.",
        "input_schema": {
            "type": "object",
            "properties": {
                "nom": {"type": "string", "description": "Nom de l'application."}
            },
            "required": ["nom"],
        },
    }
]

SYSTEM = (
    "Tu es un assistant vocal de test. Reponds en francais, de facon concise. "
    "Quand une action demande un outil, utilise le tool call approprie."
)


def main():
    if not os.getenv("NVIDIA_API_KEY"):
        print("ERREUR: NVIDIA_API_KEY n'est pas defini.")
        print('PowerShell: $env:NVIDIA_API_KEY = "ta_cle"')
        return 1

    provider = NvidiaProvider()
    if not provider.disponible():
        print("ERREUR: provider NVIDIA indisponible.")
        return 1

    print(f"Modele: {provider.modele}")
    print(f"Reasoning effort: {provider.reasoning_effort or 'default'}")

    print("1/2 Test texte...")
    rep = provider.repondre(
        SYSTEM,
        [{"role": "user", "content": "Dis simplement : NVIDIA est connecte."}],
        [],
    )
    text = " ".join(b.text for b in rep.content if b.type == "text")
    print("   ->", text or "(aucun texte)")
    if not text:
        print("   ECHEC: reponse texte vide.")
        return 2

    print("2/2 Test tool calling...")
    rep = provider.repondre(
        SYSTEM,
        [{"role": "user", "content": "Lance Spotify."}],
        TOOLS,
    )
    calls = [b for b in rep.content if b.type == "tool_use"]
    if not calls:
        print("   ECHEC: aucun tool call recu.")
        print("   Reponse:", " ".join(b.text for b in rep.content if b.type == "text"))
        return 2

    for call in calls:
        print(f"   -> {call.name}({call.input}) [id={call.id}]")

    print("OK: NVIDIA + GPT-OSS + tool calling fonctionnent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
