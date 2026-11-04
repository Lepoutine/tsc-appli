# Flaques et gerbes d'eau : plan technique (demande Mendy 04/11/2026)

Le reseau TSC Neural n'invente pas d'objet (choix de conception : pas de delire, pas de scintillement). Les flaques et les gerbes
sont donc des EFFETS du plugin, regles ensuite sur des photos reelles de pluie (intensite, taille, couleur), comme le reste.

## Ce qui existe deja (route(), HDR)
- Surfaces mouillables = normales vers le haut (G-buffer profondeur -> normale), assombrissement de l'asphalte mouille,
  reflets par marche de rayon dans l'ecran (lumieres etirees en colonnes, flou selon la distance), marquages mats.
- Ambiance pluie lissee (p18.y), rideau de pluie, brume, eau sur vitre (0.14).

## Flaques : ce qui manque = une position MONDE stable
Un masque de flaques calcule en coordonnees de vue glisserait avec la camera (faux). Il faut ancrer le motif au sol du monde :
1. Sonde 0.19 : retrouver dans les tampons de constantes du jeu (tampon 2 Mo deja vu, FOV/proche) la matrice vue -> monde
   ou la position camera (critere : stable a l'arret, varie comme la telemetrie en roulant). Lecture seule.
2. Masque : bruit fractal 2D sur (x, z) monde, seuil selon l'ambiance pluie et le temps depuis le debut de la pluie
   (les flaques grandissent), module par la courbure locale (creux = plus d'eau) et coupe sur les marquages.
3. Rendu : dans une flaque, rugosite ~0 (reflet net, lod 0), Fresnel eau, asphalte presque noir ; bord doux 0,3 m ;
   gouttes de pluie = petits anneaux animes sur la normale.
4. Reglage sur photos reelles de pluie (Panoramax / Wikimedia libres) : part de la route en flaque, contraste du reflet.

## Gerbes d'eau
- Notre camion : vitesse et position par la telemetrie (plugin tsc-telemetrie) -> gerbe derriere les roues en espace vue
  (camera exterieure) et brume d'eau dans les retroviseurs/vue arriere ; force ~ vitesse^2 x ambiance pluie x flaque sous la roue.
- Autres vehicules : le SDK ne donne pas leur position. Option : detection dans l'image + profondeur (moins precise), a tester.
- En cabine : surtout la brume soulevee par les vehicules devant (deja partiellement : brume au sol), a renforcer derriere les camions.

## Ordre
Apres les lumieres (run6/7/8). Etape 1 = sonde de la matrice monde (lecture seule, aucun risque), puis prototype flaques.
