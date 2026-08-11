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

`project.json` contient uniquement les métadonnées du projet : nom, description, dates, statut, nœuds et relations du graphe, agent courant et tâches en cours. Les fichiers réels restent des fichiers normaux.

## Graphe

Un nœud peut représenter :

- le projet ;
- un dossier ;
- un fichier ;
- une tâche ;
- un agent ;
- une ressource externe.

Une arête représente une relation explicite : `contains`, `depends_on`, `produces`, `assigned_to`, `references`.

Le graphe doit être reconstructible à partir du workspace. Il ne doit jamais devenir une source de vérité séparée des fichiers.

## Projet actif

Tony conserve un seul projet actif à la fois pour les commandes ambiguës. Il doit annoncer le changement : « Projet Holo activé. »

Les agents reçoivent toujours le chemin absolu du workspace et un sous-ensemble explicite des permissions dont ils ont besoin.

## Contrat agent

Chaque tâche déléguée possède :

```json
{
  "id": "uuid",
  "project": "workspace",
  "agent": "elio",
  "goal": "objectif utilisateur",
  "status": "queued|running|blocked|completed|failed|cancelled",
  "created_at": "ISO-8601",
  "deadline": "ISO-8601|null",
  "max_duration_seconds": 1800,
  "result": null
}
```

## Sécurité

- Un agent ne sort jamais de son workspace sans permission explicite.
- Les opérations destructrices restent soumises au système de confirmation existant.
- Les secrets et fichiers de configuration utilisateur restent exclus du workspace agent par défaut.
- Les logs d'agents doivent être séparés des logs conversationnels.

## Roadmap d'implémentation

1. `ProjectStore` : création, ouverture, fermeture et projet actif.
2. `project.json` : métadonnées et graphe.
3. Tools Tony : `creer_projet`, `ouvrir_projet`, `fermer_projet`, `lister_projets`, `projet_actif`.
4. `AgentTask` et `AgentManager`.
5. Elio.
6. Lavanda.
7. Clover.
8. UI Holo du graphe et du panneau de tâches.
