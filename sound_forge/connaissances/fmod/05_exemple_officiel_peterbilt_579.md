# Exemple officiel SCS : moteur Peterbilt 579 (jeu 1.42, FMOD 2.01.05), en chiffres

Statut : [vérifié]. Les fichiers metadata de l'exemple officiel ont été lus le 2026-11-03 sur le PC de Mendy, sans être ouverts dans FMOD. Le zip est intact (4 182 133 o) dans `Outils admin\soundforge\exemples_scs\`.
Source : https://download.eurotrucksimulator2.com/sound/example_sound_engine_peterbilt_579_142_01.zip
Les sons de l'exemple appartiennent à SCS : on n'en copie que la STRUCTURE, jamais l'audio.

## Vue d'ensemble

- 2 banques (`peterbilt_579` et `peterbilt_579_rm`), 35 sons, 11 événements.
- Un jeu de paramètres par dossier :
  - `engine/` (rpm de 350 à 3000, load, brake, turbo, play) pour engine/engine et engine/turbo ;
  - `exhaust/` (rpm, load, play) pour l'échappement ;
  - à la racine (rpm, load, brake, turbo, play) pour remote/engine.

## engine/engine

- Bus truck_engine, en 3D.
- Spatialisation :
  - atténuation de type 3, de 5 à 300 m ;
  - taille 5, étendue 200° ;
  - effet Doppler actif, priorité 4.
- 5 pistes de boucles sur la feuille rpm, toutes avec auto-pitch et fondus croisés entre couches voisines :

  | Piste | Couches | Plages |
  |---|---|---|
  | loaded | 6 | de 350-600 à 1675-3000, régimes de référence du pitch de 460 à 1260 |
  | unloaded | 7 | de 350-800 à 1650-3000 |
  | nofuel | 4 | joue seulement si load < 0,05 |
  | engine brake | 5 | voir le frein moteur ci-dessous |
  | start_stop | — | démarrage de 0 à 1,15 s, arrêt de 1,23 à 5,04 s, commande stop à 5,1 s |

- **Mélange par la charge** :

  | load | Piste qui joue |
  |---|---|
  | moins de 0,2 | unloaded |
  | de 0,2 à 0,35 | fondu entre les deux |
  | plus de 0,35 | loaded |

- **Frein moteur** : brake 0 = -80 dB, brake 0,21 = -1 dB, brake 1 = +3 dB. Il est coupé en dessous d'environ 860 tr/min.
- **Cycle de vie (play)** : une transition à 0 s, puis une boucle à partir de 1,15 s, maintenue tant que play ≥ 0,1. Quand play passe à 0, le son d'arrêt joue et l'événement s'arrête tout seul.

## engine/exhaust

- Bus truck_exhaust, en 3D jusqu'à 400 m.
- 4 couches, de exhaust_1 (350-1050) à exhaust_6 (1600-3000).
- Le volume suit :
  - la charge : 0 = -80 dB, 0,3 = -5 dB, 1 = 0 dB ;
  - le régime : 350 = -4,6 dB, 3000 = +5 dB.

## engine/turbo

- Bus truck_turbo.
- Une seule boucle sur la feuille turbo. Elle apparaît à partir de turbo 0,24 et est pleine à 0,46.

## engine/start_bad

- Bus truck_engine.
- Un MultiSound à +4,5 dB, sans paramètre.

## remote/engine (banque _rm)

- Bus traffic.
- 6 pistes allégées, de 2 à 4 couches au lieu de 4 à 7. Elles réunissent moteur, échappement, frein et turbo.
- Boucle de 1,9 à 2,58 s, maintenue tant que play ≥ 0,505.

## Ce que Sound Forge en retient

- Des couches séparées en charge et sans charge. Une couche « nofuel » (pied levé, injection coupée) est conseillée.
- Le fondu par la charge entre 0,2 et 0,35, et non linéaire de 0 à 1. Le simulateur de l'atelier suit cette courbe.
- Une piste de frein moteur.
- Un démarrage et un arrêt intégrés à engine/engine, pilotés par play.
- Un échappement à 4 couches, dont le volume suit la charge et le régime.
- Un turbo à seuil.
- Une banque _rm allégée.

Un script FMOD « EngineDesigner.js » est livré avec FMOD Studio 2.03.15 (dossier `scripts\`, Ctrl+Maj+E). Il ouvre une fenêtre avec des curseurs de régime pour tester un moteur. À étudier.
