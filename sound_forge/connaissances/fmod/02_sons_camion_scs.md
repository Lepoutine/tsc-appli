# Sons d'un camion dans ETS2 / ATS (règles officielles SCS)

Statut : [vérifié] sur le wiki officiel SCS, et recoupé avec les fichiers du jeu 1.61.1.9 (voir `../../docs/structure_son_ets2_1.61.md`).
Sources (lues le 2026-11-03) :
- https://modding.scssoft.com/wiki/Documentation/Engine/Sound
- https://modding.scssoft.com/wiki/Documentation/Engine/Sound/TruckEngine
- https://modding.scssoft.com/wiki/Documentation/Engine/Sound/TruckRemote
- https://modding.scssoft.com/wiki/Documentation/Engine/Sound/Mixer
- https://modding.scssoft.com/wiki/Documentation/Engine/Sound/TruckCabinFiltering
- Autres pages : TruckTransmission, TruckChassis, TruckCabin, Tires, SoundWorld (pas encore résumées).

## Identifier un son

- Directement : `[banque]#[événement]`, avec le chemin depuis la racine du jeu. Exemple : `/sound/ui/ui.bank#click`.
- Par un fichier `.soundref` (méthode conseillée). C'est du texte UTF-8 :
  - `source="/sound/truck/peterbilt_579.bank#engine/engine"` ;
  - une ligne facultative `position_offset=gauche(-)/droite(+);bas(-)/haut(+);avant(-)/arrière(+)`, en mètres.
- Chaque objet FMOD a un GUID. Supprimer puis recréer un objet, même avec le même nom, lui donne un AUTRE GUID.

## Moteur (événements du dossier « engine », tous dans la même banque)

| Événement | Bus | Type | Paramètres |
|---|---|---|---|
| engine/engine | truck_engine | 3D, boucle, vie pilotée par play | engine/play, engine/brake, engine/load, engine/rpm |
| engine/exhaust | truck_exhaust | 3D, boucle | exhaust/play, exhaust/load, exhaust/rpm |
| engine/turbo | truck_turbo | 3D, boucle | engine/turbo (depuis la 1.39) |
| engine/start_bad | truck_engine | 3D, une seule fois | aucun (variantes aléatoires possibles) |

- Plages des paramètres :
  - play vaut 1 (joue) ou 0 (doit s'arrêter).
  - brake va de 0 à 1 (frein moteur).
  - load va de 0 à 1 (moins de 0,05 = son de ralenti).
  - rpm va de 0 à 3000. Le wiki parle de « tours par seconde », ce qui est incohérent : c'est en pratique des tr/min [à vérifier en jeu].
  - turbo va de 0 à 1.
- Règles :
  - Un son de moteur = une banque.
  - Les 4 événements doivent être dans la même banque.
  - Mélanger des banques n'est pas conseillé.
- Configuration : dans `accessory_engine_data`, le tableau `sounds[]` (souvent mis à part dans un `@include "sound.sui"`) :
  ```
  sounds: 5
  sounds[]: "engine|/def/vehicle/truck/peterbilt.579/engine/sound_engine.soundref"
  sounds[]: "exhaust|/def/vehicle/truck/peterbilt.579/engine/sound_exhaust.soundref"
  sounds[]: "start_bad|/def/vehicle/truck/peterbilt.579/engine/sound_start_bad.soundref"
  sounds[]: "turbo|/def/vehicle/truck/peterbilt.579/engine/sound_turbo.soundref"
  sounds[]: "remote|/def/vehicle/truck/peterbilt.579/engine/sound_engine_rm.soundref"
  ```
- Position par défaut : 1 m au-dessus du premier essieu. Un `.soundref` peut la déplacer.

## Camion distant (multijoueur, depuis la 1.42)

- Il y a une banque séparée, suffixée `_rm`, par exemple `peterbilt_579_rm.bank`. Elle contient un seul événement, `remote/engine` : 3D, en boucle, sur le bus **traffic**.
- Ses paramètres sont `play`, `brake`, `load`, `rpm` et `turbo`, sans préfixe. L'échappement et le turbo sont intégrés dans ce même son, en version allégée.

## Mixeur (bus de la Master Bank : ne JAMAIS les modifier)

- master
  - cabin
    - interior : alertes, clignotants, commodos, frein de parc, essuie-glaces, vitres, siège
    - window_left, window_right, window_out : sans son direct
  - outside
    - exterior
      - traffic, trailer
      - truck_effects : coupure d'air, boîte, sellette, klaxons, marche arrière
      - truck_engine, truck_exhaust, truck_turbo
      - truck_noise : aéro, suspension
      - world
    - unprocessed
      - ambient
  - game : music, navigation, ui, ui_music, voiceover
  - radio
- Chaque événement doit être routé vers le bon bus. Sinon il tombe dans master.

## Intérieur / extérieur (filtrage cabine)

- Paramètres globaux :
  - `cabin_out` : 0 = écoute dans la cabine, 1 = dehors.
  - `wnd_left` et `wnd_right` : 0 = vitre fermée, 1 = ouverte.
  - `cabin_rot`, `cabin_type`, `surr_type` et `daytime` existent dans le modèle, mais le wiki ne les décrit pas [à vérifier].
- Chemin du son : le son extérieur passe par « Grp outside », puis se partage en 3 retours (window_out, window_left, window_right), qui sont mélangés à la fin.
- Volumes figés dans la Master Bank :

  | Retour | Écoute dans la cabine | Écoute dehors |
  |---|---|---|
  | window_out | -6 dB | +4 dB |
  | window_left | -7 dB | coupé |
  | window_right | -7 dB | coupé |

- Égaliseurs et réverbérations réglés par camion dans les réglages son de l'intérieur (depuis la 1.43) :
  - `.effect.add.window_eq.opened` / `.closed` ;
  - `.effect.equalizer.cabin.inside` / `.outside` ;
  - `.effect.reverb.window.closed` / `.opened`.
- Le jeu fait des transitions linéaires entre ces réglages. Des fréquences de coupure très différentes sur un même égaliseur donnent des artefacts.

## Conséquence pour Sound Forge

Une banque Sound Forge expose `engine/engine`, `engine/exhaust`, `engine/turbo` et `engine/start_bad`, routés vers les bons bus. Une banque `_rm` séparée expose `remote/engine`. Le mod ne remplace que les `.soundref` (ou le `.sui`) du moteur choisi.
