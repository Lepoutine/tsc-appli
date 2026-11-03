# TSC Clapet : clapet d'échappement sur touche (créé par TSC)

Décision de Mendy (03/11/2026) : le jeu ne le propose pas, donc on le crée.

## Pourquoi un système à nous
Le moteur son d'ETS2 ne transmet aux événements moteur que rpm, load, brake, turbo et play. Il n'existe aucun paramètre libre réglable par une touche. En multijoueur, chaque joueur entend les autres camions avec ses propres banques (remote/engine), à partir de ces seules valeurs.

## Les 3 briques
1. **Plugin TSC local.** Il lit la touche et joue la couche « clapet ouvert » avec notre propre FMOD. Il suit en direct le régime, la charge et le turbo grâce à la télémétrie.
2. **Serveur TSC.** Il relaie la position, le cap et l'état du clapet, plusieurs fois par seconde.
3. **Chez les autres joueurs TSC.** Leur plugin joue en 3D le clapet des camions TSC proches. Seuls les joueurs équipés de TSC l'entendent. Les règles de TruckersMP sur les plugins restent à vérifier, Convoy est OK.

## Recette du son (identique dans Sound Forge et dans le plugin)
- Les rôles :
  - `clapet` : couches en boucle par régime ;
  - `clapet_on` : son ponctuel d'ouverture ;
  - `clapet_off` : son ponctuel de fermeture.
- État K de 0 à 1. L'ouverture prend 180 ms, la fermeture 350 ms.
- Couches normales (ralenti, charge, lever de pied) : poids × (1 − 0,6·K).
- Couches clapet : fondu à puissance constante entre les régimes voisins, poids K × (0,55 + 0,45·charge). Vitesse de lecture = rpm / régime de la couche, bornée entre 0,5 et 2.
- Touche : V seule, choisie par Mendy le 03/11/2026. Le plugin ignore V quand Ctrl, Maj ou Alt est enfoncé. Dans le profil « Le Poutine de Norman », Maj seule passe la marche avant (geardrive) et Ctrl+V sert à coller. Alt+V est le seul repli libre. Dans les profils EDIT, The Misanthrope et Vladimir Poutine, V sert au blocage de différentiel.

## Sources de départ
Le mod « Scania R770 Valve Exhaust » de Mendy (scania_ng_v8.bank) contient :
- les couches `rv8op <rpm>ex` de 550 à 2000, avec les variantes exl3, exl4, exul et t ;
- les sons ponctuels `valve open`, `rv8op valve`, `rv8op exstop`, `rv8op 1170bov` et `rv8op eb shift 1-3`.

La banque est en Vorbis (code FSB5 15) : elle se décode avec vgmstream, sur une copie.

## Niveaux mesurés (03/11/2026)
Les couches `rv8op <rpm>ex` d'origine ont des niveaux très inégaux : environ −34 dB RMS à 550 tr/min et −12 dB à 2000, soit un écart de 12 fois. Dans l'aperçu, elles sont égalisées sur une cible qui monte de −17 dB à 600 tr/min jusqu'à −13 dB à 2000. Les couches clapet fermé (`rv8 exl`) sont égalisées 3 dB plus bas. Les sons d'ouverture et de fermeture ont leur crête ramenée à −3 dB.

## Plugin tsc-clapet.dll 0.1 (étape B, 03/11/2026)
- Source : `sound_forge/plugin_clapet/`. C++ sans CRT ni SDK Windows, construit avec `construire.sh` (clang + lld-link). Test sous Linux : `test/lancer.sh` (faux jeu, faux Windows, faux XAudio2, ASan), 25 vérifications.
- Plugin de télémétrie : il lit `truck.engine.rpm`, `truck.effective.throttle` et `truck.engine.enabled`, plus les événements pause et reprise. Les callbacks du jeu ne font que recopier ces valeurs.
- Tout le reste se passe dans un fil à lui :
  - la touche V seule, lue quand la fenêtre du jeu est devant et pas en pause ;
  - le son, avec XAudio2 de Windows (xaudio2_9.dll, aucune licence tierce) ;
  - la lecture des fichiers.
- Les sons sont dans `%LOCALAPPDATA%\TruckSoCleanFrance\TSC\clapet\` :
  - `c_<régime>.wav` en PCM 16 bits, 24 couches au plus ;
  - `ouverture.wav` et `fermeture.wav` ;
  - `reglages.ini` (`volume=80`).
  Le plugin écrit `journal.txt` dans ce même dossier.
- La recette est la même que dans Sound Forge, à une différence près : le plugin ne peut pas baisser l'échappement du jeu, donc le clapet s'ajoute par-dessus.
- Limites :
  - pas encore de multijoueur (étape C) ;
  - V tapé dans le chat ouvre aussi le clapet ;
  - les sons du R770 sont réservés à un usage personnel tant que l'auteur n'a pas donné son accord.
