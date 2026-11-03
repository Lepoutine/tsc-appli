# SCS Blender Tools (modèles 3D pour ETS2 / ATS)

Statut : [vérifié] sur le wiki SCS (lu le 2026-11-03), et sur le PC de Mendy pour les versions.
Sources : https://modding.scssoft.com/wiki/Documentation/Tools/SCS_Blender_Tools et ses sous-pages (Look_system, Materials), https://github.com/SCSSoftware/BlenderTools (GPL-2.0).

## Versions (PC de Mendy, 2026-11-03)

- Blender 3.6.23 avec SCS Blender Tools **2.4.1**. Son `bl_info` affiche (2, 4, "aeadde03").
- Il faut rester sur Blender 3.6 LTS : sous Blender 5.x, on obtient « No module named 'bgl' ».
- Le fichier `config.txt` de l'add-on contient les réglages de l'utilisateur. Il faut le garder à chaque mise à jour.

## Plan de la documentation officielle (base https://modding.scssoft.com/wiki/)

- **Premiers pas** :
  - Installation, Terminology_and_basics, Download et Intended_workflow, sous `Documentation/Tools/SCS_Blender_Tools/...`.
  - Le wiki conseille de lire d'abord Installation, Terminology, Global Settings et Conversion Tools.
- **Réglages et sortie** : Global_Settings, Export_Panel, Conversion_Helper et Scene_Lighting.
- **Objets** :
  - Root_objects (SCS Root = un objet du jeu), Part_system, Variant_system et Animation_system.
  - Locators : Model_Locators, Collision_Locators et Prefab_Locators.
- **Matières** : Materials, Materials/Lamp_system et Look_system.
- **Barre latérale** : SCS_Tools_Sidebar (Lamp Switcher et UV, Wrap et Stats, VColoring).
- **Menus** : SCS_Tools_menu, Import, Export, Supported_model_types et Supported_shaders.
- **Tutoriels** : `Tutorials/SCS_Blender_Tools`.

## Matières

- On règle TOUT dans le panneau **SCS Material**. Les panneaux standard de Blender ne changent que l'aperçu, et l'export peut alors être différent.
- Pour un aperçu fidèle : moteur EEVEE et vue en mode Rendered.
- **Shader presets** : liste de préréglages, avec des « flavors » qui étendent l'effet. Exemple : le flavor « shadow » fait projeter une ombre.
- **Shaders importés** : leurs attributs ne sont pas modifiables, mais ils s'exportent comme dans l'original.
- **Textures** : on les choisit par chemin ou par TOBJ. Une texture hors du dossier projet SCS provoque des erreurs à l'export.
- **TOBJ** :
  - Il est créé à l'export s'il manque (bouton Create). Un bouton Reload rouge signale des réglages périmés.
  - Ses options : U/V Repeat, TS Normal, et Color Space Linear (pour les occlusions en gris).
- **Mapping** : chaque texture choisit sa couche UV. Certains presets demandent plusieurs couches UV.
- **Merge Materials** fusionne les matières.

## Looks (variantes de textures sur la même géométrie)

- Chaque SCS Root a sa liste de looks, réglée dans le panneau SCS Looks (objet Root) ou dans l'onglet Material (maillage).
- Changer de look actif applique ses valeurs à toutes les matières de l'objet.
- **Write Through (WT)** recopie une valeur :
  - vers tous les looks de ce Root ;
  - vers le même look sur tous les Roots ;
  - ou vers tous les looks sur tous les Roots.
- Une matière partagée entre plusieurs Roots prend les valeurs de l'objet sélectionné. L'aperçu peut alors être faux, mais l'export reste correct.

## Règles TSC pour l'atelier

- Ne jamais reproduire les logos ni les marques (Scania, Volvo...) dans un modèle livré.
- Les pièces s'ajoutent en accessoires séparés. On ne touche jamais aux mods MDT de Mendy (voir la mémoire du projet).
- Les ressources libres : voir `../outils/outils_et_ressources_libres.md`.
