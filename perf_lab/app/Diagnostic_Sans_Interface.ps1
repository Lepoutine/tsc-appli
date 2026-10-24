# TSC Performance Lab - diagnostic complet sans interface, en lecture seule.
# Ecrit le rapport HTML et un resume JSON dans Documents\TSC Driver\TSC Performance Lab\rapports.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Import-Module (Join-Path $here 'PerfLab.Core.psm1') -Force
$t = Get-Date
$d = Invoke-PLDiagnostic
$report = Export-PLReport -Diag $d -Runs @(Get-PLRuns) -History @(Get-PLHistory)
$sum = [pscustomobject]@{
  DureeS = [math]::Round(((Get-Date) - $t).TotalSeconds, 1)
  Machine = $d.Machine.Nom; Processeur = $d.Machine.Processeur; Cartes = @($d.Machine.CartesGraphiques | ForEach-Object Nom)
  Jeu = $d.Game.GameDir; Documents = $d.Game.DocsDir; VersionJeu = $d.Journal.Version; Profil = $d.Graphismes.ProfileName
  ModsMontes = $d.Mods.Montes; ModsTotal = $d.Mods.Total; ModsReconnus = @($d.Mods.Liste | Where-Object Monte).Count
  ErreursJournal = @($d.Journal.Erreurs).Count; Plantages = $d.Plantages.Total; ModulesPlantages = $d.Plantages.ParModule
  Injections = @($d.Injections | ForEach-Object Fichier); Plugins = @($d.Plugins | ForEach-Object Fichier)
  Recommandations = @($d.Recommandations | ForEach-Object { "$($_.Impact) | $($_.Titre) | applicable=$($_.Applicable)" })
  Rapport = $report
}
$json = Join-Path (Split-Path $report) ('resume_' + (Get-Date -Format 'yyyy-MM-dd_HHmm') + '.json')
$sum | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $json -Encoding UTF8
$sum | ConvertTo-Json -Depth 5
