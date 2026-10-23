# TSC Performance Lab - moteur (sans interface)
# Toutes les fonctions de lecture sont sans effet sur la machine.
# Les fonctions qui modifient quelque chose (profils, reglages Windows) sauvegardent d'abord
# l'etat d'origine et inscrivent l'operation dans l'historique, pour pouvoir la restaurer.
# Regle TSC : aucune injection dans le jeu, rien qui contourne TruckersMP ou MODGuard.

Set-StrictMode -Version 2

$script:PresentMonVersion = '2.6.0'
$script:PresentMonUrl     = 'https://github.com/GameTechDev/PresentMon/releases/download/v2.6.0/PresentMon-2.6.0-x64.exe'
$script:PresentMonSha256  = 'B2A706BC6AD475749E3B7E3409263AA1E6906D45BDCF993F6DBC0F660188F1AF'

# ---------------------------------------------------------------- chemins

function Get-PLDataRoot {
  $docs = [Environment]::GetFolderPath('MyDocuments')
  $root = Join-Path $docs 'TSC Driver\TSC Performance Lab'
  foreach ($d in @($root, (Join-Path $root 'mesures'), (Join-Path $root 'profils'), (Join-Path $root 'sauvegardes'), (Join-Path $root 'outils'), (Join-Path $root 'rapports'))) {
    if (-not (Test-Path -LiteralPath $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
  }
  $root
}

function Find-PLGame {
  # Cherche l'installation Steam d'ETS2 dans toutes les bibliotheques Steam
  $cands = @()
  $steam = $null
  foreach ($k in 'HKCU:\Software\Valve\Steam', 'HKLM:\SOFTWARE\WOW6432Node\Valve\Steam', 'HKLM:\SOFTWARE\Valve\Steam') {
    $p = Get-ItemProperty -Path $k -ErrorAction SilentlyContinue
    if ($p) {
      foreach ($n in 'SteamPath', 'InstallPath') { if ($p.PSObject.Properties[$n] -and $p.$n) { $steam = $p.$n; break } }
    }
    if ($steam) { break }
  }
  if ($steam) {
    $steam = $steam -replace '/', '\'
    $cands += Join-Path $steam 'steamapps\common\Euro Truck Simulator 2'
    $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'
    if (Test-Path -LiteralPath $vdf) {
      foreach ($m in [regex]::Matches((Get-Content -LiteralPath $vdf -Raw), '"path"\s+"([^"]+)"')) {
        $cands += Join-Path ($m.Groups[1].Value -replace '\\\\', '\') 'steamapps\common\Euro Truck Simulator 2'
      }
    }
  }
  $cands += 'C:\Program Files (x86)\Steam\steamapps\common\Euro Truck Simulator 2'
  $game = $cands | Where-Object { Test-Path -LiteralPath (Join-Path $_ 'bin\win_x64\eurotrucks2.exe') } | Select-Object -First 1
  $docs = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Euro Truck Simulator 2'
  [pscustomobject]@{
    GameDir    = $game
    SteamDir   = $steam
    DocsDir    = $(if (Test-Path -LiteralPath $docs) { $docs } else { $null })
    Exe        = $(if ($game) { Join-Path $game 'bin\win_x64\eurotrucks2.exe' } else { $null })
    Running    = [bool](Get-Process -Name eurotrucks2 -ErrorAction SilentlyContinue)
  }
}

# ---------------------------------------------------------------- config.cfg

function Read-PLConfig {
  # Lit un config.cfg d'ETS2 : lignes 'uset nom "valeur"'. Renvoie un dictionnaire ordonne.
  param([Parameter(Mandatory)][string]$Path)
  $h = [ordered]@{}
  if (-not (Test-Path -LiteralPath $Path)) { return $h }
  foreach ($l in Get-Content -LiteralPath $Path) {
    if ($l -match '^\s*uset\s+(\S+)\s+"(.*)"\s*$') { $h[$Matches[1]] = $Matches[2] }
  }
  $h
}

function Write-PLConfigOverrides {
  # Ecrit une copie de config.cfg ou seules les variables donnees changent ; le reste est conserve a l'identique.
  param([Parameter(Mandatory)][string]$Source, [Parameter(Mandatory)][string]$Destination, [Parameter(Mandatory)][hashtable]$Overrides)
  $lines = @(Get-Content -LiteralPath $Source)
  $done = @{}
  $out = foreach ($l in $lines) {
    if ($l -match '^(\s*uset\s+)(\S+)(\s+)"(.*)"\s*$' -and $Overrides.ContainsKey($Matches[2])) {
      $done[$Matches[2]] = $true
      '{0}{1}{2}"{3}"' -f $Matches[1], $Matches[2], $Matches[3], $Overrides[$Matches[2]]
    } else { $l }
  }
  foreach ($k in $Overrides.Keys) { if (-not $done.ContainsKey($k)) { $out += ('uset {0} "{1}"' -f $k, $Overrides[$k]) } }
  # le jeu ecrit ce fichier en ASCII/UTF-8 sans BOM
  [IO.File]::WriteAllLines($Destination, [string[]]$out, (New-Object Text.UTF8Encoding($false)))
}

function Get-PLActiveProfileDir {
  param([string]$DocsDir)
  if (-not $DocsDir) { return $null }
  $dirs = @()
  foreach ($sub in 'profiles', 'steam_profiles') {
    $p = Join-Path $DocsDir $sub
    if (Test-Path -LiteralPath $p) { $dirs += Get-ChildItem -LiteralPath $p -Directory -ErrorAction SilentlyContinue }
  }
  # profil le plus recemment utilise = sauvegarde la plus recente
  $dirs | Sort-Object { $f = Get-ChildItem -LiteralPath $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1; if ($f) { $f.LastWriteTime } else { $_.LastWriteTime } } -Descending | Select-Object -First 1
}

function ConvertFrom-PLHexName {
  # Les dossiers de profil ETS2 sont le nom du profil en hexadecimal
  param([string]$Hex)
  if ($Hex -notmatch '^([0-9A-Fa-f]{2})+$') { return $Hex }
  $b = for ($i = 0; $i -lt $Hex.Length; $i += 2) { [Convert]::ToByte($Hex.Substring($i, 2), 16) }
  [Text.Encoding]::UTF8.GetString([byte[]]$b)
}

# Reglages graphiques suivis : libelle, et si une valeur plus haute = qualite plus haute
$script:GfxVars = [ordered]@{
  'r_mode_width'           = 'Largeur'
  'r_mode_height'          = 'Hauteur'
  'r_fullscreen'           = 'Plein ecran'
  'r_vsync'                = 'Synchro verticale'
  'r_scale_x'              = 'Echelle de rendu X'
  'r_scale_y'              = 'Echelle de rendu Y'
  'g_hq_3d_scale'          = 'Echelle 3D haute qualite'
  'r_aa'                   = 'Anticrenelage (MSAA)'
  'r_taa_tuning'           = 'TAA'
  'r_ssao'                 = 'Occlusion ambiante'
  'r_dof'                  = 'Profondeur de champ'
  'r_sun_shadow_quality'   = 'Qualite des ombres'
  'r_sun_shadow_texture_size' = 'Taille des ombres'
  'r_far_shadow_disable'   = 'Ombres lointaines coupees'
  'r_anisotropy_factor'    = 'Filtrage anisotrope'
  'r_texture_detail'       = 'Detail des textures'
  'r_mirror_scale_x'       = 'Resolution retros X'
  'r_mirror_view_distance' = 'Distance retros'
  'r_deferred_mirrors'     = 'Retros differes'
  'g_reflection'           = 'Reflets'
  'g_rain_reflection'      = 'Reflets de pluie'
  'g_grass_density'        = 'Densite herbe'
  'g_traffic'              = 'Densite du trafic'
  'g_lod_factor_traffic'   = 'Detail du trafic'
  'g_lod_factor_parked'    = 'Detail vehicules gares'
  'g_lod_factor_pedestrian'= 'Detail pietons'
  'r_light_distance_factor'= 'Distance des lumieres'
  'r_buffer_page_size'     = 'Taille des pages tampon'
  'r_minimal_unfinished_frames' = 'Images en attente'
  'g_mirrors'              = 'Retros (profil)'
  't_limit_fps'            = 'Limite d''images/s du jeu'
  't_locked_fps'           = 'Images/s verrouillees'
  'r_multimon_mode'        = 'Mode multi-ecran'
  'g_veg_detail'           = 'Detail vegetation'
  'r_sunshafts'            = 'Rayons de soleil'
  'r_mirror_group'         = 'Groupe de retros'
  'r_interior_shadow'      = 'Ombres interieures'
  'r_fake_shadows'         = 'Ombres simulees'
  'r_cloud_shadows'        = 'Ombres des nuages'
  'g_reflection_scale'     = 'Echelle des reflets'
}

function Get-PLGraphics {
  param([string]$DocsDir)
  $global = if ($DocsDir) { Read-PLConfig (Join-Path $DocsDir 'config.cfg') } else { [ordered]@{} }
  $prof = Get-PLActiveProfileDir $DocsDir
  $pcfg = if ($prof) { Read-PLConfig (Join-Path $prof.FullName 'config.cfg') } else { [ordered]@{} }
  $rows = foreach ($k in $script:GfxVars.Keys) {
    $v = $null; $src = ''
    if ($pcfg.Contains($k)) { $v = $pcfg[$k]; $src = 'profil' } elseif ($global.Contains($k)) { $v = $global[$k]; $src = 'global' }
    if ($null -ne $v) { [pscustomobject]@{ Variable = $k; Reglage = $script:GfxVars[$k]; Valeur = $v; Fichier = $src } }
  }
  [pscustomobject]@{
    Global      = $global
    Profile     = $pcfg
    ProfileDir  = $(if ($prof) { $prof.FullName } else { $null })
    ProfileName = $(if ($prof) { ConvertFrom-PLHexName $prof.Name } else { $null })
    Rows        = @($rows)
  }
}

# ---------------------------------------------------------------- machine

function Get-PLMachine {
  $cs  = Get-CimInstance Win32_ComputerSystem -ErrorAction SilentlyContinue
  $os  = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
  $cpu = Get-CimInstance Win32_Processor -ErrorAction SilentlyContinue | Select-Object -First 1
  $gpus = @(Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue | Where-Object { $_.Name -notmatch 'QXL|Basic Display|Remote' })
  $disk = foreach ($d in @(Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' -ErrorAction SilentlyContinue)) {
    [pscustomobject]@{ Lecteur = $d.DeviceID; TailleGo = [math]::Round($d.Size / 1GB, 1); LibreGo = [math]::Round($d.FreeSpace / 1GB, 1) }
  }
  $reg = { param($p, $n) $x = Get-ItemProperty -Path $p -Name $n -ErrorAction SilentlyContinue; if ($x) { $x.$n } else { $null } }
  $plan = (powercfg /getactivescheme) 2>$null | Out-String
  [pscustomobject]@{
    Nom          = $env:COMPUTERNAME
    Modele       = $(if ($cs) { "$($cs.Manufacturer) $($cs.Model)".Trim() } else { '' })
    EstShadow    = [bool]($cs -and $cs.Model -match 'Shadow')
    Windows      = $(if ($os) { "$($os.Caption) (build $($os.BuildNumber))" } else { '' })
    Processeur   = $(if ($cpu) { $cpu.Name.Trim() } else { '' })
    Coeurs       = $(if ($cpu) { $cpu.NumberOfCores } else { 0 })
    Threads      = $(if ($cpu) { $cpu.NumberOfLogicalProcessors } else { 0 })
    FrequenceMHz = $(if ($cpu) { $cpu.MaxClockSpeed } else { 0 })
    RamGo        = $(if ($cs) { [math]::Round($cs.TotalPhysicalMemory / 1GB, 1) } else { 0 })
    RamLibreGo   = $(if ($os) { [math]::Round($os.FreePhysicalMemory / 1MB, 1) } else { 0 })
    CartesGraphiques = @($gpus | ForEach-Object { [pscustomobject]@{ Nom = $_.Name; Pilote = $_.DriverVersion; Date = $(if ($_.DriverDate) { ([datetime]$_.DriverDate).ToString('dd/MM/yyyy') } else { '' }); Definition = "$($_.CurrentHorizontalResolution)x$($_.CurrentVerticalResolution)"; FrequenceHz = $_.CurrentRefreshRate } })
    Disques      = @($disk)
    PlanAlimentation = $(if ($plan -match '\(([^)]+)\)\s*$') { $Matches[1] } else { $plan.Trim() })
    HAGS         = & $reg 'HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers' 'HwSchMode'
    ModeJeu      = & $reg 'HKCU:\Software\Microsoft\GameBar' 'AutoGameModeEnabled'
    GameDVR      = & $reg 'HKCU:\System\GameConfigStore' 'GameDVR_Enabled'
    CaptureApp   = & $reg 'HKCU:\Software\Microsoft\Windows\CurrentVersion\GameDVR' 'AppCaptureEnabled'
  }
}

function Get-PLGpuPreference {
  param([string]$Exe)
  if (-not $Exe) { return $null }
  $v = Get-ItemProperty -Path 'HKCU:\Software\Microsoft\DirectX\UserGpuPreferences' -Name $Exe -ErrorAction SilentlyContinue
  if ($v) { $v.$Exe } else { $null }
}

$script:KnownOverlays = [ordered]@{
  'Discord'            = 'Discord (overlay possible)'
  'GameOverlayUI'      = 'Overlay Steam'
  'nvcontainer'        = 'NVIDIA App / ShadowPlay'
  'NVIDIA Share'       = 'NVIDIA Share (capture)'
  'GameBar'            = 'Xbox Game Bar'
  'GameBarPresenceWriter' = 'Xbox Game Bar'
  'RTSS'               = 'RivaTuner Statistics Server'
  'MSIAfterburner'     = 'MSI Afterburner'
  'obs64'              = 'OBS (capture)'
  'Medal'              = 'Medal (capture)'
  'Overwolf'           = 'Overwolf'
  'RazerCortex'        = 'Razer Cortex'
  'ProcessLasso'       = 'Process Lasso (priorites et affinites)'
  'wgc'                = 'Wargaming Game Center'
  'chrome'             = 'Chrome'
  'msedge'             = 'Edge'
  'Spotify'            = 'Spotify'
  'OneDrive'           = 'OneDrive (synchronisation)'
}

function Get-PLBackground {
  $procs = Get-Process -ErrorAction SilentlyContinue
  $found = foreach ($k in $script:KnownOverlays.Keys) {
    $p = @($procs | Where-Object { $_.ProcessName -eq $k })
    if ($p.Count) {
      $cpu = ($p | Measure-Object -Property CPU -Sum).Sum
      $mem = ($p | Measure-Object -Property WorkingSet64 -Sum).Sum
      [pscustomobject]@{ Programme = $script:KnownOverlays[$k]; Processus = $k; Instances = $p.Count; CpuCumuleS = [math]::Round([double]$cpu, 0); MemoireMo = [math]::Round($mem / 1MB) }
    }
  }
  @($found | Sort-Object CpuCumuleS -Descending)
}

# ---------------------------------------------------------------- installation du jeu : injections et plugins

function Get-PLInjections {
  param([string]$GameDir)
  if (-not $GameDir) { return @() }
  $bin = Join-Path $GameDir 'bin\win_x64'
  $known = [ordered]@{ 'dxgi.dll' = 'Proxy DXGI (souvent ReShade)'; 'd3d11.dll' = 'Proxy Direct3D 11'; 'd3d9.dll' = 'Proxy Direct3D 9'; 'dinput8.dll' = 'Proxy DirectInput'; 'opengl32.dll' = 'Proxy OpenGL'; 'version.dll' = 'Proxy version.dll' }
  $res = @()
  foreach ($f in @(Get-ChildItem -LiteralPath $bin -File -Filter *.dll -ErrorAction SilentlyContinue)) {
    $n = $f.Name.ToLower()
    $role = $null
    if ($known.Contains($n)) { $role = $known[$n] }
    elseif ($n -match '^(dxgi|d3d11)\d+\.dll$') { $role = 'Seconde couche DXGI/D3D chargee par un proxy' }
    elseif ($n -match 'reshade') { $role = 'ReShade' }
    if ($role) {
      $vi = $f.VersionInfo
      $desc = (@($vi.ProductName, $vi.FileDescription) | Where-Object { $_ }) -join ' / '
      if ($desc -match 'ReShade') { $role = 'ReShade' }
      $res += [pscustomobject]@{ Fichier = $f.Name; Role = $role; Produit = $desc; Version = $vi.FileVersion; TailleMo = [math]::Round($f.Length / 1MB, 1) }
    }
  }
  $res
}

function Get-PLPlugins {
  param([string]$GameDir)
  if (-not $GameDir) { return @() }
  $dir = Join-Path $GameDir 'bin\win_x64\plugins'
  @(Get-ChildItem -LiteralPath $dir -Recurse -File -Filter *.dll -ErrorAction SilentlyContinue | ForEach-Object {
    $vi = $_.VersionInfo
    [pscustomobject]@{
      Fichier  = $_.Name
      Version  = $vi.FileVersion
      Produit  = (@($vi.ProductName, $vi.FileDescription) | Where-Object { $_ }) -join ' / '
      Date     = $_.LastWriteTime.ToString('dd/MM/yyyy')
      TailleMo = [math]::Round($_.Length / 1MB, 1)
      Telemetrie = [bool]($_.Name -match 'telemetr|trucky|tb_64|haulmp')
    }
  })
}

# ---------------------------------------------------------------- journal du jeu

function Get-PLGameLog {
  # Analyse game.log.txt (format "HH:MM:SS.mmm : message", temps depuis le lancement du jeu)
  param([Parameter(Mandatory)][string]$Path)
  $r = [ordered]@{ Chemin = $Path; Version = $null; Rendu = @(); Erreurs = @(); Avertissements = @(); Mods = @(); Incompatibles = @(); Doublons = @(); Crochets = @(); ChargementCarteS = $null; ChargementSauvegardeS = $null; WorkshopRecus = $null; Lignes = 0 }
  if (-not (Test-Path -LiteralPath $Path)) { return [pscustomobject]$r }
  $lines = @(Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue)
  $r.Lignes = $lines.Count
  $err = @{}; $warn = @{}
  # le jeu monte les mods une fois au menu puis une fois au chargement du profil : on garde la derniere serie
  $series = New-Object System.Collections.Generic.List[object]
  $cur = $null; $lastDevice = $null; $lastT = -1000.0
  foreach ($l in $lines) {
    $t = $null; $msg = $l
    if ($l -match '^(\d{2}):(\d{2}):(\d{2})\.(\d{3})\s*:\s?(.*)$') {
      $t = [int]$Matches[1] * 3600 + [int]$Matches[2] * 60 + [int]$Matches[3] + [int]$Matches[4] / 1000.0
      $msg = $Matches[5]
    }
    if (-not $r.Version -and $msg -match '\[ufs\] Loaded pack set version (\S+)') { $r.Version = $Matches[1] }
    if ($msg -match '^\[(gfx|dxgi|dx11|disp)\]') { if ($r.Rendu.Count -lt 40) { $r.Rendu += $msg } }
    if ($msg -match '\[d3d_hook\]|hooked') { if ($r.Crochets.Count -lt 20) { $r.Crochets += $msg } }
    if ($msg -match '<ERROR>') { if ($err.ContainsKey($msg)) { $err[$msg]++ } else { $err[$msg] = 1 } }
    elseif ($msg -match '<WARNING>') { if ($warn.ContainsKey($msg)) { $warn[$msg]++ } else { $warn[$msg] = 1 } }
    if ($msg -match 'Incompatible mod\s*-\s*(.+?)\s*$') { $r.Incompatibles += $Matches[1] }
    if ($msg -match "Package with name '([^']+)' seen more than once") { $r.Doublons += $Matches[1] }
    if ($msg -match 'Received list of the steam workshop subscribed mods\. \(received (\d+)') { $r.WorkshopRecus = [int]$Matches[1] }
    if ($msg -match '^\[fs\] device (.+) mounted to mod pool\.') { $lastDevice = $Matches[1] }
    if ($msg -match '^\[mod_package_manager\] Mod "(.+)" has been mounted\. \(package_name: (.*?), version: (.*?), source: (.*?)\)') {
      if ($null -eq $cur -or ($t -ne $null -and $t - $lastT -gt 20)) { $cur = New-Object System.Collections.Generic.List[object]; $series.Add($cur) }
      $mod = [pscustomobject]@{ Ordre = $cur.Count + 1; Nom = $Matches[1]; Paquet = $Matches[2]; Version = $Matches[3]; Source = $Matches[4]; Chemin = $lastDevice; WorkshopId = $null; Fichier = $null }
      $lastDevice = $null
      if ($mod.Chemin) {
        $mod.Fichier = ($mod.Chemin -split '[\\/]')[-1]
        if ($mod.Chemin -match 'workshop/content/227300/(\d+)') { $mod.WorkshopId = $Matches[1] }
      }
      $cur.Add($mod)
      if ($t -ne $null) { $lastT = $t }
    }
    if ($t -ne $null -and $msg -match '^Map loaded') { $r.ChargementCarteS = [math]::Round($t, 1) }
    if ($t -ne $null -and $msg -match '^Loading save\.') { $r.ChargementSauvegardeS = [math]::Round($t, 1) }
  }
  $r.Erreurs = @($err.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object { [pscustomobject]@{ Nombre = $_.Value; Message = $_.Key } })
  $r.Avertissements = @($warn.GetEnumerator() | Sort-Object Value -Descending | ForEach-Object { [pscustomobject]@{ Nombre = $_.Value; Message = $_.Key } })
  if ($series.Count) { $r.Mods = @($series[$series.Count - 1].ToArray()) }
  $r.Incompatibles = @($r.Incompatibles | Select-Object -Unique)
  $r.Doublons = @($r.Doublons | Select-Object -Unique)
  [pscustomobject]$r
}

function Get-PLCrashes {
  # Plantages d'ETS2 enregistres par Windows (Application Error 1000 / blocage 1002), groupes par module en faute
  param([int]$Days = 30)
  $since = (Get-Date).AddDays(-$Days)
  $ev = @(Get-WinEvent -FilterHashtable @{ LogName = 'Application'; Id = 1000, 1002; StartTime = $since } -ErrorAction SilentlyContinue |
        Where-Object { $_.Message -match 'eurotrucks2' })
  $rows = foreach ($e in $ev) {
    # Proprietes stables quelle que soit la langue : [0] appli, [3] module en faute (pour l'ID 1000)
    $mod = $null
    if ($e.Id -eq 1000 -and $e.Properties.Count -gt 3) { $mod = [string]$e.Properties[3].Value }
    if (-not $mod -and $e.Id -eq 1002) { $mod = '(blocage, sans module)' }
    [pscustomobject]@{ Date = $e.TimeCreated; Type = $(if ($e.Id -eq 1000) { 'Plantage' } else { 'Blocage' }); Module = $mod }
  }
  [pscustomobject]@{
    Jours     = $Days
    Total     = @($rows).Count
    Dernier   = $(if (@($rows).Count) { ($rows | Sort-Object Date -Descending | Select-Object -First 1).Date } else { $null })
    ParModule = @($rows | Group-Object Module | Sort-Object Count -Descending | ForEach-Object { [pscustomobject]@{ Module = $_.Name; Nombre = $_.Count } })
    Liste     = @($rows | Sort-Object Date -Descending)
  }
}

# ---------------------------------------------------------------- mods

function Get-PLMods {
  param([string]$DocsDir, [string]$SteamDir, $GameLog)
  $items = @()
  if ($DocsDir) {
    foreach ($f in @(Get-ChildItem -LiteralPath (Join-Path $DocsDir 'mod') -ErrorAction SilentlyContinue)) {
      $size = if ($f.PSIsContainer) { (Get-ChildItem -LiteralPath $f.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum } else { $f.Length }
      $items += [pscustomobject]@{ Cle = $f.Name.ToLower(); Fichier = $f.Name; Source = 'Dossier mod'; TailleMo = [math]::Round([double]$size / 1MB, 1); Date = $f.LastWriteTime }
    }
  }
  if ($SteamDir) {
    foreach ($d in @(Get-ChildItem -LiteralPath (Join-Path $SteamDir 'steamapps\workshop\content\227300') -Directory -ErrorAction SilentlyContinue)) {
      $size = (Get-ChildItem -LiteralPath $d.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
      $items += [pscustomobject]@{ Cle = 'ws:' + $d.Name; Fichier = $d.Name; Source = 'Workshop'; TailleMo = [math]::Round([double]$size / 1MB, 1); Date = $d.LastWriteTime }
    }
  }
  $mounted = @(); $incompat = @(); $msgs = @()
  if ($GameLog) { $mounted = @($GameLog.Mods); $incompat = @($GameLog.Incompatibles); $msgs = @($GameLog.Erreurs) + @($GameLog.Avertissements) }
  $byKey = @{}
  foreach ($m in $mounted) {
    if ($m.WorkshopId) { $byKey['ws:' + $m.WorkshopId] = $m } elseif ($m.Fichier) { $byKey[$m.Fichier.ToLower()] = $m }
  }
  $rows = foreach ($it in $items) {
    $m = $byKey[$it.Cle]
    $names = @($it.Fichier, [IO.Path]::GetFileNameWithoutExtension($it.Fichier))
    if ($m) { $names += $m.Nom; $names += $m.Paquet }
    $names = @($names | Where-Object { $_ -and $_.Length -ge 4 } | Select-Object -Unique)
    $n = 0
    foreach ($e in $msgs) { foreach ($k in $names) { if ($e.Message.IndexOf($k, [StringComparison]::OrdinalIgnoreCase) -ge 0) { $n += $e.Nombre; break } } }
    $inc = $false
    foreach ($i in $incompat) { foreach ($k in $names) { if ($i.IndexOf(($k -replace '[^\w]', '_'), [StringComparison]::OrdinalIgnoreCase) -ge 0 -or $i -eq $k) { $inc = $true } } }
    [pscustomobject]@{
      Ordre = $(if ($m) { $m.Ordre } else { $null }); Nom = $(if ($m) { $m.Nom } else { [IO.Path]::GetFileNameWithoutExtension($it.Fichier) })
      Version = $(if ($m) { $m.Version } else { '' }); Source = $it.Source; Fichier = $it.Fichier; TailleMo = $it.TailleMo
      Date = $it.Date.ToString('dd/MM/yyyy'); Monte = [bool]$m; Incompatible = $inc; Messages = [int]$n
    }
  }
  [pscustomobject]@{
    Liste    = @($rows | Sort-Object @{ e = { if ($_.Ordre) { $_.Ordre } else { 99999 } } }, Nom)
    Total    = @($items).Count
    TailleGo = [math]::Round((($items | Measure-Object TailleMo -Sum).Sum) / 1024, 1)
    Montes   = $mounted.Count
    TailleMonteeGo = [math]::Round((($rows | Where-Object Monte | Measure-Object TailleMo -Sum).Sum) / 1024, 1)
  }
}

# ---------------------------------------------------------------- recommandations

function New-PLReco {
  param($Id, $Titre, $Constat, $Action, $Impact, $Risque, [bool]$TouchQualite, [bool]$Auto)
  [pscustomobject]@{ Id = $Id; Titre = $Titre; Constat = $Constat; Action = $Action; Impact = $Impact; Risque = $Risque; QualiteTouchee = $(if ($TouchQualite) { 'Oui (profil separe)' } else { 'Non' }); Applicable = $Auto }
}

function Get-PLRecommendations {
  # Regles fondees sur les donnees relevees. Aucune ne baisse la qualite du profil principal.
  param($Diag)
  $r = @()
  $rank = @{ 'Tres fort' = 0; 'Fort' = 1; 'Moyen' = 2; 'Faible' = 3; 'A mesurer' = 4 }
  if ($Diag.Plantages -and $Diag.Plantages.Total -gt 0) {
    $top = $Diag.Plantages.ParModule | Select-Object -First 3 | ForEach-Object { "$($_.Module) x$($_.Nombre)" }
    $r += New-PLReco 'crash-modules' 'Plantages du jeu' "$($Diag.Plantages.Total) plantages sur $($Diag.Plantages.Jours) jours. Modules en faute : $($top -join ', ')." 'Verifier la version de chaque plugin en cause pour la version du jeu, puis comparer des sessions avec et sans le plugin suspect.' 'Tres fort' 'Faible' $false $false
  }
  $tele = @($Diag.Plugins | Where-Object { $_.Telemetrie })
  if ($tele.Count -ge 3) {
    $r += New-PLReco 'telemetry-count' 'Plusieurs plugins de telemetrie' "$($tele.Count) plugins de telemetrie appeles a chaque image : $((@($tele | ForEach-Object Fichier)) -join ', ')." 'Garder seulement ceux dont tu utilises vraiment l''appli. Les autres peuvent etre deplaces hors du dossier plugins (reversible).' 'Moyen' 'Faible' $false $false
  }
  $gl = if ($Diag.Graphismes) { $Diag.Graphismes.Global } else { [ordered]@{} }
  $lim = if ($gl.Contains('t_limit_fps')) { [int]$gl['t_limit_fps'] } else { 0 }
  $vs = if ($gl.Contains('r_vsync')) { $gl['r_vsync'] } else { $null }
  if ($vs -eq '0' -and $lim -ne 60) {
    $r += New-PLReco 'frame-cadence' 'Rythme des images different de celui des ecrans' "Le jeu vise $(if ($lim) { "$lim images/s (t_limit_fps $lim)" } else { 'un nombre d''images non limite' }), sans synchro verticale, alors que les ecrans du PC principal affichent 60 images/s. Le surplus est jete de facon irreguliere." 'Mesurer le profil actuel puis le profil "Limite 60 images/s" sur le meme parcours, avec le flux Shadow regle a 60, et garder le plus regulier.' 'Fort' 'Faible' $false $true
  }
  if ($gl.Contains('r_multimon_mode') -and $gl['r_multimon_mode'] -ne '0') {
    $r += New-PLReco 'multimon' 'Mode multi-ecran du jeu actif' "r_multimon_mode = $($gl['r_multimon_mode']). Selon le mode, le jeu calcule une vue par ecran, ce qui multiplie le travail du processeur." 'A chiffrer : mesurer le meme parcours avec ce mode et en ecran unique etire, avant toute decision.' 'A mesurer' 'Faible' $false $false
  }
  if ($Diag.Journal -and @($Diag.Journal.Crochets).Count) {
    $r += New-PLReco 'present-hooks' 'Plugin accroche a l''affichage du jeu' "Le journal montre un plugin qui s'accroche a chaque image affichee : $((@($Diag.Journal.Crochets) | Select-Object -First 1))" 'A chiffrer : mesurer avec et sans ce plugin (deplacement reversible hors du dossier plugins).' 'A mesurer' 'Faible' $false $false
  }
  if ($Diag.Machine -and $Diag.Game -and $Diag.Game.Exe) {
    $pref = Get-PLGpuPreference $Diag.Game.Exe
    if ($pref -and $pref -match 'GpuPreference=1') {
      $r += New-PLReco 'gpu-pref' 'Preference graphique "economie d''energie"' 'Windows demande la carte economique pour eurotrucks2.exe.' 'Passer la preference en "hautes performances" (sauvegarde et restauration automatiques).' 'Faible' 'Tres faible' $false $true
    }
    if ($Diag.Machine.GameDVR -eq 1 -or $Diag.Machine.CaptureApp -eq 1) {
      $r += New-PLReco 'game-dvr' 'Capture Windows active' 'Game DVR / capture d''applications est actif : il peut enregistrer en fond et solliciter l''encodeur video.' 'Couper Game DVR et la capture d''applications (sauvegarde et restauration automatiques).' 'Moyen' 'Tres faible' $false $true
    }
    if ($Diag.Machine.PlanAlimentation -and $Diag.Machine.PlanAlimentation -notmatch 'performance|Performances|Bitsum') {
      $r += New-PLReco 'power-plan' 'Plan d''alimentation standard' "Plan actif : $($Diag.Machine.PlanAlimentation)." 'Activer le plan "Performances elevees" pendant le jeu (le plan d''origine est restaurable).' 'Faible' 'Tres faible' $false $true
    }
  }
  if ($Diag.Machine) {
    $sys = $Diag.Machine.Disques | Where-Object { $_.Lecteur -eq 'C:' }
    if ($sys -and $sys.LibreGo -lt 80) {
      $r += New-PLReco 'disk-space' 'Peu d''espace libre sur C:' "$($sys.LibreGo) Go libres." 'Liberer de l''espace (anciens mods, caches) pour garder de la marge au fichier d''echange et aux sauvegardes.' 'Moyen' 'Faible' $false $false
    }
  }
  $inj = @($Diag.Injections)
  if ($inj.Count) {
    $r += New-PLReco 'injection-cost' 'Cout du post-traitement a chiffrer' "Couches injectees : $((@($inj | ForEach-Object Fichier)) -join ', ')." 'Mesurer le meme parcours avec le prereglage ReShade actuel puis "Sans effet" pour chiffrer son cout exact. Aucun changement sans ta decision.' 'A mesurer' 'Faible' $false $false
  }
  if ($Diag.Journal -and @($Diag.Journal.Incompatibles).Count) {
    $r += New-PLReco 'incompatible-mods' 'Mods signales incompatibles' "Le jeu signale : $((@($Diag.Journal.Incompatibles)) -join ', ')." 'Mettre a jour ou retirer ces mods du profil (gestionnaire de mods du jeu).' 'Faible' 'Faible' $false $false
  }
  if ($Diag.Journal -and @($Diag.Journal.Doublons).Count) {
    $r += New-PLReco 'duplicate-packages' 'Paquets en double' "Presents deux fois (fichier .scs et dossier) : $((@($Diag.Journal.Doublons)) -join ', ')." 'Garder une seule copie de chaque paquet pour alleger le chargement.' 'Faible' 'Faible' $false $false
  }
  if ($Diag.Journal -and $Diag.Journal.ChargementCarteS -and $Diag.Journal.ChargementCarteS -gt 180) {
    $r += New-PLReco 'load-time' 'Chargement tres long' "Carte chargee en $([math]::Round($Diag.Journal.ChargementCarteS / 60, 1)) min." 'Comparer le temps de chargement avec un profil de test allege pour chiffrer le cout des gros mods.' 'Moyen' 'Faible' $false $false
  }
  @($r | Sort-Object { $rank[$_.Impact] })
}

# ---------------------------------------------------------------- diagnostic complet

function Invoke-PLDiagnostic {
  $g = Find-PLGame
  $log = $null
  if ($g.DocsDir) { $log = Get-PLGameLog (Join-Path $g.DocsDir 'game.log.txt') }
  $d = [pscustomobject]@{
    Date        = Get-Date
    Machine     = Get-PLMachine
    Game        = $g
    Graphismes  = Get-PLGraphics $g.DocsDir
    Injections  = @(Get-PLInjections $g.GameDir)
    Plugins     = @(Get-PLPlugins $g.GameDir)
    Journal     = $log
    Mods        = Get-PLMods -DocsDir $g.DocsDir -SteamDir $g.SteamDir -GameLog $log
    Plantages   = Get-PLCrashes
    ArrierePlan = Get-PLBackground
    Recommandations = @()
  }
  $d.Recommandations = Get-PLRecommendations $d
  $d
}

# ---------------------------------------------------------------- mesures (PresentMon, sans injection)

function Get-PLPresentMon {
  # Renvoie le chemin de PresentMon verifie par empreinte SHA-256 ; le telecharge si besoin.
  param([switch]$NoDownload)
  $exe = Join-Path (Join-Path (Get-PLDataRoot) 'outils') "PresentMon-$script:PresentMonVersion-x64.exe"
  if (-not (Test-Path -LiteralPath $exe)) {
    if ($NoDownload) { return $null }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $tmp = "$exe.part"
    Invoke-WebRequest -Uri $script:PresentMonUrl -OutFile $tmp -UseBasicParsing
    Move-Item -LiteralPath $tmp -Destination $exe -Force
  }
  $h = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash
  if ($h -ne $script:PresentMonSha256) { Remove-Item -LiteralPath $exe -Force; throw "Empreinte de PresentMon incorrecte ($h) : fichier supprime." }
  $exe
}

function Get-PLPercentile {
  param([double[]]$Sorted, [double]$P)
  if (-not $Sorted.Count) { return $null }
  $i = [math]::Ceiling($P / 100 * $Sorted.Count) - 1
  $Sorted[[math]::Max(0, [math]::Min($Sorted.Count - 1, $i))]
}

function Get-PLFrameStats {
  # Statistiques de temps de trame a partir d'un CSV PresentMon (formats v1 et v2)
  param([Parameter(Mandatory)][string]$CsvPath, [string]$Process = 'eurotrucks2.exe', [double]$SkipSeconds = 2)
  $rows = @(Import-Csv -LiteralPath $CsvPath)
  if (-not $rows.Count) { throw 'Aucune image enregistree : le jeu etait-il au premier plan et en mouvement ?' }
  $cols = $rows[0].PSObject.Properties.Name
  $ftCol = @('FrameTime', 'MsBetweenPresents', 'msBetweenPresents') | Where-Object { $cols -contains $_ } | Select-Object -First 1
  if (-not $ftCol) { throw "Colonne de temps de trame introuvable dans le CSV ($($cols -join ', '))." }
  $cpuCol = @('CPUBusy', 'MsCPUBusy') | Where-Object { $cols -contains $_ } | Select-Object -First 1
  $gpuCol = @('GPUBusy', 'MsGPUBusy') | Where-Object { $cols -contains $_ } | Select-Object -First 1
  $dispCol = @('DisplayedTime', 'MsBetweenDisplayChange', 'msBetweenDisplayChange') | Where-Object { $cols -contains $_ } | Select-Object -First 1
  $inv = [Globalization.CultureInfo]::InvariantCulture
  $num = { param($s) $v = 0.0; if ([double]::TryParse([string]$s, [Globalization.NumberStyles]::Float, $inv, [ref]$v)) { $v } else { [double]::NaN } }
  if ($cols -contains 'Application') { $rows = @($rows | Where-Object { $_.Application -eq $Process -or -not $Process }) }
  # le processus peut avoir plusieurs chaines d'affichage : garder la principale (la plus d'images)
  if ($cols -contains 'SwapChainAddress') {
    $main = $rows | Group-Object SwapChainAddress | Sort-Object Count -Descending | Select-Object -First 1
    if ($main) { $rows = @($main.Group) }
  }
  $ft = New-Object System.Collections.Generic.List[double]
  $cpu = New-Object System.Collections.Generic.List[double]
  $gpu = New-Object System.Collections.Generic.List[double]
  $disp = New-Object System.Collections.Generic.List[double]
  $elapsed = 0.0
  foreach ($r in $rows) {
    $v = & $num $r.$ftCol
    if ([double]::IsNaN($v) -or $v -le 0 -or $v -gt 5000) { continue }
    $elapsed += $v / 1000
    if ($elapsed -lt $SkipSeconds) { continue }
    $ft.Add($v)
    if ($cpuCol) { $c = & $num $r.$cpuCol; if (-not [double]::IsNaN($c)) { $cpu.Add($c) } }
    if ($gpuCol) { $g = & $num $r.$gpuCol; if (-not [double]::IsNaN($g)) { $gpu.Add($g) } }
    if ($dispCol) { $d = & $num $r.$dispCol; if (-not [double]::IsNaN($d) -and $d -gt 0) { $disp.Add($d) } }
  }
  if ($ft.Count -lt 30) { throw "Trop peu d'images exploitables ($($ft.Count))." }
  $arr = $ft.ToArray()
  $sorted = [double[]]($arr | Sort-Object)
  $sum = 0.0; foreach ($x in $arr) { $sum += $x }
  $mean = $sum / $arr.Count
  $var = 0.0; foreach ($x in $arr) { $var += ($x - $mean) * ($x - $mean) }
  $sd = [math]::Sqrt($var / $arr.Count)
  $diff = 0.0; for ($i = 1; $i -lt $arr.Count; $i++) { $diff += [math]::Abs($arr[$i] - $arr[$i - 1]) }
  # 1 % et 0,1 % les plus lents : moyenne des temps de trame les plus longs, convertie en images/s
  $worst = { param($pct) $n = [math]::Max(1, [math]::Floor($sorted.Count * $pct / 100)); $s = 0.0; for ($i = $sorted.Count - $n; $i -lt $sorted.Count; $i++) { $s += $sorted[$i] }; 1000 / ($s / $n) }
  # saccade : image au moins 2 fois plus longue que la mediane des 30 precedentes et 4 ms de plus
  $stutters = 0; $win = New-Object System.Collections.Generic.Queue[double]
  foreach ($x in $arr) {
    if ($win.Count -ge 10) {
      $m = Get-PLPercentile -Sorted ([double[]]($win.ToArray() | Sort-Object)) -P 50
      if ($x -ge 2 * $m -and $x -ge $m + 4) { $stutters++ }
    }
    $win.Enqueue($x); if ($win.Count -gt 30) { [void]$win.Dequeue() }
  }
  $dur = $sum / 1000
  $med = { param($list) if ($list.Count) { Get-PLPercentile -Sorted ([double[]]($list.ToArray() | Sort-Object)) -P 50 } else { $null } }
  $cpuMed = & $med $cpu; $gpuMed = & $med $gpu; $ftMed = Get-PLPercentile -Sorted $sorted -P 50
  $limit = 'Indetermine'
  if ($null -ne $gpuMed -and $null -ne $cpuMed) {
    if ($gpuMed -ge 0.9 * $ftMed) { $limit = 'Carte graphique' }
    elseif ($cpuMed -ge 0.9 * $ftMed) { $limit = 'Processeur' }
    else { $limit = 'Ni l''un ni l''autre (attente : synchro, limite ou affichage)' }
  }
  [pscustomobject]@{
    Images         = $arr.Count
    DureeS         = [math]::Round($dur, 1)
    FpsMoyen       = [math]::Round(1000 / $mean, 1)
    Fps1PctBas     = [math]::Round((& $worst 1), 1)
    Fps01PctBas    = [math]::Round((& $worst 0.1), 1)
    TrameMedianeMs = [math]::Round($ftMed, 2)
    TrameP95Ms     = [math]::Round((Get-PLPercentile -Sorted $sorted -P 95), 2)
    TrameP99Ms     = [math]::Round((Get-PLPercentile -Sorted $sorted -P 99), 2)
    TrameMaxMs     = [math]::Round($sorted[-1], 1)
    EcartTypeMs    = [math]::Round($sd, 2)
    VariationMoyMs = [math]::Round($diff / [math]::Max(1, $arr.Count - 1), 2)
    Saccades       = $stutters
    SaccadesParMin = [math]::Round($stutters / [math]::Max(0.1, $dur / 60), 1)
    CpuOccupeMs    = $(if ($null -ne $cpuMed) { [math]::Round($cpuMed, 2) } else { $null })
    GpuOccupeMs    = $(if ($null -ne $gpuMed) { [math]::Round($gpuMed, 2) } else { $null })
    Limite         = $limit
    AffichageMedianMs = $(if ($disp.Count) { [math]::Round((& $med $disp), 2) } else { $null })
    ColonneTrame   = $ftCol
  }
}

function Start-PLCapture {
  # Lance PresentMon (ETW, sans injection) sur eurotrucks2.exe et echantillonne CPU/GPU/RAM en parallele.
  # PresentMon demande les droits administrateur : Windows affiche une confirmation.
  param([int]$Seconds = 180, [Parameter(Mandatory)][string]$Label, [string]$Zone = '', [string]$Profil = '')
  if (-not (Get-Process -Name eurotrucks2 -ErrorAction SilentlyContinue)) { throw 'ETS2 n''est pas lance.' }
  $pm = Get-PLPresentMon
  $id = Get-Date -Format 'yyyyMMdd_HHmmss'
  $dir = Join-Path (Join-Path (Get-PLDataRoot) 'mesures') $id
  New-Item -ItemType Directory -Path $dir -Force | Out-Null
  $csv = Join-Path $dir 'presentmon.csv'
  $args = @('--process_name', 'eurotrucks2.exe', '--output_file', "`"$csv`"", '--timed', $Seconds, '--terminate_after_timed', '--no_console_stats', '--stop_existing_session', '--session_name', 'TSCPerfLab')
  $p = Start-Process -FilePath $pm -ArgumentList $args -Verb RunAs -WindowStyle Hidden -PassThru
  $samples = Measure-PLLoad -Seconds $Seconds
  $p.WaitForExit(($Seconds + 30) * 1000) | Out-Null
  $samples | Export-Csv -LiteralPath (Join-Path $dir 'charge.csv') -NoTypeInformation -Encoding UTF8
  if (-not (Test-Path -LiteralPath $csv)) { throw 'PresentMon n''a rien enregistre (droits administrateur refuses ?).' }
  $stats = Get-PLFrameStats -CsvPath $csv
  $run = [pscustomobject]@{
    Id = $id; Date = (Get-Date).ToString('dd/MM/yyyy HH:mm'); Libelle = $Label; Zone = $Zone; Profil = $Profil
    Machine = $env:COMPUTERNAME; Stats = $stats
    Charge = [pscustomobject]@{
      CpuMoy = [math]::Round(($samples | Measure-Object Cpu -Average).Average, 1)
      CpuMax = ($samples | Measure-Object Cpu -Maximum).Maximum
      GpuMoy = [math]::Round(($samples | Measure-Object Gpu3D -Average).Average, 1)
      GpuMax = ($samples | Measure-Object Gpu3D -Maximum).Maximum
      RamLibreMinMo = ($samples | Measure-Object RamLibreMo -Minimum).Minimum
    }
  }
  $run | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $dir 'mesure.json') -Encoding UTF8
  $run
}

function Measure-PLLoad {
  # Charge processeur (compteurs bruts : independant de la langue), carte graphique et memoire, une fois par seconde
  param([int]$Seconds = 30)
  $out = New-Object System.Collections.Generic.List[object]
  $prev = Get-CimInstance Win32_PerfRawData_PerfOS_Processor -Filter "Name='_Total'" -ErrorAction SilentlyContinue
  for ($i = 0; $i -lt $Seconds; $i++) {
    $g = Get-Counter -Counter '\GPU Engine(*)\Utilization Percentage' -SampleInterval 1 -MaxSamples 1 -ErrorAction SilentlyContinue
    if (-not $g) { Start-Sleep -Seconds 1 }
    $cur = Get-CimInstance Win32_PerfRawData_PerfOS_Processor -Filter "Name='_Total'" -ErrorAction SilentlyContinue
    $cpu = $null
    if ($prev -and $cur) {
      $dt = [double]($cur.Timestamp_Sys100NS - $prev.Timestamp_Sys100NS)
      if ($dt -gt 0) { $cpu = [math]::Round(100 * (1 - ([double]($cur.PercentProcessorTime - $prev.PercentProcessorTime) / $dt)), 1) }
    }
    $prev = $cur
    $g3d = 0.0; $dec = 0.0; $enc = 0.0
    if ($g) {
      foreach ($c in $g.CounterSamples) {
        if ($c.InstanceName -match 'engtype_3d') { $g3d += $c.CookedValue }
        elseif ($c.InstanceName -match 'engtype_videodecode') { $dec += $c.CookedValue }
        elseif ($c.InstanceName -match 'engtype_videoencode') { $enc += $c.CookedValue }
      }
    }
    $os = Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue
    $out.Add([pscustomobject]@{ T = $i; Cpu = $cpu; Gpu3D = [math]::Round([math]::Min(100, $g3d), 1); Decodage = [math]::Round($dec, 1); Encodage = [math]::Round($enc, 1); RamLibreMo = $(if ($os) { [math]::Round($os.FreePhysicalMemory / 1KB) } else { $null }) })
  }
  $out.ToArray()
}

function Get-PLRuns {
  $root = Join-Path (Get-PLDataRoot) 'mesures'
  @(Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue | Sort-Object Name -Descending | ForEach-Object {
    $j = Join-Path $_.FullName 'mesure.json'
    if (Test-Path -LiteralPath $j) { Get-Content -LiteralPath $j -Raw | ConvertFrom-Json }
  })
}

function Compare-PLRuns {
  # Compare deux mesures. Un ecart de moins de 3 % est considere comme du bruit de mesure.
  param([Parameter(Mandatory)]$Avant, [Parameter(Mandatory)]$Apres)
  $defs = @(
    @('FpsMoyen', 'Images/s moyennes', 1),
    @('Fps1PctBas', 'Images/s des 1 % les plus lents', 1),
    @('Fps01PctBas', 'Images/s des 0,1 % les plus lents', 1),
    @('TrameP99Ms', 'Temps de trame 99e centile (ms)', -1),
    @('EcartTypeMs', 'Ecart-type des temps de trame (ms)', -1),
    @('VariationMoyMs', 'Variation d''une image a l''autre (ms)', -1),
    @('SaccadesParMin', 'Saccades par minute', -1)
  )
  foreach ($d in $defs) {
    $a = $Avant.Stats.($d[0]); $b = $Apres.Stats.($d[0])
    $pct = $null; $verdict = 'n/d'
    if ($null -ne $a -and $null -ne $b -and [double]$a -ne 0) {
      $pct = [math]::Round(100 * ([double]$b - [double]$a) / [double]$a, 1)
      $better = $pct * $d[2]
      $verdict = if ([math]::Abs($pct) -lt 3) { 'Pareil (bruit)' } elseif ($better -gt 0) { 'Mieux' } else { 'Moins bien' }
    }
    [pscustomobject]@{ Mesure = $d[1]; Avant = $a; Apres = $b; EcartPct = $pct; Verdict = $verdict }
  }
}

# ---------------------------------------------------------------- profils, historique, restauration

function Get-PLHistoryPath { Join-Path (Get-PLDataRoot) 'historique.json' }

function Get-PLHistory {
  $p = Get-PLHistoryPath
  if (Test-Path -LiteralPath $p) { @(Get-Content -LiteralPath $p -Raw | ConvertFrom-Json) } else { @() }
}

function Add-PLHistory {
  param([Parameter(Mandatory)]$Entry)
  $h = @(Get-PLHistory) + @($Entry)
  ConvertTo-Json -InputObject @($h) -Depth 6 | Set-Content -LiteralPath (Get-PLHistoryPath) -Encoding UTF8
}

function Backup-PLConfigs {
  # Copie config.cfg global et celui du profil actif dans sauvegardes\<horodatage>
  param([Parameter(Mandatory)]$Game, [string]$Reason = '')
  $graph = Get-PLGraphics $Game.DocsDir
  $id = Get-Date -Format 'yyyyMMdd_HHmmss_fff'
  $dir = Join-Path (Join-Path (Get-PLDataRoot) 'sauvegardes') $id
  New-Item -ItemType Directory -Path $dir -Force | Out-Null
  $files = @()
  $g = Join-Path $Game.DocsDir 'config.cfg'
  if (Test-Path -LiteralPath $g) { Copy-Item -LiteralPath $g -Destination (Join-Path $dir 'global_config.cfg'); $files += [pscustomobject]@{ Copie = 'global_config.cfg'; Original = $g } }
  if ($graph.ProfileDir) {
    $p = Join-Path $graph.ProfileDir 'config.cfg'
    if (Test-Path -LiteralPath $p) { Copy-Item -LiteralPath $p -Destination (Join-Path $dir 'profil_config.cfg'); $files += [pscustomobject]@{ Copie = 'profil_config.cfg'; Original = $p } }
  }
  [pscustomobject]@{ Id = $id; Dossier = $dir; Fichiers = $files; Raison = $Reason } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $dir 'sauvegarde.json') -Encoding UTF8
  [pscustomobject]@{ Id = $id; Dossier = $dir; Fichiers = $files }
}

function Save-PLProfile {
  # Enregistre les reglages graphiques actuels (variables suivies) comme profil nomme
  param([Parameter(Mandatory)][string]$Name, [Parameter(Mandatory)]$Game, [string]$Description = '')
  $graph = Get-PLGraphics $Game.DocsDir
  $vals = [ordered]@{}
  foreach ($k in $script:GfxVars.Keys) { if ($graph.Global.Contains($k)) { $vals[$k] = $graph.Global[$k] } }
  $prof = [ordered]@{}
  foreach ($k in $script:GfxVars.Keys) { if ($graph.Profile.Contains($k)) { $prof[$k] = $graph.Profile[$k] } }
  $obj = [pscustomobject]@{ Nom = $Name; Description = $Description; Cree = (Get-Date).ToString('dd/MM/yyyy HH:mm'); Global = $vals; Profil = $prof; Integre = $false }
  $file = Join-Path (Join-Path (Get-PLDataRoot) 'profils') (($Name -replace '[^\w\- ]', '_') + '.json')
  $obj | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $file -Encoding UTF8
  Add-PLHistory ([pscustomobject]@{ Date = (Get-Date).ToString('dd/MM/yyyy HH:mm:ss'); Action = 'Profil enregistre'; Detail = $Name; Sauvegarde = $null; Restaurable = $false })
  $obj
}

function Get-PLProfiles {
  $list = @()
  # Profils integres : ils ne changent que le rythme des images, jamais un reglage de qualite
  $list += [pscustomobject]@{ Nom = 'Limite 60 images/s'; Description = 'Limite du jeu a 60 images/s (t_limit_fps 60), au rythme des ecrans 60 Hz et d''un flux Shadow a 60. Aucun reglage de qualite modifie.'; Cree = ''; Global = [pscustomobject]@{ t_limit_fps = '60' }; Profil = [pscustomobject]@{}; Integre = $true }
  $list += [pscustomobject]@{ Nom = 'Synchro verticale'; Description = 'Synchro verticale activee (r_vsync 1) : images calees sur la frequence de l''ecran du Shadow. Aucun reglage de qualite modifie.'; Cree = ''; Global = [pscustomobject]@{ r_vsync = '1' }; Profil = [pscustomobject]@{}; Integre = $true }
  foreach ($f in @(Get-ChildItem -LiteralPath (Join-Path (Get-PLDataRoot) 'profils') -Filter *.json -ErrorAction SilentlyContinue)) {
    $list += Get-Content -LiteralPath $f.FullName -Raw | ConvertFrom-Json
  }
  $list
}

function ConvertTo-PLHashtable {
  param($Obj)
  $h = @{}
  if ($Obj -is [System.Collections.IDictionary]) { foreach ($k in $Obj.Keys) { $h[$k] = [string]$Obj[$k] } }
  elseif ($Obj) { foreach ($p in $Obj.PSObject.Properties) { $h[$p.Name] = [string]$p.Value } }
  $h
}

function Get-PLProfileDiff {
  # Ce que l'application d'un profil changerait, variable par variable
  param([Parameter(Mandatory)]$Profile, [Parameter(Mandatory)]$Game)
  $graph = Get-PLGraphics $Game.DocsDir
  $rows = @()
  foreach ($scope in 'Global', 'Profil') {
    $want = ConvertTo-PLHashtable $Profile.$scope
    $cur = if ($scope -eq 'Global') { $graph.Global } else { $graph.Profile }
    foreach ($k in $want.Keys) {
      $now = if ($cur.Contains($k)) { $cur[$k] } else { '(absent)' }
      if ($now -ne $want[$k]) { $rows += [pscustomobject]@{ Fichier = $scope; Variable = $k; Reglage = $script:GfxVars[$k]; Actuel = $now; Nouveau = $want[$k] } }
    }
  }
  $rows
}

function Set-PLProfile {
  # Applique un profil : jeu ferme obligatoire, sauvegarde complete avant toute ecriture
  param([Parameter(Mandatory)]$Profile, [Parameter(Mandatory)]$Game)
  if (Get-Process -Name eurotrucks2 -ErrorAction SilentlyContinue) { throw 'Ferme ETS2 avant d''appliquer un profil : le jeu reecrit config.cfg en quittant.' }
  $diff = @(Get-PLProfileDiff -Profile $Profile -Game $Game)
  if (-not $diff.Count) { return [pscustomobject]@{ Change = 0; Sauvegarde = $null } }
  $bk = Backup-PLConfigs -Game $Game -Reason "Avant profil $($Profile.Nom)"
  $graph = Get-PLGraphics $Game.DocsDir
  $g = ConvertTo-PLHashtable $Profile.Global
  if ($g.Count) { $f = Join-Path $Game.DocsDir 'config.cfg'; Write-PLConfigOverrides -Source $f -Destination $f -Overrides $g }
  $p = ConvertTo-PLHashtable $Profile.Profil
  if ($p.Count -and $graph.ProfileDir) { $f = Join-Path $graph.ProfileDir 'config.cfg'; Write-PLConfigOverrides -Source $f -Destination $f -Overrides $p }
  Add-PLHistory ([pscustomobject]@{ Date = (Get-Date).ToString('dd/MM/yyyy HH:mm:ss'); Action = 'Profil applique'; Detail = "$($Profile.Nom) : " + (($diff | ForEach-Object { "$($_.Variable) $($_.Actuel) -> $($_.Nouveau)" }) -join ', '); Sauvegarde = $bk.Id; Restaurable = $true; Type = 'config' })
  [pscustomobject]@{ Change = $diff.Count; Sauvegarde = $bk.Id }
}

function Restore-PLBackup {
  # Remet les fichiers de configuration d'une sauvegarde (en sauvegardant d'abord l'etat actuel)
  param([Parameter(Mandatory)][string]$BackupId, [Parameter(Mandatory)]$Game)
  if (Get-Process -Name eurotrucks2 -ErrorAction SilentlyContinue) { throw 'Ferme ETS2 avant de restaurer.' }
  $dir = Join-Path (Join-Path (Get-PLDataRoot) 'sauvegardes') $BackupId
  $meta = Get-Content -LiteralPath (Join-Path $dir 'sauvegarde.json') -Raw | ConvertFrom-Json
  $now = Backup-PLConfigs -Game $Game -Reason "Avant restauration de $BackupId"
  foreach ($f in @($meta.Fichiers)) { Copy-Item -LiteralPath (Join-Path $dir $f.Copie) -Destination $f.Original -Force }
  Add-PLHistory ([pscustomobject]@{ Date = (Get-Date).ToString('dd/MM/yyyy HH:mm:ss'); Action = 'Restauration'; Detail = "Configuration du $BackupId remise"; Sauvegarde = $now.Id; Restaurable = $true; Type = 'config' })
}

# Reglages Windows reversibles : on note l'ancienne valeur dans l'historique
function Set-PLRegistryValue {
  param([string]$Path, [string]$Name, $Value, [string]$Kind = 'DWord', [string]$Label)
  $old = Get-ItemProperty -Path $Path -Name $Name -ErrorAction SilentlyContinue
  $oldVal = if ($old) { $old.$Name } else { $null }
  if (-not (Test-Path -Path $Path)) { New-Item -Path $Path -Force | Out-Null }
  Set-ItemProperty -Path $Path -Name $Name -Value $Value -Type $Kind
  Add-PLHistory ([pscustomobject]@{ Date = (Get-Date).ToString('dd/MM/yyyy HH:mm:ss'); Action = $Label; Detail = "$Path\$Name : $oldVal -> $Value"; Sauvegarde = $null; Restaurable = $true; Type = 'registre'; Chemin = $Path; Nom = $Name; Ancien = $oldVal; Genre = $Kind })
}

function Invoke-PLReco {
  # Applique une recommandation marquee "Applicable"
  param([Parameter(Mandatory)][string]$Id, [Parameter(Mandatory)]$Game)
  switch ($Id) {
    'gpu-pref'   { Set-PLRegistryValue 'HKCU:\Software\Microsoft\DirectX\UserGpuPreferences' $Game.Exe 'GpuPreference=2;' 'String' 'Preference graphique hautes performances' }
    'game-dvr'   { Set-PLRegistryValue 'HKCU:\System\GameConfigStore' 'GameDVR_Enabled' 0 'DWord' 'Game DVR coupe'
                   Set-PLRegistryValue 'HKCU:\Software\Microsoft\Windows\CurrentVersion\GameDVR' 'AppCaptureEnabled' 0 'DWord' 'Capture d''applications coupee' }
    'power-plan' {
      $old = (powercfg /getactivescheme) | Out-String
      $oldGuid = if ($old -match '([0-9a-f]{8}-[0-9a-f-]{27})') { $Matches[1] } else { $null }
      powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c | Out-Null
      Add-PLHistory ([pscustomobject]@{ Date = (Get-Date).ToString('dd/MM/yyyy HH:mm:ss'); Action = 'Plan Performances elevees'; Detail = "ancien plan $oldGuid"; Sauvegarde = $null; Restaurable = $true; Type = 'alimentation'; Ancien = $oldGuid })
    }
    'frame-cadence' { Set-PLProfile -Profile ((Get-PLProfiles) | Where-Object Nom -eq 'Limite 60 images/s' | Select-Object -First 1) -Game $Game | Out-Null }
    default { throw "Recommandation $Id non applicable automatiquement." }
  }
}

function Undo-PLHistoryEntry {
  # Annule une entree de l'historique (configuration, registre ou plan d'alimentation)
  param([Parameter(Mandatory)]$Entry, [Parameter(Mandatory)]$Game)
  if (-not $Entry.Restaurable) { throw 'Cette operation n''a rien a restaurer.' }
  $type = if ($Entry.PSObject.Properties['Type']) { $Entry.Type } else { 'config' }
  switch ($type) {
    'config' { Restore-PLBackup -BackupId $Entry.Sauvegarde -Game $Game }
    'registre' {
      if ($null -eq $Entry.Ancien) { Remove-ItemProperty -Path $Entry.Chemin -Name $Entry.Nom -ErrorAction SilentlyContinue }
      else { Set-ItemProperty -Path $Entry.Chemin -Name $Entry.Nom -Value $Entry.Ancien -Type $Entry.Genre }
      Add-PLHistory ([pscustomobject]@{ Date = (Get-Date).ToString('dd/MM/yyyy HH:mm:ss'); Action = 'Annulation'; Detail = "$($Entry.Action) annule ($($Entry.Nom) = $($Entry.Ancien))"; Sauvegarde = $null; Restaurable = $false })
    }
    'alimentation' {
      if ($Entry.Ancien) { powercfg /setactive $Entry.Ancien | Out-Null }
      Add-PLHistory ([pscustomobject]@{ Date = (Get-Date).ToString('dd/MM/yyyy HH:mm:ss'); Action = 'Annulation'; Detail = "Plan d'alimentation $($Entry.Ancien) remis"; Sauvegarde = $null; Restaurable = $false })
    }
  }
}

# ---------------------------------------------------------------- rapport

function ConvertTo-PLHtmlTable {
  param($Rows, [string[]]$Props)
  $rows = @($Rows)
  if (-not $rows.Count) { return '<p class="vide">Aucune donnee.</p>' }
  if (-not $Props) { $Props = $rows[0].PSObject.Properties.Name }
  $enc = { param($s) [System.Net.WebUtility]::HtmlEncode([string]$s) }
  $h = '<table><tr>' + (($Props | ForEach-Object { '<th>' + (& $enc $_) + '</th>' }) -join '') + '</tr>'
  foreach ($r in $rows) { $h += '<tr>' + (($Props | ForEach-Object { '<td>' + (& $enc $r.$_) + '</td>' }) -join '') + '</tr>' }
  $h + '</table>'
}

function Export-PLReport {
  param([Parameter(Mandatory)]$Diag, $Runs, $History, [string]$Path)
  if (-not $Path) { $Path = Join-Path (Join-Path (Get-PLDataRoot) 'rapports') ("Rapport_TSC_Performance_Lab_" + (Get-Date -Format 'yyyy-MM-dd_HHmm') + '.html') }
  $m = $Diag.Machine
  $sec = @()
  $sec += '<h2>Machine</h2>' + (ConvertTo-PLHtmlTable @([pscustomobject]@{ Nom = $m.Nom; Modele = $m.Modele; Windows = $m.Windows; Processeur = "$($m.Processeur) ($($m.Coeurs) coeurs / $($m.Threads) threads)"; Memoire = "$($m.RamGo) Go"; Alimentation = $m.PlanAlimentation }))
  $sec += ConvertTo-PLHtmlTable $m.CartesGraphiques
  $sec += ConvertTo-PLHtmlTable $m.Disques
  $sec += '<h2>Recommandations (classees par impact)</h2>' + (ConvertTo-PLHtmlTable $Diag.Recommandations @('Impact', 'Risque', 'Titre', 'Constat', 'Action', 'QualiteTouchee'))
  $sec += '<h2>Reglages graphiques</h2>' + (ConvertTo-PLHtmlTable $Diag.Graphismes.Rows)
  if ($Diag.Plantages) { $sec += "<h2>Plantages ($($Diag.Plantages.Total) sur $($Diag.Plantages.Jours) jours)</h2>" + (ConvertTo-PLHtmlTable $Diag.Plantages.ParModule) }
  $sec += '<h2>Injections et plugins</h2>' + (ConvertTo-PLHtmlTable $Diag.Injections) + (ConvertTo-PLHtmlTable $Diag.Plugins)
  if ($Diag.Journal) { $sec += '<h2>Erreurs du journal (top 30)</h2>' + (ConvertTo-PLHtmlTable @($Diag.Journal.Erreurs | Select-Object -First 30)) }
  $sec += "<h2>Mods ($($Diag.Mods.Total), $($Diag.Mods.TailleGo) Go, $($Diag.Mods.Montes) montes)</h2>" + (ConvertTo-PLHtmlTable $Diag.Mods.Liste)
  $sec += '<h2>Arriere-plan</h2>' + (ConvertTo-PLHtmlTable $Diag.ArrierePlan)
  if ($Runs) {
    $flat = @($Runs | ForEach-Object { [pscustomobject]@{ Date = $_.Date; Libelle = $_.Libelle; Zone = $_.Zone; Profil = $_.Profil; FpsMoy = $_.Stats.FpsMoyen; Fps1Pct = $_.Stats.Fps1PctBas; Fps01Pct = $_.Stats.Fps01PctBas; P99Ms = $_.Stats.TrameP99Ms; SaccadesMin = $_.Stats.SaccadesParMin; Limite = $_.Stats.Limite; CpuPct = $_.Charge.CpuMoy; GpuPct = $_.Charge.GpuMoy } })
    $sec += '<h2>Mesures</h2>' + (ConvertTo-PLHtmlTable $flat)
  }
  if ($History) { $sec += '<h2>Historique des modifications</h2>' + (ConvertTo-PLHtmlTable @($History) @('Date', 'Action', 'Detail')) }
  $css = 'body{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#1b1f24;background:#fff}h1{color:#b00020}h2{margin-top:28px;border-bottom:2px solid #b00020;padding-bottom:4px}table{border-collapse:collapse;margin:8px 0;font-size:13px;width:100%}th,td{border:1px solid #d0d4d9;padding:4px 6px;text-align:left;vertical-align:top}th{background:#f2f3f5}.vide{color:#777}.limites{font-size:12px;color:#555}'
  $limits = '<p class="limites">Limites des mesures : PresentMon mesure les images produites par le jeu sur la machine qui le fait tourner. Avec Shadow, ce que tu vois depend aussi de l''encodage, du reseau et du decodage sur ton PC, non compris dans ces chiffres. Deux mesures ne se comparent que sur le meme parcours, a la meme heure du jeu et avec la meme meteo.</p>'
  $html = "<!doctype html><html lang=`"fr`"><head><meta charset=`"utf-8`"><title>TSC Performance Lab</title><style>$css</style></head><body><h1>TSC Performance Lab</h1><p>Rapport du $((Get-Date).ToString('dd/MM/yyyy HH:mm')) - machine $($m.Nom) - ETS2 $($Diag.Journal.Version)</p>$limits$($sec -join "`n")</body></html>"
  [IO.File]::WriteAllText($Path, $html, (New-Object Text.UTF8Encoding($true)))
  $Path
}

Export-ModuleMember -Function *-PL*, ConvertFrom-PLHexName, ConvertTo-PLHashtable, ConvertTo-PLHtmlTable
