# TSCF Audio Lab : audit et plan (03/11/2026)

Réponse à la section 12 du cahier des charges de Mendy (`project-files/sound_forge/TSCF_Audio_Lab_cahier_des_charges.pdf`).
Audit fait en lecture seule. Aucun fichier de Mendy n'a été modifié, et rien n'a été installé.

## La vérité sur l'« écoute » jusqu'ici (sections 1 et 2)

Claude, le modèle qui fait ce travail, **ne reçoit pas de son**. Il lit des chiffres. Tous les avis donnés jusqu'ici sur les aperçus v2 à v9 viennent de mesures : bandes de fréquence, crêtes, enveloppe, craquements. Ce ne sont pas des écoutes. Le cahier des charges a raison : une mesure n'est pas une sensation. Pour une vraie perception auditive par une IA, il faut un modèle audio multimodal appelé par API. C'est payant, et les sons partent chez un tiers : la décision revient à Mendy.

## Section par section

| § | Exigence | Ce qui existe | Manque |
|---|---|---|---|
| 2 | Perception auditive par modèle audio | rien | choix d'un modèle audio par API (décision de Mendy : coût, confidentialité), à tester sur ses vrais sons |
| 2 | Mesure numérique | `mesure_son.py` (bandes, crête, enveloppe, allumage, craquements), `audio_lab/controles.py` | librosa/SciPy pas indispensables : tout tourne en NumPy |
| 3 | Outils | PC : Python 3.15.1 + NumPy 2.5.4, FMOD Studio 2.03.12 et 2.03.15 + fmodstudiocl, vgmstream, Blender 3.6, template SCS 1.43 migré, exemple Peterbilt (relevé par la session PC, 03/11). Cloud : ffmpeg | PC : FFmpeg, SciPy, librosa, soundfile, REAPER ou Audacity, Sonic Visualiser, Demucs/UVR. Python 3.15 est trop récent pour librosa, SciPy et Demucs : il faudrait un Python 3.12 à part. Installation par Mendy uniquement. |
| 4.1-4.2 | Inventaire + SHA-256, originaux en lecture seule | **fait** : `audio_lab/inventaire.py`, 87 fichiers (Mes_sons copiés + 3 vidéos) → `expert_son/audio_lab/inventaire_sources.json/.csv`. `verifier()` recalcule les empreintes avant chaque travail. | colonne « droits » à remplir par Mendy |
| 4.3 | WAV de travail sans écraser | extraction ffmpeg des vidéos (cloud), copies seulement | — |
| 4.4 | Segments étiquetés | repérage chiffré des 3 vidéos (ralenti stable 164L 1-10,5 s ; R580 115-138 s et 204-223 s ; R620 surtout en roulant) | fichier d'étiquettes horodaté (à faire, étape 2) |
| 5 | Fondamentale, harmoniques, régime | 164L : allumage 33,3 Hz → 500 tr/min, harmoniques 66,7 et 100 Hz, modulation 4,2 et 8,4 Hz | aucune architecture moteur n'est déduite du son seul (règle respectée) |
| 6 | Couches idle/low/mid/high, accélération, décélération, turbo, frein moteur, démarrage, arrêt | ralenti réel (v8), couches 500-1300 des sons de Mendy, claquements, sons d'air | couches low/mid/high tirées des vraies vidéos (R580, R620), turbo, frein moteur |
| 7 | FMOD + SCS | projet `tsc_v8_mendy` (template 1.43 migré 2.03), script de construction, vrai build v2 réussi le 03/11 15:26 (non installé) ; plan v3 `experts/forge/PLAN_MOD_V8_V3.md` | build v3 après accord de Mendy |
| 8 | A/B à volume égal | **fait** : `audio_lab/ab.py` (même sonie, alternance A/B avec repères sonores, écarts de bandes) | captures cabine/extérieur en jeu |
| 9 | Tests automatiques + rapport CSV/JSON horodaté | **fait** : `audio_lab/controles.py` (crête vraie, LUFS BS.1770, écrêtage, DC, silences, raccord de boucle) ; 4 tests vérifient LUFS (-3,01 sur un sinus 1 kHz), crête vraie, raccord et inventaire | — |
| 10 | Copies, versions horodatées, journal, restauration | mémoire commune (`memoire/entrees.jsonl`), sources en lecture seule, sauvegarde v1 du projet FMOD | procédure de retour arrière écrite pour l'essai dans TSCF_Lab |
| 11 | Livrables | WAV d'aperçu, rapports, projet FMOD | projet REAPER ou Audacity (une fois l'outil installé), .scs, captures en jeu ; tout le reste est marqué « non testé » |

## Premiers résultats des tests automatiques (`expert_son/audio_lab/`)

- Aperçus v5 à v9 : aucun écrêtage, aucun décalage continu (DC), aucun silence anormal. Seule la crête vraie du ralenti v6 à 120 tr/min dépasse légèrement −1 dBTP.
- Boucles de ralenti réelles v8 : les raccords sont propres sur A, C et D. Sur **B (R580)**, le niveau saute de 2,3 dB entre la fin et le début de la boucle : il faudra la recouper avant de l'utiliser.

## Plan, dans l'ordre des dépendances

1. **Fait** : inventaire SHA-256, contrôles automatiques, A/B à volume égal (NumPy seul, testé).
2. Étiquettes horodatées des segments des 3 vidéos (ralenti, montée, charge, décélération, rapports, freins, air), puis couches low/mid/high tirées des vrais enregistrements.
3. **Écoute par IA** : seulement si Mendy choisit un modèle audio. Test d'abord sur 5 extraits connus, avec comparaison à son avis.
4. Projet FMOD v3 (Forge) sur une copie, vrai build, banque décodée puis contrôlée par l'étape 1.
5. .scs contrôlé (Mods), essai dans TSCF_Lab avec sauvegarde, une fois le fil Graphics prévenu, puis lecture de game.log.
6. Validation à l'écoute par Mendy : c'est lui qui tranche.

## Décisions qui reviennent à Mendy

- Le modèle audio pour l'écoute par IA : quel service, avec quel budget, et accepte-t-il d'envoyer ses sons à ce tiers ?
- L'installation sur le PC d'un Python 3.12, de FFmpeg, SciPy et librosa, puis de Demucs, qui demande torch et environ 2 à 3 Go. Il reste environ 7,4 Go libres.
- REAPER (payant après l'essai) ou Audacity (gratuit) pour le projet éditable.
