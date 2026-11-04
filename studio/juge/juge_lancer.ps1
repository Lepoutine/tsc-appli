# (c) 2026 Truck So Clean France. Juge de l'atelier Spartan Studio : tout en un seul lancement, rien a cliquer.
#  1) ouvre l'atelier en mode capture (juge_capture.html) : 8 rendus (4 vues x plein jour / couchant) -> juge\captures_atelier
#  2) complete les photos reelles libres (Wikimedia Commons, CC0 / CC BY, auteur et source notes) -> juge\photos_reelles
#  3) juge DINOv2 gele (poids deja sur le PC pour TSC Graphics) -> juge\juge_resultats.json
# Ne modifie ni le jeu, ni les mods, ni l'atelier (juge_capture.html = index.html + juge\capture.js, a cote d'index.html).
param(
  [string]$Python = "$env:USERPROFILE\Documents\TSC Driver\Outils admin\tsc_graphics\venv_neural\Scripts\python.exe",
  [string]$Poids = "$env:USERPROFILE\Documents\TSC Driver\Outils admin\tsc_graphics\poids_externes\dinov2_vit_small_patch14_lvd142m\model.safetensors",
  [int]$Port = 47830, [int]$Photos = 400, [string]$Navigateur = 'msedge.exe',
  [string]$ApresUtc = ''   # ex. 23:45 : attend cette heure UTC avant de commencer (PC encore occupe par un autre entrainement)
)
$ErrorActionPreference = 'Stop'
if ($ApresUtc) {
  $debut = [DateTime]::UtcNow.Date.Add([TimeSpan]::Parse($ApresUtc)); if ($debut -lt [DateTime]::UtcNow.AddHours(-6)) { $debut = $debut.AddDays(1) }
  while ([DateTime]::UtcNow -lt $debut) { Write-Host ("attente jusqu'a " + $debut.ToString('HH:mm') + ' UTC'); Start-Sleep -Seconds 300 }
}
$juge = Split-Path -Parent $MyInvocation.MyCommand.Path
$atelier = Split-Path -Parent $juge
$captures = Join-Path $juge 'captures_atelier'; New-Item -ItemType Directory -Force $captures | Out-Null
foreach ($f in @($Python, $Poids, (Join-Path $atelier 'juge_capture.html'))) { if (-not (Test-Path -LiteralPath $f)) { throw "introuvable : $f" } }
Write-Host "1/3 Captures de l'atelier..."

$types = @{ '.html' = 'text/html; charset=utf-8'; '.js' = 'text/javascript; charset=utf-8'; '.css' = 'text/css; charset=utf-8'; '.json' = 'application/json; charset=utf-8'
  '.png' = 'image/png'; '.jpg' = 'image/jpeg'; '.svg' = 'image/svg+xml'; '.woff2' = 'font/woff2'; '.ttf' = 'font/ttf'; '.glb' = 'model/gltf-binary'; '.dds' = 'image/vnd-ms.dds' }
$http = New-Object System.Net.HttpListener
$http.Prefixes.Add("http://127.0.0.1:$Port/"); $http.Start()
$edge = $null; $fin = $false; $n = 0; $erreur = ''
try {
  $edge = Start-Process $Navigateur "--app=http://127.0.0.1:$Port/juge_capture.html --window-size=1600,900" -PassThru
  $limite = (Get-Date).AddMinutes(4)
  while (-not $fin -and (Get-Date) -lt $limite) {
    $t = $http.GetContextAsync()
    while (-not $t.Wait(500)) { if ((Get-Date) -ge $limite) { break } }
    if (-not $t.IsCompleted) { break }
    $ctx = $t.Result; $req = $ctx.Request; $rep = $ctx.Response
    try {
      $rel = [Uri]::UnescapeDataString($req.Url.AbsolutePath.TrimStart('/'))
      if ($req.HttpMethod -eq 'POST' -and $rel -eq 'juge/capture') {
        $nom = ($req.QueryString['nom'] -replace '[^\w\-]', '_')
        $sr = New-Object IO.StreamReader($req.InputStream); $d = $sr.ReadToEnd(); $sr.Close()
        [IO.File]::WriteAllBytes((Join-Path $captures "$nom.png"), [Convert]::FromBase64String(($d -split ',', 2)[1])); $n++
        $b = [Text.Encoding]::UTF8.GetBytes('ok')
      } elseif ($req.HttpMethod -eq 'POST' -and $rel -eq 'juge/fin') {
        $fin = $true; $erreur = [string]$req.QueryString['erreur']; $b = [Text.Encoding]::UTF8.GetBytes('ok')
      } else {
        if (-not $rel) { $rel = 'index.html' }
        $chemin = [IO.Path]::GetFullPath((Join-Path $atelier $rel))
        if (-not $chemin.StartsWith($atelier, [StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath $chemin -PathType Leaf)) { $rep.StatusCode = 404; $b = [Text.Encoding]::UTF8.GetBytes('introuvable') }
        else { $ext = [IO.Path]::GetExtension($chemin).ToLower(); $rep.ContentType = $(if ($types.ContainsKey($ext)) { $types[$ext] } else { 'application/octet-stream' }); $b = [IO.File]::ReadAllBytes($chemin) }
      }
      $rep.ContentLength64 = $b.Length; $rep.OutputStream.Write($b, 0, $b.Length)
    } catch { $rep.StatusCode = 500 } finally { $rep.Close() }
  }
} finally {
  $http.Stop()
  if ($edge -and -not $edge.HasExited) { try { $edge.CloseMainWindow() | Out-Null } catch {} }
}
Write-Host "   $n captures$(if ($erreur) { ' (erreur : ' + $erreur + ')' })$(if (-not $fin) { ' (temps depasse)' })"
if ($n -lt 4) { throw "pas assez de captures ($n) : l'atelier n'a pas fini de charger" }

Write-Host "2/3 Photos reelles libres (CC0 / CC BY)..."
$env:PYTHONUNBUFFERED = '1'
& $Python -u (Join-Path $juge 'collecte_photos.py') --sortie (Join-Path $juge 'photos_reelles') --max $Photos
Write-Host "   + matieres PBR libres (CC0 : Poly Haven, ambientCG)..."
& $Python -u (Join-Path $juge 'collecte_textures.py') --sortie (Join-Path $juge 'matieres_libres') --max 120
Write-Host "3/3 Juge DINOv2..."
& $Python -u (Join-Path $juge 'juge_atelier.py') --poids $Poids --reel (Join-Path $juge 'photos_reelles') --rendus $captures --sortie (Join-Path $juge 'juge_resultats.json')
Write-Host "Fini : $(Join-Path $juge 'juge_resultats.json')"
