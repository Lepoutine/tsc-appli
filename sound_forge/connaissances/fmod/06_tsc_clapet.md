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
- Touche : Maj+V, choisie par Mendy le 03/11/2026 (Sound Forge et plugin en jeu). Elle est libre dans tous ses profils. V seule sert au blocage de différentiel dans certains profils, et Ctrl+V sert à coller.

## Sources de départ
Le mod « Scania R770 Valve Exhaust » de Mendy (scania_ng_v8.bank) contient :
- les couches `rv8op <rpm>ex` de 550 à 2000, avec les variantes exl3, exl4, exul et t ;
- les sons ponctuels `valve open`, `rv8op valve`, `rv8op exstop`, `rv8op 1170bov` et `rv8op eb shift 1-3`.

La banque est en Vorbis (code FSB5 15) : elle se décode avec vgmstream, sur une copie.
