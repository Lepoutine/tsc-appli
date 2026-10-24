# Registre maître de l'écosystème TSCF

Version 1.0 du 24/10/2026. Audit fait à partir du code de l'appli (bundle `TSC_code_2026-10-23`, commit 7f8056f),
des fichiers partagés du projet (`publication_mods/`, `tsc_2.14.27/`) et de ce dépôt.
Aucune fonctionnalité ni aucun fichier n'a été supprimé ou modifié pendant cet audit.

## Échelle de maturité (cahier des charges §5.2)

| Niveau | Sens |
|---|---|
| 1 | Maquette visuelle |
| 2 | Prototype technique |
| 3 | Fonction implémentée |
| 4 | Fonction testée (tests automatiques ou banc) |
| 5 | Validée dans ETS2 par un chauffeur |
| 6 | Documentée et livrable |

Règle : un niveau n'est attribué que s'il est prouvé (commit, test, capture en jeu). Sans preuve, on garde le niveau inférieur.

## 1. Produits et projets

| Produit | Version | Où | Niveau | Preuve / remarque |
|---|---|---|---|---|
| Appli TSC (lanceur + tablette) | 2.14.27 | `tsc_2.14.27/Appli_TSC.exe` | 3 | Compilée le 23/10, publiée par Mendy. Pas de test en jeu noté pour l'écran Mods TSC |
| Écran « Mods TSC » (install / mise à jour / retrait) | 2.14.27 | `ui/modstsc.js` | 3 | Vérifie taille et empreinte ; garde l'ancienne version dans `mod_tsc_ancien` |
| Catalogue des mods | 1 | `publication_mods/catalogue_mods.json` | 3 | 11 mods. Crédits à corriger (voir `MENTIONS_PRODUITS.md`) |
| Bétaillère Normandie | 1.5 | `publication_mods/` | 5 | Vue en jeu par Mendy le 24/10 (captures) |
| Benne Normandie Show | 1.1 | `publication_mods/` | 3 | Non testée en jeu |
| Cuir capitonné Scania R/S 2016 | 1.1 | `publication_mods/` | 3 | Non testé en jeu |
| 4 mods noms (Normand, Turque, Corse, Cobra) | 1.0.1 | `publication_mods/` | 3 | Non testés en jeu |
| Citerne TSC (modèle AkirixDesign3D acheté) | 1.7 | pack remorques | 3 | Non testée en jeu. Garder la facture du modèle |
| Citerne compat MDT Ekeri | 1.0 | release `mods` | 3 | Non testée en jeu |
| Madame Afro TSC | 1.0.0 | release `mods` | 3 | **Autorisation à prouver** |
| Mods GPS TSC (7) | 2.x | `Tete_Pilote_TSC/mods/` | 3 | Livrés avec l'appli |
| Kit templates à peindre | — | `kit_templates/` | 2 | `construire_mod.py` à lancer sur le PC |
| Vidéo bêta officielle | — | `video_beta/` | 6 | Publiée le 23/10 |
| TSC Performance Lab | 0.1.0 | `perf_lab/` (ce dépôt) | 4 | 43 tests pwsh ; essai sur le Shadow en cours |
| TSC MapForge, Field Inspector, TSC Explore | — | — | 0 | Pas commencés |
| Contrôle des accès (pseudos, invité, abonnements) | — | — | 0 | Demandé le 23/10, à présenter avant de coder |

## 2. Fonctions de simulation et d'interaction déjà commencées (priorité n°4)

| Fonction | Fichiers | Niveau | Ce qui existe | Ce qui manque |
|---|---|---|---|---|
| Pilote de tête (regards carrefours, stops, ronds-points, circulation) | `ui/engine.js` v3, `ui/worker.js`, `ui/roadnet.js`, `ui/pilotools.js`, `Pilote_Tete_TSC.ps1` | 4 | 14 scénarios (`scen.js`), conduite simulée (`drive2.js`), rejeu de trajets (`rejeu.js`), sortie OpenTrack UDP 4242 | Vérification sur un trajet enregistré en jeu (~1,3 s carrefours, ~2 s stops) |
| Chronotachygraphe RP + tickets | `ui/tacho.js`, `ui/tickets.js`, `tests_pilote/tacho_semaine.ps1` | 3 | Activités auto (conduite / travail / dispo / repos), tickets envoyés sur Discord | Validation en jeu notée |
| Mode à pied | `Pilote_Tete_TSC.ps1` (bloc TM Real Walk), `ui/comps.js`, sons de portière | 3 | Caméra libre du jeu + import de TM Real Walk téléchargé par le joueur, avec sauvegarde | C'est le plugin d'Izuan Bakar qui fait la marche : TSCF n'a pas de moteur de déplacement propre |
| Bip de recul | `ui/recul.js` | 3 | Accélère près du point de livraison du jeu | Le jeu ne donne pas la distance des obstacles |
| Échappement V8 synthétisé | `ui/echap*.js` | 3 | Synthèse en direct depuis la télémétrie | — |
| GPS TSC 2.0 | `ui/gps.js`, mods GPS | 3 | Thèmes, couleurs de carte | — |
| Atelier skins | `ui/atelier.js` | 2 | Lecture / écriture DDS, éditeur 2D, aperçu 3D remorque | Export d'un mod complet depuis l'appli |
| Chaîne de production des mods (cloud) | `tests_pilote/cuir`, `betaillere`, `benne`, `citerne`, `kit`, `hashfs` | 4 | Lecture HashFS, PMG/PMD, DDS, cuisson de textures, ajout de pièces décal et de points d'accroche | Base possible du futur TSCF Creation Studio (§3) |
| Tablette mobile | `ui/m.html`, `Telecharger_CF.ps1` | 3 | Tunnel cloudflared officiel | — |
| Optimiseur / Performance Lab | `ui/opti.js`, `perf_lab/` | 4 | Mesure PresentMon, profils réversibles | — |

Points d'intérêt, bulles d'information, choix du bâtiment de chargement (§2.3-2.4) : **rien n'existe encore**.
Aucun mécanisme d'intégration n'est identifié à ce jour pour faire marcher le personnage sans TM Real Walk ; à étudier
avant toute annonce (§2.2). Règles en place : ne pas copier le code ni les ressources de TM Real Walk, ni patcher ou
renommer sa DLL.

## 3. Points d'attention relevés pendant l'audit

1. **Secret exposé** : une adresse de webhook Discord complète (avec son jeton) est écrite en clair dans
   `Pilote_Tete_TSC.ps1` (variable `ticketHookTsc`), donc présente dans l'exe distribué. N'importe quel testeur peut
   l'extraire et poster dans le salon. À faire : régénérer le webhook côté Discord, puis le faire passer par le site HUB
   ou un relais au lieu de l'embarquer. Le jeton n'est recopié dans aucun document du registre.
2. **Contenus de l'appli** : visuels d'accueil, musique d'intro et `TSC_Photoreal.fx` confirmés créations TSCF le 24/10.
   Reste : `carte/roads.json` (« Grand Utopia ») vient de la carte de MyGodness et est livré avec l'appli sans accord connu.
3. **Crédits du catalogue** : plusieurs mods portent « Créations de Poutine – propriété de Truck So Clean France » alors
   qu'ils contiennent des modèles SCS modifiés. Correction proposée dans `MENTIONS_PRODUITS.md`.
4. **Autorisations non archivées** : Madame Afro (modèle gratuit, auteur inconnu) et templates MDT. Citerne : modèle acheté (facture à garder).
   Le catalogue dit « avec autorisation » mais aucune preuve n'est conservée.
5. **Polices chargées depuis Google** : la tablette contacte fonts.googleapis.com (adresse IP du joueur transmise).
6. **Mentions de licence incohérentes** entre `TSC_Photoreal.fx` (« libre d'utilisation pour les membres TSC ») et le
   reste de l'appli (« Tous droits réservés »).
7. **Plugin scs-telemetry.dll** : lié à 60 des 140 plantages ETS2 relevés par Performance Lab (23/10).
8. Le dépôt GitHub `tsc-appli` ne contient que les releases, Performance Lab et ce registre ; le code de l'appli est
   dans les bundles sur le PC (`Reprise_Code`). L'archive des sources existe donc, mais en un seul endroit.

## 4. Fichiers préservés

Rien n'a été supprimé. Versions précédentes conservées : `publication_mods/anciennes_versions/` (bétaillère 1.2 à 1.4,
benne 1.0.1, cuir 1.0), bundles `TSC_code_2.14.27` et `TSC_code_2026-10-23`.
