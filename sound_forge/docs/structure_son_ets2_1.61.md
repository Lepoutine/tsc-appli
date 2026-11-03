# Structure du son d'un camion dans ETS2 1.61 (relevée par l'analyseur, 03/11/2026)

Relevé fait sur le PC de Mendy (ETS2 1.61.1.9), en lecture seule. Seuls les noms et la structure sont notés ici. Aucun son ni aucune banque du jeu n'est copié.

## Versions

- Moteur audio du jeu : `fmod.dll` et `fmodstudio.dll` en **2.3.11**. Banques du jeu : format FEV 146.
- FMOD Studio installé chez Mendy : 2.03.12 et 2.03.15 (avec `fmodstudiocl.exe`). Sound Forge compile avec une version 2.03.x.
- Les anciennes banques de mods (scaniat2, scania3series) sont en FEV 141/142.

## Chaîne de définitions (Scania R 2016)

1. `def/vehicle/truck/scania.r_2016/engine/*.sii` : `accessory_engine_data`. Chaque moteur inclut un jeu de sons (`sound_hi.sui`, `sound_lo.sui`, `sound_590s.sui`, `sound_r560.sui`).
2. `engine/sound_hi.sui` : `sounds[]: "nom|/def/.../fichier.soundref"` pour 5 entrées : `engine`, `exhaust`, `start_bad`, `turbo` et `remote`.
3. `engine/sound_hi_engine.soundref` : une ligne `source="/sound/truck/scania_2016_v8.bank#engine/engine"`.
4. Les autres familles suivent le même principe : `cabin/sound.sui` (klaxon, bruit aéro, pluie), `chassis/sound.sui` (freins pneumatiques, marche arrière, sellette…), `interior/sound.sui` (clignotants, commodos, frein de parc, alertes, vitres, essuie-glaces), `transmission/sound.sui` (ralentisseur). Les entrées pointent soit vers des `.soundref` propres au camion, soit vers `/sound/truck/default/*.soundref`.
5. Un `.sui` accepte 3 formes pour chaque entrée : vide ou `-`, un fichier `.soundref`, ou directement `banque#événement`.

## Événements attendus d'une banque moteur

- Scania : `event:/engine/engine`, `event:/engine/exhaust`, `event:/engine/start_bad`, `event:/engine/turbo`, `event:/remote/engine`.
- Volvo FH 2021 : mêmes noms, avec les préfixes `engine_hi/`, `engine_lo/`, `remote_hi/` et `remote_lo/`.

## Paramètres FMOD utilisés par le jeu (projet camion)

`rpm`, `load`, `brake`, `turbo`, `play`, `engine/rpm`, `engine/load`, `engine/brake`, `engine/turbo`, `engine/play`, `exhaust/rpm`, `exhaust/load`, `exhaust/play`, `cabin_out`, `cabin_rot`, `cabin_type`, `surr_type`, `wnd_left`, `wnd_right`, `daytime`, `Event Cone Angle`.

Projet commun (effets, intérieur) : en plus `aero_speed`, `air_pressure`, `retarder`, `start`, `susp_speed`, `trans_rpm`, `window_stop`, `aero_wnd`, `brake_int`, `rain_int`, `speed`, `wheel_wear`.

## Bus (identiques dans tous les projets SCS, à ne jamais modifier)

`/`, `/cabin` (`interior`, `window_left`, `window_out`, `window_right`), `/game` (`intro`, `music`, `navigation`, `ui`, `ui_music`, `voiceover`), `/outside` (`exterior` avec `traffic`, `trailer`, `truck_effects`, `truck_engine`, `truck_exhaust`, `truck_noise`, `truck_turbo`, `world` ; `unprocessed/ambient`), `/radio`.

Un `.bank.guids` exporté par FMOD décrit tout le projet : les lignes `bank:`, puis `bus:`, puis `event:`, puis `parameter:`.

## Conséquences pour Sound Forge

- Une banque moteur Sound Forge doit exposer les 5 événements ci-dessus (avec les préfixes du camion visé), piloter `rpm`/`load` (et `engine/*`, `exhaust/*`), et router vers `/outside/exterior/truck_engine`, `truck_exhaust` et `truck_turbo`, ainsi que vers `/cabin` pour l'intérieur.
- Le mod livré ajoute sa banque et ses `.soundref`. Il remplace seulement le `.sui` du moteur choisi (ou en ajoute un nouveau), jamais les banques du jeu.
