# Mode Projet de Tony

Le Mode Projet transforme Tony en chef d'orchestre. Un projet est toujours un vrai workspace sur disque ; le graphe Holo n'est qu'une représentation visuelle de ce workspace.

## Workspace

```text
projets/
└── nom-du-projet/
    ├── .tony/
    │   └── project.json
    ├── docs/
    ├── src/
    ├── assets/
    ├── output/
    └── logs/
```

`project.json` contient les métadonnées du projet et les nœuds/arêtes du graphe. Les fichiers réels restent des fichiers normaux.

Le répertoire racine est configurable avec `projets.racine` dans `config.yaml`. Par défaut, Tony utilise `projets/` à la racine du dépôt.

## Outils Tony disponibles

Les cinq opérations de base sont maintenant de vrais tools du registre :

- `creer_projet(nom, description?)`
- `ouvrir_projet(nom)`
- `fermer_projet()`
- `lister_projets()`
- `projet_actif()`

Le projet actif est mémorisé dans `projets/.tony-active.json`, ce qui permet de le retrouver après un redémarrage. Un seul projet est actif à la fois.

## Graphe

Un nœud peut représenter le projet, un dossier, un fichier, une tâche, un agent ou une ressource externe. Une arête représente par exemple `contains`, `depends_on`, `produces`, `assigned_to` ou `references`.

Le graphe ne doit jamais devenir une source de vérité séparée des fichiers : Holo reconstruit progressivement sa vue à partir du workspace et des métadonnées `.tony`.

## Agents

Tony dispose maintenant d'un `AgentManager` asynchrone partagé :

```text
Tony
  ↓
lancer_agent
  ↓
AgentManager
  ├── Elio    → code
  ├── Lavanda → web
  └── Clover  → fichiers
```

Chaque tâche possède un identifiant, un workspace, un objectif, un statut, une progression, des dates de début/fin et un mécanisme d'annulation.

`Elio` possède déjà une première boucle autonome : il inspecte le workspace, lit/écrit des fichiers et exécute des commandes de développement autorisées, puis recommence jusqu'à satisfaction ou limite d'étapes. Il reste strictement confiné au workspace et refuse les commandes destructrices évidentes.

Lavanda et Clover sont actuellement des contrats d'agent enregistrés, prêts à recevoir respectivement le moteur web et le moteur bureautique/fichiers.

## Sécurité

- Un agent ne sort jamais de son workspace.
- Les outils destructeurs de Tony gardent leur système de confirmation.
- Elio ne peut pas utiliser `git push`, `git reset --hard` ou `git clean` via son outil terminal.
- Les secrets du dépôt ne sont pas automatiquement injectés dans le contexte d'un agent.
- Les tâches longues sont asynchrones : Tony reste disponible pendant leur exécution.

## Smoke test

```powershell
uv run python scripts/test_project_agents.py
```

Ce test ne fait aucun appel LLM et ne crée aucun fichier permanent.

## Prochaine étape

1. Brancher le graphe Holo sur `ProjectStore`.
2. Donner à Elio une meilleure mémoire de tâche et une vraie boucle test/review.
3. Brancher Lavanda sur les outils web existants.
4. Brancher Clover sur les outils fichiers/Word/PDF.
5. Ajouter les événements d'agents au HUD/Holo.
