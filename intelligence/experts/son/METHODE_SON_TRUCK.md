# Expert son : méthode pour le « son truck ultime » (V8 Scania R/S 2016)

1re tâche de l'expert Sound Engineering, reprise du fil Sound Forge le 03/11/2026. L'état de départ est dans
`project-files/sound_forge/passation_v8_mendy.md`. Sur le PC, il y a aussi `Bureau\TSC_Sound_Forge\PASSATION_SON_TRUCK.md`.
Statut : **conçu**. Rien n'est validé tant que Mendy n'a pas écouté la vraie banque dans TSCF_Lab.

## Pourquoi la v2 ne suffit pas (hypothèses à confirmer par la mesure)

La v2 a corrigé ce qui s'entendait comme un défaut : plus de coupure, plus de grésillement mesuré. Elle n'a pas travaillé ce qui fait un V8 :
- des boucles coupées au passage par zéro, mais pas sur un **cycle moteur entier**, donc le motif d'allumage peut sauter à chaque tour de boucle ;
- des sources courtes (3 à 5 s) et déjà compressées, avec peu de couches basses ;
- des coups de gaz obtenus en accélérant le même son, sans montée ni descente propres ;
- aucune écoute de la vraie banque, et aucun essai en jeu.

## Méthode, dans l'ordre

1. **Mesurer avant d'agir**, sans rien demander à Mendy. Comparer chaque extrait v2 à la référence avec `mesure_son.py comparer`. Les références sont le V8 open pipe de `Mes_sons`, la vidéo citée par Mendy et les passages de coups de gaz du Cadillac V8 notés dans la passation. On obtient en clair ce qui manque : le gras sous 250 Hz, le borborygme (demi-ordre), l'irrégularité du ralenti, les craquements, l'écrêtage, le punch, les jonctions de boucle.
2. **Choisir les sources par la mesure.** Parmi les 360 sons, garder pour chaque régime le meilleur : régime estimé juste, sans écrêtage, le plus long, le plus irrégulier. Un tableau source → régime → note va dans le rapport.
3. **Couper chaque boucle sur un nombre entier de cycles moteur.** En 4 temps, un cycle dure 2 tours, soit 120 / tr/min secondes : 0,2 s à 600 tr/min. Le point de coupe est un passage par zéro proche d'un multiple de ce cycle, avec un fondu de 20 à 50 ms. La mesure de jonction doit valoir moins de 20 x et moins de 2 dB.
4. **Monter des couches réelles en charge et sans charge** à 600, 800, 1000, 1200, 1500, 1800 et 2100 tr/min, avec un fondu à puissance constante entre deux couches. On ne décale jamais une couche de plus de 12 % de hauteur.
5. **Faire des coups de gaz dédiés** : une montée et une descente courtes, tirées de vrais coups de gaz, plus une couche de craquements de décélération quand la charge vaut 0 et que le régime descend. Comment les déclencher dans ETS2 reste **à vérifier** dans les pages SCS TruckEngine (paramètres rpm et load, évènements disponibles) avant de coder.
6. **Gras et grave** : ils viennent des sources choisies et des couches basses, pas d'un gros égaliseur. On garde au plus +4 dB de gain, sans écrêtage et avec un facteur de crête proche de la référence.
7. **Deux mixages**, un pour l'extérieur et un pour la cabine. Ils passent par les bus du template SCS 1.43, et le master reste intact.
8. **Construction** : expert Sound Forge. Le build passe par `fmodstudiocl` et les GUID exportés sont les vrais. Le .scs est contrôlé par Mod Engineering.
9. **Validation** : on écoute d'abord la vraie banque compilée (décodée), puis on installe dans **TSCF_Lab seulement**, avec une sauvegarde, après l'accord de Mendy sur un aperçu. Son retour va dans la mémoire (`tsc_ia.py noter --agent son --type test`).

## Outils

- `mesure_son.py`, testé (numpy seulement, comme sur le Shadow) : il mesure et compare deux sons, puis donne le diagnostic en clair.
- Après le passage de l'expert : `Mesurer_Mes_sons.bat`, qui relève tous les sons de `Mes_sons` d'un coup, en lecture seule.
