# Blender 3.6 piloté par script, et SCS Blender Tools

- Source : https://docs.blender.org/manual/id/3.6/advanced/command_line/arguments.html (lu le 03/11/2026)
- Source : https://modding.scssoft.com/wiki/Documentation/Tools/SCS_Blender_Tools (sommaire, lu le 03/11/2026)
- Version : Blender 3.6 ; SCS Blender Tools 2.4.1 (installée chez Mendy). Statut : vérifié (doc), mode arrière-plan pas encore lancé chez Mendy.

## Arguments Blender utiles
- `-b` : sans interface (arrière-plan). `-P script.py` : exécute un script Python. `--python-expr "..."` : une expression.
- `--python-exit-code N` : code de sortie si le script plante (indispensable pour savoir qu'un export a échoué).
- Tout ce qui suit `--` est laissé au script (lu dans `sys.argv`).
- `--factory-startup` : ignore les réglages de l'utilisateur ; attention, il ne charge alors pas les add-ons installés : ajouter `--addons io_scs_tools` (nom du module à vérifier chez Mendy).
- `-noaudio` : pas de son.
- Les arguments sont exécutés dans l'ordre : le fichier .blend avant `-P`.
- Exemple : `blender -b copie.blend --python-exit-code 2 -P controle.py -- --rapport rapport.json`.

## SCS Blender Tools (sommaire officiel)
- Pages : Installation, Download, panneau Export, Materials, systèmes Look / Variant / Part, Supported shaders.
- La doc des versions 1.12 et avant est séparée (legacy) : ne pas la suivre pour la 2.4.1.

## Règles TSC
- Toujours travailler sur une copie du .blend.
- Contrôles automatiques prévus : UV présentes, échelle appliquée (1,1,1), origine, nombre de looks/variants ; l'export passe ensuite au contrôle .scs de Mod Engineering.
