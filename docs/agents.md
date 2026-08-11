# Architecture multi-agents — Mode Projet

Objectif : faire de Tony l'orchestrateur et de trois agents spécialisés des exécutants autonomes, sans casser le moteur vocal ni le registre d'outils actuel.

## Agents

### Elio — code

Responsable des tâches de développement longues : inspecter un dépôt, modifier le code, lancer les tests, analyser les erreurs, corriger et recommencer jusqu'à un critère de réussite explicite.

Le modèle de raisonnement peut être plus lourd que celui de Tony. Il ne doit pas bloquer la boucle vocale principale. Un candidat pour les tâches longues est `openai/gpt-oss-120b` via NVIDIA, à valider selon disponibilité et quotas.

### Lavanda — web

Responsable de la recherche internet : chercher, recouper, extraire les faits, conserver les sources et produire un résultat exploitable par Tony ou Elio.

Elle doit distinguer clairement faits, hypothèses et résultats non vérifiés.

### Clover — fichiers

Responsable des fichiers locaux : Word, PDF, texte, dossiers et exports. Elle travaille dans un espace de travail explicite et ne doit pas modifier un fichier arbitrairement hors du périmètre demandé.

## Contrat commun d'un agent

Chaque agent reçoit une tâche structurée :

```json
{
  "id": "task-...",
  "agent": "elio|lavanda|clover",
  "objectif": "...",
  "contexte": "...",
  "workspace": "...",
  "contraintes": [],
  "critere_succes": "...",
  "deadline": null,
  "max_duration_seconds": 1800
}
```

Et produit des événements structurés :

```json
{
  "task_id": "task-...",
  "status": "queued|running|waiting|verifying|success|failed|cancelled",
  "message": "...",
  "artifacts": [],
  "tests": [],
  "next_action": "..."
}
```

## Orchestrateur Tony

Tony ne fait pas lui-même une tâche longue. Il :

1. comprend l'objectif ;
2. choisit l'agent ;
3. crée ou ouvre le workspace ;
4. lance l'agent en arrière-plan ;
5. annonce brièvement le démarrage ;
6. reste disponible pour les autres demandes ;
7. expose l'état et le résultat sur demande ;
8. demande une confirmation avant toute action sensible ou irréversible.

Les tâches sont exécutées hors de la boucle vocale. Un agent peut donc travailler pendant plusieurs minutes pendant que Tony continue à répondre normalement.

```text
                     TONY
                       |
                 Agent Manager
                       |
          +------------+------------+
          |            |            |
        ELIO        LAVANDA       CLOVER
         code          web        fichiers
          |            |            |
          +------------+------------+
                       |
                  Project Store
                       |
             dossiers réels sur disque
```

## Mode Projet

Un projet est un dossier réel dans un répertoire racine configuré. Le graphe visuel du Holo est une représentation de ces projets, pas une seconde base de données : chaque nœud pointe vers un dossier existant.

Les agents doivent travailler dans le dossier du projet sélectionné et conserver leurs artefacts, logs et rapports dans un sous-dossier dédié.

Voir `docs/mode-projet.md` pour le format du workspace et du graphe.

## Règles de sécurité

- aucun agent ne reçoit les secrets globaux sans nécessité ;
- workspace explicite pour toute modification de fichiers ;
- commandes potentiellement destructrices soumises à confirmation ;
- Elio doit tester avant de déclarer une tâche de code réussie ;
- Lavanda conserve les URL des sources utilisées ;
- Clover conserve les fichiers produits et leur chemin exact ;
- Tony reste disponible pendant qu'un agent travaille.
