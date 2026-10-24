# TSCF Spartan Studio

Atelier de création de livrées ETS2 de Truck So Clean France : on compose une peinture en direct sur le camion et sa remorque en 3D,
on la peaufine (bientôt à la voix), et le mod n'est généré qu'après validation.

État : phase 3 (édition de la livrée : calques, propriétés, déplacement à la souris, annuler, sauvegarde, export du projet). Voir `docs/ARCHITECTURE.md` pour le plan et `docs/RAPPORT_TESTS.md` pour ce qui est vérifié.

## Lancer

1. Copier le dossier `studio` sur le PC (par exemple `Documents\TSC Driver\Spartan_Studio`).
2. Double-cliquer `Lancer_Studio.bat` : l'atelier s'ouvre dans Microsoft Edge. Fermer la fenêtre noire arrête l'atelier.

Rien n'est installé et rien n'est exposé sur le réseau (adresse 127.0.0.1 uniquement).

## Utiliser

- Glisser : tourner autour de l'ensemble · Molette : zoom · Clic droit : déplacer · Double-clic : zoom sur le détail visé.
- Barre du bas : vues 3/4 avant, avant, gauche, droite, arrière, 3/4 arrière, dessus, et capture d'image.
- Touches 1 à 6 : avant, arrière, gauche, droite, dessus, 3/4.
- Panneau de gauche : choix du camion et de la remorque, affichage (ensemble, écartés, camion seul, remorque seule), éclairage.
- Un bandeau orange signale tout modèle provisoire (forme générique, pas le modèle ETS2 exact).

## Modifier la livrée

- Panneau de droite : onglet Camion ou Remorque, puis les calques (fond, vagues, bandes, textes, images). L'œil masque un calque, les flèches changent l'ordre.
- Cliquer un calque, ou directement l'élément sur le véhicule, pour le modifier : texte, police, couleur, finition, taille, position en mètres, inclinaison, opacité. Glisser l'élément sur le véhicule le déplace.
- « Ajouter » : texte, bande, vague, image (le lion TSCF ou une image du PC).
- Tout est enregistré automatiquement sur le PC. « Exporter » crée un fichier `.tscf.json` (sauvegarde, partage, et base du futur export du mod).

## Ajouter un modèle réel

Les modèles réels sont convertis sur le PC depuis les fichiers du jeu ou du mod, et ne sont jamais publiés.

```
python outils/pmg_vers_glb.py --code <code TSC>/tests_pilote/cuir --racine <dossier extrait> ^
       --modele tnkdorse/chassis.pmg --roue tnkdorse/upg/wheel/disk.pmg --roue tnkdorse/upg/wheel/ftire.pmg ^
       --sortie modeles/citerne_tsc.glb
```

Le Scania R 2016 s'assemble avec plusieurs `--modele` (cabine + châssis), `--parties defaultpart,eu_part`, un `--accessoire` par pièce (posé sur le repère du même nom), `--roue-avant`, `--roue-arriere` et `--sellette hook_t`.

Puis l'ajouter à `modeles/modeles.json` (`camions` ou `remorques` : `id`, `nom`, `fichier`). Les fichiers `.glb` ne vont pas dans le dépôt.

## Contenu

- `index.html`, `css/`, `js/` : l'atelier (`scene.js` rendu et caméra, `vehicules.js` modèles, `projection.js` placement de la livrée, `livree.js` peinture des éléments).
- `vendor/three` : Three.js 0.170 (licence MIT) ; `vendor/polices` : Saira, Rajdhani, Kaushan Script (licence OFL).
- `outils/pmg_vers_glb.py` : conversion des modèles SCS.
- `serveur.ps1`, `Lancer_Studio.bat` : lancement local.
