# TSC Performance Lab - releve du PC principal (celui qui affiche Shadow)
# LECTURE SEULE : ce script ne modifie aucun reglage. Il ecrit un dossier et un .zip sur le Bureau.
# Lancement : clic droit > Executer avec PowerShell, PENDANT que Shadow est ouvert et que tu roules dans ETS2.

$ErrorActionPreference = 'SilentlyContinue'
$stamp = Get-Date -Format 'yyyy-MM-dd_HHmm'
$out = Join-Path ([Environment]::GetFolderPath('Desktop')) "TSC_PC_principal_$stamp"
New-Item -ItemType Directory -Path $out -Force | Out-Null
function Save($name, $obj) { $obj | Out-String -Width 300 | Set-Content -Path (Join-Path $out $name) -Encoding UTF8 }
Write-Host "TSC Performance Lab - releve du PC principal (lecture seule)" -ForegroundColor Cyan
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
Add-Type -TypeDefinition @'
using System; using System.Runtime.InteropServices;
public class TscDisp {
  [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] public struct DD { public int cb; [MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string Name; [MarshalAs(UnmanagedType.ByValTStr, SizeConst=128)] public string Str; public int Flags; [MarshalAs(UnmanagedType.ByValTStr, SizeConst=128)] public string Id; [MarshalAs(UnmanagedType.ByValTStr, SizeConst=128)] public string Key; }
  [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] public struct DM { [MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string n; public short a; public short b; public short size; public short ext; public int fields; public int x; public int y; public int orient; public int fixedOut; public short c1; public short c2; public short c3; public short c4; public short c5; [MarshalAs(UnmanagedType.ByValTStr, SizeConst=32)] public string f; public short lp; public int bpp; public int w; public int h; public int flags; public int hz; public int i1; public int i2; public int i3; public int i4; public int i5; public int i6; public int pw; public int ph; }
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool EnumDisplayDevices(string d, int i, ref DD dd, int f);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern bool EnumDisplaySettings(string d, int m, ref DM dm);
}
'@
$ecrans = @()
for ($i = 0; $i -lt 16; $i++) {
  $dd = New-Object TscDisp+DD; $dd.cb = [Runtime.InteropServices.Marshal]::SizeOf($dd)
  if (-not [TscDisp]::EnumDisplayDevices($null, $i, [ref]$dd, 0)) { break }
  if (($dd.Flags -band 1) -eq 0) { continue }   # pas rattache au bureau
  $dm = New-Object TscDisp+DM; $dm.size = [int16][Runtime.InteropServices.Marshal]::SizeOf($dm)
  if ([TscDisp]::EnumDisplaySettings($dd.Name, -1, [ref]$dm)) {
    $max = 0; $m = 0; $t = New-Object TscDisp+DM; $t.size = $dm.size
    while ([TscDisp]::EnumDisplaySettings($dd.Name, $m, [ref]$t)) { if ($t.w -eq $dm.w -and $t.h -eq $dm.h -and $t.hz -gt $max) { $max = $t.hz }; $m++ }
    $ecrans += [pscustomobject]@{ Ecran = $dd.Name; Carte = $dd.Str; Principal = [bool]($dd.Flags -band 4); Definition = "$($dm.w)x$($dm.h)"; Position = "$($dm.x),$($dm.y)"; FrequenceHz = $dm.hz; FrequenceMaxHz = $max }
  }
}
$moniteurs = Get-CimInstance -Namespace root\wmi WmiMonitorID | ForEach-Object { [pscustomobject]@{ Fabricant = -join [char[]]($_.ManufacturerName -ne 0); Modele = -join [char[]]($_.UserFriendlyName -ne 0) } }
Save '02_ecrans.txt' @(($ecrans | Format-Table -AutoSize), $moniteurs)

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
Save '04_shadow_client.txt' @($shadowApps, $shadowProc)
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
$ctr = @('\Processor(_Total)\% Processor Time', '\GPU Engine(*engtype_VideoDecode)\Utilization Percentage', '\GPU Engine(*engtype_3D)\Utilization Percentage', '\Memory\Available MBytes')
$s = Get-Counter -Counter $ctr -SampleInterval 1 -MaxSamples 30
# les compteurs GPU existent par moteur : on additionne par echantillon avant de resumer
$rows = foreach ($smp in $s) {
  $sum = @{ 'Processeur %' = 0; 'Decodage video %' = 0; 'GPU 3D %' = 0; 'RAM libre Mo' = 0 }
  foreach ($c in $smp.CounterSamples) {
    $k = if ($c.Path -match 'videodecode') { 'Decodage video %' } elseif ($c.Path -match 'engtype_3d') { 'GPU 3D %' } elseif ($c.Path -match 'processor') { 'Processeur %' } else { 'RAM libre Mo' }
    $sum[$k] += $c.CookedValue }
  foreach ($k in $sum.Keys) { [pscustomobject]@{ Mesure = $k; Valeur = $sum[$k] } } }
$agg = $rows | Group-Object Mesure | ForEach-Object {
  [pscustomobject]@{ Mesure = $_.Name; Moyenne = [math]::Round(($_.Group | Measure-Object Valeur -Average).Average,1); Max = [math]::Round(($_.Group | Measure-Object Valeur -Maximum).Maximum,1) } }
Save '06_charge_30s.txt' $agg

# 7. Processus et overlays
Write-Host "[7/7] Processus..."
Save '07_processus.txt' (Get-Process | Sort-Object CPU -Descending | Select-Object -First 30 ProcessName, Id, CPU, @{n='MemMo';e={[math]::Round($_.WorkingSet64/1MB)}})
Start-Process dxdiag.exe -ArgumentList "/t `"$(Join-Path $out 'dxdiag.txt')`"" -Wait

Compress-Archive -Path "$out\*" -DestinationPath "$out.zip" -Force
Write-Host ""
Write-Host "Termine. Envoie ce fichier dans le fil TSC Performance Lab :" -ForegroundColor Green
Write-Host "$out.zip"
try { Read-Host "Appuie sur Entree pour fermer" } catch {}
