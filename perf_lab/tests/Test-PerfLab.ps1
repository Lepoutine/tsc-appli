# Tests du moteur TSC Performance Lab sur des donnees d'exemple (aucun acces au jeu ni a Windows requis)
# Lancement : pwsh -File perf_lab/tests/Test-PerfLab.ps1
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Import-Module (Join-Path $here '..\app\PerfLab.Core.psm1') -Force
$data = Join-Path $here 'donnees'
$tmp = Join-Path ([IO.Path]::GetTempPath()) ("perflab_test_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tmp | Out-Null
$fail = 0
function Check($name, $cond) { if ($cond) { Write-Host "OK    $name" } else { Write-Host "ECHEC $name" -ForegroundColor Red; $script:fail++ } }

# --- journal du jeu
$log = Get-PLGameLog (Join-Path $data 'game.log.txt')
Check 'version du jeu' ($log.Version -eq '1.61.1.9')
Check 'carte graphique vue par le jeu' (@($log.Rendu | Where-Object { $_ -match 'Quadro RTX 6000' }).Count -eq 1)
Check 'derniere serie de mods seulement (2 mods)' (@($log.Mods).Count -eq 2)
Check 'ordre de la derniere serie' ($log.Mods[0].Nom -eq 'TM Realistic Rain with Coating Glass V1.3' -and $log.Mods[1].Nom -eq 'Air Ride Ultimate')
Check 'identifiant Workshop' ($log.Mods[1].WorkshopId -eq '713338424')
Check 'fichier du mod utilisateur' ($log.Mods[0].Fichier -eq 'TM Realistic Rain with Coating Glass V1.3_locked.scs')
Check 'mod incompatible' ($log.Incompatibles[0] -eq 'RPM_1_2_4_x_Real_Poland_Compatibility___40_1_56__41_')
Check 'erreurs groupees et comptees' ($log.Erreurs[0].Nombre -eq 2)
Check 'paquet en double' ($log.Doublons[0] -eq 'promods-cap-v161')
Check 'carte chargee a 441,7 s' ($log.ChargementCarteS -eq 441.7)
Check 'crochet sur l''affichage detecte, sans faux positif' (@($log.Crochets).Count -eq 1 -and $log.Crochets[0] -match 'Present hooked')
Check 'abonnements Workshop' ($log.WorkshopRecus -eq 22)

# --- config.cfg : lecture et ecriture ciblee
$cfg = Read-PLConfig (Join-Path $data 'config.cfg')
Check 'lecture config' ($cfg['t_limit_fps'] -eq '99' -and $cfg['r_vsync'] -eq '0')
$copy = Join-Path $tmp 'config.cfg'
Copy-Item (Join-Path $data 'config.cfg') $copy
Write-PLConfigOverrides -Source $copy -Destination $copy -Overrides @{ t_limit_fps = '60'; r_nouvelle = '1' }
$after = Read-PLConfig $copy
Check 'variable modifiee' ($after['t_limit_fps'] -eq '60')
Check 'autres variables intactes' ($after['r_far_shadow_disable'] -eq '1' -and $after['g_traffic'] -eq '1.0' -and $after.Count -eq 8)
Check 'variable absente ajoutee' ($after['r_nouvelle'] -eq '1')
$orig = @(Get-Content (Join-Path $data 'config.cfg')); $new = @(Get-Content $copy)
Check 'commentaire et ordre conserves' ($new[0] -eq $orig[0] -and $new[3] -eq $orig[3])
Check 'nom de profil hexadecimal' ((ConvertFrom-PLHexName '4C6520506F7574696E65') -eq 'Le Poutine')

# --- statistiques de temps de trame sur un CSV PresentMon synthetique
# 6000 images a 10 ms, dont une saccade a 40 ms toutes les 100 images ; carte graphique occupee 9,5 ms par image
$csv = Join-Path $tmp 'pm.csv'
$sb = New-Object Text.StringBuilder
[void]$sb.AppendLine('Application,ProcessID,SwapChainAddress,PresentRuntime,SyncInterval,PresentFlags,AllowsTearing,PresentMode,FrameType,CPUStartTime,FrameTime,CPUBusy,CPUWait,GPULatency,GPUTime,GPUBusy,GPUWait,DisplayLatency,DisplayedTime')
for ($i = 0; $i -lt 6000; $i++) {
  $ft = if ($i % 100 -eq 99) { 40 } else { 10 }
  [void]$sb.AppendLine("eurotrucks2.exe,1234,0x1,DXGI,0,0,1,Hardware: Independent Flip,Application,$i,$ft,4.0,6.0,1,9.5,9.5,0.5,20,$ft")
}
# une seconde chaine d'affichage parasite, a ignorer
for ($i = 0; $i -lt 50; $i++) { [void]$sb.AppendLine("eurotrucks2.exe,1234,0x2,DXGI,0,0,1,Composed,Application,$i,500,1,1,1,1,1,1,1,500") }
[IO.File]::WriteAllText($csv, $sb.ToString())
$st = Get-PLFrameStats -CsvPath $csv -SkipSeconds 0
Check 'chaine principale seule (6000 images)' ($st.Images -eq 6000)
# moyenne : (5940*10 + 60*40)/6000 = 10,3 ms -> 97,1 images/s
Check 'images/s moyennes 97,1' ($st.FpsMoyen -eq 97.1)
# 1 % le plus lent = 60 images a 40 ms -> 25 images/s
Check '1 % le plus lent 25 images/s' ($st.Fps1PctBas -eq 25)
Check '0,1 % le plus lent 25 images/s' ($st.Fps01PctBas -eq 25)
Check 'mediane 10 ms' ($st.TrameMedianeMs -eq 10)
Check '99e centile 10 ms (60 saccades = 1 %)' ($st.TrameP99Ms -eq 10)
Check '60 saccades detectees' ($st.Saccades -eq 60)
Check 'limite : carte graphique' ($st.Limite -eq 'Carte graphique')
Check 'colonne v2 utilisee' ($st.ColonneTrame -eq 'FrameTime')

# format v1 (MsBetweenPresents) et rythme regulier sans saccade
$csv1 = Join-Path $tmp 'pm1.csv'
$sb = New-Object Text.StringBuilder
[void]$sb.AppendLine('Application,ProcessID,SwapChainAddress,Runtime,SyncInterval,PresentFlags,Dropped,TimeInSeconds,msInPresentAPI,msBetweenPresents')
for ($i = 0; $i -lt 3000; $i++) { [void]$sb.AppendLine("eurotrucks2.exe,1,0x1,DXGI,0,0,0,$($i/60),0.1,16.667") }
[IO.File]::WriteAllText($csv1, $sb.ToString())
$st1 = Get-PLFrameStats -CsvPath $csv1 -SkipSeconds 0
Check 'format v1 lu' ($st1.ColonneTrame -eq 'msBetweenPresents' -and $st1.FpsMoyen -eq 60)
Check 'aucune saccade sur rythme regulier' ($st1.Saccades -eq 0 -and $st1.EcartTypeMs -eq 0)
Check 'limite indeterminee sans colonnes CPU/GPU' ($st1.Limite -eq 'Indetermine')

# --- comparaison
$a = [pscustomobject]@{ Stats = $st }; $b = [pscustomobject]@{ Stats = $st1 }
$cmp = @(Compare-PLRuns -Avant $a -Apres $b)
Check 'comparaison : saccades en baisse = mieux' (($cmp | Where-Object Mesure -eq 'Saccades par minute').Verdict -eq 'Mieux')
Check 'comparaison : images/s moyennes en baisse = moins bien' (($cmp | Where-Object Mesure -eq 'Images/s moyennes').Verdict -eq 'Moins bien')
Check 'comparaison : 1 % bas en hausse = mieux' (($cmp | Where-Object Mesure -eq 'Images/s des 1 % les plus lents').Verdict -eq 'Mieux')

# --- recommandations a partir d'un diagnostic simule
$diag = [pscustomobject]@{
  Machine = $null; Game = $null; Injections = @([pscustomobject]@{ Fichier = 'dxgi.dll' }); Plugins = @(
    [pscustomobject]@{ Fichier = 'scs-telemetry.dll'; Telemetrie = $true }, [pscustomobject]@{ Fichier = 'telemetry_tb_64.dll'; Telemetrie = $true }, [pscustomobject]@{ Fichier = 'TruckyTelemetry.dll'; Telemetrie = $true })
  Graphismes = [pscustomobject]@{ Global = $cfg }; Journal = $log
  Plantages = [pscustomobject]@{ Total = 140; Jours = 30; ParModule = @([pscustomobject]@{ Module = 'telemetry_tb_64.dll'; Nombre = 65 }) }
}
$rec = @(Get-PLRecommendations $diag)
$ids = @($rec | ForEach-Object Id)
Check 'reco plantages en tete' ($rec[0].Id -eq 'crash-modules')
Check 'reco cadence (99 images/s vs ecrans 60 Hz)' ($ids -contains 'frame-cadence')
Check 'reco multi-ecran' ($ids -contains 'multimon')
Check 'reco crochet affichage' ($ids -contains 'present-hooks')
Check 'reco telemetrie multiple' ($ids -contains 'telemetry-count')
Check 'reco paquets en double' ($ids -contains 'duplicate-packages')
Check 'reco chargement long' ($ids -contains 'load-time')
Check 'aucune reco ne touche la qualite du profil principal' (@($rec | Where-Object { $_.QualiteTouchee -ne 'Non' }).Count -eq 0)

# --- tableau HTML : echappement
$html = ConvertTo-PLHtmlTable @([pscustomobject]@{ A = '<script>' })
Check 'echappement HTML' ($html -match '&lt;script&gt;' -and $html -notmatch '<script>')

Remove-Item -Recurse -Force $tmp
if ($fail) { Write-Host "$fail test(s) en echec" -ForegroundColor Red; exit 1 } else { Write-Host 'Tous les tests passent.' -ForegroundColor Green }
