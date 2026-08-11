# Outils Jarvis

Les outils sont le contrat commun entre Claude, Ollama et NVIDIA. Un outil doit
être ajouté dans `tools/` avec `@outil(...)` : le registre le découvre
automatiquement au démarrage.

## Règle d'architecture

Un outil ne doit jamais contenir de logique spécifique à Claude, Ollama ou
NVIDIA. Le provider traduit uniquement le contrat LLM vers le format attendu par
son API. Cela permet de changer de modèle sans réécrire les intégrations.

```text
                    Tony
                      |
                 ProviderLLM
              /       |       \
          Claude    Ollama    NVIDIA
              \       |       /
               contrat interne
                      |
                 registre tools
                      |
       PC / web / mail / Discord / agenda...
```

## Ajouter un outil

```python
from core.registre import outil

@outil(
    nom="ma_fonction",
    description="Explique clairement quand Tony doit utiliser cet outil.",
    parametres={
        "type": "object",
        "properties": {
            "texte": {"type": "string"},
        },
        "required": ["texte"],
    },
)
def ma_fonction(texte: str):
    return "..."
```

Utiliser `confirmation=True` pour une action irréversible ou sensible et
`lent=True` avec `phrase_attente` pour une action qui peut prendre plusieurs
secondes.

## Audit

Avant de considérer un outil comme terminé :

```powershell
uv run python scripts/audit_tools.py
```

L'audit est volontairement **non destructif**. Il vérifie la découverte,
le schéma JSON, la cohérence avec la signature Python et la conversion vers
OpenAI function calling utilisée par NVIDIA. Il ne lance jamais une application,
n'envoie jamais un mail, ne touche pas aux lampes et n'ouvre pas de navigateur.

Le test NVIDIA déjà présent (`scripts/test_nvidia_compat.py`) valide en plus le
contrat LLM sur une réponse texte et un tool call.

## Vision

`capture_screen` reste un outil normal. Le provider décide seulement si le
modèle courant sait recevoir une image. Un modèle texte comme
`meta/llama-3.1-8b-instruct` ne doit pas être forcé à traiter une capture.
Le futur routage multimodal pourra envoyer la même conversation à un modèle
vision sans modifier l'outil.
