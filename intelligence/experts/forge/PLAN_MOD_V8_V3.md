# Mod son V8 de Mendy : plan v3 (expert Forge), 03/11/2026

Demande de Mendy (03/11 20:11) : ralenti très bas, échappement grave, claquements au passage de rapport, bruits d'air (suspension pneumatique, décompression, etc.).
Base : projet `tsc_v8_mendy` existant (template SCS 1.43 migré en 2.03, build fmodstudiocl qui marche, v2 non installée). On le reprend sans le refaire.
Aperçu à valider d'abord : `apercu_v5/v5_scenario_complet_ralenti_300.wav` et `_200.wav` (simulation hors FMOD, faite avec les sons de Mendy).

## Où chaque demande va dans le jeu (sources : fiches scs_sons_camion, filtrage_cabine, fmodstudiocl, structure_jeu_161)

| Demande | Événement du jeu | Réglage FMOD |
|---|---|---|
| Ralenti très bas (« bop bop ») | `engine/engine` et `engine/exhaust` | Le jeu garde son vrai ralenti (~600 tr/min, réglé dans le moteur). Sous 650 tr/min et `load` < 0,05, on joue la boucle galop (allumages à 200 ou 300 tr/min recomposés), fondu vers les couches entre 650 et 850. |
| Échappement grave | `engine/exhaust` | EQ de l'événement : +4 dB de 70 à 250 Hz, aigus adoucis au-dessus de 2 kHz. Couches propres seulement (500 à 1300 ; les 1500 à 2300 sont écrêtées dès la source). |
| Claquements au passage de rapport | `engine/exhaust` | Le jeu ne signale pas le changement de rapport au son. Le passage se voit comme une chute de `load` à 0 avec un régime haut : instrument de claquements (claquant_1-3) quand `load` < 0,05 et `rpm` > 800, intensité selon le régime. |
| Pschitt de boîte pneumatique | `engine/exhaust` (v3) | Même déclencheur, une fois par chute de charge, avec un délai de reprise de 1 s. Il sonne aussi à une simple levée de pied. Version exacte possible ensuite par le plugin TSC (rapport lu dans la télémétrie, comme TSC Clapet). |
| Décompression (purge du compresseur) | `chassis/sound.sui` → `air_cutoff` | Événement `chassis/air_cutoff` dans notre banque (air_compressor). |
| Frein pneumatique et suspension | `chassis/sound.sui` → `air_brake` | Événement `chassis/air_brake` : relâchement (brake1) suivi de la suspension qui se remet à niveau (liftaxle, 3 s, plus bas). Il n'y a pas d'événement « suspension » propre au camion dans le jeu. |
| Frein de parc | `interior/sound.sui` | Plus tard, s'il le veut : c'est un son intérieur. |

## Fichiers du mod (rien n'est installé avant l'accord de Mendy)

- `sound/truck/tsc_v8_mendy.bank` + `.bank.guids` (vrai build, `-export-guids`, GUIDS.txt renommé).
- `.soundref` moteur existants + 2 nouveaux : `chassis_air_cutoff.soundref`, `chassis_air_brake.soundref`.
- `def/vehicle/truck/scania.{r,s}_2016/chassis/...sound.sui` : copie de l'original du jeu 1.61 où seules les lignes `air_brake` et `air_cutoff` changent.
- Contrôle `.scs` par l'expert Mods (étape 2), puis test dans TSCF_Lab avec sauvegarde.

## Ordre
1. Mendy écoute v5 et choisit 300 ou 200 tr/min (et dit ce qui ne va pas).
2. Forge : script v3 du projet FMOD, vrai build sur le PC, banque décodée et mesurée.
3. Mods : contrôle du `.scs`.
4. Test en jeu dans TSCF_Lab, après accord.
