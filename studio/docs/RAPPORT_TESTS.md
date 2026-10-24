# TSCF Spartan Studio : rapport de tests

Seul ce qui a réellement été essayé est marqué « validé ».

## Phase 2 (24/10/2026)

Essais dans Chromium (rendu logiciel SwiftShader) sur un serveur local, captures à l'appui.

| Fonction | Résultat |
|---|---|
| Conversion de la vraie citerne TSC (mod AkirixDesign3D) en .glb : 54 pièces, ombres factices écartées, sens des faces SCS corrigé, roues posées sur les repères `wheel_*` | Validé (15 Mo) |
| Chargement de la citerne réelle, attelage sur le repère `hook` (z −4,99) | Validé |
| Tracteur provisoire type Scania R, signalé par le bandeau orange | Validé |
| Vrai Scania R 2016 converti depuis les fichiers du jeu : cabine R haute + châssis 4x2 (parties « défaut » et « EU », jamais UK), 33 accessoires posés sur leurs repères, roues avant et arrière jumelées, sellette sur `hook_t` | Validé (5 Mo), attelé à la citerne |
| Matières des pièces non peintes choisies d'après la texture d'origine (plastique noir, acier, pneus, feux) ; ombres factices `shadowonly` écartées | Validé visuellement |
| Vue de face et de dos cadrée sur la face visée (avant : calandre entière) | Validé |
| Vues 3/4 avant, gauche, droite, avant, 3/4 arrière | Validé |
| Modes ensemble, écartés, camion seul | Validé |
| Éclairages studio photo, coucher de soleil, nuit | Validé |
| Livrée d'essai projetée sur la citerne réelle et le tracteur ; texte lisible des deux côtés, non retourné | Validé |
| Matières : noir laqué vernis, rouge nacré, or (canal métal/rugosité séparé) | Validé visuellement (rendu logiciel) |
| Serveur local `serveur.ps1` : sert le dossier, types MIME corrects, refuse `../` | Validé sous PowerShell 7 (Linux) |
| `Lancer_Studio.bat` et ouverture dans Edge sur le PC de Mendy | **Non testé** (pas de Windows ici) |
| Rotation à la souris, molette, double-clic sur un détail | Code en place, **non essayé à la main** |
| Mode « remorque seule », éclairage « plein jour », vue dessus | **Non essayé** |
| Fluidité sur la carte graphique du PC | **Non mesurée** |

Limites connues :
- Le cadrage 3/4 en mode « camion seul » est décalé dans les captures automatiques (à vérifier à la main).
- Le texte d'essai TSCF sur la cabine touche le haut du toit : la vraie livrée cabine arrive en phase 3.
- Les textures d'origine du modèle (ombrage cuit, détails) ne sont pas encore chargées : les pièces non peintes sont en couleurs unies.
- La livrée d'essai ne sert qu'à juger les matières ; la vraie livrée TSCF éditable arrive en phase 3.
