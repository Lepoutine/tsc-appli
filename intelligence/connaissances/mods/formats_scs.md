# Formats de fichiers du moteur SCS (Prism3D)

- Source : https://modding.scssoft.com/wiki/Documentation/Engine/Formats (lu le 03/11/2026)
- Source : https://modding.scssoft.com/wiki/Documentation/Engine/Mod_manager (manifest, lu le 03/11/2026)
- Version : wiki SCS au 03/11/2026 ; jeu visé ETS2 1.61. Statut : vérifié.

## Formats (rôle en une ligne)
- Modèles compilés : `.pmd` (description), `.pmg` (géométrie), `.pmc` (collisions), `.pma` (animation), `.ppd` (préfab).
- Formats d'export Blender (avant conversion) : `.pit`, `.pim`, `.pic`, `.pia`, `.pip`.
- Définitions : `.sii` (unités), `.sui` (morceaux inclus par `@include`, sans en-tête SiiNunit).
- Matières et textures : `.mat` (matière), `.tobj` (lien vers la texture DDS).
- Son : `.soundref` (renvoie vers `fichier.bank#événement`).
- Archives : `.zip` pour les mods, `.scs` pour les données du jeu ; un mod `.scs` doit rester un zip lisible par le jeu (voir la fiche piège zip .scs).

## manifest.sii (gestionnaire de mods)
- À la racine du mod. Unité `mod_package : .nom_du_paquet` (nom commençant par un point).
- Clés : `package_version`, `display_name` (facultatif), `author`, `category[]` (seulement les 2 premières, parmi la liste officielle), `icon`, `description_file`, `compatible_versions[]` (facultatif, jokers acceptés, ex. `1.61.*`), `mp_mod_optional` (facultatif).
- Icône : `.jpg` de 276 x 162 px exactement, à la racine.
- Description : `.txt` UTF-8 à la racine ; versions traduites `nom.[locale].txt`.
- `mp_mod_optional: true` seulement si le mod ne change pas le jeu des autres joueurs ; le serveur doit autoriser les mods optionnels.

## Contrôles à faire par Verifier_Mods_TSC.ps1 (étape 2 du plan)
- manifest présent, icône 276x162, description UTF-8, catégories valides.
- extensions connues seulement ; segments de noms d'unités ≤ 11 caractères (règle TSC).
