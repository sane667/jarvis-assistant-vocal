# Vision et génération multimodale NVIDIA

Tony garde `meta/llama-3.1-8b-instruct` comme cerveau vocal rapide. Les modèles multimodaux sont appelés uniquement lorsqu'une requête le justifie.

## Routing cible

| Usage | Modèle | Entrées | Sortie |
|---|---|---|---|
| Conversation + tools | `meta/llama-3.1-8b-instruct` | texte | texte / tool calls |
| Vision + documents + vidéo | `nvidia/nemotron-nano-12b-v2-vl` | texte, image, vidéo | texte |
| Vision/vidéo avec raisonnement | `nvidia/cosmos3-nano-reasoner` | texte, image, MP4 | texte |
| Génération / édition image | `black-forest-labs/flux.2-klein-4b` | texte, image | image |
| Génération vidéo | `nvidia/cosmos3-nano` | texte, image | MP4 |

Ces endpoints sont documentés par NVIDIA comme disponibles gratuitement pour l'usage API de développement, avec les limites et conditions du service NVIDIA. Les modèles peuvent être modifiés, limités ou retirés : le code doit donc traiter l'indisponibilité proprement.

## Règles de routing

1. Ne jamais envoyer une image ou une vidéo au modèle vocal par défaut.
2. Une commande texte simple reste sur Llama 3.1 8B.
3. Une demande du type « regarde mon écran », « lis cette image » ou « analyse cette vidéo » route vers un modèle vision.
4. Une demande « crée une image » route vers FLUX.
5. Une demande « crée une vidéo » route vers Cosmos3 Nano.
6. Les modèles multimodaux ne doivent pas être utilisés pour les tools ordinaires sauf si leur capacité de tool calling est explicitement validée par un smoke test.
7. Une erreur d'un provider multimodal ne doit jamais bloquer Tony : retour gracieux vers Tony texte ou message d'indisponibilité.

## Vision écran

Le futur tool `voir_ecran` doit :

- capturer l'écran uniquement à la demande ;
- encoder l'image sans persister la capture par défaut ;
- transmettre une image + prompt au modèle vision ;
- retourner uniquement le texte utile à Tony ;
- ne jamais envoyer automatiquement l'écran à NVIDIA en arrière-plan.

## Génération d'image

Le futur tool `generer_image` doit enregistrer les résultats dans le workspace du projet actif, par exemple :

```text
projets/<projet>/assets/generated/<timestamp>-<slug>.png
```

Il doit retourner à Tony le chemin du fichier et une description courte. Le modèle n'a pas besoin d'être dans la boucle conversationnelle principale.

## Génération vidéo

Le futur tool `generer_video` utilise `nvidia/cosmos3-nano` et enregistre le MP4 dans le workspace actif. Les paramètres de durée, FPS, résolution et seed seront exposés progressivement après validation de l'endpoint.

## Important

Les capacités multimodales de NVIDIA ne sont pas toutes exposées via le même format API. Avant intégration définitive, chaque modèle doit avoir son propre smoke test : texte/image/vidéo selon le cas, vérification du type de réponse, gestion du rate limit et timeout.