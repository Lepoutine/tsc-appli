# Conversion Tools, et création de skins (paint jobs)

Statut : [vérifié] sur le wiki SCS. [à vérifier] pour la méthode du wiki communautaire, signalée comme partiellement inexacte.
Sources (lues le 2026-11-03) :
- https://modding.scssoft.com/wiki/Documentation/Tools/Conversion_Tools
- https://modding.scssoft.com/wiki/Documentation/Engine/Units/accessory_paint_job_data
- https://trucksimulator.wiki.gg/wiki/Modding/Creating_Skins

## Conversion Tools (format intermédiaire vers format du jeu)

- La version 2.21 convient à ETS2/ATS 1.58 et plus, en 64 bits. Pour le jeu 1.61, c'est la 2.21.
- On les décompresse dans un dossier où l'on peut écrire.
- **Depuis Blender** : Output properties > Conversion Helper > Conversion Tools Path, puis les boutons du panneau.
- **En ligne de commande** :
  - `conversion_tools/convert.cmd` convertit `conversion_tools/base` vers `conversion_tools/rsrc/base/@cache`.
  - On zippe ce `@cache` pour obtenir le mod.
  - Les montages supplémentaires vont dans `extra_mount.txt`, un chemin par ligne. Chacun produit son `rsrc/<nom>/@cache`.
- **Journal** : `conversion_tools/mass_convert.log` (versions 2.19 et plus).
- Il faut tout convertir : les modèles exportés par SCS Blender Tools, les définitions, les sons et les cartes.

## accessory_paint_job_data (définition d'une peinture)

- **Modes** :
  - simple : `base_color` ;
  - **colormask** : `paint_job_mask` est un masque RGB, et chaque canal reçoit une couleur (`mask_r/g/b_color`, verrouillables avec `mask_*_locked`) ;
  - **airbrush** (`airbrush: true`) : le RGB du masque est mélangé à la couleur de base selon son canal alpha. Ce mode est incompatible avec colormask ;
  - **flipflake** (`flipflake: true`, métallisé ou nacré) : `flip_color`, `flip_strength` (0,27), `flake_color`, `flake_uvscale` (32), `flake_density` (1), `flake_shininess` (50), `flake_clearcoat_rolloff` (2,2), et `flake_noise` (une tobj dont le RGB multiplie la couleur et l'alpha sert de masque). Ce mode est incompatible avec colormask.
- **Divers** :
  - `base_color_locked`, `flip_color_locked` et `flake_color_locked` : à false, le joueur peut changer la couleur.
  - `alternate_uvset` active le flavor altuv.
  - `base_texture_override` est une tobj qui remplace la texture de base de truckpaint (alpha et spéculaire).
  - `stock` doit être **false** aujourd'hui.

## Fichiers d'une peinture de camion (méthode manuelle, à vérifier en 1.61)

- `vehicle/truck/upgrade/paintjob/<nom>.dds` et `.tobj` : la texture peinte sur le gabarit du camion.
- `def/vehicle/truck/<marque.modele>/paint_job/<nom>.sii` : le `accessory_paint_job_data`, avec nom, prix, niveau, icône, masque, etc.
- `material/ui/accessory/<icone>.dds`, `.tobj` et `.mat` : l'icône, d'environ 290x70.
- **Règles** :
  - Tout en minuscules (des majuscules peuvent faire planter le jeu).
  - Ne pas reprendre les noms des peintures d'origine.
  - L'archive `.scs` est un ZIP en mode « stockage », sans compression.
- **Outil communautaire existant** : *Paint Job Packer*. Il génère toute l'arborescence et les gabarits, et le joueur n'a plus qu'à peindre le DDS. Sa licence n'a pas encore été vérifiée : forum.scssoft.com, t=282956. À vérifier avant de l'intégrer à l'atelier.
- Gabarits de peinture : un pack communautaire existe (sujet du forum SCS « Complete pack of truck & trailer templates »). Sa licence est à vérifier, sinon on extrait les gabarits soi-même avec SCS Extractor sur le PC du joueur.

## Règles TSC (rappel)

- Mendy : chaque skin Spartan suit [[tsc-methode-skin-spartan]] (mémoire du projet).
- Les noms d'unités SII ont 11 caractères au plus par segment, sauf le suffixe `.addon_hookup`.
