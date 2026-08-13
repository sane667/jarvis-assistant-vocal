# Architecture multi-agents — Mode Projet

Tony est l'orchestrateur vocal. Les agents spécialisés exécutent les tâches longues en arrière-plan et utilisent le workspace du projet actif.

## État actuel

- **AgentManager** : opérationnel, asynchrone, suivi de statut/progression et annulation.
- **Elio** : première boucle autonome opérationnelle pour les tâches de code dans un workspace.
- **Lavanda** : contrat enregistré, moteur web à brancher.
- **Clover** : contrat enregistré, moteur fichiers/bureautique à brancher.
- **ProjectStore** : opérationnel et persistant.

## Agents

### Elio — code

Elio inspecte un workspace, lit et modifie les fichiers, exécute des commandes de développement autorisées, analyse leurs sorties et recommence jusqu'à un critère de réussite explicite ou une limite d'étapes.

Le modèle utilisé est celui du provider courant de Tony dans cette première version. L'architecture permet ensuite de donner à Elio un modèle dédié plus lourd, par exemple `openai/gpt-oss-120b` via NVIDIA, sans ralentir Tony.

### Lavanda — web

Responsable de la recherche internet : chercher, recouper, conserver les sources et produire un résultat exploitable par Tony ou Elio. Le contrat est enregistré ; le moteur web est la prochaine implémentation.

### Clover — fichiers

Responsable des fichiers locaux : Word, PDF, texte, dossiers et exports. Elle travaillera dans un workspace explicite et ne modifiera pas arbitrairement des fichiers hors périmètre.

## Contrat commun

Chaque tâche reçoit :

```json
{
  "id": "task-...",
  "agent": "elio|lavanda|clover",
  "objectif": "...",
  "contexte": "...",
  "workspace": "...",
  "contraintes": [],
  "critere_succes": "...",
  "deadline": null
}
```

Et expose : `queued`, `running`, `success`, `failed`, `cancelled`, ainsi qu'une progression lisible.

## Orchestrateur Tony

Tony :

1. comprend l'objectif ;
2. choisit l'agent ;
3. utilise le projet actif comme workspace par défaut ;
4. lance la tâche en arrière-plan ;
5. reste disponible ;
6. consulte le statut sur demande ;
7. peut annuler une tâche ;
8. annonce le résultat final.

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

## Sécurité

- aucun agent ne reçoit les secrets globaux sans nécessité ;
- workspace explicite pour les modifications ;
- les commandes destructrices restent protégées ;
- Elio ne peut pas sortir de son workspace ;
- Elio ne peut pas effectuer `git push`, `git reset --hard` ou `git clean` via son terminal ;
- Tony reste disponible pendant les tâches longues.

Voir `docs/mode-projet.md` pour le workspace et le graphe.
