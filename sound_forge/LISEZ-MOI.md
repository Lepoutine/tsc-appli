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

## Studio (phase 1) : `ui/`

`ui/index.html` (avec `forge.css`, `forge_audio.js`, `forge_gen.js`, `forge.js`) est l'atelier Sound Forge, prévu pour s'afficher dans la tablette TSC Driver comme Spartan Studio (dans un cadre, page `forge/index.html`).

- Import de sons (WAV, OGG, MP3, FLAC) par glisser-déposer, rôle et régime devinés d'après le nom du fichier (`ralenti_600.wav`, `charge_1400.wav`...).
- Pistes avec formes d'onde, coupe au doigt ou à la souris, volume, graves, aigus, volume égalisé, boucle avec fondu.
- Simulateur régime et charge qui joue vraiment le moteur : fondu à puissance constante entre les régimes voisins, vitesse de lecture selon le régime, mélange charge / pied levé, turbo.
- Export des couches en WAV 48 kHz 24 bits (prêtes pour le projet FMOD de la phase 3) et sauvegarde du projet (`.tscforge.json`).
- Onglet Analyse ETS2 : lit `base_connaissances.json` de l'analyseur, filtre par état, diagnostic par camion, choix du camion visé.
- Le projet et les sons restent sur le PC (stockage local du navigateur de la tablette), rien à ressaisir après une mise à jour.

Pas encore fait : bouton « Analyser mon ETS2 » relié au service de la tablette, projet FMOD (phase 3), vrai build (phase 4), mod ETS2 (phase 5).

## Tous les sons dans Forge (04/11/2026)

- **Importer tous mes sons** : choisis le dossier `TSC_Sound_Forge` du Bureau. Le fichier `forge_pack.json` (fait par `intelligence/experts/son/pack_forge.py`) donne à chaque son son rôle, son régime et une note. Réimporter ne crée pas de doublons.
- Vidéos (MP4) et sons longs acceptés : tire les bords rouges puis **Extraire le passage** crée une nouvelle couche, l'original reste entier.
- Nouveaux rôles : coup de gaz, claquements, frein moteur, pschitt de boîte, purge, frein pneumatique, frein de parc, suspension, référence.
- **Pupitre d'effets** : un bouton par effet (touches 1 à 9), joué par-dessus le simulateur.
- **Contrôles** de la couche choisie : crête, niveau moyen, écrêtage, raccord de boucle (mêmes seuils que l'Audio Lab). Ce sont des mesures, l'écoute tranche.
- Filtre des pistes par famille (moteur, effets, références, autres).

## TSC Clapet
Le clapet d'échappement sur touche (V seule) est intégré au simulateur, avec les rôles `clapet`, `clapet_on` et `clapet_off`. La recette et les règles sont dans `connaissances/fmod/06_tsc_clapet.md`. Le plugin en jeu et le partage multijoueur viendront après la validation du son par Mendy.
