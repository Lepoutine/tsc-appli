# TSC Intelligence : plan d'intégration des 10 experts

Version 1 du 03/11/2026. Réponse aux points 11 et 12 de la directive maître de Mendy et à son extension (IA 9 et IA 10).
Audit fait en lecture seule sur : le code de l'appli 2.14.54 (`code_tsc/TSC_code_2026-11-03c.bundle`), ce dépôt, le dossier partagé du projet et la mémoire du projet. Rien de l'existant n'a été modifié.

## 0. Ce qu'est un « expert TSC », honnêtement

Un expert TSC n'est pas un nom posé sur une IA généraliste. C'est l'assemblage, pour un métier, de :

1. un modèle de raisonnement (Claude, utilisé sous la licence de son API) ;
2. **ses outils TSC réels** (scripts, plugins, analyseurs déjà écrits et testés) ;
3. **sa base de connaissances sourcée** (source, version, date de vérification, statut) ;
4. **sa mémoire** des décisions, réglages, erreurs corrigées et tests ;
5. **ses tests** et un banc d'évaluation sur des données réelles ;
6. **ses permissions** (ce qu'il fait seul, ce qui demande l'accord de Mendy).

Les points 2 à 6 sont la technologie propre à TSC. On n'entraîne un modèle à nous (poids) que lorsqu'un gain est mesuré : c'est le cas des textures (TSC Textures IA), pas encore ailleurs.

## 1. Architecture actuelle vérifiée

| Bloc | Où | État prouvé |
|---|---|---|
| Appli TSC (lanceur Go + tablette PowerShell/WebView2 + écrans JS) | code 2.14.54 | construite et publiée |
| Pilote de tête + plugin télémétrie C++ (SDK SCS 1.18) | `Tete_Pilote_TSC`, `plugin_src` | utilisé en jeu depuis le 16/10, 5 203 décisions journalisées |
| Mémoire TSC (décisions du pilote envoyées au service) | `ui/memoire.js`, worker | 1er envoi réussi le 02/11 |
| Service TSC (worker Cloudflare : accès, paiement, tickets, téléphone, mémoire) | `serveur_acces/worker.js` | en service |
| Écran de bord TSC (plugin D3D11 + pages) | `plugin_src/ecran`, `plugin/ecran` | validé en jeu (2.14.53) |
| TSC Graphics (plugin DX11 tsc-graphics 0.1 à 0.14) + audit du pipeline | `project-files/tsc_graphics` | posé dans TSCF_Lab, rendu pas encore validé |
| TSC Textures IA (Real-ESRGAN + grain + détecteur + encodeur BC) | PC `Outils admin\tsc_graphics\ia_textures` | lot 1 en cours |
| TSC Performance Lab (42/42 tests sur le Shadow) + mode zones | `perf_lab`, `Tete_Pilote_TSC/perf_lab` | testé |
| Constructeurs de mods (bétaillère, benne, citerne, cuir, MDT, lecteur HashFS) | `tests_pilote` | mods vus en jeu |
| Écrans Mods TSC et Console | `ui/modstsc.js`, `ui/console.js` | en service |
| Sound Forge (interface, générateur, analyseur ETS2 0.4, base FMOD/Blender) | `sound_forge` | aucun son encore validé en jeu |
| Spartan Studio (atelier 3D Three.js, vrais modèles SCS) | `ui/studio` | dans l'appli depuis 2.14.30 |
| Registre maître + registre des créations (vérificateur) | `registre` | tenu |
| Mémoire du projet (fichiers de mémoire des sessions Claude) | mémoire du projet | tenue à chaque session |

Détail par expert, avec chaque chemin : `agents/agents.json` (vérifié par `outils/tsc_ia.py verifier`, 0 chemin manquant dans le code et le dossier projet).

## 2. Les IA déjà présentes

Il n'y a aujourd'hui **aucune IA qui tourne seule chez le joueur**, sauf le Pilote de tête (règles + routes apprises, pas un réseau de neurones) et TSC Textures IA (en cours). Le reste du travail « intelligent » est fait par Claude pendant les sessions, avec les outils ci-dessus. L'assistant Claude dans Forge et dans l'atelier est prévu (clé API gardée dans le worker) mais pas branché.

## 3. Les 10 domaines et leur niveau réel (échelle 0-6 du registre)

| # | Expert | Niveau | Ce qui manque surtout |
|---|---|---|---|
| 1 | Neural Graphics | 3 | jeu de captures fixe pour comparer chaque version |
| 2 | Textures | 3 | jeu de test fixe, contrôle UV automatique |
| 3 | Performance | 4 | mesure de frametime fiable derrière ReShade |
| 4 | Mod Engineering | 4 | analyseur automatique du game.log, contrôle .scs avant livraison |
| 5 | Sound Engineering (acoustique) | 2 | module de mesure des sons (annoncé, pas codé) |
| 6 | Driving Intelligence | 5 | rejouer `traces.json` à chaque version |
| 7 | Software Engineering | 5 | suite de tests unique avant chaque version |
| 8 | Knowledge & Quality | 3 | liste de contrôle de livraison par type |
| 9 | Atelier Spartan / Blender | 3 | Blender piloté par script, contrôles UV/échelle/origine |
| 10 | FMOD / Sound Forge | 3 | chaîne fmodstudiocl → GUID réels → .soundref → .scs testée |

Partage des rôles entre 5 et 10, pour ne rien faire en double : **5** sait quoi entendre (mesure, boucles, couches, EQ, intérieur/extérieur) ; **10** fabrique le mod (projet FMOD, banques, GUID, définitions, .scs). Aucun expert n'est déclaré pleinement opérationnel tant que sa tâche du banc (`evaluation/taches.json`) n'est pas réussie.

## 4. Bases de connaissances nécessaires

Règle : une fiche = une source, une version, une date de vérification, un domaine, un statut (`vérifié`, `vérifié partiel`, `à vérifier`, `conçu`). Pas de source, pas de fiche. On résume avec nos mots, on ne recopie pas les docs protégées.

Existant : 12 fiches FMOD/Blender (Sound Forge) + 8 fiches TSC (pipeline de rendu, Shadow, piège zip .scs, noms SII 11 caractères, règles de mods, SDK télémétrie, build, échelle de maturité). Elles sont réunies dans `connaissances/index.json` sans être recopiées.

## 5. Sources documentaires à intégrer (par priorité)

| Expert | Sources officielles |
|---|---|
| Mods, Atelier, Forge | SCS Modding Wiki (formats SII/SUI, .mat, .tobj, PMG/PMD, accessoires, sons), SCS Blender Tools 2.4.1, Conversion Tools |
| Forge | FMOD Studio 2.03 (manuel, API de script, fmodstudiocl), template SCS 1.43 |
| Atelier | API Python de Blender 3.6 (bpy, mode arrière-plan) |
| Graphics, Performance | Direct3D 11 et HLSL (Microsoft Learn), PresentMon, RenderDoc |
| Textures | formats DDS/BC1-7 (Microsoft), licences des modèles (OpenModelDB, Real-ESRGAN BSD-3) |
| Conduite | SDK télémétrie SCS (déjà inclus), règles tachygraphe UE (règlement 561/2006) |
| Logiciel | WebView2, PowerShell 5.1/7, Go, Cloudflare Workers |

## 6. Outils métier propres à chaque expert

Listés et vérifiés dans `agents/agents.json`. Outils partagés (un seul propriétaire, réutilisé par les autres) :

- **Analyse ETS2** (Steam, jeu, mods, profils, archives, FMOD) : `sound_forge/analyse/Analyser_ETS2.ps1`, déjà générique. Propriétaire : Mod Engineering. Réutilisé par Forge, Atelier, Textures.
- **Lecture des archives SCS** : `tests_pilote/hashfs/hashfs2.py`.
- **Construction et contrôle des .scs** : Mod Engineering seulement (Atelier et Forge lui passent leurs fichiers).
- **Mesure de coût** : Performance. **Validation** : Qualité.

## 7. Mémoire commune

`memoire/entrees.jsonl` : une ligne par fait, avec agent (`commun` ou l'expert), type (décision, paramètre, problème, correction, test, limite, amélioration, projet), preuve, fichiers, version, statut. 33 entrées de départ, toutes reprises de faits déjà prouvés.

Au démarrage, chaque expert lance `tsc_ia.py demarrer <expert>` : il relit ses outils, ses fiches, la mémoire commune et la sienne, et ses lacunes, **avant** de proposer quoi que ce soit. Avant de poser une question à Mendy : `tsc_ia.py chercher <mots>`, puis les fichiers autorisés, puis la doc officielle.

## 8. Échanges entre experts

`tsc_ia.py transfert` écrit une fiche de passage (`transferts/`) : de qui, vers qui, objet, fichiers avec taille et date, hypothèses, preuve, statut. L'intelligence centrale (le coordinateur du projet) enchaîne les passages et fait vérifier par Qualité avant de présenter **un seul livrable** à Mendy.

Exemple : Textures (matériau route) → Neural Graphics (rendu) → Performance (coût en ms) → Mod Engineering (intégration .scs) → Qualité (contrôle) → Mendy.

## 9. Apprentissage et mise à jour, trois mécanismes séparés

- **Mémoire** : un incident résolu et vérifié devient une entrée (`noter`), relue au démarrage.
- **Mise à jour documentaire** : une nouvelle info fiable devient ou modifie une fiche, avec sa date ; à chaque nouvelle version d'ETS2, de FMOD ou d'un outil, on revérifie les fiches de cette version.
- **Entraînement de modèles** : seulement TSC Textures IA pour l'instant ; une nouvelle version n'est gardée que si elle bat la précédente sur un jeu de test fixe (sinon retour arrière).

## 10. Tests d'autonomie et de fiabilité

`evaluation/taches.json` : une tâche réelle par expert, avec les mesures demandées (résolu, interventions de Mendy, diagnostic juste, erreurs introduites, connaissances réutilisées, coût). `tests/test_tsc_ia.py` : 10 tests de l'outil commun (tous OK).

## Ordre de développement (dépendances)

1. **Fait** : socle commun (registre des experts, mémoire, base jointe, vérificateur, banc, tests).
2. **Mod Engineering** : analyseur automatique du game.log (erreur → mod → fichier) et contrôle des .scs avant livraison (attributs zip, noms SII, chemins). Faisable dans le cloud, sans risque, testable sur les mods déjà validés.
3. **Analyse ETS2 commune** : sortir la partie générique d'`Analyser_ETS2.ps1` en module partagé (à lancer sur le PC, lecture seule).
4. **Forge** : compiler l'exemple Peterbilt 579 par fmodstudiocl, GUID réels, mod .scs contrôlé par l'étape 2 (sur le PC).
5. **Atelier** : piloter Blender 3.6 en arrière-plan sur une copie, contrôles UV/échelle/origine, export par l'étape 2.
6. **Textures et Graphics** : jeux de test fixes (suite du fil TSC Graphics, sans toucher à ses fichiers).
7. **Conduite et Logiciel** : rejeu de `traces.json` et suite de tests avant chaque version.
8. **Branchement dans l'appli** (assistant Claude dans Forge et l'atelier via le worker) : après les abonnements, car cela engage des coûts d'API.

## Décisions qui reviennent à Mendy

- Le branchement de l'assistant Claude dans l'appli (étape 8) : il coûte de l'argent à chaque utilisation.
- Où ranger les sources de l'appli (aujourd'hui des bundles) : dépôt privé ou non.
