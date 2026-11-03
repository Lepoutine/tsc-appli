# TSC Performance Lab - optimisation du PC principal qui sert UNIQUEMENT a afficher Shadow (demande de Mendy, 03/11/2026)
# Tout est sauvegarde avant et reversible : relancer avec -Restaurer remet chaque reglage a sa valeur d'origine.
# Ne touche a aucune protection (antivirus, pare-feu, mises a jour de securite), ni a Shadow lui-meme, ni aux pilotes.
# Lancement (PowerShell) : le script se relance en administrateur si besoin.
param([switch]$Restaurer)
$ErrorActionPreference = 'SilentlyContinue'

$dossier = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'TSC Driver\Optimisation_PC_Shadow'
New-Item -ItemType Directory -Path $dossier -Force | Out-Null
$sauvegarde = Join-Path $dossier 'sauvegarde.json'
$journal = Join-Path $dossier ("journal_" + (Get-Date -Format 'yyyy-MM-dd_HHmm') + '.txt')
function Dire($t, $c = 'Gray') { Write-Host $t -ForegroundColor $c; Add-Content -Path $journal -Value $t -Encoding UTF8 }

# administrateur requis (plan d'alimentation, carte reseau)
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
  $src = $MyInvocation.MyCommand.Path
  if (-not $src) { $src = Join-Path $env:TEMP 'Optimiser_PC_Shadow.ps1'; $MyInvocation.MyCommand.ScriptBlock.ToString() | Set-Content -Path $src -Encoding UTF8 }
  $a = "-NoProfile -ExecutionPolicy Bypass -File `"$src`""; if ($Restaurer) { $a += ' -Restaurer' }
  Start-Process powershell -Verb RunAs -ArgumentList $a; return
}

$cs = Get-WmiObject Win32_ComputerSystem
if ($cs.Model -match 'Shadow') { Write-Host "Ce script se lance sur le PC physique qui affiche Shadow, pas dans Shadow." -ForegroundColor Yellow; Read-Host 'Entree pour fermer'; return }

# reglages du registre touches : chemin, nom, valeur optimisee, type
$cles = @(
  @{ C = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects'; N = 'VisualFXSetting'; V = 2; T = 'DWord'; Q = 'Effets visuels de Windows : priorite aux performances' },
  @{ C = 'HKCU:\System\GameConfigStore'; N = 'GameDVR_Enabled'; V = 0; T = 'DWord'; Q = 'Enregistrement en arriere-plan Xbox (Game DVR) coupe' },
  @{ C = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\GameDVR'; N = 'AppCaptureEnabled'; V = 0; T = 'DWord'; Q = 'Capture Xbox Game Bar coupee' },
  @{ C = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications'; N = 'GlobalUserDisabled'; V = 1; T = 'DWord'; Q = 'Applications du Store en arriere-plan coupees' },
  @{ C = 'HKCU:\Software\Microsoft\GameBar'; N = 'AutoGameModeEnabled'; V = 1; T = 'DWord'; Q = 'Mode Jeu de Windows active' },
  @{ C = 'HKCU:\Control Panel\Desktop'; N = 'MenuShowDelay'; V = '0'; T = 'String'; Q = 'Menus instantanes' }
)

if ($Restaurer) {
  if (-not (Test-Path $sauvegarde)) { Dire "Aucune sauvegarde trouvee ($sauvegarde) : rien a restaurer." Yellow; Read-Host 'Entree pour fermer'; return }
  $s = Get-Content $sauvegarde -Raw | ConvertFrom-Json
  Dire "Restauration depuis $sauvegarde" Cyan
  foreach ($r in $s.registre) {
    if ($r.Existait) { Set-ItemProperty -Path $r.C -Name $r.N -Value $r.Valeur; Dire "  remis : $($r.C)\$($r.N) = $($r.Valeur)" }
    else { Remove-ItemProperty -Path $r.C -Name $r.N; Dire "  retire : $($r.C)\$($r.N) (n'existait pas avant)" }
  }
  if ($s.plan) { powercfg /setactive $s.plan | Out-Null; Dire "  plan d'alimentation remis : $($s.plan)" }
  foreach ($n in $s.reseau) {
    if ($n.EEE -ne $null) { Set-NetAdapterAdvancedProperty -Name $n.Nom -RegistryKeyword $n.CleEEE -RegistryValue $n.EEE -NoRestart; Dire "  $($n.Nom) : Ethernet econome ($($n.CleEEE)) remis a $($n.EEE)" }
    if ($n.Veille) { Enable-NetAdapterPowerManagement -Name $n.Nom -NoRestart; Dire "  $($n.Nom) : mise en veille de la carte reautorisee" }
  }
  Dire "Termine. Redemarre la session Windows pour que tout soit pris en compte." Green
  Read-Host 'Entree pour fermer'; return
}

Dire "TSC - optimisation du PC qui affiche Shadow (reversible : relancer avec -Restaurer)" Cyan
if (Test-Path $sauvegarde) { Dire "Une sauvegarde existe deja : on la garde (c'est l'etat d'ORIGINE)." Yellow; $s = Get-Content $sauvegarde -Raw | ConvertFrom-Json }
else {
  $s = [ordered]@{ date = (Get-Date).ToString('s'); registre = @(); plan = $null; reseau = @() }
  foreach ($k in $cles) {
    $p = Get-ItemProperty -Path $k.C -Name $k.N
    $s.registre += [ordered]@{ C = $k.C; N = $k.N; Existait = ($p -ne $null -and $p.PSObject.Properties[$k.N] -ne $null); Valeur = if ($p) { $p.($k.N) } else { $null } }
  }
  $g = (powercfg /getactivescheme) -replace '.*:\s*([0-9a-fA-F-]{36}).*', '$1'
  $s.plan = $g.Trim()
  foreach ($a in (Get-NetAdapter -Physical | Where-Object Status -eq 'Up')) {
    $e = Get-NetAdapterAdvancedProperty -Name $a.Name | Where-Object { $_.RegistryKeyword -match 'EEE' } | Select-Object -First 1
    $pm = Get-NetAdapterPowerManagement -Name $a.Name
    $s.reseau += [ordered]@{ Nom = $a.Name; CleEEE = if ($e) { $e.RegistryKeyword } else { $null }; EEE = if ($e) { $e.RegistryValue[0] } else { $null }; Veille = ($pm -and $pm.AllowComputerToTurnOffDevice -eq 'Enabled') }
  }
  $s | ConvertTo-Json -Depth 5 | Set-Content -Path $sauvegarde -Encoding UTF8
  Dire "Sauvegarde de l'etat d'origine : $sauvegarde" Green
}

# 1. registre
foreach ($k in $cles) {
  if (-not (Test-Path $k.C)) { New-Item -Path $k.C -Force | Out-Null }
  New-ItemProperty -Path $k.C -Name $k.N -Value $k.V -PropertyType $k.T -Force | Out-Null
  Dire "  OK  $($k.Q)"
}
# 2. plan d'alimentation hautes performances (le processeur ne descend plus en frequence pendant le decodage)
$hp = '8c5e7fda-e8bf-4a96-9a85-cf2e1a3d8b9a'
powercfg /setactive $hp 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { powercfg /duplicatescheme $hp | Out-Null; powercfg /setactive $hp | Out-Null }
Dire "  OK  Plan d'alimentation : Performances elevees"
# 3. carte reseau : pas de mise en veille, pas d'Ethernet econome (evite les micro-coupures du flux)
foreach ($a in (Get-NetAdapter -Physical | Where-Object Status -eq 'Up')) {
  Disable-NetAdapterPowerManagement -Name $a.Name -NoRestart
  # le mot-cle varie selon le fabricant : *EEE (standard), EEELinkAdvertisement (Intel I217/I219), ...
  $e = Get-NetAdapterAdvancedProperty -Name $a.Name | Where-Object { $_.RegistryKeyword -match 'EEE' } | Select-Object -First 1
  if ($e) { Set-NetAdapterAdvancedProperty -Name $a.Name -RegistryKeyword $e.RegistryKeyword -RegistryValue 0 -NoRestart; if ($?) { Dire "  OK  $($a.Name) : Ethernet econome ($($e.RegistryKeyword)) coupe" } else { Dire "  !!  $($a.Name) : Ethernet econome NON coupe (a faire dans le Gestionnaire de peripheriques)" Yellow } }
  Dire "  OK  Carte reseau $($a.Name) ($($a.LinkSpeed)) : veille et mode econome coupes"
}
# 4. pour cette session seulement : programmes gourmands fermes, Shadow en priorite haute
foreach ($n in 'RazerCortex', 'Razer Cortex', 'CortexLauncherService') { Get-Process -Name $n | Stop-Process -Force; }
Dire "  OK  Razer Cortex ferme pour cette session (non desinstalle)"
$sh = Get-Process | Where-Object { $_.ProcessName -match '^(Shadow|ShadowPC)' }
foreach ($p in $sh) { $p.PriorityClass = 'AboveNormal' }
if ($sh) { Dire "  OK  Shadow en priorite haute pour cette session" } else { Dire "  --  Shadow pas ouvert : priorite non changee" }

# 5. ce que le script ne peut pas regler pour toi (dans l'application Shadow)
$ecrans = Get-WmiObject Win32_VideoController | Select-Object -First 1
Dire ""
Dire "A regler dans l'application Shadow (Parametres > Streaming), d'apres ton PC :" Cyan
Dire "  - Images par seconde : 60 (tes ecrans sont a 60 Hz ; 100 fps surcharge le decodage sans rien afficher de plus)"
Dire "  - Codec : H.264 (ton processeur graphique $($ecrans.Name) ne decode pas bien le H.265)"
Dire "  - Decodage materiel : active"
Dire "  - Debit : 'Automatique' ou 50 Mbit/s maximum en Ethernet"
Dire "  - Si un seul ecran sert a Shadow : definition 1920x1080 (moins d'image a decoder)"
Dire "Pilote graphique : $($ecrans.Name), version $($ecrans.DriverVersion). Un pilote recent (site Intel) aide le decodage materiel."
Dire ""
Dire "Termine. Ferme puis rouvre Shadow. Pour tout annuler : relance ce script avec -Restaurer." Green
Read-Host 'Entree pour fermer'
