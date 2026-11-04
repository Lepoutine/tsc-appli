# TSC Neural sur d'autres jeux : ce qui est commun, ce qui est propre a ETS2

Objectif Mendy (04/11/2026) : a terme, TSC Neural sur tous les jeux compatibles. Un jeu n'est dit « compatible » qu'apres mesure
(juge v3 + garde-fous + cout GPU), comme ETS2. Jamais sur un jeu multijoueur dont l'anti-triche l'interdit, aucun contournement.

## Commun (reutilisable tel quel)
- `neural/` : reseau par pixel, caracteristiques, entrainement (juge PatchGAN + juge vision DINOv2), export HLSL, gardes de champion.
  Le reseau ne voit que l'image finale 8 bits (+ guide optionnel) : rien de propre a ETS2.
- Mode « image seule » (sans guide) : marche sur n'importe quelle image finale (10 % de l'entrainement est deja fait sans guide).
- Juge v3, jeu de test fixe, images reelles Panoramax libres, garde-fous de livraison, `tests/`.
- `ps_ldr` : recomposition detail garde + bloc `neural_ldr` (dependent seulement de tLdr, tProf, tGb2, p1, p11).

## Propre a ETS2 (a refaire par jeu ou par moteur)
| Element | ETS2 | Ce qu'il faut pour un autre jeu |
|---|---|---|
| Reperage des passes | E_GBUF / E_HDR par OMSetRenderTargets (formats, 4 cibles G-buffer, HDR RGBA16F) | sonde de trace (deja dans le plugin) puis regles du jeu |
| Profondeur | D32S8 Z inverse, ciel 0, cabine > plage_max | detection auto du tampon de profondeur (comme ReShade) + sens du Z |
| Constantes guide | proche 0,2 / plage_min 0,01 / plage_max 0,9 / decalage_z -0,000194 (ini + caracteristiques.py) | profil par jeu (memes cles ini) |
| Albedo | cible 2 du G-buffer (gb2) | souvent absent : guide albedo a 0 (le reseau sait faire, cas « sans G-buffer ») |
| Multi-ecrans | 3 vues, ordre HDR L,R,C / LDR L,C,R (ldr_hdr0..2) | une vue le plus souvent |
| Pieges moteur | vtable 50/53 remise (copie au passage G-buffer -> HDR, 0.16.5) | a decouvrir par jeu |
| API | DX11 | DX12/Vulkan = autre plugin (chantier separe) |

## Ordre propose
1. American Truck Simulator (meme moteur : verifier seulement formats et vues).
2. Jeux DX11 solo, mode image seule, puis guide profondeur auto.
3. DX12 / Vulkan.
Pour chaque jeu : enregistrer ses images (cle enregistre), petit entrainement --depart du champion ETS2, mesure juge v3, garde-fous.
