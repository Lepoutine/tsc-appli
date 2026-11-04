# TSC Graphics / Neural - base de connaissances prouvees (programme Virtuoso)

Regle : un fait n'entre ici qu'avec sa preuve (mesure datee, version, ou source publique avec licence). Rien d'invente.
Une hypothese non mesuree est marquee **A VERIFIER**. Les images du jeu et derives restent prives (jamais publies).

## Moteur ETS2 (DX11), observe par le plugin
| Fait | Preuve |
|---|---|
| Le moteur remet les entrees 50/53 de la vtable (ClearRTV/ClearDSV) : nos crochets de clear ne sont jamais appeles | 0.16.4 en jeu 04/11 : compteur 0 ; corrige 0.16.5 (copie au passage G-buffer -> HDR), compteur > 0 |
| Ordre des vues 3 ecrans : HDR L, R, C ; LDR L, C, R | 0.18, cles ldr_hdr0..2 = 0/2/1, a confirmer en jeu avec vue = 4 (**A VERIFIER** en jeu) |
| Le HLSL et l'ini se rechargent a chaud (1 s) | toutes les sessions 0.13 -> 0.17 |

## Rendu (mesures en jeu, TSCF_Lab, 3 ecrans)
| Fait | Preuve |
|---|---|
| 0.16.5 pluie : joint 1,03 (avant 0,81), juge 2,05 vs brut 3,07, gardes OK ; route A/B mieux 12/12 | lot_04-11_0165_pluie |
| Soleil a l'arret : libre5 0,15 -> 0,951 vs ldr seul 1,030 (brut 1,022), gardes OK | lot_04-11_0165_sec ; Mendy : « c'est mieux » |
| Lot 3 textures : pas mieux en simulation -> coupe | 04/11 |

## TSC Neural (entrainement)
| Fait | Preuve |
|---|---|
| Sans perte de detail, le reseau lisse (detail garde 0,57 run4) | run4 ; corrige v0.6 (perte detail + champion detail_min 0,75) |
| Entrainer sur jeu8 SANS effets alors que le jeu applique les effets fait chuter le detail en jeu (0,62) | run4 en jeu ; corrige enr_effet = 1 |
| Un seul eclairage appris -> derive orange en jeu des que l'entree change | run3 ; corrige --variations |
| Videos reelles ~4x plus douces que Panoramax : juge v2 sans detail (reel 1,14, brut 2,15) ; juge v3 = Panoramax libre | 04/11 |
| Ombres du jeu trop grises / pas assez bleues vs Panoramax | signature Panoramax 04/11 (**A VERIFIER** apres correction) |

## Sources reelles autorisees
- Panoramax : etalab-2.0 / CC0 / CC-BY -> `reel_panoramax/libre_commercial` (attribution.csv). CC-BY-SA -> `sa_a_decider`, non utilise.
- Videos de Mendy : privees.
- Interdit : yt-dlp, images web au hasard, fichiers PNG/Snowymoon/Project Next Gen (etude en lecture seule seulement).

## Gardes-fous de livraison (tout champion / toute version)
p1 <= reel + 0,03 ; sol asphalte <= 1,15 ; surfaces claires <= 1,10 ; p99 <= 0,97 ; ciel ecrete <= 1 % ;
teinte asphalte pas plus loin du reel que le brut ; |delta| <= 2 sur neutres cabine ; detail garde >= 0,75 ;
stable a 1, 2 et 3 ecrans ; tests `tsc_graphics/tests` verts (parite Python/HLSL, guide, compilation).

## Objectif en cours
Ecart restant (rendu 0.17 -> reel, juge sans detail, images jamais vues) reduit d'au moins 60 % (Mendy 04/11 16:57).
Baseline juge v3 : en cours de mesure.
