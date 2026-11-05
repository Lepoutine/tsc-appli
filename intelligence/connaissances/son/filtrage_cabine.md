# Son intérieur / extérieur : filtrage de cabine ETS2

- Source : https://modding.scssoft.com/wiki/Documentation/Engine/Sound/TruckCabinFiltering (lu le 03/11/2026)
- Source : https://modding.scssoft.com/wiki/Documentation/Engine/Sound (soundref, lu le 03/11/2026)
- Version : wiki SCS au 03/11/2026, mécanisme présent depuis le jeu 1.43. Statut : vérifié (doc), pas encore réglé sur un son TSC.

## Ce que fait le jeu
- Paramètres globaux envoyés par le jeu : `cabin_out` (0 = auditeur dedans, 1 = dehors), `wnd_left` et `wnd_right` (0 = vitre fermée, 1 = ouverte).
- Le son du moteur est traité comme extérieur et sort dans `Grp outside`, qui se divise en trois bus : `Rtn window_out`, `Rtn window_left`, `Rtn window_right`.
- Volumes fixés par la banque maître (non modifiables) : `Rtn window_out` −6 dB dedans, +4 dB dehors ; vitres gauche/droite −7 dB dedans, coupées dehors.
- La réverbération de cabine est sur `Grp cabin`, dans la banque du camion.

## Ce que le moddeur règle par camion (le jeu interpole entre les deux bornes)
- EQ des vitres : `.effect.add.window_eq.closed` / `.opened`.
- EQ d'écoute : `.effect.equalizer.cabin.inside` / `.outside`.
- Réverbération : `.effect.reverb.window.closed` / `.opened`.
- La doc déconseille des `low_crossover` / `high_crossover` très différents entre les deux bornes d'un même EQ, et une réverbération qui change trop l'écho.

## Position du son (.soundref)
- Ligne `source="/sound/truck/xxx.bank#engine/exhaust"` ; ligne facultative `position_offset=gauche/droite;bas/haut;avant/arrière` en mètres.
- Les événements moteur sont 3D ; position par défaut : 1 m au-dessus du premier essieu. Pour l'échappement d'un V8 à tubes verticaux, déplacer l'`exhaust` vers l'arrière de la cabine.

## Usage TSC
- Le « bop bop » du ralenti doit garder son grave dedans : régler l'EQ `cabin.inside` (coupe des aigus, pas du corps 80-250 Hz) plutôt que retoucher les WAV.
