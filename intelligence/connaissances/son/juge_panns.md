# Juge son PANNs Cnn14 : provenance, licence, ce qu'il mesure

- Choix de Mendy (04/11/2026 21:47) : juge pré-entraîné LOCAL, gelé, aucun son envoyé à un tiers ; son oreille tranche.
- Sources (lues le 04/11/2026) :
  - code et architecture : https://github.com/qiuqiangkong/audioset_tagging_cnn (licence MIT) ; article Kong et al., « PANNs: Large-Scale Pretrained Audio Neural Networks for Audio Pattern Recognition » (2020) ;
  - poids : https://zenodo.org/records/3987831, fichier Cnn14_mAP=0.431.pth, 327 428 481 octets, md5 541141fa2ee191a88f24a3219fff024e, licence **Creative Commons Attribution 4.0** : usage commercial permis, **attribution obligatoire** (« PANNs, Qiuqiang Kong et al., CC BY 4.0 ») dans les crédits de tout produit qui s'en sert ;
  - étiquettes : class_labels_indices.csv d'AudioSet (copie du dépôt PANNs, intelligence/experts/son/audioset_labels.csv).
- Où sont les poids : project-files/tsc_intelligence/expert_son/modeles/ (pas dans le dépôt : 327 Mo). Copie d'origine : Téléchargements de Mendy.

## Ce qui est vérifié
- Lecture des poids par un dépickleur restreint (seuls les tenseurs passent : un fichier piégé est refusé, test unitaire).
- Réécriture NumPy de Cnn14 : sur le vrai ralenti 164L, sorties « Vehicle » 0,51, « Engine » 0,15, « Idling » 0,15, « Heavy engine (low frequency) » 0,10 : la chaîne entière est cohérente.
- Sans aucun réglage (centres de classes), 25 sons sur 28 bien classés entre vrais enregistrements et synthèses refusées (validation un-contre-tous).

## Limites (méthode Graphics : comparer à contenu semblable)
- Les vrais enregistrements entre eux sont loin (distance 0,29 à 0,34) : le juge entend aussi le micro, le vent, la pièce. Ne comparer qu'à régime égal, et ne jamais lire la distance brute comme « plus réel ».
- Sur un extrait court tiré au hasard, la tête « réalisme » (centres de classes) se trompait 2 fois sur 8 au banc. Le 04/11 au soir : +45 vrais moteurs libres (fiche bibliotheque_commons_son) et tête logistique équilibrée ; validation un-contre-tous par fenêtre de 4 s : synthèses reconnues 53/59 (contre 46/59), vrais fichiers 59/61 (contre 57/61) ; au banc, 10 sur 12 même sans aucun son du même camion à l'apprentissage (contre 9 sur 12 avec). Reste faible : les synthèses à coups de gaz (v3_2).
- Le juge mesure, il n'écoute pas pour Mendy.
