# WebView2 : runtime de la tablette TSC

- Source : https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution (lu le 03/11/2026)
- Version : documentation Microsoft Learn au 03/11/2026. Statut : vérifié.

## Points utiles
- Runtime « Evergreen » (conseillé) : mis à jour tout seul avec Edge, une copie partagée par toutes les applis. Une mise à jour s'applique au redémarrage de l'appli.
- Runtime « Fixed Version » : version embarquée par l'appli, plus de 250 Mo, pas de mise à jour automatique, ne marche pas depuis un chemin réseau.
- Windows 11 : runtime inclus dans le système. Windows 10 : présent sur la plupart des PC mais pas tous, donc il faut le vérifier.
- Détection : valeur `pv` (texte) sous `...\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}`, en HKLM (WOW6432Node sur Windows 64 bits) ou en HKCU. Absent si la clé manque, ou si `pv` est vide ou `0.0.0.0`.
- Installation : bootstrapper (~2 Mo, en ligne) ou installeur autonome (hors ligne) ; option `/silent /install`. Sans élévation : installation par utilisateur.
- Une appli de production doit utiliser le runtime WebView2, pas Edge Stable.

## Usage TSC
- Le lanceur doit vérifier `pv` avant d'ouvrir la tablette, et proposer l'installeur Microsoft s'il manque (au lieu d'une fenêtre blanche).
- Prévoir les nouvelles API par test de présence (le runtime peut être bloqué par un administrateur ou hors ligne).
