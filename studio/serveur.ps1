# TSCF Spartan Studio : petit serveur local (127.0.0.1 seulement) qui sert le dossier de l'atelier, puis ouvre Microsoft Edge.
# Edge est choisi pour la phase 4 : il fournit la reconnaissance vocale et les voix françaises naturelles.
param([int]$Port = 47830)
$ErrorActionPreference = 'Stop'
$racine = Split-Path -Parent $MyInvocation.MyCommand.Path
$types = @{ '.html' = 'text/html; charset=utf-8'; '.js' = 'text/javascript; charset=utf-8'; '.css' = 'text/css; charset=utf-8'; '.json' = 'application/json; charset=utf-8'
  '.png' = 'image/png'; '.jpg' = 'image/jpeg'; '.svg' = 'image/svg+xml'; '.woff2' = 'font/woff2'; '.glb' = 'model/gltf-binary'; '.dds' = 'image/vnd-ms.dds'; '.txt' = 'text/plain; charset=utf-8' }
$http = New-Object System.Net.HttpListener
$http.Prefixes.Add("http://127.0.0.1:$Port/")
$http.Start()
$url = "http://127.0.0.1:$Port/index.html"
Write-Host "TSCF Spartan Studio : $url (fermer cette fenetre pour arreter l'atelier)"
try { Start-Process "msedge.exe" "--app=$url" } catch { try { Start-Process $url } catch { Write-Host "Ouvre cette adresse dans Edge : $url" } }
while ($http.IsListening) {
  $ctx = $http.GetContext(); $rep = $ctx.Response
  try {
    $rel = [Uri]::UnescapeDataString($ctx.Request.Url.AbsolutePath.TrimStart('/'))
    if (-not $rel) { $rel = 'index.html' }
    $chemin = [IO.Path]::GetFullPath((Join-Path $racine $rel))
    # rien en dehors du dossier de l'atelier
    if (-not $chemin.StartsWith($racine, [StringComparison]::OrdinalIgnoreCase) -or -not (Test-Path -LiteralPath $chemin -PathType Leaf)) {
      $rep.StatusCode = 404; $b = [Text.Encoding]::UTF8.GetBytes('introuvable')
    } else {
      $ext = [IO.Path]::GetExtension($chemin).ToLower()
      $rep.ContentType = $(if ($types.ContainsKey($ext)) { $types[$ext] } else { 'application/octet-stream' })
      $rep.AddHeader('Cache-Control', 'no-store')
      $b = [IO.File]::ReadAllBytes($chemin)
    }
    $rep.ContentLength64 = $b.Length; $rep.OutputStream.Write($b, 0, $b.Length)
  } catch { $rep.StatusCode = 500 } finally { $rep.Close() }
}
