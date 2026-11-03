# TSC Intelligence

Socle commun des 10 experts IA de l'écosystème Truck So Clean France (directive maître de Mendy, 03/11/2026).
Voir `PLAN_INTEGRATION.md` pour l'audit et le plan.

| Dossier | Rôle |
|---|---|
| `agents/agents.json` | Les 10 experts : spécialité, niveau prouvé (0-6), outils existants avec leur chemin, fiches, lacunes, règle avant d'agir |
| `connaissances/index.json` | Base de connaissances commune (sourcée, versionnée, datée) ; joint la base Sound Forge sans la recopier |
| `memoire/entrees.jsonl` | Mémoire commune et par expert : décisions, réglages, erreurs corrigées, tests, avec preuve |
| `transferts/` | Fiches de passage entre experts (fichiers, versions, hypothèses, preuves) |
| `evaluation/taches.json` | Banc d'évaluation : une tâche réelle par expert |
| `outils/tsc_ia.py` | Outil commun (Python 3 seul) |

```
python3 intelligence/outils/tsc_ia.py demarrer mods          # relire l'état avant d'agir
python3 intelligence/outils/tsc_ia.py chercher zip scs       # fiches + mémoire
python3 intelligence/outils/tsc_ia.py noter --agent mods --type correction --resume "..." --preuve "..."
python3 intelligence/outils/tsc_ia.py transfert --de textures --vers graphics --objet "..." --fichiers f.dds --preuve "..."
python3 intelligence/outils/tsc_ia.py verifier --projet /mnt/project-files --code <clone du bundle>
python3 -m unittest discover -s intelligence/tests
```

Règles : rien d'inventé (pas de source, pas de fiche) ; une entrée de mémoire sans preuve est refusée ; un expert n'est dit opérationnel qu'après sa tâche du banc réussie ; l'outil ne modifie jamais le jeu, un mod ou l'appli.
