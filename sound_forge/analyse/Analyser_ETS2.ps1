# (c) 2026 Truck So Clean France. Tous droits reserves. TSC Sound Forge, by Truck So Clean France.
# Analyseur ETS2 de TSC Sound Forge (phase 0). LECTURE SEULE : aucun fichier du jeu, d'un mod ou d'un profil n'est modifie.
# Il trouve tout seul Steam, ETS2/ATS, Documents, profils, dossier mod, Workshop, FMOD Studio, puis lit les archives
# (jeu + mods) et ecrit une base de connaissances + un rapport dans l'espace de travail de Sound Forge.
#   powershell -ExecutionPolicy Bypass -File Analyser_ETS2.ps1 [-Sortie <dossier>] [-SansCache] [-Echantillons scania.r_2016,volvo.fh_2021]
param([string]$Sortie = '', [switch]$SansCache, [string[]]$Echantillons = @(), [string]$JeuDossier = '')
$ErrorActionPreference = 'Stop'
$ici = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $Sortie) { $Sortie = Join-Path $env:LOCALAPPDATA 'TruckSoCleanFrance\TSC\soundforge' }
$cacheDir = Join-Path $Sortie 'cache'
foreach ($d in $Sortie, $cacheDir) { if (-not (Test-Path -LiteralPath $d)) { [void](New-Item -ItemType Directory -Path $d) } }
$debut = Get-Date
$versionAnalyseur = '0.2'   # a changer a chaque modification de l'analyse : le cache des versions precedentes est alors relu
function Note([string]$m) { Write-Host ('[' + (Get-Date -Format 'HH:mm:ss') + '] ' + $m) }

if (-not ('TscSoundForge.SfAnalyse' -as [type])) {
  Add-Type -TypeDefinition (Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $ici 'SoundForge.Analyse.cs')) -ReferencedAssemblies System.IO.Compression, System.Core
}

# ---------------- 1. Detection automatique des installations ----------------
$docs = [Environment]::GetFolderPath('MyDocuments'); if (-not $docs) { $docs = Join-Path $env:USERPROFILE 'Documents' }
$steam = $null; try { $steam = ((Get-ItemProperty 'HKCU:\Software\Valve\Steam' -ErrorAction Stop).SteamPath) -replace '/', '\' } catch {}
$libs = @(); if ($steam) { $libs += $steam }
if ($steam) { $vdf = Join-Path $steam 'steamapps\libraryfolders.vdf'; if (Test-Path -LiteralPath $vdf) { foreach ($m in [regex]::Matches((Get-Content -Raw -LiteralPath $vdf), '"path"\s+"([^"]+)"')) { $libs += ($m.Groups[1].Value -replace '\\\\', '\') } } }
$libs += "${env:ProgramFiles(x86)}\Steam", "$env:ProgramFiles\Steam"
$libs = @($libs | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | ForEach-Object { [IO.Path]::GetFullPath($_).TrimEnd('\') } | Sort-Object -Unique)

function Jeu-Info([string]$nom, [string]$exe, [string]$appid) {
  $l = @()
  foreach ($lib in $libs) {
    $g = Join-Path $lib ("steamapps\common\" + $nom)
    if (Test-Path -LiteralPath (Join-Path $g "bin\win_x64\$exe")) {
      $v = ''; try { $v = [Diagnostics.FileVersionInfo]::GetVersionInfo((Join-Path $g "bin\win_x64\$exe")).ProductVersion } catch {}
      $build = ''; $acf = Join-Path $lib "steamapps\appmanifest_$appid.acf"; if (Test-Path -LiteralPath $acf) { $mm = [regex]::Match((Get-Content -Raw -LiteralPath $acf), '"buildid"\s+"(\d+)"'); if ($mm.Success) { $build = $mm.Groups[1].Value } }
      $fm = @(Get-ChildItem -LiteralPath (Join-Path $g 'bin\win_x64') -Filter 'fmod*.dll' -ErrorAction SilentlyContinue | ForEach-Object { $_.Name + ' ' + ([Diagnostics.FileVersionInfo]::GetVersionInfo($_.FullName).ProductVersion) })
      $l += [ordered]@{ dossier = $g; version_exe = $v; build_steam = $build; fmod_du_jeu = $fm; bibliotheque = $lib }
    }
  }
  return $l
}
Note 'Recherche des installations...'
$ets2 = @(Jeu-Info 'Euro Truck Simulator 2' 'eurotrucks2.exe' '227300')
$ats = @(Jeu-Info 'American Truck Simulator' 'amtrucks.exe' '270880')
if ($JeuDossier) { $ets2 = @([ordered]@{ dossier = $JeuDossier; version_exe = ''; build_steam = ''; fmod_du_jeu = @(); bibliotheque = '' }) + $ets2 }
$jeu = $(if ($ets2.Count) { $ets2[0] } else { $null })

$etsDocs = Join-Path $docs 'Euro Truck Simulator 2'
$log = Join-Path $etsDocs 'game.log.txt'; $logTxt = ''
if (Test-Path -LiteralPath $log) { try { $fs = [IO.File]::Open($log, 'Open', 'Read', 'ReadWrite'); $sr = New-Object IO.StreamReader($fs, [Text.Encoding]::UTF8); $logTxt = $sr.ReadToEnd(); $sr.Close() } catch {} }
$verLog = ''; $mv = [regex]::Match($logTxt, 'init ver\.([0-9][0-9A-Za-z.]*)'); if ($mv.Success) { $verLog = $mv.Groups[1].Value }
$lignesSon = @([regex]::Matches($logTxt, '(?im)^.*(fmod|\.bank|soundref|\[sound\]|sound .*(error|warning|fail)).*$') | ForEach-Object { $_.Value.Trim() } | Select-Object -Last 60)

$profils = @(); foreach ($d in 'profiles', 'steam_profiles') { $p = Join-Path $etsDocs $d; if (Test-Path -LiteralPath $p) { foreach ($q in Get-ChildItem -LiteralPath $p -Directory) { if (Test-Path -LiteralPath (Join-Path $q.FullName 'profile.sii')) {
  $nom = $q.Name; try { if ($q.Name -match '^([0-9A-Fa-f]{2})+$') { $by = [byte[]]@(for ($i = 0; $i -lt $q.Name.Length; $i += 2) { [Convert]::ToByte($q.Name.Substring($i, 2), 16) }); $nom = [Text.Encoding]::UTF8.GetString($by) } } catch {}
  $profils += [ordered]@{ dossier = $d + '\' + $q.Name; nom = $nom; modifie = (Get-Item -LiteralPath (Join-Path $q.FullName 'profile.sii')).LastWriteTime.ToString('yyyy-MM-dd HH:mm') } } } } }

# FMOD Studio : registre (programmes installes) + dossiers habituels
Note 'Recherche de FMOD Studio...'
$fmod = @()
foreach ($k in 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*') {
  foreach ($e in @(Get-ItemProperty $k -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -like 'FMOD Studio*' })) { $fmod += [ordered]@{ nom = [string]$e.DisplayName; version = [string]$e.DisplayVersion; dossier = [string]$e.InstallLocation; source = 'registre' } }
}
foreach ($base in @($env:ProgramFiles, ${env:ProgramFiles(x86)}) | Where-Object { $_ }) {
  $fs1 = Join-Path $base 'FMOD SoundSystem'
  if (Test-Path -LiteralPath $fs1) { foreach ($d in Get-ChildItem -LiteralPath $fs1 -Directory -ErrorAction SilentlyContinue) {
    $exe = @('FMOD Studio.exe', 'fmodstudio.exe') | ForEach-Object { Join-Path $d.FullName $_ } | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if ($exe) { $cl = Join-Path $d.FullName 'fmodstudiocl.exe'; $fmod += [ordered]@{ nom = $d.Name; version = ([Diagnostics.FileVersionInfo]::GetVersionInfo($exe).ProductVersion); dossier = $d.FullName; ligne_de_commande = (Test-Path -LiteralPath $cl); source = 'dossier' } } } }
}

# ---------------- 2. Sources a analyser (ordre de chargement du jeu) ----------------
$sources = New-Object 'System.Collections.Generic.List[TscSoundForge.SfSource]'
function Ajouter([string]$chemin, [string]$role, [int]$prio, [string]$nom) {
  $s = New-Object TscSoundForge.SfSource; $s.Chemin = $chemin; $s.Role = $role; $s.Priorite = $prio; $s.Nom = $nom; $s.Id = $chemin; $s.Actif = ($role -ne 'inactif')
  $sources.Add($s)
}
if ($jeu) {
  $arch = @(Get-ChildItem -LiteralPath $jeu.dossier -Filter '*.scs' -File | Sort-Object @{ e = { $_.Name -like 'dlc_*' } }, Name)
  $i = 0; foreach ($a in $arch) { Ajouter $a.FullName 'jeu' $i $a.Name; $i++ }
}
# mods actifs (dernier profil charge, d'apres game.log : le premier liste est le moins prioritaire)
$modDir = Join-Path $etsDocs 'mod'
$ws = @{}; foreach ($lib in $libs) { $p = Join-Path $lib 'steamapps\workshop\content\227300'; if (Test-Path -LiteralPath $p) { foreach ($d in Get-ChildItem -LiteralPath $p -Directory) { $ws[$d.Name] = $d.FullName } } }
function Fichiers-Mod([string]$dossierOuBase) {
  if (Test-Path -LiteralPath $dossierOuBase -PathType Container) {
    $f = @(Get-ChildItem -LiteralPath $dossierOuBase -Force -ErrorAction SilentlyContinue | Where-Object { -not $_.PSIsContainer -and $_.Extension -in '.scs', '.zip' } | ForEach-Object { $_.FullName })
    if ($f.Count) { return $f }; return @($dossierOuBase)
  }
  return @(foreach ($e in '.scs', '.zip') { if (Test-Path -LiteralPath ($dossierOuBase + $e)) { $dossierOuBase + $e } })
}
$actifs = @(); $bl = [regex]::Matches($logTxt, '\[mods\] Active \d+ mods')
if ($bl.Count) {
  $blk = $logTxt.Substring($bl[$bl.Count - 1].Index)
  foreach ($m in [regex]::Matches($blk, '(?m)\[mods\] Active (local mod (.+?)|workshop mod ID (\d+)) \(name: (.*?), version')) {
    if ($m.Groups[2].Success -and $m.Groups[2].Value) { $actifs += [pscustomobject]@{ kind = 'local'; id = $m.Groups[2].Value; nom = $m.Groups[4].Value } }
    else { $actifs += [pscustomobject]@{ kind = 'workshop'; id = $m.Groups[3].Value; nom = $m.Groups[4].Value } }
  }
}
$vus = @{}; $prio = 1000
foreach ($a in $actifs) {
  $fl = $(if ($a.kind -eq 'local') { Fichiers-Mod (Join-Path $modDir $a.id) } elseif ($ws.ContainsKey($a.id)) { Fichiers-Mod $ws[$a.id] } else { @() })
  foreach ($f in $fl) { if (-not $vus.ContainsKey($f)) { $vus[$f] = 1; Ajouter $f 'actif' $prio ($a.nom + $(if ($a.kind -eq 'workshop') { ' (Workshop ' + $a.id + ')' } else { '' })) } }
  $prio++
}
# autres mods presents (inactifs) : analyses pour information, ils n'entrent pas dans les conflits
if (Test-Path -LiteralPath $modDir) { foreach ($f in Get-ChildItem -LiteralPath $modDir -Force) { if (($f.PSIsContainer -or $f.Extension -in '.scs', '.zip') -and -not $vus.ContainsKey($f.FullName)) { $vus[$f.FullName] = 1; Ajouter $f.FullName 'inactif' -1 $f.Name } } }
foreach ($id in $ws.Keys) { foreach ($f in (Fichiers-Mod $ws[$id])) { if (-not $vus.ContainsKey($f)) { $vus[$f] = 1; Ajouter $f 'inactif' -1 ('Workshop ' + $id + ' ' + (Split-Path $f -Leaf)) } } }

# ---------------- 3. Analyse (avec cache : seules les sources modifiees sont relues) ----------------
$sha = [Security.Cryptography.SHA1]::Create()
$n = 0; $relues = 0
foreach ($s in $sources) {
  $n++
  try { $it = Get-Item -LiteralPath $s.Chemin -Force; $cle = $versionAnalyseur + '|' + $s.Chemin + '|' + $(if ($it.PSIsContainer) { 'dossier|' + $it.LastWriteTimeUtc.Ticks } else { '' + $it.Length + '|' + $it.LastWriteTimeUtc.Ticks }) } catch { $cle = $versionAnalyseur + '|' + $s.Chemin + '|?' }
  $cf = Join-Path $cacheDir (([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($s.Chemin.ToLowerInvariant()))) -replace '-', '') + '.txt')
  $ok = $false
  if (-not $SansCache -and (Test-Path -LiteralPath $cf)) { try { $ok = $s.Charger([IO.File]::ReadAllText($cf, [Text.Encoding]::UTF8), $cle) } catch { $ok = $false } }
  if (-not $ok) {
    Write-Progress -Activity 'Analyse de mon ETS2' -Status $s.Nom -PercentComplete ([int](100 * $n / [Math]::Max(1, $sources.Count)))
    $s.Fichiers.Clear(); $s.Unites.Clear(); $s.Refs.Clear(); $s.Includes.Clear(); $s.Evenements.Clear(); $s.Banques.Clear(); $s.Camions.Clear(); $s.Etat = 'ok'; $s.Message = ''
    [void][TscSoundForge.SfAnalyse]::AnalyserSource($s); $s.Cle = $cle; $relues++
    [IO.File]::WriteAllText($cf, $s.Serialiser(), (New-Object Text.UTF8Encoding($false)))
  }
}
Write-Progress -Activity 'Analyse de mon ETS2' -Completed
Note ("$($sources.Count) sources ($relues relues, $($sources.Count - $relues) depuis le cache)")

# ---------------- 4. Base de connaissances (JSON) ----------------
$env1 = [ordered]@{
  date = (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'); duree_s = 0; machine = $env:COMPUTERNAME; windows = [string][Environment]::OSVersion.Version
  steam = $steam; bibliotheques = $libs; ets2 = $ets2; ats = $ats; version_game_log = $verLog; documents_ets2 = $etsDocs; dossier_mod = $modDir
  profils = $profils; mods_actifs_game_log = $actifs.Count; workshop_installes = $ws.Count; fmod_studio = $fmod; journal_son = $lignesSon
  sources_relues = $relues; sources_cache = ($sources.Count - $relues)
}
$env1.duree_s = [int]((Get-Date) - $debut).TotalSeconds
$json = [TscSoundForge.SfAnalyse]::Fusionner($sources, ($env1 | ConvertTo-Json -Depth 6 -Compress))
$fJson = Join-Path $Sortie 'base_connaissances.json'
[IO.File]::WriteAllText($fJson, $json, (New-Object Text.UTF8Encoding($false)))
$B = $json | ConvertFrom-Json

# ---------------- 5. Echantillons de definitions son (texte, pour l'etude des structures ; jamais redistribues) ----------------
if (-not $Echantillons.Count) { $Echantillons = @('scania.r_2016', 'scania.s_2016', 'volvo.fh_2021') | Where-Object { $id = $_; @($B.camions | Where-Object { $_.id -eq $id }).Count } }
$ech = Join-Path $Sortie 'echantillons'
function Ecrire-Echantillon([string]$chemin, $src, [string]$t) {
  $dst = Join-Path $ech ($chemin.Trim('/') -replace '/', '\'); $dd = Split-Path -Parent $dst; if (-not (Test-Path -LiteralPath $dd)) { [void](New-Item -ItemType Directory -Path $dd -Force) }
  [IO.File]::WriteAllText($dst, "# source : " + $src.Nom + "`r`n" + $t, (New-Object Text.UTF8Encoding($false)))
}
# source gagnante (la plus prioritaire, hors mods inactifs) de chaque fichier lu
$gagnant = @{}; foreach ($s in ($sources | Where-Object { $_.Role -ne 'inactif' } | Sort-Object Priorite)) { foreach ($f in $s.Fichiers) { $gagnant[$f[0].ToLowerInvariant()] = $s } }
$banquesVues = @{}
foreach ($id in $Echantillons) {
  $c = $B.camions | Where-Object { $_.id -eq $id } | Select-Object -First 1; if (-not $c) { continue }
  $a_lire = @{}; foreach ($f in @($c.fichiers_son)) { $a_lire[$f.ToLowerInvariant()] = 1 }
  foreach ($r in @($c.references)) {
    $p = (($r.reference -split '#')[0]).Trim('/').ToLowerInvariant(); if ($p -like '*.soundref') { $a_lire[$p] = 1 }
    $m = [regex]::Match($r.raison, '-> /?([^#\s]+\.bank)#'); if ($m.Success) { $banquesVues[$m.Groups[1].Value.ToLowerInvariant()] = 1 }
    if ($p -like '*.bank') { $banquesVues[$p] = 1 }
  }
  foreach ($p in $a_lire.Keys) { if ($gagnant.ContainsKey($p)) { $t = [TscSoundForge.SfAnalyse]::LireTexte($gagnant[$p].Chemin, $p); if ($null -ne $t) { Ecrire-Echantillon $p $gagnant[$p] $t } } }
}
# les .bank.guids des banques utilisees par ces camions (liste des evenements officiels du jeu)
foreach ($b in @($banquesVues.Keys | Select-Object -First 12)) { $g = $b + '.guids'; if ($gagnant.ContainsKey($g)) { $t = [TscSoundForge.SfAnalyse]::LireTexte($gagnant[$g].Chemin, $g); if ($null -ne $t) { Ecrire-Echantillon $g $gagnant[$g] $t } } }

# ---------------- 6. Rapport lisible ----------------
$R = $B.resume; $sb = New-Object Text.StringBuilder
function L([string]$t) { [void]$sb.AppendLine($t) }
L '# TSC Sound Forge : analyse de mon ETS2'
L ''; L ('Analyse du ' + $env1.date + ' sur ' + $env1.machine + ' (' + $env1.duree_s + ' s, lecture seule : rien n''a ete modifie).')
L ''; L '## Tableau de bord'
L ('- ETS2 : ' + $(if ($jeu) { $jeu.version_exe + ' (game.log : ' + $verLog + ') dans ' + $jeu.dossier } else { 'NON TROUVE' }))
L ('- FMOD du jeu : ' + $(if ($jeu -and $jeu.fmod_du_jeu.Count) { $jeu.fmod_du_jeu -join ', ' } else { 'non trouve' }))
L ('- FMOD Studio : ' + $(if ($fmod.Count) { ($fmod | ForEach-Object { $_.nom + ' ' + $_.version }) -join ', ' } else { 'non installe (necessaire seulement pour compiler, phase 3)' }))
L ('- ATS : ' + $(if ($ats.Count) { $ats[0].version_exe } else { 'non installe' }))
L ('- Camions identifies : ' + $R.camions + ' ; moteurs : ' + $R.moteurs + ' ; banques FMOD visibles : ' + $R.banques + ' (dossiers d''accessoires de mods ignores : ' + $R.dossiers_accessoires_ignores + ')')
L ('- Mods audio : ' + $R.mods_audio + ' ; conflits potentiels : ' + $R.conflits + ' ; fichiers son ou moteur du jeu remplaces par des mods : ' + $R.remplacements_du_jeu)
L ('- Compatibilite : ' + $R.compatibles + ' compatibles, ' + $R.partiels + ' partiels, ' + $R.non_pris_en_charge + ' non pris en charge, ' + $R.non_verifies + ' non verifies')
L ('- Profils : ' + $profils.Count + ' ; mods actifs (game.log) : ' + $actifs.Count + ' ; Workshop installes : ' + $ws.Count)
L ''; L '## Camions'
L '| Camion | Origine | Moteurs | Etat | Raison |'; L '|---|---|---|---|---|'
foreach ($c in $B.camions) { L ('| ' + $c.id + ' | ' + $c.origine + ' | ' + @($c.moteurs).Count + ' | ' + $c.compatibilite + ' | ' + $c.raison + ' |') }
L ''; L '## Detail des camions de test'
foreach ($id in $Echantillons) { $c = $B.camions | Where-Object { $_.id -eq $id } | Select-Object -First 1; if (-not $c) { continue }
  L ''; L ('### ' + $id + ' : ' + $c.compatibilite + ' (' + $c.origine + ')'); L $c.raison
  L ('Moteurs : ' + (@($c.moteurs | ForEach-Object { ($_ -split ' \| ')[1] }) -join ', '))
  foreach ($r in @($c.references)) { L ('- [' + $r.etat + '] ' + $r.fichier + ' -> ' + $r.reference + ' : ' + $r.raison) } }
L ''; L '## Conflits entre mods (meme fichier son fourni par plusieurs mods actifs)'
$cf2 = @($B.conflits | Where-Object { $_.type -eq 'plusieurs_mods' }); if (-not $cf2.Count) { L 'Aucun.' } else { foreach ($c in $cf2 | Select-Object -First 300) { L ('- ' + $c.chemin + ' : ' + ($c.sources -join ' < ') + ' ; le jeu utilise ' + $c.gagnant) } }
L ''; L '## Mods qui remplacent des fichiers son du jeu'
$rp = @($B.conflits | Where-Object { $_.type -eq 'remplace_le_jeu' }); if (-not $rp.Count) { L 'Aucun.' } else { foreach ($c in $rp | Select-Object -First 200) { L ('- ' + $c.chemin + ' : ' + $c.gagnant) }; if ($rp.Count -gt 200) { L ('- ... et ' + ($rp.Count - 200) + ' autres (voir base_connaissances.json)') } }
L ''; L '## Sources non lisibles ou protegees'
$np = @($B.sources | Where-Object { $_.etat -ne 'ok' -or $_.chiffres -gt 0 }); if (-not $np.Count) { L 'Aucune.' } else { foreach ($s in $np) { L ('- ' + $s.nom + ' (' + $s.role + ') : ' + $s.etat + $(if ($s.chiffres) { ', ' + $s.chiffres + ' fichier(s) chiffre(s)' } else { '' }) + ' ' + $s.message) } }
L ''; L '## Journal du jeu (lignes son / FMOD)'
if (-not $lignesSon.Count) { L 'Aucune ligne son dans game.log.txt.' } else { L '```'; foreach ($l in $lignesSon) { L $l }; L '```' }
$fMd = Join-Path $Sortie 'rapport_analyse.md'
[IO.File]::WriteAllText($fMd, $sb.ToString(), (New-Object Text.UTF8Encoding($false)))
Note ("Fini en $($env1.duree_s) s. Rapport : $fMd")
Note ("Camions $($R.camions), moteurs $($R.moteurs), banques $($R.banques), mods audio $($R.mods_audio), conflits $($R.conflits)")
