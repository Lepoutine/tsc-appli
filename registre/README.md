# Registre TSCF

Registre maître et registre des créations et des crédits de l'écosystème Truck So Clean France (version 1.0, 24/10/2026).

| Fichier | Rôle |
|---|---|
| `REGISTRE_MAITRE.md` | Audit : produits, versions, niveau de maturité, fonctions de simulation déjà commencées, points d'attention |
| `registre_creations.json` | **Source** du registre des ressources (seul fichier à modifier) |
| `REGISTRE_CREATIONS.md` | Vue lisible, générée |
| `CREDITS.txt` | Crédits des composants, générés, à joindre à l'appli et aux mods |
| `MENTIONS_PRODUITS.md` | Mentions légales et crédits produit par produit |
| `PROTECTION_ET_SIGNALEMENT.md` | Règles d'intégration, mesures de protection, questions pour un juriste, procédure de signalement |
| `preuves/` | Captures des licences et des accords d'auteurs (à remplir) |

Mettre à jour : modifier `registre_creations.json`, puis `python3 registre/generer.py`.
La vérification seule (`python3 registre/generer.py --verifier`) échoue si un champ manque, si une valeur est inconnue ou
si une ressource à l'origine non établie est marquée distribuable.
