# Vision et generation multimodale NVIDIA

Tony conserve `meta/llama-3.1-8b-instruct` pour la conversation vocale rapide. Les capacites lourdes ne sont appelees que lorsqu'elles sont necessaires.

## Routing actuel

| Usage | Modele | Entrees | Sortie |
|---|---|---|---|
| Conversation + tools | `meta/llama-3.1-8b-instruct` | texte | texte / tool calls |
| Vision ecran / image | `nvidia/nemotron-nano-12b-v2-vl` | texte + image | texte / tool calls |
| Generation / edition image | `black-forest-labs/flux.2-klein-4b` | texte + image optionnelle | image |

Le Nemotron Nano 12B v2 VL dispose d'un endpoint NVIDIA gratuit, accepte image et video et supporte le function calling. NVIDIA documente explicitement l'usage de `nvidia/nemotron-nano-12b-v2-vl` avec `https://integrate.api.nvidia.com/v1/chat/completions`. citeturn3search0turn3search2

FLUX.2 Klein 4B expose une API OpenAI-compatible `/v1/images/generations` et `/v1/images/edits`. NVIDIA le presente comme son modele image compact et rapide. citeturn2search0turn2search6

## Vision ecran

Le tool `capture_screen` capture une vraie image JPEG. Le provider NVIDIA transforme le `tool_result` image en contenu `image_url`, puis detecte automatiquement la presence d'une image et route la requete vers le VLM.

Important : le modele vocal rapide n'est jamais utilise pour interpreter une capture. Apres une capture, Tony utilise le VLM et lui demande explicitement de decrire uniquement ce qu'il voit. Cela empeche les hallucinations du type « je vois l'ancienne erreur ».

`capture_screen` normalise aussi toujours `ecran` en entier avant de comparer les index des moniteurs.

## Generation d'image

Le tool `generer_image` est expose au registre de tools. Il utilise :

```text
black-forest-labs/flux.2-klein-4b
POST /v1/images/generations
```

L'image est sauvegardee dans :

```text
projets/<projet-actif>/output/images/
```

ou dans `generated/` si aucun projet n'est actif.

NVIDIA documente le modele et l'appel OpenAI-compatible avec `response_format: b64_json`. citeturn2search8

## Regles

1. Une demande texte simple reste sur Llama 3.1 8B.
2. Une demande sur l'ecran appelle `capture_screen`, puis le VLM.
3. Une demande « genere une image » appelle `generer_image`.
4. Le VLM ne doit pas rappeler `capture_screen` apres avoir recu la capture : il doit analyser l'image deja fournie.
5. Une erreur multimodale est transformee en reponse courte et exploitable.
6. Les capacites multimodales ne doivent pas ralentir le chemin vocal normal.

## Prochaine etape

La generation video sera ajoutee dans un outil separe, sur le meme principe, afin de ne pas melanger image, video et conversation vocale dans un seul provider.
