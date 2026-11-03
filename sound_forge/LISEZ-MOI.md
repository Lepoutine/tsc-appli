# TSC Sound Forge, by Truck So Clean France

Studio audio pour ETS2, integre a TSC Driver. Plan valide par Mendy le 03/11/2026.

## Phase 0 : analyseur ETS2 (lecture seule)

`Analyser_mon_ETS2.bat` lance `analyse/Analyser_ETS2.ps1` :

- trouve Steam et ses bibliotheques, ETS2 (et ATS), Documents, profils, dossier mod, Workshop, FMOD Studio et la version FMOD du jeu ;
- lit le jeu et les mods (dossier, HashFS v1/v2, zip) sans rien extraire ni modifier ; les fichiers chiffres ou proteges sont signales, jamais forces ;
- repere camions, moteurs, definitions son (.sii/.sui), .soundref, banques .bank et .bank.guids, verifie chaque reference son (banque presente, evenement present dans le .bank.guids) ;
- calcule les etats : compatible / partiel / non pris en charge / non verifie (la compatibilite en jeu ne se confirme qu'en jeu) ;
- liste les conflits (meme fichier son fourni par plusieurs mods actifs, ordre du dernier profil charge d'apres game.log) ;
- ecrit dans `%LOCALAPPDATA%\TruckSoCleanFrance\TSC\soundforge\` : `base_connaissances.json`, `rapport_analyse.md`, `echantillons\` (definitions texte du Scania R et du Volvo FH pour l'etude), `cache\` (seules les archives modifiees sont relues).

Options : `-SansCache`, `-Echantillons scania.r_2016,volvo.fh_2021`, `-Sortie <dossier>`.
