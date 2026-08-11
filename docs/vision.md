# Vision et generation multimodale NVIDIA

Tony conserve `meta/llama-3.1-8b-instruct` pour la conversation vocale rapide. Les capacites lourdes ne sont appelees que lorsqu'elles sont necessaires.

## Routing actuel

| Usage | Modele | Entrees | Sortie |
|---|---|---|---|
| Conversation + tools | `meta/llama-3.1-8b-instruct` | texte | texte / tool calls |
| Vision ecran / image / video | `nvidia/nemotron-nano-12b-v2-vl` | texte + image/video | texte / tool calls |
| Generation / edition image | `black-forest-labs/flux.2-klein-4b` | texte + image optionnelle | image |

Le Nemotron Nano 12B v2 VL est disponible via `https://integrate.api.nvidia.com/v1/chat/completions`, accepte les images et les videos et prend en charge le function calling.

FLUX.2 Klein 4B dispose d'un endpoint NVIDIA natif `https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b`. Pour la generation, le payload minimal utilise par Tony est `prompt + seed + steps`, ce qui evite les erreurs de validation dues a des champs superflus.

## Vision ecran

Le tool `capture_screen` capture une vraie image JPEG. Le provider NVIDIA transforme le `tool_result` image en contenu `image_url`, puis detecte automatiquement la presence d'une image et route la requete vers le VLM.

Le modele vocal rapide n'est jamais utilise pour interpreter une capture. Apres une capture, Tony utilise le VLM et lui demande explicitement de decrire uniquement ce qu'il voit.

`capture_screen` normalise aussi toujours `ecran` en entier avant de comparer les index des moniteurs.

## Generation d'image

Le tool `generer_image` utilise le endpoint NIM natif de FLUX.2 Klein 4B :

```text
POST https://ai.api.nvidia.com/v1/genai/black-forest-labs/flux.2-klein-4b
```

Payload de generation :

```json
{
  "prompt": "...",
  "seed": 0,
  "steps": 4
}
```

La reponse est normalisee depuis `artifacts[0].base64` (avec support du format `data[].b64_json` en fallback).

L'image est sauvegardee dans :

```text
projets/<projet-actif>/output/images/
```

ou dans `generated/` si aucun projet n'est actif.

## Regles

1. Une demande texte simple reste sur Llama 3.1 8B.
2. Une demande sur l'ecran appelle `capture_screen`, puis le VLM.
3. Une demande « genere une image » appelle `generer_image`.
4. Le VLM ne doit pas rappeler `capture_screen` apres avoir recu la capture : il analyse l'image deja fournie.
5. Une erreur multimodale est transformee en reponse courte et exploitable.
6. Les capacites multimodales ne doivent pas ralentir le chemin vocal normal.
7. Les operations fichiers de Clover restent independantes des capacites vision de Tony.

## Video

Le VLM `nvidia/nemotron-nano-12b-v2-vl` sait aussi recevoir des videos pour analyse. La generation video est une capacite distincte : NVIDIA documente des endpoints OpenAI-compatibles pour WAN2.2 dans les NIM Visual Generative AI recents. Elle sera ajoutee plus tard dans un outil dedie afin de ne pas melanger generation d'image, generation video et conversation vocale.
