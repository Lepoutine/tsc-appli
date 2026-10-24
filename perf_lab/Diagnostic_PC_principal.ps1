# TSC Performance Lab - releve du PC principal (celui qui affiche Shadow)
# LECTURE SEULE : ce script ne modifie aucun reglage. Il ecrit un dossier et un .zip sur le Bureau.
# Lancement : clic droit > Executer avec PowerShell, PENDANT que Shadow est ouvert et que tu roules dans ETS2.

$ErrorActionPreference = 'SilentlyContinue'
$stamp = Get-Date -Format 'yyyy-MM-dd_HHmm'
$out = Join-Path ([Environment]::GetFolderPath('Desktop')) "TSC_PC_principal_$stamp"
New-Item -ItemType Directory -Path $out -Force | Out-Null
# Get-CimInstance, ou Get-WmiObject si CIM ne repond pas (cas constate sur le PC principal)
function W($Class, $Filter) {
  $p = @{ ClassName = $Class; ErrorAction = 'Stop' }; if ($Filter) { $p.Filter = $Filter }
  try { Get-CimInstance @p } catch { $q = @{ Class = $Class }; if ($Filter) { $q.Filter = $Filter }; Get-WmiObject @q }
}
function Save($name, [object[]]$parts) { ($parts | ForEach-Object { if ($_ -is [string]) { $_ } else { $_ | Format-Table -AutoSize -Wrap | Out-String -Width 300 } }) -join "`r`n" | Set-Content -Path (Join-Path $out $name) -Encoding UTF8 }
Write-Host "TSC Performance Lab - releve du PC principal (lecture seule)" -ForegroundColor Cyan
if ((W Win32_ComputerSystem).Model -match 'Shadow') {
  Write-Host ""
  Write-Host "Ce script tourne DANS Shadow. Il doit etre lance sur le PC physique qui affiche Shadow (ferme ou reduis la fenetre Shadow d'abord)." -ForegroundColor Yellow
  Remove-Item $out -Recurse -Force; try { Read-Host "Appuie sur Entree pour fermer" } catch {}; return
}
Write-Host "Dossier : $out"

# 1. Machine
Write-Host "[1/7] Machine..."
$m = @()
$m += (W Win32_ComputerSystem | Select-Object Manufacturer, Model, TotalPhysicalMemory | Format-List | Out-String)
$m += (W Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, FreePhysicalMemory | Format-List | Out-String)
$m += (W Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed, CurrentClockSpeed | Format-List | Out-String)
$m += (W Win32_VideoController | Select-Object Name, DriverVersion, DriverDate, CurrentHorizontalResolution, CurrentVerticalResolution, CurrentRefreshRate | Format-List | Out-String)
$m += ((W Win32_LogicalDisk 'DriveType=3') | Select-Object DeviceID, @{n='TailleGo';e={[math]::Round($_.Size/1GB,1)}}, @{n='LibreGo';e={[math]::Round($_.FreeSpace/1GB,1)}} | Format-Table -AutoSize | Out-String)
Add-Type -AssemblyName Microsoft.VisualBasic
$ci = New-Object Microsoft.VisualBasic.Devices.ComputerInfo
$m += "Processeur (registre) : " + (Get-ItemProperty 'HKLM:\HARDWARE\DESCRIPTION\System\CentralProcessor\0').ProcessorNameString
$m += "Threads : $([Environment]::ProcessorCount)"
$m += "Memoire totale Mo : $([math]::Round($ci.TotalPhysicalMemory / 1MB)) ; libre Mo : $([math]::Round($ci.AvailablePhysicalMemory / 1MB))"
$m += "Windows : $($ci.OSFullName) $([Environment]::OSVersion.Version)"
$m -join "`r`n" | Set-Content -Path (Join-Path $out '01_machine.txt') -Encoding UTF8

# 2. Ecrans : definition et frequence de chaque ecran
Write-Host "[2/7] Ecrans..."
Add-Type -AssemblyName System.Windows.Forms
$ecrans = [System.Windows.Forms.Screen]::AllScreens | ForEach-Object { [pscustomobject]@{ Ecran = $_.DeviceName; Principal = $_.Primary; Definition = "$($_.Bounds.Width)x$($_.Bounds.Height)"; Position = "$($_.Bounds.X),$($_.Bounds.Y)" } }
$moniteurs = Get-CimInstance -Namespace root\wmi WmiMonitorID | ForEach-Object { [pscustomobject]@{ Fabricant = -join [char[]]($_.ManufacturerName -ne 0); Modele = -join [char[]]($_.UserFriendlyName -ne 0) } }
Save '02_ecrans.txt' (@(,$ecrans) + @(,$moniteurs) + @(,(W Win32_VideoController | Select-Object Name, CurrentHorizontalResolution, CurrentVerticalResolution, CurrentRefreshRate, MaxRefreshRate)))

# 3. Windows
Write-Host "[3/7] Reglages Windows..."
Save '03_windows.txt' @(
  (powercfg /getactivescheme),
  "HAGS (HwSchMode) : " + (Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers').HwSchMode,
  "Mode Jeu : " + (Get-ItemProperty 'HKCU:\Software\Microsoft\GameBar').AutoGameModeEnabled,
  "Game DVR : " + (Get-ItemProperty 'HKCU:\System\GameConfigStore').GameDVR_Enabled,
  (Get-ItemProperty 'HKCU:\Software\Microsoft\DirectX\UserGpuPreferences' | Out-String)
)

# 4. Client Shadow
Write-Host "[4/7] Client Shadow..."
$keys = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*','HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
$shadowApps = Get-ItemProperty $keys | Where-Object { $_.DisplayName -match 'Shadow' } | Select-Object DisplayName, DisplayVersion, InstallLocation
$shadowProc = Get-Process | Where-Object { $_.ProcessName -match 'shadow' } | Select-Object ProcessName, Id, CPU, @{n='MemMo';e={[math]::Round($_.WorkingSet64/1MB)}}, Path
Save '04_shadow_client.txt' (@(,$shadowApps) + @(,$shadowProc))
$logs = Join-Path $out 'shadow_logs'; New-Item -ItemType Directory $logs -Force | Out-Null
foreach ($base in @($env:APPDATA, $env:LOCALAPPDATA)) {
  Get-ChildItem $base -Directory | Where-Object { $_.Name -match 'shadow' } | ForEach-Object {
    Get-ChildItem $_.FullName -Recurse -File -Include *.log, *.txt | Where-Object { $_.LastWriteTime -gt (Get-Date).AddDays(-2) -and $_.Length -lt 20MB } |
      Select-Object -First 30 | ForEach-Object { Copy-Item $_.FullName (Join-Path $logs ($_.Directory.Name + '_' + $_.Name)) }
  }
}

# 5. Reseau
Write-Host "[5/7] Reseau (environ 1 minute)..."
$gw = (Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway } | Select-Object -First 1).IPv4DefaultGateway.NextHop
function PingStats($target, $n) {
  $t = @(); $lost = 0
  foreach ($line in (ping.exe -n $n -w 1000 $target)) { if ($line -match '(?:temps|time)[=<](\d+)') { $t += [int]$Matches[1] } elseif ($line -match '(?:D.lai|timed out|Impossible|unreachable)') { $lost++ } }
  if ($t.Count -lt 2) { return [pscustomobject]@{ Cible = $target; Resultat = 'aucune reponse' } }
  $j = 0; for ($i = 1; $i -lt $t.Count; $i++) { $j += [math]::Abs($t[$i] - $t[$i-1]) }
  [pscustomobject]@{ Cible = $target; Envois = $n; Pertes = $n - $t.Count; MinMs = ($t | Measure-Object -Minimum).Minimum; MoyMs = [math]::Round(($t | Measure-Object -Average).Average,1); MaxMs = ($t | Measure-Object -Maximum).Maximum; GigueMs = [math]::Round($j / ($t.Count - 1),1) }
}
Save '05_reseau.txt' @(
  (Get-NetAdapter | Where-Object Status -eq 'Up' | Select-Object Name, InterfaceDescription, MediaType, LinkSpeed),
  (netsh wlan show interfaces),
  (PingStats $gw 30), (PingStats '1.1.1.1' 30)
)

# 6. Charge pendant le flux Shadow : decodage video, 3D, processeur (30 s)
Write-Host "[6/7] Charge pendant 30 s : roule dans ETS2 pendant ce temps..."
# noms de compteurs dans la langue de Windows : 238 = objet Processeur, 6 = % temps processeur
$perf = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Perflib\CurrentLanguage' -ErrorAction SilentlyContinue).Counter
$pn = @{}; if ($perf) { for ($k = 0; $k -lt $perf.Count - 1; $k += 2) { $pn[$perf[$k]] = $perf[$k + 1] } }
$cpuPath = if ($pn['238'] -and $pn['6']) { "\$($pn['238'])(_Total)\$($pn['6'])" } else { '\Processor(_Total)\% Processor Time' }
Add-Type -AssemblyName Microsoft.VisualBasic
$ci = New-Object Microsoft.VisualBasic.Devices.ComputerInfo
$rows = @()
# deux appels separes : si l'un des compteurs manque, l'autre est quand meme lu (15 x 2 s = 30 s)
for ($i = 0; $i -lt 15; $i++) {
  $g = Get-Counter -Counter '\GPU Engine(*)\Utilization Percentage' -SampleInterval 1 -MaxSamples 1 -ErrorAction SilentlyContinue
  $p = Get-Counter -Counter $cpuPath -SampleInterval 1 -MaxSamples 1 -ErrorAction SilentlyContinue
  $dec = 0; $g3d = 0; $cpu = $null
  if ($g) { foreach ($c in $g.CounterSamples) { if ($c.InstanceName -match 'engtype_videodecode') { $dec += $c.CookedValue } elseif ($c.InstanceName -match 'engtype_3d') { $g3d += $c.CookedValue } } }
  if ($p) { $cpu = [math]::Round($p.CounterSamples[0].CookedValue, 1) }
  if (-not $g -and -not $p) { Start-Sleep -Seconds 2 }
  $rows += [pscustomobject]@{ 'Processeur %' = $cpu; 'Decodage video %' = [math]::Round($dec,1); 'GPU 3D %' = [math]::Round($g3d,1); 'RAM libre Mo' = [math]::Round($ci.AvailablePhysicalMemory / 1MB) }
}
$agg = foreach ($k in 'Processeur %', 'Decodage video %', 'GPU 3D %', 'RAM libre Mo') {
  [pscustomobject]@{ Mesure = $k; Moyenne = [math]::Round(($rows | Measure-Object $k -Average).Average,1); Max = ($rows | Measure-Object $k -Maximum).Maximum } }
$noteGpu = if (-not (Get-Counter -ListSet 'GPU Engine' -ErrorAction SilentlyContinue)) { 'Compteurs GPU non disponibles sur ce pilote : decodage et 3D non mesures (0 = absence de donnees).' } else { '' }
Save '06_charge_30s.txt' (@(,$agg) + @($noteGpu))

# 7. Processus et overlays
Write-Host "[7/7] Processus..."
Save '07_processus.txt' @(,(Get-Process | Sort-Object CPU -Descending | Select-Object -First 30 ProcessName, Id, CPU, @{n='MemMo';e={[math]::Round($_.WorkingSet64/1MB)}}))
Start-Process dxdiag.exe -ArgumentList "/t `"$(Join-Path $out 'dxdiag.txt')`"" -Wait

Compress-Archive -Path "$out\*" -DestinationPath "$out.zip" -Force
Write-Host ""
Write-Host "Termine. Envoie ce fichier dans le fil TSC Performance Lab :" -ForegroundColor Green
Write-Host "$out.zip"
try { Read-Host "Appuie sur Entree pour fermer" } catch {}
