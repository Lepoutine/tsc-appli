# Recette Sound Forge : créer l'événement moteur par script

Statut : [à vérifier] C'est le plan de la phase 3, construit à partir des fiches 01 à 03 et de l'exemple officiel Peterbilt (fiche 05, à suivre en priorité pour les plages et les courbes). Chaque point sera coché après le test sur le PC de Mendy, puis en jeu.

## Entrée

Le projet `.tscforge.json` de l'atelier, et les couches exportées en WAV 48 kHz 24 bits :
- `ralenti_600.wav` ;
- `charge_<rpm>.wav` ;
- `sans_<rpm>.wav` ;
- `turbo.wav` ;
- `demarrage.wav`.

## Étapes (script lancé par fmodstudiocl, ou par le serveur de scripts sur le port 3663)

1. Copier le modèle SCS 1.43 vers `Bureau\TSC_Sound_Forge\<projet>\FMOD_Project\`. Renommer le `.fspro` et l'ouvrir dans FMOD Studio 2.03 (conversion automatique).
2. Créer la banque `tsc_<projet>` (en minuscules) avec `studio.project.create('Bank')`.
3. Créer les dossiers d'événements `engine` et `remote`. Créer les événements `engine/engine`, `engine/exhaust` et `engine/turbo` (3D), et `engine/start_bad` (3D, joué une fois). Dans une autre banque `tsc_<projet>_rm`, créer `remote/engine`.
4. Créer les paramètres d'événement :
   - `engine/rpm` de 0 à 3000 ;
   - `engine/load`, `engine/brake` et `engine/turbo` de 0 à 1 ;
   - `engine/play` de 0 à 1.
   - Faire de même avec `exhaust/*` sur l'échappement, et `rpm`, `load`, `brake`, `turbo` et `play` sur `remote/engine`.
5. **Moteur** : ajouter une piste « charge » et une piste « sans charge ».
   - Sur chaque piste, poser un SingleSound par régime sur le paramètre `rpm`, de la moitié de l'écart avec le voisin du bas à la moitié de l'écart avec le voisin du haut.
   - Ajouter des fondus enchaînés (`setFadeInCurve` / `setFadeOutCurve`) qui se chevauchent.
   - Automatiser la hauteur (pitch) de chaque instrument selon `rpm` (rapport rpm / régime de la couche, comme dans le simulateur de l'atelier).
   - Automatiser le volume des deux pistes selon `load`, comme dans l'exemple SCS : uniquement « sans charge » en dessous de 0,2, fondu entre 0,2 et 0,35, uniquement « charge » au-dessus. Une piste « nofuel » joue si load < 0,05.
   - Ajouter une piste de frein moteur (brake 0 = -80 dB, 0,21 = -1 dB, 1 = +3 dB, coupée sous ~860 tr/min), et intégrer le démarrage et l'arrêt pilotés par play.
6. **Échappement** : même structure avec les couches marquées « échappement », ou une copie filtrée des couches moteur s'il n'y en a pas [à décider avec Mendy].
7. **Turbo** : une boucle, avec volume et hauteur automatisés par `engine/turbo`.
8. **start_bad** : un MultiSound avec les sons de démarrage, en lecture aléatoire.
9. **Routage** : engine vers `bus:/outside/exterior/truck_engine`, exhaust vers `truck_exhaust`, turbo vers `truck_turbo`, start_bad vers `truck_engine`, remote vers `traffic`.
10. Assigner les événements à leurs banques, puis `save()`.
11. `build({ banks: ['tsc_<projet>', 'tsc_<projet>_rm'] })`, puis `exportGUIDs()`. Renommer `GUIDs.txt` en `.bank.guids` pour chaque banque.
12. **Vérifier** : les fichiers existent, l'en-tête RIFF FEV est en version 146, le `.guids` contient les 5 événements, et l'analyseur passe le camion en « compatible ».
13. Écrire les `.soundref` et le `.sui` du moteur visé, puis le mod (phase 5).

Si le build échoue, ne JAMAIS annoncer de succès, et ne jamais fabriquer de `.bank` ni de `.guids`.
