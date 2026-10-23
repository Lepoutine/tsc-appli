# TSC Performance Lab - releve du PC principal (celui qui affiche Shadow)
# LECTURE SEULE : ce script ne modifie aucun reglage. Il ecrit un dossier et un .zip sur le Bureau.
# Lancement : clic droit > Executer avec PowerShell, PENDANT que Shadow est ouvert et que tu roules dans ETS2.

$ErrorActionPreference = 'SilentlyContinue'
$stamp = Get-Date -Format 'yyyy-MM-dd_HHmm'
$out = Join-Path ([Environment]::GetFolderPath('Desktop')) "TSC_PC_principal_$stamp"
New-Item -ItemType Directory -Path $out -Force | Out-Null
function Save($name, [object[]]$parts) { ($parts | ForEach-Object { if ($_ -is [string]) { $_ } else { $_ | Format-Table -AutoSize -Wrap | Out-String -Width 300 } }) -join "`r`n" | Set-Content -Path (Join-Path $out $name) -Encoding UTF8 }
Write-Host "TSC Performance Lab - releve du PC principal (lecture seule)" -ForegroundColor Cyan
if ((Get-CimInstance Win32_ComputerSystem).Model -match 'Shadow') {
  Write-Host ""
  Write-Host "Ce script tourne DANS Shadow. Il doit etre lance sur le PC physique qui affiche Shadow (ferme ou reduis la fenetre Shadow d'abord)." -ForegroundColor Yellow
  Remove-Item $out -Recurse -Force; try { Read-Host "Appuie sur Entree pour fermer" } catch {}; return
}
Write-Host "Dossier : $out"

# 1. Machine
Write-Host "[1/7] Machine..."
Save '01_machine.txt' @(
  (Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model, TotalPhysicalMemory),
  (Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber, FreePhysicalMemory),
  (Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed, CurrentClockSpeed),
  (Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion, DriverDate, AdapterRAM, CurrentHorizontalResolution, CurrentVerticalResolution, CurrentRefreshRate),
  (Get-CimInstance Win32_Battery | Select-Object Name, BatteryStatus, EstimatedChargeRemaining),
  (Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | Select-Object DeviceID, @{n='TailleGo';e={[math]::Round($_.Size/1GB,1)}}, @{n='LibreGo';e={[math]::Round($_.FreeSpace/1GB,1)}})
)

# 2. Ecrans : definition et frequence de chaque ecran
Write-Host "[2/7] Ecrans..."
Add-Type -AssemblyName System.Windows.Forms
$ecrans = [System.Windows.Forms.Screen]::AllScreens | ForEach-Object { [pscustomobject]@{ Ecran = $_.DeviceName; Principal = $_.Primary; Definition = "$($_.Bounds.Width)x$($_.Bounds.Height)"; Position = "$($_.Bounds.X),$($_.Bounds.Y)" } }
$moniteurs = Get-CimInstance -Namespace root\wmi WmiMonitorID | ForEach-Object { [pscustomobject]@{ Fabricant = -join [char[]]($_.ManufacturerName -ne 0); Modele = -join [char[]]($_.UserFriendlyName -ne 0) } }
Save '02_ecrans.txt' (@(,$ecrans) + @(,$moniteurs) + @(,(Get-CimInstance Win32_VideoController | Select-Object Name, CurrentHorizontalResolution, CurrentVerticalResolution, CurrentRefreshRate, MaxRefreshRate)))

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
$rows = @()
for ($i = 0; $i -lt 30; $i++) {
  $cpu = (Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor -Filter "Name='_Total'").PercentProcessorTime
  $ram = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1KB)
  $dec = 0; $g3d = 0
  foreach ($c in (Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine)) {
    if ($c.Name -match 'engtype_VideoDecode') { $dec += $c.UtilizationPercentage } elseif ($c.Name -match 'engtype_3D') { $g3d += $c.UtilizationPercentage } }
  $rows += [pscustomobject]@{ 'Processeur %' = $cpu; 'Decodage video %' = $dec; 'GPU 3D %' = $g3d; 'RAM libre Mo' = $ram }
  Start-Sleep -Seconds 1
}
$agg = foreach ($k in 'Processeur %', 'Decodage video %', 'GPU 3D %', 'RAM libre Mo') {
  [pscustomobject]@{ Mesure = $k; Moyenne = [math]::Round(($rows | Measure-Object $k -Average).Average,1); Max = ($rows | Measure-Object $k -Maximum).Maximum } }
Save '06_charge_30s.txt' @(,$agg)

# 7. Processus et overlays
Write-Host "[7/7] Processus..."
Save '07_processus.txt' @(,(Get-Process | Sort-Object CPU -Descending | Select-Object -First 30 ProcessName, Id, CPU, @{n='MemMo';e={[math]::Round($_.WorkingSet64/1MB)}}))
Start-Process dxdiag.exe -ArgumentList "/t `"$(Join-Path $out 'dxdiag.txt')`"" -Wait

Compress-Archive -Path "$out\*" -DestinationPath "$out.zip" -Force
Write-Host ""
Write-Host "Termine. Envoie ce fichier dans le fil TSC Performance Lab :" -ForegroundColor Green
Write-Host "$out.zip"
try { Read-Host "Appuie sur Entree pour fermer" } catch {}
