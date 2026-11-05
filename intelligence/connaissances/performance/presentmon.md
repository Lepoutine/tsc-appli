# PresentMon : mesurer le frametime d'ETS2

- Source : https://github.com/GameTechDev/PresentMon (README, lu le 03/11/2026)
- Version : dépôt GameTechDev/PresentMon, branche principale au 03/11/2026 (licence MIT, Intel)
- Domaine : performance. Statut : vérifié (documentation officielle), pas encore lancé sur le Shadow.

## Ce que dit la source
- Trois parties : l'outil console (`PresentMon`), un service, et une appli de capture avec affichage en jeu.
- Il lit les événements ETW de Windows sur les présentations d'images : pas d'injection dans le jeu, donc pas de conflit avec ReShade ni avec notre plugin DX11.
- Il faut lancer en administrateur, ou être membre du groupe « Performance Log Users ».
- Mesures utiles : `CPUFrameTime` (temps d'une image côté CPU), `msGPUActive` (temps où le GPU travaille), `DisplayLatency` (de l'entrée à l'affichage).
- Avertissement de la doc : avec la planification GPU accélérée par le matériel (HAGS), les temps GPU peuvent être faussés.

## Comment TSC s'en sert
- Remplace le compteur interne pour juger une version de TSC Graphics : même trajet, même météo, 60 s, puis moyenne et 1 % bas du frametime.
- Lancement : par Mendy (binaire externe), jamais par Claude sur le PC. Capture en CSV, analysée ensuite dans le cloud.
- Sur le Shadow, noter si HAGS est actif avant de comparer des temps GPU.
