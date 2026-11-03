# Base de connaissances TSC : FMOD et Blender

C'est la référence que Claude consulte avant chaque création, dans Sound Forge (sons) et dans l'atelier Spartan Studio (Blender et skins). Elle est demandée par Mendy le 2026-11-03.

## Règles

- Chaque fiche donne ses sources (lien officiel et date de lecture) et un statut :
  - **[vérifié]** : lu dans la documentation officielle, ou constaté dans les fichiers du jeu ou sur le PC.
  - **[à vérifier]** : déduit ou venant d'une source non officielle. Ne pas s'en servir pour un joueur avant un test.
- On résume avec nos propres mots, sans recopier les documentations protégées. Les données sous licence libre (MIT...) peuvent être copiées avec leur licence.
- Après chaque test en jeu, on met à jour la fiche concernée et son statut.
- `index.json` liste les fiches avec leurs mots-clés. C'est ce fichier que l'assistant de l'appli charge pour trouver la bonne fiche.

## Contenu

- `fmod/01_scripting_fmod_studio.md` : piloter FMOD Studio par script (port 3663, fmodstudiocl, fonctions, pièges).
- `fmod/02_sons_camion_scs.md` : événements, paramètres et bus des sons de camion dans ETS2/ATS.
- `fmod/03_procedure_mod_son_scs.md` : procédure officielle d'un mod de son, modèles et exemples à télécharger.
- `fmod/04_recette_moteur_sound_forge.md` : notre recette pour créer l'événement moteur par script (phase 3).
- `fmod/05_exemple_officiel_peterbilt_579.md` : l'exemple moteur officiel SCS décrit en chiffres (couches, plages, courbes de charge et de frein).
- `fmod/reference/fmod_studio_2.03_api.json` : toutes les fonctions de l'API de script (MIT).
- `blender/01_scs_blender_tools.md` : SCS Blender Tools (versions, plan de la doc, matières, looks).
- `blender/02_conversion_et_skins.md` : Conversion Tools, `accessory_paint_job_data`, fichiers d'une peinture.
- `outils/outils_et_ressources_libres.md` : outils existants intégrables et ressources libres, avec leurs licences.
- Voir aussi `../docs/structure_son_ets2_1.61.md` (relevé sur le jeu) et `../docs/techniques_sound_forge.md` (guide de métier).

## À compléter

- Pages SCS : TruckTransmission, TruckChassis, TruckCabin, Tires, SoundWorld, Variant/Part/Locators, Export, Supported_shaders.
- API Python de Blender 3.6 pour piloter Blender en arrière-plan (`blender -b -P script.py`).

Une copie de travail existe aussi sur le PC de Mendy, dans `Outils admin\soundforge\base_savoir\`, avec `donnees\fmod_ets2_1.61.json` (GUID des bus master, paramètres globaux, événements de 12 banques du jeu). Ce dépôt reste la version de référence.
