# NVIDIA NIM

Le provider NVIDIA utilise l'API OpenAI-compatible et suit le meme contrat interne que le provider Ollama.

## Architecture

Les tools de Jarvis ne connaissent pas le provider. Le provider convertit :

`historique interne -> messages OpenAI -> NVIDIA -> tool_calls -> Bloc/Reponse interne`

Ainsi les tools classiques (heure, meteo, applications, volume, stats PC, memoire, agenda, mail, Discord, OBS, Hue, etc.) restent independants du modele.

## Profil recommande pour la voix

```yaml
mode: nvidia
nvidia:
  modele: "meta/llama-3.1-8b-instruct"
  base_url: "https://integrate.api.nvidia.com/v1"
  reasoning_effort: ""
  max_tokens: 512
  temperature: 0.2
  vision: false
voix_locale: piper
```

`openai/gpt-oss-120b` reste interessant pour une future couche d'agents et de taches longues, mais son raisonnement ajoute une latence inutile aux commandes vocales courtes.

## Tool calling

NVIDIA recoit les tools avec le format OpenAI :

```json
{
  "type": "function",
  "function": {
    "name": "...",
    "description": "...",
    "parameters": {"type": "object", "properties": {}}
  }
}
```

Les tool calls sont ensuite reconvertis en `Bloc("tool_use", ...)`. Le moteur principal continue donc de fonctionner comme avec Claude et Ollama.

## Vision

La vision est volontairement opt-in. `meta/llama-3.1-8b-instruct` n'est pas le modele a utiliser pour les captures d'ecran. Pour activer la vision, choisir un modele NVIDIA multimodal compatible puis mettre `vision: true`.

## Test

```powershell
uv run python scripts/test_nvidia_compat.py
```

Le test verifie une reponse texte et un appel de tool `lancer_application`.
