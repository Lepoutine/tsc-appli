# TSC Performance Lab dans la tablette : contrat d'interface

Demande de Mendy (24/10/2026) : l'outil doit être dans la tablette TSC et optimiser dans les zones fréquentées ou chargées.

Le moteur est dans `perf_lab/app/` (PowerShell 5.1, sans interface). La tablette n'a qu'un écran à ajouter et une boucle d'une seconde à faire tourner.

## Ce que fait le « mode zones »

- La tablette lui passe, chaque seconde, la position du camion lue dans la télémétrie scs-telemetry (déjà installée par l'appli).
- Le moteur mesure la charge du Shadow (carte graphique 3D et processeur, sans droits administrateur) et note chaque case de 500 m comme lourde ou normale. La carte des zones lourdes se construit au fil des trajets et reste dans `Documents\TSC Driver\TSC Performance Lab\zones\carte.json`.
- En zone lourde (3 s de charge saturée, ou entrée dans une case déjà connue comme lourde, ou case lourde 15 s devant le camion), si le mode automatique est activé :
  - le jeu passe en priorité « au-dessus de la normale » ;
  - les tâches de fond connues (Steam webhelper, navigateurs, Discord, Razer, OneDrive, Spotify…) passent en priorité « en dessous de la normale » ;
  - le plan d'alimentation passe en « Performances élevées » s'il existe.
- Après 30 s normales, tout revient exactement à l'état d'origine. L'état d'origine est écrit dans `zones\boost_en_cours.json` avant tout changement, donc rien ne reste modifié même après un plantage : la tablette appelle `restaurer` à son démarrage.
- **Jamais modifiés :** le jeu, ses fichiers, `config.cfg`, les mods, les profils, la qualité graphique. Aucune injection et aucune commande console, donc compatible TruckersMP et MODGuard (règle 6).
- **Conseil :** après au moins 10 minutes de trajets, si plus de 15 % du temps se passe en zone lourde, le moteur propose le profil « Limite 60 images/s ». Il ne l'applique jamais lui-même : le profil s'applique jeu fermé, avec une sauvegarde avant et un retour en un clic.

## Appel depuis la tablette

```powershell
Import-Module "<dossier appli>\perf_lab\app\PerfLab.Zones.psm1"   # charge aussi PerfLab.Core.psm1
$json = Invoke-PLTablet -Action <action> -Parametres @{ ... }      # renvoie toujours une chaîne JSON compacte
```

L'état de la surveillance vit dans la session PowerShell qui a importé le module. Il faut donc garder un seul runspace dédié au mode zones, et non un nouveau processus à chaque appel. Un échantillon prend jusqu'à environ 1 s (lecture des compteurs), il ne faut donc pas l'appeler depuis le fil de l'interface.

| Action | Paramètres | Réponse |
|---|---|---|
| `restaurer` | aucun | `{ Restaures: ["eurotrucks2 : AboveNormal -> Normal", …] }`. À appeler au démarrage de la tablette. |
| `demarrer` | `automatique` (bool) : si faux, le moteur observe et apprend la carte sans rien changer | état |
| `echantillon` | `x`, `z` (double, position monde `truck_placement` du SDK) ; facultatifs : `vitesse` (m/s), `cap` (heading du SDK, de 0 à 1), `pause` (bool), `fps` (images/s si la tablette en a une mesure) | état |
| `arreter` | aucun | état ; la carte est enregistrée et tout est restauré |
| `etat` | aucun | état |
| `zones` | aucun | les 20 zones lourdes connues : `Case`, `X`, `Z`, `Echantillons`, `PartLourde`, `GpuMoy`, `FpsMoy`, `Vu` |
| `conseil` | aucun | `SecondesEnregistrees`, `PartEnZoneLourde`, `ProposerProfil`, `Profil`, `Texte` |
| `reglages` | aucun (lecture) ou les clés à changer | réglages (seuils, durées, liste des tâches de fond, `PlanPerformant`) |

L'état contient : `Actif`, `Automatique`, `Etat` (`Normal` ou `Lourd`), `Case`, `CaseLourde`, `CaseEchantillons`, `Echantillons`, `SecondesLourdes`, `ZonesLourdesConnues`, et `Changements` (liste lisible des changements en cours, à afficher tels quels).

## Écran suggéré

- Un interrupteur « Mode zones chargées » avec deux positions : observer seulement, ou optimiser automatiquement.
- Un voyant « Zone normale / Zone chargée », avec la liste `Changements` affichée en dessous.
- Le compteur des zones lourdes connues, et la liste `zones` avec un bouton pour voir chaque zone sur la carte de la tablette, si elle en a une.
- L'encart `conseil`. Quand `ProposerProfil` est vrai, un bouton envoie vers l'application du profil, jeu fermé.
- Un bouton « Tout remettre comme avant » qui appelle `restaurer`.

## À savoir

- Process Lasso tourne sur le Shadow et peut lui-même changer les priorités ou le plan d'alimentation. Si les changements « sautent », il faut l'exclure d'eurotrucks2 ou mettre `PlanPerformant` à faux.
- Les tests sont dans `perf_lab/tests/Test-PerfLab.ps1` : `pwsh -File perf_lab/tests/Test-PerfLab.ps1`.
