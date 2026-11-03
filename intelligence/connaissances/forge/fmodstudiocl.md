# FMOD Studio 2.03 en ligne de commande, banques et GUID pour ETS2

- Source : https://d1s9dnlmdewoh1.cloudfront.net/2.03/studio/advanced-topics.html (miroir officiel du manuel FMOD Studio 2.03, lu le 03/11/2026)
- Source : https://d1s9dnlmdewoh1.cloudfront.net/2.03/studio/getting-events-into-your-game.html (lu le 03/11/2026)
- Source : https://d1s9dnlmdewoh1.cloudfront.net/2.03/studio/scripting-terminal-reference.html (lu le 03/11/2026)
- Source : https://modding.scssoft.com/wiki/Documentation/Engine/Sound et /Sound/Downloads (lus le 03/11/2026)
- Version : FMOD Studio 2.03 ; ETS2 1.61. Statut : vérifié (docs), chaîne pas encore lancée chez Mendy.

## fmodstudiocl (outil en ligne de commande, dans le dossier d'installation de FMOD Studio)
- Windows : `C:\Program Files\FMOD SoundSystem\FMOD Studio <VERSION>\fmodstudiocl.exe`.
- `-build` : construit toutes les banques pour toutes les plateformes réglées dans les préférences.
- `-banks "Master, Truck"` : liste des banques à construire (avec `-build`).
- `-platforms "Desktop"` : liste des plateformes (avec `-build`).
- `-export-guids` : exporte les GUID des événements et du mixeur en fichiers texte (avec `-build`).
- `-diagnostic` : contrôle le projet (corruptions, erreurs).
- `-script fichier.js` : exécute un script JavaScript Studio.
- Exemple : `fmodstudiocl -build -banks "Master, Truck" -export-guids projet.fspro`.

## Sortie
- Par défaut dans le sous-dossier `Build` du projet, un sous-dossier par plateforme.
- La banque maître produit aussi un `.strings.bank` (noms, chemins, GUID) ; sans elle, les événements ne se trouvent que par GUID.
- Encodage conseillé pour PC : Vorbis (curseur de qualité).

## Exigences ETS2
- GUID : `File > Export GUIDs...` (ou `-export-guids`) écrit `GUIDS.txt` dans le dossier Build ; il faut le renommer `<nom de la banque>.guids` et le poser à côté du `.bank`.
- Les GUID viennent TOUJOURS de cet export, jamais écrits à la main (règle Mendy).
- Correspondance publiée par SCS : jeu 1.56 → FMOD Studio 2.03.09 ; 1.43 → 2.02.05 ; 1.39 → 2.01.05. Rien de publié pour 1.61 : garder la 2.03 installée chez Mendy et vérifier en jeu.
- Le dernier gabarit de banque maître publié est `fmod_template_sound_project_143_01` ; vérifier sa version avant usage.

## Scripts Studio
- Studio charge les `.js` du dossier `Scripts` du projet à chaque ouverture ; `studio.project.save()` puis `studio.project.build()` construisent depuis un script.
- Studio accepte aussi du JavaScript par TCP sur le port 3663 (console à distance).
