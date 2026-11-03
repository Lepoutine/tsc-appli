# TSC Sound Forge : techniques d'exécution (guide de métier)

Établi le 2026-11-03 à partir de l'analyse 0.2 de l'installation ETS2 1.61.1.9 (FMOD 2.3.11) du PC de Mendy, et de la documentation officielle SCS (modding.scssoft.com).
Ce qui est marqué [vérifié] a été lu dans les fichiers du jeu. Ce qui est marqué [à vérifier] doit être confirmé (doc officielle SCS ou test en jeu) avant de servir pour une demande de joueur.
Ce guide est enrichi après chaque test en jeu. Il sert aussi de base à l'assistant Claude de l'appli.

## 1. Chaîne son d'un camion [vérifié]

    def/vehicle/truck/<camion>/engine/<moteur>.sii      (le moteur pointe vers un .sui de son)
      -> engine/sound_<jeu>.sui                         (liste "role|chemin.soundref")
        -> engine/sound_<jeu>_<role>.soundref           (une ligne : source="/sound/truck/<banque>.bank#<evenement>")
          -> sound/truck/<banque>.bank (+ .bank.guids)  (banque FMOD compilée + liste des GUID)

- Rôles moteur obligatoires : `engine`, `exhaust`, `start_bad`, `turbo` et `remote` (son extérieur, vue lointaine).
- Exemple Scania R 2016 : `sound_hi.sui` -> `sound_hi_engine.soundref` -> `/sound/truck/scania_2016_v8.bank#engine/engine`. Les variantes du même camion (`sound_lo`, `sound_590s`, `sound_r560`) ont une banque par famille de moteurs.
- Autres .sui du camion :
  - `cabin/sound.sui` : horn, aero_noise, rain_noise.
  - `chassis/sound.sui` : air_brake, air_cutoff, reverse, lift_axle, hook_attach/detach, trailer_cables.
  - `interior/sound.sui` : clignotants, commodos, alertes, essuie-glaces, vitres.
  - `interior/sound_effects*.sui`.
  - `transmission/sound.sui` : retarder.
- Les sons communs sont dans `/sound/truck/default/*.soundref`. Un camion ne surcharge que ce qui lui est propre.
- Format d'une entrée .sui : `sounds[]: "role|/chemin/fichier.soundref"`. Une valeur vide ou "-" veut dire aucun son. On peut aussi écrire directement `"role|/sound/truck/x.bank#evenement"`.
- Klaxons accessoires : `accessory_horn_addon_data` avec `sound_path: "/sound/truck/horn/xxx.soundref"`.

## 2. Banques FMOD [vérifié]

- Format des banques du jeu : RIFF FEV 146.146 (FMOD 2.03). Des mods anciens sont en FEV 141/142 et sont à recompiler.
- Un `.bank.guids` décrit TOUT le projet FMOD (toutes ses banques). Ses lignes ont la forme `{guid} type:/chemin`, dans l'ordre bank:, bus:, event:, parameter:.
- Événements d'un projet moteur : `engine/engine`, `engine/exhaust`, `engine/start_bad`, `engine/turbo` et `remote/engine`. Le Volvo FH 2021 utilise les préfixes `engine_hi`/`engine_lo`/`remote_hi`/`remote_lo`.
- Paramètres envoyés par le jeu aux événements moteur : `rpm`, `load`, `brake`, `turbo`, `play`, `engine/rpm|load|brake|turbo|play`, `exhaust/rpm|load|play`, `cabin_out`, `cabin_rot`, `cabin_type`, `surr_type`, `wnd_left`, `wnd_right`, `daytime` et `Event Cone Angle`.
- Le projet commun (effets, klaxons, intérieur) reçoit en plus `aero_speed`, `air_pressure`, `retarder`, `start`, `susp_speed`, `trans_rpm`, `window_stop`, `speed`, `rain_int`, `brake_int`, `wheel_wear` et `aero_wnd`.
- Les bus sont identiques, avec les mêmes GUID, dans tous les projets SCS : `/cabin/...`, `/game/...`, `/outside/exterior/truck_engine|truck_exhaust|truck_turbo|truck_noise|truck_effects|trailer|traffic|world`, `/outside/unprocessed/ambient` et `/radio`. Une banque maison doit respecter cette arborescence.

## 2bis. Règles officielles SCS (modding.scssoft.com, lu le 2026-11-03)

- Événements moteur (dossier "engine", tous en 3D, dans la même banque) :
  - `engine/engine` : bus truck_engine, boucle, paramètres play/brake/load/rpm.
  - `engine/exhaust` : bus truck_exhaust, boucle, paramètres exhaust/play, exhaust/load, exhaust/rpm.
  - `engine/turbo` : bus truck_turbo, boucle, paramètre engine/turbo.
  - `engine/start_bad` : bus truck_engine, joué une fois.
- `remote/engine` est dans une banque `_rm` séparée depuis la 1.42. Il est en 3D, sur le bus traffic, en boucle, avec les paramètres play/brake/load/rpm/turbo. L'échappement et le turbo y sont intégrés dans ce seul événement (version allégée pour les camions distants).
- Plages des paramètres :
  - play vaut 0 ou 1 (cycle de vie : 1 = joue, 0 = doit s'arrêter).
  - brake va de 0 à 1 (frein moteur).
  - load va de 0 à 1 (moins de 0,05 = ralenti).
  - turbo va de 0 à 1.
  - rpm va de 0 à 3000. Le wiki parle de « tours par seconde », ce qui est incohérent : [à vérifier].
- .soundref : `source="[banque]#[evenement]"` est obligatoire. `position_offset=` est optionnel, en mètres (gauche/droite ; bas/haut ; avant/arrière). Par défaut, le son est placé 1 m au-dessus du premier essieu.
- Projet FMOD :
  - Toujours partir du modèle (template), en renommant template.fspro.
  - Créer une NOUVELLE banque (GUID unique), avec un nom sans majuscule, sans espace et sans caractère spécial.
  - Ne jamais renommer "master", ni supprimer ou recréer les bus standard. Des bus recréés ont d'autres GUID et ne marchent pas.
  - Dupliquer un événement par copier-coller lui donne un nouveau GUID.
- Build :
  - File > Build produit build/<nom>.bank. Ignorer master.bank et master.strings.bank.
  - File > Export GUIDs produit GUIDs.txt, à renommer en <nom>.bank.guids.
  - Livrer seulement <nom>.bank et <nom>.bank.guids.
- Intégration : soit remplacer une banque entière (même nom), soit ajouter une nouvelle banque et écraser seulement le .soundref visé. Écraser le moins de fichiers possible, pour rester compatible avec les autres mods.
- Modèles officiels : le plus récent est le 1.43 (FMOD 2.01.05), à https://download.eurotrucksimulator2.com/sound/fmod_template_sound_project_143_01.zip. Le wiki indique FMOD 2.03.09 à partir du jeu 1.56, mais il n'existe AUCUN modèle 1.5x/1.6x. Le jeu 1.61 utilise FMOD 2.3.11.
- [vérifié 2026-11-03] Le modèle 1.43 est téléchargé dans `Outils admin\soundforge\template_scs_143\`.
  - Son `build\guids.txt` contient master, master.strings, 28 bus et 7 paramètres globaux : cabin_out, cabin_rot, cabin_type, daytime, surr_type, wnd_left et wnd_right.
  - TOUS les bus et GUID des .bank.guids du jeu 1.61 s'y trouvent à l'identique, y compris /cabin/window_out et /game/intro. Le modèle a 2 bus de plus : /game/voiceover/effects et /speaker.
  - Le modèle 1.43 est donc une base valide pour la 1.61.
  - Il est au format Studio.02.01, et FMOD Studio 2.03 le convertit à la première ouverture. Il faut toujours travailler sur une COPIE et garder le zip intact.
  - Il ne contient aucun événement ni aucune banque camion. Les événements sont à créer (voir plus haut dans cette section).

## 3. Méthode pour une demande de joueur (son moteur) [à vérifier sur le modèle officiel SCS]

1. Identifier le camion et le moteur visés dans base_connaissances.json (id, .sui utilisé, banque actuelle).
2. Partir du modèle de projet FMOD officiel SCS (mêmes bus, paramètres et GUID), jamais d'un projet vide.
3. Créer les événements obligatoires (section 2). Les piloter par `rpm`/`load` (couches par régime, fondu enchaîné), `turbo` et `brake` (frein moteur), avec `cabin_out`/`cabin_type` pour l'intérieur et l'extérieur.
4. Compiler avec fmodstudiocl en version 2.03.x (FMOD Studio 2.03.12 et 2.03.15 sont installés chez Mendy).
5. Livrer un mod : `sound/truck/<banque>.bank`, `.bank.guids`, `.soundref` et `.sui`. Ils remplacent uniquement ceux du moteur visé. Ne jamais écraser /sound/truck/default.
6. Relancer l'analyseur : le camion doit passer « compatible ». Puis tester en jeu : game.log ne doit montrer aucune erreur [fs] ni FMOD.

## 3bis. Préparation des couches dans l'atelier (phase 1)

- Une couche par régime, enregistrée à régime stable : ralenti (~600 tr/min), puis 3 à 5 régimes en charge, et les mêmes sans charge (lever de pied).
- Couper un morceau stable de 2 à 10 s. Régler le fondu de boucle (100 à 300 ms) pour que la boucle ne claque pas.
- Le simulateur de l'atelier fait un fondu à puissance constante entre les deux couches voisines, et accélère ou ralentit chaque couche selon le rapport régime / régime de la couche (0,5 à 2). Le mélange charge / sans charge suit `load`. C'est la même logique que celle qui sera écrite dans FMOD (paramètres rpm et load).
- L'export des couches se fait en WAV 48 kHz 24 bits (coupe, volume, égaliseur et boucle sans clic appliqués). Ce sont ces fichiers qui seront importés dans le projet FMOD en phase 3.

## 4. Pièges constatés sur le PC de Mendy [vérifié]

- ZAF (Zeemods Audio Framework) est actif sans `zeemods.common`, ce qui donne FMOD_ERR_FILE_NOTFOUND dans game.log.
- Le mod "Volvo FH Open pipe 1000HP" remplace `engine/sound_d13.sui` du FH 2024 et pointe vers `volvo_d13.bank`, qui est absente.
- Les mods chiffrés (BBM VPE, Ekeri No REF Tape, TM...) sont illisibles. Pas d'intégration sans l'accord de leur auteur.

## 5. Règles de diffusion

TSC vend le logiciel et son assistant de création, jamais les fichiers d'ETS2, de FMOD ni de mods tiers.
Les fichiers lus restent sur le PC de l'utilisateur. Les créations appartiennent à leur auteur.

## 6. Blender (atelier skins et modèles) : à compléter

- Installé chez Mendy :
  - Blender 3.6.23 avec SCS Blender Tools 2.4.1 (io_scs_tools). Son bl_info affiche (2, 4, "aeadde03") même en 2.4.1. Réinstallé et vérifié le 2026-11-03, licence GPL-2.0.
  - Un profil Blender 5.2 sans add-on.
  - Paint.NET 5.1.12.
  - SCS Extractor (06/2025).
- À apprendre dans la documentation officielle SCS (modding.scssoft.com) :
  - le travail avec SCS Blender Tools (import/export PIM/PIT, Scs Root, looks, variants) ;
  - les Conversion Tools (converter_pix, packer .scs) ;
  - les modèles de peinture officiels par camion ;
  - les textures DDS/TOBJ.
- La dernière version de SCS Blender Tools est la v2.4.1 (github.com/SCSSoftware/BlenderTools/releases). Elle est supportée officiellement jusqu'à Blender 3.6. Sous Blender 5.x, elle donne l'erreur "No module named 'bgl'". Il faut donc rester sur Blender 3.6 LTS pour l'atelier.
- L'asset officiel est scs_blender_tools_addon.zip, pas le zip du code source.
- Le fichier config.txt de l'add-on contient les réglages de l'utilisateur. Il faut le conserver à chaque mise à jour.

## 7. Interface des deux modules : style tablette TSC [demande de Mendy, 2026-11-03]

Sound Forge et l'atelier Blender s'affichent dans le style de la tablette TSC (Tete_Pilote_TSC\ui\index.html), chacun avec son espace de travail. L'aperçu validé le 2026-11-03 à 05h09 est à https://claude.ai/artifact/HmPSAW1AphQc5GC6UTqP9W.

Repères du style existant :
- Couleurs :
  - fonds : --shell #050608, --bezel #121418, --scr #0a0b0e, --p #111317, --p2 #16181d ;
  - lignes : --line #24272e, --line2 #1b1e24 ;
  - texte : --tx #f1f2f4, --mut #8b8f99 ;
  - accents : --red #d9202b, --red2 #a5141d, --gold #e2b04a ;
  - états : --ok #2fd16b, --warn #ffb020, --bad #ff4b57.
- Polices : Montserrat pour les titres, Inter pour le texte, Kaushan Script pour l'accent.
- Composants :
  - .tab : cadre de la tablette, coins de 44px.
  - section.pg : une par page (p-home, p-veh, p-atelier, p-set...).
  - .grid : colonne principale et panneau latéral de 340px, une seule colonne sur petit écran.
  - .card : fond --p, bord --line, coins de 12px.
  - .stats : 4 colonnes, qui passent à 2.
  - .kv, .tg, et .hint (--mut, 12px).
  - Icônes SVG en ligne dans les h3.

## 6bis. Ressources libres de droit (sons, modèles, textures) [règle Mendy, 2026-11-03]

- Acceptées : CC0 / domaine public (Poly Haven, ambientCG, Kenney, Freesound filtré CC0, OpenGameArt filtré CC0), et CC-BY à condition de citer l'auteur dans les crédits.
- Refusées : non commercial (NC), sans modification (ND), « gratuit » sans licence écrite, fichiers extraits d'autres jeux, modèles qui reproduisent les logos et marques (Scania, Volvo...).
- Poly Haven : API publique utilisable même en commercial, avec la mention « Powered by Poly Haven » si l'appli l'utilise en direct.
- Freesound : l'API n'est pas libre pour une appli vendue (accord commercial à négocier avec l'UPF). Le joueur télécharge lui-même ses sons CC0 sur le site, puis les importe.
- Dans Sound Forge, chaque son porte sa licence et sa source. Un son à licence refusée n'est jamais exporté. Un son CC-BY sans auteur bloque l'export. L'export écrit CREDITS_sons.txt.
- Bibliothèque de départ sur le PC de Mendy : Outils admin\soundforge\bibliotheque_libre\ (modeles, textures, sons), avec un LICENCE.txt par ressource et INDEX.csv.
