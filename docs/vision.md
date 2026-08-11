# Vision et génération multimodale NVIDIA

Tony garde `meta/llama-3.1-8b-instruct` comme cerveau vocal rapide. Les capacités lourdes sont appelées uniquement quand la demande le justifie.

## Routing cible

| Usage | Modèle | Entrées | Sortie |
|---|---|---|---|
| Conversation + tools | `meta/llama-3.1-8b-instruct` | texte | texte / tool calls |
| Vision écran / images | `meta/llama-3.2-90b-vision-instruct` ou `nvidia/nemotron-nano-12b-v2-vl` | texte + image | texte |
| Vision/vidéo + raisonnement | `nvidia/cosmos3-nano-reasoner` | texte + image/vidéo | texte |
| Omni image/vidéo/audio | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | texte + image/vidéo/audio | texte |
| Génération / édition image | `black-forest-labs/flux.2-klein-4b` | texte + image optionnelle | image |
| Génération vidéo | `nvidia/cosmos3-nano` | texte + image optionnelle | vidéo |

NVIDIA expose actuellement des endpoints gratuits pour plusieurs de ces modèles. La disponibilité et les limites peuvent évoluer ; le code doit toujours gérer les erreurs et timeouts proprement. citeturn1search0turn1search1turn1search5

## Règles de routing

1. Ne jamais envoyer une image ou une vidéo au modèle vocal par défaut.
2. Une commande texte simple reste sur Llama 3.1 8B.
3. Une demande du type « regarde mon écran », « lis cette image » ou « analyse cette vidéo » route vers un modèle vision.
4. Une demande « crée une image » route vers FLUX.2 Klein.
5. Une demande « crée une vidéo » route vers Cosmos3 Nano.
6. Les modèles multimodaux ne prennent pas automatiquement les tools ordinaires : leur tool calling doit être validé séparément.
7. Une erreur d'un provider multimodal ne doit jamais bloquer Tony.

## Vision écran

Le tool `capture_screen` doit capturer l'écran uniquement à la demande, ne pas persister la capture par défaut et transmettre l'image au modèle vision. L'API OpenAI-compatible de Cosmos3 accepte notamment des images/vidéos sous forme de contenu multimodal ; les VLM NVIDIA documentent également les entrées image et vidéo. citeturn2search3

## Génération d'image

`black-forest-labs/flux.2-klein-4b` possède un endpoint OpenAI-compatible `/v1/images/generations` et un endpoint `/v1/images/edits`. NVIDIA documente également l'édition avec plusieurs images d'entrée. citeturn0search1turn0search3

Le futur tool `generer_image` enregistrera les résultats dans le workspace du projet actif :

```text
projets/<projet>/assets/generated/<timestamp>-<slug>.png
```

## Génération vidéo

`nvidia/cosmos3-nano` est destiné à la génération texte-vers-vidéo et image-vers-vidéo. L'API Cosmos3 distingue le générateur du reasoner : le générateur produit la vidéo, le reasoner analyse images/vidéos. citeturn2search9

## Tests obligatoires

Chaque capacité multimodale doit avoir son smoke test séparé :

- endpoint accessible ;
- modèle accepté ;
- format d'entrée correct ;
- type de sortie correct ;
- timeout ;
- rate limit ;
- message d'erreur exploitable par Tony.

Aucune de ces capacités ne doit ralentir le chemin vocal normal.
