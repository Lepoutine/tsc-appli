# API télémétrie SCS : ce qu'elle donne, ce qu'elle ne donne pas

- Sources, lues le 04/11/2026 :
  - `scssdk_telemetry_truck_common_channels.h` et `readme.txt` du SDK télémétrie SCS, copie publiée avec la caisse scs-sdk-rs 0.2.2 :
    https://rust-digger.code-maven.com/src/scs-sdk-rs-0.2.2/sdk/include/common/scssdk_telemetry_truck_common_channels.h
    https://rust-digger.code-maven.com/src/scs-sdk-rs-0.2.2/sdk/readme.txt
  - Les en-têtes officiels utilisés par notre plugin sont dans le dépôt du code (fiche `sdk_telemetrie_scs`, ETS2 télémétrie 1.18).
- Statut : vérifié partiel. C'est une copie tierce du SDK : avant de s'appuyer sur un canal précis, le recouper avec l'en-tête du dépôt du code. Seul le fichier des canaux **camion** a été lu ; les canaux remorque, mission et les événements de jeu sont dans d'autres en-têtes, non relus ici.

## Règles du SDK (readme)
- Les API **ne sont pas sûres entre fils** : le jeu appelle le plugin depuis un seul fil (le fil principal), et le plugin ne doit rappeler le jeu que depuis ce fil, pendant un appel du jeu.
- Chaque pas de physique compte comme une « image » pour la télémétrie.
- Les canaux `dev.` ne sont pas documentés : les ignorer.
- Si l'enregistrement d'un canal échoue, c'est qu'il a été retiré : le plugin doit prendre une valeur par défaut, pas planter.
- L'échelle de la carte est donnée par le canal `local_scale` (le temps et les distances du jeu ne sont pas ceux du réel).

## Unités utiles au Pilote de tête et au tachygraphe
- Vitesse `truck.speed` en m/s (négative en marche arrière) ; régulateur `truck.cruise_control` en m/s, 0 si coupé.
- Régime `truck.engine.rpm` ; rapport `truck.engine.gear` (>0 avant, 0 point mort, <0 arrière).
- Pédales en deux versions : `input` (ce que fait le joueur) et `effective` (après courbe, régulateur, boîte auto). Le frein `effective` **n'inclut pas** ralentisseur, frein de parc ni frein moteur, qui ont leurs propres canaux.
- Pression d'air en psi, températures en °C, carburant et AdBlue en litres, consommation en L/km, autonomie en km, odomètre en km.
- Navigation : distance restante en mètres, temps restant en secondes, limite de vitesse en m/s, ces trois-là **selon le conseiller de route** (et l'option « limite du conseiller » du joueur).
- Rotations en **tours**, pas en degrés ni en radians.

## Ce que le fichier des canaux camion ne donne pas (donc à calculer ou à éviter)
- Aucun état d'activité du conducteur (conduite, autre travail, disponibilité, repos) : le tachygraphe TSC doit le **déduire** (vitesse, moteur, temps du jeu), comme dans la fiche `tachygraphe_165_2014`.
- Aucune information sur les autres véhicules ou la circulation.
- Température des freins **approximative**, pour le camion entier, pas par roue.
- Adhérence de la route : seulement un indice de « substance » par roue, qu'il faut traduire avec la configuration du jeu.
- Relation non linéaire entre la levée d'essieu et son décalage en mètres.
