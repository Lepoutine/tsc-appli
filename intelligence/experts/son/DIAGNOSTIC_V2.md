# Diagnostic de la v2 du V8 (expert son, 03/11/2026)

J'ai mesuré, en lecture seule, 65 sons copiés depuis `Bureau\TSC_Sound_Forge\Mes_sons` : les 60 sons du V8 open pipe, les 22 boucles réparées, les 4 aperçus v2 et 1 souffle. Aucun fichier n'a été modifié. Toutes les mesures sont dans `mesures_mes_sons_v8.csv`.

## Ce que montrent les chiffres

1. **Les couches hautes sont écrêtées dès la source.** Écrêtage, c'est la part des échantillons au maximum :

   | Couche | Écrêtage | Facteur de crête |
   |---|---|---|
   | 2300_op_idle | 18,6 % | 3,4 dB |
   | 2100_op_idle | 8,9 % | 4,6 dB |
   | 1900_op_idle | 4,6 % | 5,5 dB |
   | 1700_op_idle | 1,4 % | — |
   | 1500_op_idle | 1,0 % | — |

   Les boucles réparées v2 reprennent le même défaut (c_2300 à 18,6 %). Cela donne un son dur et saturé dans les montées de régime, quel que soit le réglage dans FMOD.

2. **Les coups de gaz v2 n'ont aucun craquement.** L'aperçu « trois coups de gaz » mesure 0 craquement par seconde. Tes sons « claquant_1 à 3 » en ont pourtant 12 à 15 par seconde. Les pétarades de décélération d'un V8 open pipe ne sont donc pas dans la v2.

3. **Les coups de gaz sont fabriqués** en accélérant les mêmes boucles, sans vraie montée ni redescente enregistrée. C'est ce qu'indique la passation du fil Sound Forge ; je ne l'ai pas mesuré moi-même.

4. **Les régimes inscrits dans les noms des fichiers ne correspondent pas tous au son.** Par exemple, la fréquence d'allumage de 1500_op_idle n'est pas celle d'un V8 à 1500 tr/min. Le mod d'origine décale la hauteur au moment de jouer la couche. Il faut donc caler chaque couche à l'oreille et à la mesure, et ne pas se fier au nom.

## Ce que fera la v3

- Ne garder que les couches propres : 1900_op et 2000_op_ori ne sont pas écrêtées. Les couches abîmées seront remplacées ou réparées.
- Ajouter une couche de craquements de décélération, tirée de claquant_1 à 3, qui se déclenche quand on relâche l'accélérateur.
- Faire de vrais coups de gaz, avec une montée et une redescente propres.
- Faire écouter un aperçu à Mendy avant toute installation, puis installer seulement sur TSCF_Lab.
