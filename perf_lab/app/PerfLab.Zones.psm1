# TSC Performance Lab - zones chargees
# Carte des zones ou le jeu rame, construite a partir des trajets, et "mode zone chargee" :
# dans une zone lourde, le Shadow est libere cote Windows (priorite au jeu, taches de fond ralenties,
# plan d'alimentation performant), puis tout revient a l'etat d'origine a la sortie de la zone.
# Rien dans le jeu, ses fichiers, ses mods ou ses profils n'est modifie. Aucune injection, aucune console.
# La position du camion est fournie par l'appelant (la tablette TSC lit deja la telemetrie scs-telemetry).
Set-StrictMode -Version 2
Import-Module (Join-Path $PSScriptRoot 'PerfLab.Core.psm1')

# Reglages par defaut (modifiables par la tablette via Set-PLZoneSettings)
$script:ZoneDefaults = [ordered]@{
  TailleCaseM        = 500    # cote d'une case de la carte, en metres du monde du jeu
  EchantillonsMin    = 10     # echantillons necessaires avant de juger une case
  PartLourdeMin      = 0.3    # part d'echantillons lourds pour qu'une case soit lourde
  GpuLourd           = 95     # % carte graphique au-dela duquel l'instant est lourd
  CpuLourd           = 90     # % processeur au-dela duquel l'instant est lourd
  ImagesCible        = 60     # images/s visees (si la mesure d'images est disponible)
  EntreeSecondes     = 3      # instants lourds consecutifs avant d'entrer en mode zone chargee
  SortieSecondes     = 30     # instants normaux consecutifs avant d'en sortir
  AnticipationS      = 15     # regarde la case ou sera le camion dans N secondes
  PrioriteJeu        = 'AboveNormal'
  ProcessusDeFond    = @('steamwebhelper', 'RazerCortex', 'Razer Synapse', 'OneDrive', 'msedge', 'chrome', 'firefox', 'Discord', 'NVIDIA Share', 'EpicGamesLauncher', 'Spotify')
  PrioriteFond       = 'BelowNormal'
  PlanPerformant     = $true
}
$script:Watch = $null

function Get-PLZoneRoot {
  $d = Join-Path (Get-PLDataRoot) 'zones'
  if (-not (Test-Path -LiteralPath $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
  $d
}

function Get-PLZoneSettings {
  $s = [ordered]@{}; foreach ($k in $script:ZoneDefaults.Keys) { $s[$k] = $script:ZoneDefaults[$k] }
  $f = Join-Path (Get-PLZoneRoot) 'reglages.json'
  if (Test-Path -LiteralPath $f) {
    $saved = Get-Content -LiteralPath $f -Raw | ConvertFrom-Json
    foreach ($p in $saved.PSObject.Properties) { if ($s.Contains($p.Name)) { $s[$p.Name] = $p.Value } }
  }
  [pscustomobject]$s
}

function Set-PLZoneSettings {
  param([Parameter(Mandatory)][hashtable]$Values)
  $cur = Get-PLZoneSettings
  foreach ($k in $Values.Keys) { if ($cur.PSObject.Properties.Name -contains $k) { $cur.$k = $Values[$k] } }
  $cur | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path (Get-PLZoneRoot) 'reglages.json') -Encoding UTF8
  $cur
}

function Get-PLZoneKey {
  # Case de la carte contenant la position (X, Z) du monde du jeu
  param([Parameter(Mandatory)][double]$X, [Parameter(Mandatory)][double]$Z, [double]$Size = 500)
  '{0}_{1}' -f [math]::Floor($X / $Size), [math]::Floor($Z / $Size)
}

function Get-PLZoneMap {
  $f = Join-Path (Get-PLZoneRoot) 'carte.json'
  $map = @{}
  if (Test-Path -LiteralPath $f) {
    $raw = Get-Content -LiteralPath $f -Raw | ConvertFrom-Json
    foreach ($p in $raw.PSObject.Properties) { $map[$p.Name] = $p.Value }
  }
  $map
}

function Save-PLZoneMap {
  param([Parameter(Mandatory)][hashtable]$Map)
  $f = Join-Path (Get-PLZoneRoot) 'carte.json'
  [pscustomobject]$Map | ConvertTo-Json -Depth 4 -Compress | Set-Content -LiteralPath "$f.tmp" -Encoding UTF8
  Move-Item -LiteralPath "$f.tmp" -Destination $f -Force
}

function Test-PLHeavySample {
  # Un instant est lourd si les images/s tombent sous la cible, ou a defaut si la carte graphique ou le processeur saturent
  param($Load, $Settings)
  if ($null -ne $Load.Fps -and $Load.Fps -gt 0) { return ($Load.Fps -lt 0.85 * $Settings.ImagesCible) }
  (($null -ne $Load.Gpu -and $Load.Gpu -ge $Settings.GpuLourd) -or ($null -ne $Load.Cpu -and $Load.Cpu -ge $Settings.CpuLourd))
}

function Add-PLZoneSample {
  # Ajoute un echantillon a la case ; renvoie la case mise a jour
  param([Parameter(Mandatory)][hashtable]$Map, [Parameter(Mandatory)][string]$Key, [Parameter(Mandatory)][bool]$Heavy, $Load, [double]$X, [double]$Z)
  $c = $Map[$Key]
  if (-not $c) { $c = [pscustomobject]@{ N = 0; Lourds = 0; GpuMoy = 0.0; FpsMoy = $null; X = $X; Z = $Z; Vu = '' } }
  $n = $c.N + 1
  if ($null -ne $Load.Gpu) { $c.GpuMoy = [math]::Round(($c.GpuMoy * $c.N + $Load.Gpu) / $n, 1) }
  if ($null -ne $Load.Fps) { $c.FpsMoy = $(if ($null -eq $c.FpsMoy) { [math]::Round($Load.Fps, 1) } else { [math]::Round(($c.FpsMoy * $c.N + $Load.Fps) / $n, 1) }) }
  $c.N = $n
  if ($Heavy) { $c.Lourds++ }
  $c.Vu = (Get-Date).ToString('yyyy-MM-dd')
  $Map[$Key] = $c
  $c
}

function Test-PLZoneHeavy {
  param($Cell, $Settings)
  [bool]($Cell -and $Cell.N -ge $Settings.EchantillonsMin -and ($Cell.Lourds / $Cell.N) -ge $Settings.PartLourdeMin)
}

function Get-PLHeavyZones {
  # Zones lourdes connues, les plus lourdes d'abord
  param([int]$Top = 20)
  $s = Get-PLZoneSettings; $map = Get-PLZoneMap
  @($map.Keys | Where-Object { Test-PLZoneHeavy $map[$_] $s } | ForEach-Object {
    $c = $map[$_]
    [pscustomobject]@{ Case = $_; X = $c.X; Z = $c.Z; Echantillons = $c.N; PartLourde = [math]::Round($c.Lourds / $c.N, 2); GpuMoy = $c.GpuMoy; FpsMoy = $c.FpsMoy; Vu = $c.Vu }
  } | Sort-Object PartLourde, Echantillons -Descending | Select-Object -First $Top)
}

function Get-PLQuickLoad {
  # Charge instantanee du Shadow, sans droits administrateur (carte graphique 3D, processeur)
  $gpu = $null; $cpu = $null
  $g = Get-Counter -Counter '\GPU Engine(*engtype_3D)\Utilization Percentage' -MaxSamples 1 -ErrorAction SilentlyContinue
  if ($g) { $sum = 0.0; foreach ($c in $g.CounterSamples) { $sum += $c.CookedValue }; $gpu = [math]::Round([math]::Min(100, $sum), 1) }
  if (-not $script:CpuPath) { $script:CpuPath = Get-PLCpuCounterPath }
  $p = Get-Counter -Counter $script:CpuPath -MaxSamples 1 -ErrorAction SilentlyContinue
  if ($p) { $cpu = [math]::Round($p.CounterSamples[0].CookedValue, 1) }
  [pscustomobject]@{ Gpu = $gpu; Cpu = $cpu; Fps = $null }
}

# --- mode zone chargee : actions cote Windows, toutes reversibles

function Get-PLBoostPlan {
  # Liste des changements a faire, a partir des processus en cours (fonction pure, testable)
  param([Parameter(Mandatory)]$Processes, [Parameter(Mandatory)]$Settings)
  $plan = New-Object System.Collections.Generic.List[object]
  foreach ($p in $Processes) {
    if ($p.Name -eq 'eurotrucks2') {
      if ([string]$p.Priority -ne $Settings.PrioriteJeu) { $plan.Add([pscustomobject]@{ Type = 'priorite'; Id = $p.Id; Nom = $p.Name; Ancien = [string]$p.Priority; Nouveau = $Settings.PrioriteJeu }) }
    }
    elseif (@($Settings.ProcessusDeFond) -contains $p.Name -and @('Normal', 'AboveNormal', 'High') -contains [string]$p.Priority) {
      $plan.Add([pscustomobject]@{ Type = 'priorite'; Id = $p.Id; Nom = $p.Name; Ancien = [string]$p.Priority; Nouveau = $Settings.PrioriteFond })
    }
  }
  $plan.ToArray()
}

function Get-PLBoostStatePath { Join-Path (Get-PLZoneRoot) 'boost_en_cours.json' }

function Enable-PLZoneBoost {
  # Applique le mode zone chargee et note l'etat d'origine (restaure meme apres un plantage, voir Restore-PLZoneBoost)
  param($Settings = (Get-PLZoneSettings))
  if (Test-Path -LiteralPath (Get-PLBoostStatePath)) { return }
  $procs = @(Get-Process -ErrorAction SilentlyContinue | ForEach-Object { $pr = $null; try { $pr = $_.PriorityClass } catch { }; if ($pr) { [pscustomobject]@{ Name = $_.ProcessName; Id = $_.Id; Priority = $pr } } })
  $plan = @(Get-PLBoostPlan -Processes $procs -Settings $Settings)
  $done = New-Object System.Collections.Generic.List[object]
  foreach ($c in $plan) {
    try { (Get-Process -Id $c.Id -ErrorAction Stop).PriorityClass = $c.Nouveau; $done.Add($c) } catch { }
  }
  if ($Settings.PlanPerformant) {
    $cur = (powercfg /getactivescheme) -replace '.*:\s*([0-9a-fA-F-]{36}).*', '$1'
    $high = '8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c'
    if ($cur -and $cur -ne $high -and (powercfg /list | Select-String $high)) {
      powercfg /setactive $high | Out-Null
      $done.Add([pscustomobject]@{ Type = 'alimentation'; Id = $null; Nom = 'plan'; Ancien = $cur.Trim(); Nouveau = $high })
    }
  }
  [pscustomobject]@{ Debut = (Get-Date).ToString('s'); Changements = $done.ToArray() } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Get-PLBoostStatePath) -Encoding UTF8
  $done.ToArray()
}

function Restore-PLZoneBoost {
  # Remet chaque processus et le plan d'alimentation a l'etat d'origine ; a appeler a la sortie de zone et au demarrage de la tablette
  $f = Get-PLBoostStatePath
  if (-not (Test-Path -LiteralPath $f)) { return @() }
  $st = Get-Content -LiteralPath $f -Raw | ConvertFrom-Json
  foreach ($c in @($st.Changements)) {
    try {
      if ($c.Type -eq 'priorite') { $p = Get-Process -Id $c.Id -ErrorAction Stop; if ($p.ProcessName -eq $c.Nom) { $p.PriorityClass = $c.Ancien } }
      elseif ($c.Type -eq 'alimentation') { powercfg /setactive $c.Ancien | Out-Null }
    } catch { }
  }
  Remove-Item -LiteralPath $f -Force
  @($st.Changements)
}

# --- surveillance en direct

function Start-PLZoneWatch {
  # A appeler quand la tablette active le mode zones ; restaure un eventuel mode reste actif
  param([switch]$Automatique)
  Restore-PLZoneBoost | Out-Null
  $s = Get-PLZoneSettings
  $script:Watch = [pscustomobject]@{
    Actif = $true; Automatique = [bool]$Automatique; Settings = $s; Map = (Get-PLZoneMap)
    Etat = 'Normal'; Lourds = 0; Normaux = 0; Case = ''; DernierEnregistrement = (Get-Date)
    Echantillons = 0; SecondesLourdes = 0; Changements = @()
  }
  Get-PLZoneStatus
}

function Update-PLZoneWatch {
  # Un echantillon (1 par seconde environ). Position et vitesse viennent de la telemetrie lue par la tablette.
  # Load peut etre fourni (tests, ou images/s d'une mesure en cours) ; sinon il est lu sur la machine.
  param([Parameter(Mandatory)][double]$X, [Parameter(Mandatory)][double]$Z, [double]$VitesseMs = 0, [double]$Cap = [double]::NaN,
        [bool]$Pause = $false, $Load = $null, [switch]$SansAction)
  $w = $script:Watch
  if (-not $w -or -not $w.Actif) { throw 'Surveillance des zones non demarree (Start-PLZoneWatch).' }
  if ($Pause) { return (Get-PLZoneStatus) }
  $s = $w.Settings
  if ($null -eq $Load) { $Load = Get-PLQuickLoad }
  $key = Get-PLZoneKey -X $X -Z $Z -Size $s.TailleCaseM
  $heavyNow = Test-PLHeavySample $Load $s
  [void](Add-PLZoneSample -Map $w.Map -Key $key -Heavy $heavyNow -Load $Load -X $X -Z $Z)
  $w.Case = $key; $w.Echantillons++
  # anticipation : case ou sera le camion dans quelques secondes. Cap = heading du SDK SCS (0 a 1 : 0 nord, 0,25 ouest,
  # 0,5 sud, 0,75 est) ; dans le monde du jeu le nord est vers -Z et l'est vers +X
  $ahead = $null
  if (-not [double]::IsNaN($Cap) -and $VitesseMs -gt 2) {
    $d = $VitesseMs * $s.AnticipationS
    $a = $Cap * 2 * [math]::PI
    $ahead = Get-PLZoneKey -X ($X - [math]::Sin($a) * $d) -Z ($Z - [math]::Cos($a) * $d) -Size $s.TailleCaseM
  }
  $known = (Test-PLZoneHeavy $w.Map[$key] $s) -or ($ahead -and (Test-PLZoneHeavy $w.Map[$ahead] $s))
  if ($heavyNow -or $known) { $w.Lourds++; $w.Normaux = 0 } else { $w.Normaux++; $w.Lourds = 0 }
  if ($w.Etat -eq 'Lourd') { $w.SecondesLourdes++ }
  if ($w.Etat -eq 'Normal' -and ($known -or $w.Lourds -ge $s.EntreeSecondes)) {
    $w.Etat = 'Lourd'
    if ($w.Automatique -and -not $SansAction) { $w.Changements = @(Enable-PLZoneBoost -Settings $s) }
  }
  elseif ($w.Etat -eq 'Lourd' -and $w.Normaux -ge $s.SortieSecondes) {
    $w.Etat = 'Normal'
    if ($w.Automatique -and -not $SansAction) { Restore-PLZoneBoost | Out-Null }
    $w.Changements = @()
  }
  if (((Get-Date) - $w.DernierEnregistrement).TotalSeconds -ge 30) { Save-PLZoneMap $w.Map; $w.DernierEnregistrement = Get-Date }
  Get-PLZoneStatus
}

function Stop-PLZoneWatch {
  if ($script:Watch) { Save-PLZoneMap $script:Watch.Map; $script:Watch.Actif = $false; $script:Watch.Etat = 'Normal'; $script:Watch.Changements = @() }
  Restore-PLZoneBoost | Out-Null
  Get-PLZoneStatus
}

function Get-PLZoneStatus {
  $w = $script:Watch
  if (-not $w) { return [pscustomobject]@{ Actif = $false; Etat = 'Arrete' } }
  $c = $w.Map[$w.Case]
  [pscustomobject]@{
    Actif = $w.Actif; Automatique = $w.Automatique; Etat = $w.Etat; Case = $w.Case
    CaseLourde = (Test-PLZoneHeavy $c $w.Settings); CaseEchantillons = $(if ($c) { $c.N } else { 0 })
    Echantillons = $w.Echantillons; SecondesLourdes = $w.SecondesLourdes
    ZonesLourdesConnues = @($w.Map.Keys | Where-Object { Test-PLZoneHeavy $w.Map[$_] $w.Settings }).Count
    Changements = @($w.Changements | ForEach-Object { "$($_.Nom) : $($_.Ancien) -> $($_.Nouveau)" })
  }
}

function Get-PLZoneAdvice {
  # Conseil a afficher sur la tablette : si les zones lourdes reviennent souvent, proposer le profil "Limite 60 images/s",
  # a appliquer jeu ferme (Set-PLProfile fait une sauvegarde avant). Jamais applique automatiquement.
  param([double]$PartMin = 0.15)
  $s = Get-PLZoneSettings; $map = Get-PLZoneMap
  $n = 0; $heavy = 0
  foreach ($k in $map.Keys) { $n += $map[$k].N; if (Test-PLZoneHeavy $map[$k] $s) { $heavy += $map[$k].N } }
  $part = $(if ($n) { [math]::Round($heavy / $n, 2) } else { 0 })
  [pscustomobject]@{
    SecondesEnregistrees = $n; PartEnZoneLourde = $part
    ProposerProfil = ($n -ge 600 -and $part -ge $PartMin)
    Profil = 'Limite 60 images/s'
    Texte = $(if ($n -lt 600) { 'Pas encore assez de trajets enregistres (10 minutes minimum).' }
              elseif ($part -ge $PartMin) { "Tu passes $([math]::Round($part * 100)) % du temps dans des zones lourdes. Le profil 'Limite 60 images/s' peut lisser ces passages sans toucher la qualite ; il s'applique jeu ferme et se restaure en un clic." }
              else { 'Les zones lourdes sont rares sur tes trajets : rien a changer.' })
  }
}

function Invoke-PLTablet {
  # Point d'entree unique pour la tablette TSC : une action, des parametres, une reponse JSON
  param([Parameter(Mandatory)][ValidateSet('etat', 'demarrer', 'echantillon', 'arreter', 'zones', 'conseil', 'reglages', 'restaurer')][string]$Action,
        [hashtable]$Parametres = @{})
  $r = switch ($Action) {
    'etat'        { Get-PLZoneStatus }
    'demarrer'    { Start-PLZoneWatch -Automatique:([bool]$Parametres['automatique']) }
    'echantillon' {
      $a = @{ X = [double]$Parametres['x']; Z = [double]$Parametres['z'] }
      if ($Parametres.ContainsKey('vitesse')) { $a.VitesseMs = [double]$Parametres['vitesse'] }
      if ($Parametres.ContainsKey('cap')) { $a.Cap = [double]$Parametres['cap'] }
      if ($Parametres.ContainsKey('pause')) { $a.Pause = [bool]$Parametres['pause'] }
      if ($Parametres.ContainsKey('fps')) { $a.Load = [pscustomobject]@{ Gpu = $null; Cpu = $null; Fps = [double]$Parametres['fps'] } }
      Update-PLZoneWatch @a
    }
    'arreter'     { Stop-PLZoneWatch }
    'zones'       { Get-PLHeavyZones }
    'conseil'     { Get-PLZoneAdvice }
    'reglages'    { if ($Parametres.Count) { Set-PLZoneSettings -Values $Parametres } else { Get-PLZoneSettings } }
    'restaurer'   { [pscustomobject]@{ Restaures = @(Restore-PLZoneBoost | ForEach-Object { "$($_.Nom) : $($_.Nouveau) -> $($_.Ancien)" }) } }
  }
  ConvertTo-Json -InputObject $r -Depth 5 -Compress
}

Export-ModuleMember -Function *-PLZone*, Get-PLHeavyZones, Test-PLHeavySample, Get-PLQuickLoad, Get-PLBoostPlan, Invoke-PLTablet
