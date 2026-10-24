# TSCF Spartan Studio : audit et architecture (phase 1)

## 1. Ce qui existe déjà et qu'on réutilise

| Existant (code TSC, bundle 2.14.29) | Ce qu'il fait | Rôle dans le Studio |
|---|---|---|
| `tests_pilote/cuir/scs_model.py`, `pmg.py` | Lit et réécrit les modèles SCS (.pmg v21, .pmd) à l'octet près | Base du convertisseur `outils/pmg_vers_glb.py` (modèles réels dans l'aperçu) |
| `tests_pilote/flotte/cuisson.py`, `cuisson_uv.py`, `benne/raster.py` | « Cuit » la position 3D de chaque texel dans l'UV de peinture | Export phase 6 : passer de la livrée en mètres à la vraie texture de peinture du véhicule |
| `tests_pilote/flotte/lion_kit.py`, `tscf_kit.py` (PC) | Éléments de livrée en mètres (toile s/y, noir laqué, or, rouge, lion, couronnes) | Même repère que le Studio : les éléments s'échangent sans conversion |
| `scania_s_mod.py`, `volvo_fh_mod.py`, `ekeri_mod.py`, `scania_r_tscf_mod.py`, `build_citerne_tscf.py` (PC) | Construisent les .scs (paint_job, accessoires, textures) | Export phase 6 : on leur passe la texture produite par le Studio |
| `tests_pilote/flotte/pack.py` + catalogue | Packs par catégorie, refuse les conflits | Livraison des livrées validées dans le pack « Peintures camions » |
| `Tete_Pilote_TSC/ui/atelier.js` (tablette) | Atelier skins 2D : lecture/écriture DDS BC1/BC3/32 bits, aperçu 3D boîte | Encodeur DDS repris tel quel en phase 6 ; l'atelier tablette reste en place |
| `tests_pilote/hashfs/hashfs2.py` | Lit les archives SCS HashFS v2 (base.scs, def.scs) | Extraire les modèles de camions du jeu sur le PC pour les convertir |
| Registre TSCF (`registre/`) | Crédits et licences | Chaque ressource du Studio y passe avant diffusion |

Rien de tout cela n'est modifié : le Studio est un dossier à part (`studio/`).

## 2. Choix techniques (étudiés avant de coder)

| Besoin | Choix | Pourquoi | Écarté |
|---|---|---|---|
| Visualisation 3D | **Three.js 0.170** (fourni dans `vendor/`, hors ligne) | Matières physiques (vernis, métal, rugosité), ombres, caméra orbitale, glTF ; déjà utilisé par l'atelier tablette | Babylon.js (plus lourd, rien de plus utile ici), moteur maison (trop long) |
| Modèles réels | **Conversion .pmg → .glb** par `outils/pmg_vers_glb.py` (sur le PC, depuis le jeu ou le mod) | Aperçu fidèle au modèle ETS2 ciblé ; les modèles SCS ne sont jamais publiés | Modèles 3D génériques du web (pas le vrai véhicule) |
| Édition des textures | **Livrée en calques, en mètres** (s depuis l'avant, y depuis le sol), peinte sur une planche Canvas 2D (couleur + matière) puis projetée sur la carrosserie | Chaque élément reste modifiable seul ; les deux côtés se lisent depuis l'extérieur, jamais en miroir (règle TSCF) ; même repère que `tscf_kit.py` | Peindre directement dans l'UV (illisible pour un humain, différent pour chaque camion) |
| Export | Phase 6 : cuisson de la planche dans l'UV réelle de peinture (cuisson.py ou passe GPU équivalente), DDS, puis builders de mod existants | Ce qui est vu est ce qui est exporté ; gabarits réellement compatibles | |
| Reconnaissance vocale FR | **Microsoft Edge (Web Speech API)** : le Studio s'ouvre dans Edge en mode application | Gratuit, français correct, sans installation. WebView2 (la tablette) ne fournit pas la reconnaissance vocale, d'où Edge | Vosk hors ligne (secours possible, modèle FR 41 Mo, moins précis), Whisper local (lourd sur le PC de jeu) |
| Synthèse vocale | **speechSynthesis d'Edge** (voix françaises naturelles « Denise », « Henri ») | Naturelle, gratuite | |
| Assistant conversationnel | **Claude (API Anthropic) avec des outils** qui ne peuvent agir que sur le projet : `modifier_element`, `ajouter_element`, `annuler`, `creer_variantes`, `comparer`, `valider_version`… Les commandes simples (« annule », « montre l'autre côté ») sont reconnues sur place, sans réseau | Comprend le contexte, reformule les demandes ambiguës ; les modifications passent toutes par l'historique | Règles seules (ne comprend pas les demandes libres) |
| Versions | Projet = fichier JSON (véhicules, éléments, versions) ; historique par opérations, sauvegarde automatique sur le PC par le petit serveur local | Annuler/rétablir illimité, versions nommées, duplication, restauration | |
| Lancement | `Lancer_Studio.bat` → `serveur.ps1` (127.0.0.1 seulement) → Edge | Pas d'installation, rien d'exposé sur le réseau | |

## 3. Repères

- Repère SCS gardé partout : x à droite, y en haut, avant vers −z, mètres.
- Remorque : origine au sol ; le repère `hook` du modèle donne le pivot. Camion : la sellette (`fifth_wheel`, sinon 0 ; 0,97 ; 0) se place sous le pivot.
- Planche de livrée par véhicule : côté gauche, côté droit, dessus, avant, arrière (170 px/m, 4096 px maximum).
  - Côté gauche : l'avant est à gauche de la planche ; côté droit : l'avant est à droite. Un élément placé à « s mètres de l'avant » tombe au même endroit des deux côtés ; les textes ne sont jamais retournés ; les formes (vagues, lion) sont retournées pour garder leur sens vers l'avant.

## 4. Interface

- En-tête : emblème TSCF, « TSCF Spartan Studio », devise en Kaushan Script, nom du projet et phase.
- Gauche : ensemble (camion, remorque), affichage (ensemble, écartés, camion seul, remorque seule), éclairage (studio photo, plein jour, coucher de soleil, nuit), puis en phase 3 la liste des calques et leurs réglages.
- Centre : vue 3D libre (glisser, molette, clic droit, double-clic = zoom sur le détail), barre de vues (3/4 avant, avant, gauche, droite, arrière, 3/4 arrière, dessus, capture), bandeau orange tant qu'un modèle provisoire est affiché.
- Droite : assistant vocal (phase 4), historique et versions (phase 5), export (phase 6, seulement après validation).
- Couleurs : noir profond `#0a0a0c`, rouge Spartiate `#b3121b`, or `#c9a24a` en dégradé métal ; polices Saira (titres), Rajdhani (interface), Kaushan Script (devise). Aucune capitale espacée dans les livrées (règle de Mendy) ; elles ne servent qu'aux titres de l'interface.

## 5. Plan

| Phase | Contenu | État |
|---|---|---|
| 1 | Audit, choix, interface | Fait (ce document) |
| 2 | Camion + remorque 3D, rotation, zoom, vues, éclairages, livrée d'essai | Fait, testé dans Chromium (voir RAPPORT_TESTS.md). Camion encore provisoire |
| 3 | Livrée TSCF éditable : calques (fond, vagues, lion, textes, liserés), sélection à la souris, poignées, continuité camion/remorque | À faire |
| 4 | Assistant vocal (Edge + Claude), modifications en direct | À faire |
| 5 | Historique, versions, comparaison, sauvegarde automatique | À faire |
| 6 | Validation explicite, cuisson UV, DDS, mod via les builders TSC, essai en jeu par Mendy | À faire |
| 7 | Volvo, Renault, DAF, MDT, Wielton, grandes remorques | À faire |
