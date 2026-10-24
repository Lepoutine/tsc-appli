# TSC Performance Lab - interface (Windows, WPF)
# Lancement : Lancer_TSC_Performance_Lab.bat (ou powershell -STA -File TSC_Performance_Lab.ps1)

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName PresentationFramework, PresentationCore, WindowsBase, System.Windows.Forms, Microsoft.VisualBasic
# la console est cachee : toute erreur au demarrage est affichee dans une fenetre
trap { [Windows.MessageBox]::Show("Erreur au demarrage de TSC Performance Lab :`n`n$($_.Exception.Message)", 'TSC Performance Lab', 'OK', 'Error') | Out-Null; exit 1 }
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$modulePath = Join-Path $here 'PerfLab.Core.psm1'
Import-Module $modulePath -Force

$AppVersion = '0.1.0'

[xml]$xaml = @'
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="TSC Performance Lab" Width="1220" Height="820" MinWidth="980" MinHeight="640"
        WindowStartupLocation="CenterScreen" Background="#14171C" Foreground="#E8EAED" FontFamily="Segoe UI" FontSize="13">
  <Window.Resources>
    <Style TargetType="Button">
      <Setter Property="Background" Value="#B00020"/>
      <Setter Property="Foreground" Value="White"/>
      <Setter Property="BorderThickness" Value="0"/>
      <Setter Property="Padding" Value="14,7"/>
      <Setter Property="Margin" Value="0,0,8,0"/>
      <Setter Property="Cursor" Value="Hand"/>
      <Style.Triggers>
        <Trigger Property="IsEnabled" Value="False"><Setter Property="Opacity" Value="0.45"/></Trigger>
      </Style.Triggers>
    </Style>
    <Style x:Key="Second" TargetType="Button" BasedOn="{StaticResource {x:Type Button}}">
      <Setter Property="Background" Value="#2A3038"/>
    </Style>
    <Style TargetType="DataGrid">
      <Setter Property="Background" Value="#1B1F25"/>
      <Setter Property="Foreground" Value="#E8EAED"/>
      <Setter Property="RowBackground" Value="#1B1F25"/>
      <Setter Property="AlternatingRowBackground" Value="#20252C"/>
      <Setter Property="GridLinesVisibility" Value="Horizontal"/>
      <Setter Property="HorizontalGridLinesBrush" Value="#2A3038"/>
      <Setter Property="BorderBrush" Value="#2A3038"/>
      <Setter Property="IsReadOnly" Value="True"/>
      <Setter Property="HeadersVisibility" Value="Column"/>
      <Setter Property="CanUserAddRows" Value="False"/>
      <Setter Property="Margin" Value="0,6,0,6"/>
    </Style>
    <Style TargetType="DataGridColumnHeader">
      <Setter Property="Background" Value="#2A3038"/>
      <Setter Property="Foreground" Value="#E8EAED"/>
      <Setter Property="Padding" Value="6,4"/>
      <Setter Property="BorderThickness" Value="0"/>
    </Style>
    <Style TargetType="TextBlock" x:Key="H"><Setter Property="FontSize" Value="16"/><Setter Property="FontWeight" Value="SemiBold"/><Setter Property="Margin" Value="0,10,0,4"/></Style>
    <Style TargetType="TextBlock" x:Key="Note"><Setter Property="Foreground" Value="#9AA3AD"/><Setter Property="TextWrapping" Value="Wrap"/></Style>
    <Style TargetType="Border" x:Key="Card"><Setter Property="Background" Value="#1B1F25"/><Setter Property="CornerRadius" Value="6"/><Setter Property="Padding" Value="14"/><Setter Property="Margin" Value="0,0,10,10"/></Style>
    <Style TargetType="TabItem">
      <Setter Property="Foreground" Value="#E8EAED"/>
      <Setter Property="Template">
        <Setter.Value>
          <ControlTemplate TargetType="TabItem">
            <Border x:Name="b" Padding="14,8" Background="Transparent" BorderThickness="0,0,0,3" BorderBrush="Transparent">
              <ContentPresenter ContentSource="Header"/>
            </Border>
            <ControlTemplate.Triggers>
              <Trigger Property="IsSelected" Value="True"><Setter TargetName="b" Property="BorderBrush" Value="#B00020"/><Setter TargetName="b" Property="Background" Value="#1B1F25"/></Trigger>
            </ControlTemplate.Triggers>
          </ControlTemplate>
        </Setter.Value>
      </Setter>
    </Style>
  </Window.Resources>
  <DockPanel>
    <Border DockPanel.Dock="Top" Background="#0E1014" Padding="18,12">
      <DockPanel>
        <StackPanel Orientation="Horizontal">
          <TextBlock Text="TSC" Foreground="#B00020" FontWeight="Bold" FontSize="22"/>
          <TextBlock Text=" Performance Lab" FontSize="22" FontWeight="Light"/>
        </StackPanel>
        <TextBlock x:Name="TxtMachine" HorizontalAlignment="Right" VerticalAlignment="Center" Foreground="#9AA3AD"/>
      </DockPanel>
    </Border>
    <Border DockPanel.Dock="Bottom" Background="#0E1014" Padding="18,6">
      <DockPanel>
        <ProgressBar x:Name="Busy" DockPanel.Dock="Right" Width="160" Height="6" IsIndeterminate="True" Visibility="Hidden" Foreground="#B00020" Background="#2A3038" BorderThickness="0"/>
        <TextBlock x:Name="TxtStatus" Foreground="#9AA3AD" Text="Pret."/>
      </DockPanel>
    </Border>
    <TabControl x:Name="Tabs" Background="#14171C" BorderThickness="0" Padding="18,10">
      <TabItem Header="Tableau de bord">
        <DockPanel>
          <StackPanel DockPanel.Dock="Top" Orientation="Horizontal" Margin="0,0,0,10">
            <Button x:Name="BtnDiag" Content="Lancer le diagnostic"/>
            <TextBlock Style="{StaticResource Note}" VerticalAlignment="Center" Text="Lecture seule : rien n'est modifie pendant le diagnostic."/>
          </StackPanel>
          <WrapPanel DockPanel.Dock="Top" x:Name="Cards"/>
          <TextBlock DockPanel.Dock="Top" Style="{StaticResource H}" Text="Recommandations, classees par impact"/>
          <StackPanel DockPanel.Dock="Bottom" Orientation="Horizontal">
            <Button x:Name="BtnApplyReco" Content="Appliquer la recommandation choisie" IsEnabled="False"/>
            <TextBlock Style="{StaticResource Note}" VerticalAlignment="Center" Text="Seules les lignes marquees 'Applicable' peuvent etre appliquees ; chaque changement est sauvegarde et annulable dans Historique."/>
          </StackPanel>
          <DataGrid x:Name="GridReco" AutoGenerateColumns="False" SelectionMode="Single">
            <DataGrid.Columns>
              <DataGridTextColumn Header="Impact" Binding="{Binding Impact}" Width="80"/>
              <DataGridTextColumn Header="Risque" Binding="{Binding Risque}" Width="80"/>
              <DataGridTextColumn Header="Constat" Binding="{Binding Titre}" Width="220"/>
              <DataGridTextColumn Header="Detail" Binding="{Binding Constat}" Width="*">
                <DataGridTextColumn.ElementStyle><Style TargetType="TextBlock"><Setter Property="TextWrapping" Value="Wrap"/></Style></DataGridTextColumn.ElementStyle>
              </DataGridTextColumn>
              <DataGridTextColumn Header="Action proposee" Binding="{Binding Action}" Width="*">
                <DataGridTextColumn.ElementStyle><Style TargetType="TextBlock"><Setter Property="TextWrapping" Value="Wrap"/></Style></DataGridTextColumn.ElementStyle>
              </DataGridTextColumn>
              <DataGridTextColumn Header="Qualite touchee" Binding="{Binding QualiteTouchee}" Width="90"/>
              <DataGridCheckBoxColumn Header="Applicable" Binding="{Binding Applicable}" Width="75"/>
            </DataGrid.Columns>
          </DataGrid>
        </DockPanel>
      </TabItem>
      <TabItem Header="Diagnostic">
        <ScrollViewer VerticalScrollBarVisibility="Auto">
          <StackPanel>
            <TextBlock Style="{StaticResource H}" Text="Machine"/>
            <DataGrid x:Name="GridMachine" MaxHeight="300"/>
            <TextBlock Style="{StaticResource H}" Text="Cartes graphiques"/>
            <DataGrid x:Name="GridGpu"/>
            <TextBlock Style="{StaticResource H}" Text="Disques"/>
            <DataGrid x:Name="GridDisk"/>
            <TextBlock Style="{StaticResource H}" Text="Reglages graphiques du jeu"/>
            <DataGrid x:Name="GridGfx" MaxHeight="420"/>
            <TextBlock Style="{StaticResource H}" Text="Injections dans le dossier du jeu"/>
            <DataGrid x:Name="GridInj"/>
            <TextBlock Style="{StaticResource H}" Text="Plugins"/>
            <DataGrid x:Name="GridPlug"/>
            <TextBlock Style="{StaticResource H}" Text="Programmes en arriere-plan connus"/>
            <DataGrid x:Name="GridBg"/>
          </StackPanel>
        </ScrollViewer>
      </TabItem>
      <TabItem Header="Mods">
        <DockPanel>
          <DockPanel DockPanel.Dock="Top" Margin="0,0,0,6">
            <TextBlock x:Name="TxtMods" Style="{StaticResource Note}" VerticalAlignment="Center"/>
            <TextBox x:Name="TxtFilter" Width="260" HorizontalAlignment="Right" Background="#1B1F25" Foreground="#E8EAED" BorderBrush="#2A3038" Padding="6,4" ToolTip="Filtrer par nom"/>
          </DockPanel>
          <TextBlock DockPanel.Dock="Bottom" Style="{StaticResource Note}" Text="Un mod n'est jamais designe comme responsable du seul fait qu'il est actif. 'Messages' = lignes du journal qui le citent ; seule une mesure avec et sans lui permet de conclure sur son cout."/>
          <DataGrid x:Name="GridMods"/>
        </DockPanel>
      </TabItem>
      <TabItem Header="Erreurs">
        <Grid>
          <Grid.RowDefinitions><RowDefinition Height="Auto"/><RowDefinition Height="2*"/><RowDefinition Height="Auto"/><RowDefinition Height="3*"/></Grid.RowDefinitions>
          <TextBlock x:Name="TxtCrash" Style="{StaticResource H}" Text="Plantages enregistres par Windows"/>
          <DataGrid x:Name="GridCrash" Grid.Row="1"/>
          <TextBlock x:Name="TxtLog" Grid.Row="2" Style="{StaticResource H}" Text="Erreurs du journal du jeu"/>
          <DataGrid x:Name="GridLog" Grid.Row="3"/>
        </Grid>
      </TabItem>
      <TabItem Header="Mesures">
        <DockPanel>
          <Border DockPanel.Dock="Top" Style="{StaticResource Card}">
            <StackPanel>
              <WrapPanel>
                <StackPanel Margin="0,0,12,0"><TextBlock Text="Libelle"/><TextBox x:Name="InLabel" Width="220" Background="#14171C" Foreground="#E8EAED" BorderBrush="#2A3038" Padding="4" Text="Reference"/></StackPanel>
                <StackPanel Margin="0,0,12,0"><TextBlock Text="Zone"/><ComboBox x:Name="InZone" Width="170" SelectedIndex="0"><ComboBoxItem Content="Ville chargee"/><ComboBoxItem Content="Campagne"/><ComboBoxItem Content="Noeud routier exigeant"/><ComboBoxItem Content="Autre"/></ComboBox></StackPanel>
                <StackPanel Margin="0,0,12,0"><TextBlock Text="Duree"/><ComboBox x:Name="InDur" Width="110" SelectedIndex="2"><ComboBoxItem Content="60 s"/><ComboBoxItem Content="120 s"/><ComboBoxItem Content="180 s"/><ComboBoxItem Content="300 s"/></ComboBox></StackPanel>
                <StackPanel Margin="0,0,12,0"><TextBlock Text="Profil en place"/><TextBox x:Name="InProfil" Width="200" Background="#14171C" Foreground="#E8EAED" BorderBrush="#2A3038" Padding="4" Text="Actuel"/></StackPanel>
                <Button x:Name="BtnMeasure" Content="Mesurer" VerticalAlignment="Bottom"/>
                <Button x:Name="BtnImport" Style="{StaticResource Second}" Content="Importer un CSV PresentMon" VerticalAlignment="Bottom"/>
              </WrapPanel>
              <TextBlock Style="{StaticResource Note}" Margin="0,8,0,0" Text="Methode : roule sur le meme parcours, a la meme heure du jeu et par la meme meteo pour chaque mesure. La mesure lit les images produites par le jeu via PresentMon (Intel, sans injection) ; Windows demande une confirmation administrateur. Elle ne voit pas l'encodage, le reseau ni le decodage sur ton PC principal."/>
            </StackPanel>
          </Border>
          <StackPanel DockPanel.Dock="Bottom">
            <StackPanel Orientation="Horizontal" Margin="0,4,0,0">
              <Button x:Name="BtnCompare" Content="Comparer les deux mesures choisies" IsEnabled="False"/>
              <TextBlock Style="{StaticResource Note}" VerticalAlignment="Center" Text="Choisis deux lignes (Ctrl + clic) : la plus ancienne est 'avant'. Un ecart de moins de 3 % est du bruit de mesure."/>
            </StackPanel>
            <DataGrid x:Name="GridCompare" MaxHeight="230"/>
          </StackPanel>
          <DataGrid x:Name="GridRuns" SelectionMode="Extended"/>
        </DockPanel>
      </TabItem>
      <TabItem Header="Profils">
        <DockPanel>
          <StackPanel DockPanel.Dock="Top" Orientation="Horizontal" Margin="0,0,0,8">
            <Button x:Name="BtnSaveProfile" Style="{StaticResource Second}" Content="Enregistrer les reglages actuels comme profil"/>
            <Button x:Name="BtnApplyProfile" Content="Appliquer le profil choisi" IsEnabled="False"/>
          </StackPanel>
          <TextBlock DockPanel.Dock="Top" Style="{StaticResource Note}" Text="Le jeu doit etre ferme. Avant toute ecriture, config.cfg (global et profil) est sauvegarde ; la restauration se fait dans Historique. Le profil Ultra que tu enregistres n'est jamais modifie par l'outil."/>
          <DataGrid x:Name="GridProfiles" DockPanel.Dock="Top" MaxHeight="240" SelectionMode="Single"/>
          <TextBlock DockPanel.Dock="Top" Style="{StaticResource H}" Text="Ce que le profil choisi changerait"/>
          <DataGrid x:Name="GridDiff"/>
        </DockPanel>
      </TabItem>
      <TabItem Header="Historique">
        <DockPanel>
          <StackPanel DockPanel.Dock="Top" Orientation="Horizontal" Margin="0,0,0,8">
            <Button x:Name="BtnUndo" Content="Annuler l'operation choisie" IsEnabled="False"/>
            <Button x:Name="BtnOpenData" Style="{StaticResource Second}" Content="Ouvrir le dossier des sauvegardes"/>
          </StackPanel>
          <DataGrid x:Name="GridHist" SelectionMode="Single"/>
        </DockPanel>
      </TabItem>
      <TabItem Header="Rapport">
        <StackPanel>
          <TextBlock Style="{StaticResource Note}" Text="Le rapport reprend le diagnostic, les recommandations, les mesures et l'historique des modifications, dans un fichier HTML a ouvrir ou a envoyer." Margin="0,0,0,10"/>
          <StackPanel Orientation="Horizontal"><Button x:Name="BtnReport" Content="Exporter le rapport" IsEnabled="False"/></StackPanel>
          <TextBlock x:Name="TxtReport" Style="{StaticResource Note}" Margin="0,10,0,0"/>
        </StackPanel>
      </TabItem>
    </TabControl>
  </DockPanel>
</Window>
'@

$win = [Windows.Markup.XamlReader]::Load((New-Object System.Xml.XmlNodeReader $xaml))
$ui = @{}
$xaml.SelectNodes('//*[@*[local-name()="Name"]]') | ForEach-Object { $n = $_.GetAttribute('Name', 'http://schemas.microsoft.com/winfx/2006/xaml'); if ($n) { $ui[$n] = $win.FindName($n) } }

$state = @{ Diag = $null; Game = (Find-PLGame); Job = $null }

function Set-Status($text) { $ui.TxtStatus.Text = $text }
function Show-Error($msg) { [Windows.MessageBox]::Show($msg, 'TSC Performance Lab', 'OK', 'Error') | Out-Null }
function Ask($msg) { [Windows.MessageBox]::Show($msg, 'TSC Performance Lab', 'YesNo', 'Question') -eq 'Yes' }
function Set-Grid($grid, $rows) { $list = New-Object System.Collections.ArrayList; foreach ($r in @($rows)) { if ($null -ne $r) { [void]$list.Add($r) } }; $grid.ItemsSource = $null; $grid.ItemsSource = $list }

# Travail en arriere-plan : l'interface reste utilisable pendant une mesure ou un diagnostic
function Start-Background([string]$Label, [scriptblock]$Work, [object[]]$Arguments, [scriptblock]$OnDone) {
  if ($state.Job) { Show-Error 'Une operation est deja en cours.'; return }
  $ps = [powershell]::Create()
  [void]$ps.AddScript("Import-Module '$modulePath'").AddStatement().AddScript($Work.ToString())
  foreach ($a in $Arguments) { [void]$ps.AddArgument($a) }
  $state.Job = @{ PS = $ps; Handle = $ps.BeginInvoke(); Done = $OnDone; Label = $Label; Start = Get-Date }
  $ui.Busy.Visibility = 'Visible'; Set-Status "$Label..."
}
$timer = New-Object Windows.Threading.DispatcherTimer
$timer.Interval = [TimeSpan]::FromMilliseconds(400)
$timer.Add_Tick({
  $j = $state.Job
  if (-not $j) { return }
  if (-not $j.Handle.IsCompleted) { Set-Status ("{0}... {1:mm\:ss}" -f $j.Label, ((Get-Date) - $j.Start)); return }
  $state.Job = $null; $ui.Busy.Visibility = 'Hidden'
  try {
    $res = $j.PS.EndInvoke($j.Handle)
    if ($j.PS.Streams.Error.Count) { throw $j.PS.Streams.Error[0].Exception }
    Set-Status "$($j.Label) : termine."
    & $j.Done (@($res) | Select-Object -Last 1)
  } catch { Set-Status "$($j.Label) : echec."; Show-Error $_.Exception.Message }
  finally { $j.PS.Dispose() }
})
$timer.Start()

function New-Card($title, $value, $note, $color) {
  $b = New-Object Windows.Controls.Border; $b.Style = $win.FindResource('Card'); $b.Width = 260
  $sp = New-Object Windows.Controls.StackPanel
  $t = New-Object Windows.Controls.TextBlock; $t.Text = $title; $t.Foreground = '#9AA3AD'
  $v = New-Object Windows.Controls.TextBlock; $v.Text = $value; $v.FontSize = 22; $v.FontWeight = 'SemiBold'; $v.Foreground = $color; $v.TextWrapping = 'Wrap'
  $n = New-Object Windows.Controls.TextBlock; $n.Text = $note; $n.Foreground = '#9AA3AD'; $n.TextWrapping = 'Wrap'; $n.Margin = '0,4,0,0'
  [void]$sp.Children.Add($t); [void]$sp.Children.Add($v); [void]$sp.Children.Add($n); $b.Child = $sp
  [void]$ui.Cards.Children.Add($b)
}

function Show-Diag($d) {
  $state.Diag = $d; $state.Game = $d.Game
  $m = $d.Machine
  $ui.TxtMachine.Text = "$($m.Nom) - $($m.Processeur) - $(@($m.CartesGraphiques | ForEach-Object Nom) -join ', ')"
  $ui.Cards.Children.Clear()
  $red = '#FF5C6C'; $ok = '#5CD68A'; $warn = '#F2B84B'
  $c = $d.Plantages
  New-Card 'Stabilite (30 jours)' $(if ($c.Total) { "$($c.Total) plantages" } else { 'Aucun plantage' }) $(if ($c.Total) { 'Module le plus cite : ' + $c.ParModule[0].Module } else { 'Journal Windows' }) $(if ($c.Total -gt 5) { $red } elseif ($c.Total) { $warn } else { $ok })
  $gl = $d.Graphismes.Global
  $lim = if ($gl.Contains('t_limit_fps')) { $gl['t_limit_fps'] } else { '?' }
  $vs = if ($gl.Contains('r_vsync')) { $gl['r_vsync'] } else { '?' }
  New-Card 'Cadence des images' "Limite $lim images/s" "Synchro verticale : $(if ($vs -eq '1') { 'oui' } else { 'non' })" $(if ($lim -eq '60' -or $vs -eq '1') { $ok } else { $warn })
  New-Card 'Mods' "$($d.Mods.Montes) montes" "$($d.Mods.Total) fichiers, $($d.Mods.TailleGo) Go au total" $(if ($d.Mods.Montes -gt 80) { $warn } else { $ok })
  $ne = if ($d.Journal) { ($d.Journal.Erreurs | Measure-Object Nombre -Sum).Sum } else { 0 }
  New-Card 'Journal du jeu' "$([int]$ne) erreurs" $(if ($d.Journal -and $d.Journal.ChargementCarteS) { "Carte chargee en $([math]::Round($d.Journal.ChargementCarteS / 60, 1)) min - ETS2 $($d.Journal.Version)" } else { 'game.log.txt' }) $(if ($ne -gt 100) { $warn } else { $ok })
  New-Card 'Injections et plugins' "$(@($d.Injections).Count) + $(@($d.Plugins).Count)" 'Couches dans le dossier du jeu + plugins' $(if (@($d.Plugins | Where-Object Telemetrie).Count -ge 3) { $warn } else { $ok })
  Set-Grid $ui.GridReco $d.Recommandations
  $mrow = [pscustomobject]@{ Machine = $m.Nom; Modele = $m.Modele; Windows = $m.Windows; Processeur = $m.Processeur; 'Coeurs/threads' = "$($m.Coeurs)/$($m.Threads)"; 'Memoire Go' = "$($m.RamGo) ($($m.RamLibreGo) libres)"; Alimentation = $m.PlanAlimentation; HAGS = $m.HAGS; 'Mode Jeu' = $m.ModeJeu; 'Game DVR' = $m.GameDVR; Shadow = $m.EstShadow }
  Set-Grid $ui.GridMachine $mrow
  Set-Grid $ui.GridGpu $m.CartesGraphiques
  Set-Grid $ui.GridDisk $m.Disques
  Set-Grid $ui.GridGfx $d.Graphismes.Rows
  Set-Grid $ui.GridInj $d.Injections
  Set-Grid $ui.GridPlug $d.Plugins
  Set-Grid $ui.GridBg $d.ArrierePlan
  $ui.TxtMods.Text = "$($d.Mods.Montes) mods montes pour le profil $($d.Graphismes.ProfileName) ($($d.Mods.TailleMonteeGo) Go) sur $($d.Mods.Total) presents ($($d.Mods.TailleGo) Go)."
  Set-Grid $ui.GridMods $d.Mods.Liste
  $ui.TxtCrash.Text = "Plantages enregistres par Windows : $($c.Total) en $($c.Jours) jours, par module en faute"
  Set-Grid $ui.GridCrash $c.ParModule
  if ($d.Journal) { $ui.TxtLog.Text = "Erreurs du journal du jeu ($($d.Journal.Lignes) lignes lues)"; Set-Grid $ui.GridLog (@($d.Journal.Erreurs) + @($d.Journal.Avertissements) | Sort-Object Nombre -Descending) }
  $ui.BtnReport.IsEnabled = $true
}

function Refresh-Runs { Set-Grid $ui.GridRuns @(Get-PLRuns | ForEach-Object { [pscustomobject]@{ Id = $_.Id; Date = $_.Date; Libelle = $_.Libelle; Zone = $_.Zone; Profil = $_.Profil; 'Img/s moy' = $_.Stats.FpsMoyen; '1 % bas' = $_.Stats.Fps1PctBas; '0,1 % bas' = $_.Stats.Fps01PctBas; 'P99 ms' = $_.Stats.TrameP99Ms; 'Ecart-type ms' = $_.Stats.EcartTypeMs; 'Saccades/min' = $_.Stats.SaccadesParMin; Limite = $_.Stats.Limite; 'CPU %' = $_.Charge.CpuMoy; 'GPU %' = $_.Charge.GpuMoy } }) }
function Refresh-Profiles { $state.Profiles = @(Get-PLProfiles); Set-Grid $ui.GridProfiles @($state.Profiles | Select-Object Nom, Description, Cree, Integre) }
function Refresh-History {
  $state.History = @(Get-PLHistory)
  $rows = @($state.History | ForEach-Object { [pscustomobject]@{ Date = $_.Date; Action = $_.Action; Detail = $_.Detail; Annulable = [bool]$_.Restaurable } })
  [array]::Reverse($rows)
  Set-Grid $ui.GridHist $rows
}

# ---- evenements

$ui.BtnDiag.Add_Click({ Start-Background 'Diagnostic' { Invoke-PLDiagnostic } @() { param($d) Show-Diag $d } })

$ui.GridReco.Add_SelectionChanged({ $r = $ui.GridReco.SelectedItem; $ui.BtnApplyReco.IsEnabled = [bool]($r -and $r.Applicable) })
$ui.BtnApplyReco.Add_Click({
  $r = $ui.GridReco.SelectedItem; if (-not $r) { return }
  if (-not (Ask "Appliquer : $($r.Titre) ?`n`n$($r.Action)`n`nL'etat actuel est sauvegarde et l'operation pourra etre annulee dans Historique.")) { return }
  try { Invoke-PLReco -Id $r.Id -Game $state.Game; Refresh-History; Set-Status "Applique : $($r.Titre). Relance le diagnostic pour voir l'effet." } catch { Show-Error $_.Exception.Message }
})

$ui.TxtFilter.Add_TextChanged({
  if (-not $state.Diag) { return }
  $f = $ui.TxtFilter.Text
  Set-Grid $ui.GridMods @($state.Diag.Mods.Liste | Where-Object { -not $f -or $_.Nom -like "*$f*" -or $_.Fichier -like "*$f*" })
})

$ui.BtnMeasure.Add_Click({
  if (-not (Get-Process -Name eurotrucks2 -ErrorAction SilentlyContinue)) { Show-Error 'Lance ETS2 et commence a rouler sur ton parcours de test avant de mesurer.'; return }
  $sec = [int](($ui.InDur.SelectedItem.Content) -replace '\D', '')
  $zone = $ui.InZone.SelectedItem.Content
  $ui.Tabs.SelectedIndex = 4
  Start-Background "Mesure de $sec s (roule normalement)" { param($s, $l, $z, $p) Start-PLCapture -Seconds $s -Label $l -Zone $z -Profil $p } @($sec, $ui.InLabel.Text, $zone, $ui.InProfil.Text) { param($run) Refresh-Runs; Set-Status "Mesure '$($run.Libelle)' : $($run.Stats.FpsMoyen) images/s en moyenne, $($run.Stats.Fps1PctBas) pour les 1 % les plus lents, $($run.Stats.SaccadesParMin) saccades/min." }
})

$ui.BtnImport.Add_Click({
  $dlg = New-Object Microsoft.Win32.OpenFileDialog; $dlg.Filter = 'CSV PresentMon (*.csv)|*.csv'
  if (-not $dlg.ShowDialog()) { return }
  try {
    $st = Get-PLFrameStats -CsvPath $dlg.FileName
    $id = Get-Date -Format 'yyyyMMdd_HHmmss'
    $dir = Join-Path (Join-Path (Get-PLDataRoot) 'mesures') $id; New-Item -ItemType Directory -Path $dir | Out-Null
    Copy-Item -LiteralPath $dlg.FileName -Destination (Join-Path $dir 'presentmon.csv')
    [pscustomobject]@{ Id = $id; Date = (Get-Date).ToString('dd/MM/yyyy HH:mm'); Libelle = $ui.InLabel.Text + ' (importe)'; Zone = $ui.InZone.SelectedItem.Content; Profil = $ui.InProfil.Text; Machine = $env:COMPUTERNAME; Stats = $st; Charge = [pscustomobject]@{} } |
      ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $dir 'mesure.json') -Encoding UTF8
    Refresh-Runs
  } catch { Show-Error $_.Exception.Message }
})

$ui.GridRuns.Add_SelectionChanged({ $ui.BtnCompare.IsEnabled = ($ui.GridRuns.SelectedItems.Count -eq 2) })
$ui.BtnCompare.Add_Click({
  $ids = @($ui.GridRuns.SelectedItems | ForEach-Object Id | Sort-Object)
  $runs = @(Get-PLRuns)
  $a = $runs | Where-Object Id -eq $ids[0]; $b = $runs | Where-Object Id -eq $ids[1]
  Set-Grid $ui.GridCompare (Compare-PLRuns -Avant $a -Apres $b)
})

$ui.GridProfiles.Add_SelectionChanged({
  $i = $ui.GridProfiles.SelectedIndex
  $ui.BtnApplyProfile.IsEnabled = ($i -ge 0)
  if ($i -ge 0 -and $state.Game.DocsDir) { Set-Grid $ui.GridDiff (Get-PLProfileDiff -Profile $state.Profiles[$i] -Game $state.Game) }
})
$ui.BtnSaveProfile.Add_Click({
  $name = [Microsoft.VisualBasic.Interaction]::InputBox('Nom du profil (par exemple : Ultra TSC) :', 'Enregistrer un profil', 'Ultra TSC')
  if (-not $name) { return }
  try { Save-PLProfile -Name $name -Game $state.Game | Out-Null; Refresh-Profiles; Refresh-History } catch { Show-Error $_.Exception.Message }
})
$ui.BtnApplyProfile.Add_Click({
  $p = $state.Profiles[$ui.GridProfiles.SelectedIndex]
  $diff = @(Get-PLProfileDiff -Profile $p -Game $state.Game)
  if (-not $diff.Count) { Set-Status "Le profil '$($p.Nom)' est deja en place."; return }
  $txt = ($diff | ForEach-Object { "$($_.Variable) : $($_.Actuel) -> $($_.Nouveau)" }) -join "`n"
  if (-not (Ask "Appliquer le profil '$($p.Nom)' ?`n`n$txt`n`nLes fichiers actuels sont sauvegardes avant l'ecriture.")) { return }
  try { $r = Set-PLProfile -Profile $p -Game $state.Game; Refresh-History; Set-Grid $ui.GridDiff @(); $ui.InProfil.Text = $p.Nom; Set-Status "Profil '$($p.Nom)' applique ($($r.Change) reglage(s)). Sauvegarde $($r.Sauvegarde)." } catch { Show-Error $_.Exception.Message }
})

$ui.GridHist.Add_SelectionChanged({ $r = $ui.GridHist.SelectedItem; $ui.BtnUndo.IsEnabled = [bool]($r -and $r.Annulable) })
$ui.BtnUndo.Add_Click({
  $sel = $ui.GridHist.SelectedItem
  $e = $state.History | Where-Object { $_.Date -eq $sel.Date -and $_.Action -eq $sel.Action -and $_.Detail -eq $sel.Detail } | Select-Object -First 1
  if (-not (Ask "Annuler : $($e.Action) ($($e.Detail)) ?")) { return }
  try { Undo-PLHistoryEntry -Entry $e -Game $state.Game; Refresh-History; Set-Status 'Operation annulee.' } catch { Show-Error $_.Exception.Message }
})
$ui.BtnOpenData.Add_Click({ Start-Process explorer.exe (Get-PLDataRoot) })

$ui.BtnReport.Add_Click({
  try {
    $p = Export-PLReport -Diag $state.Diag -Runs @(Get-PLRuns) -History @(Get-PLHistory)
    $ui.TxtReport.Text = "Rapport enregistre : $p"
    Start-Process $p
  } catch { Show-Error $_.Exception.Message }
})

$ui.TxtMachine.Text = "$env:COMPUTERNAME - version $AppVersion"
Refresh-Runs; Refresh-Profiles; Refresh-History
if (-not $state.Game.GameDir) { Set-Status 'ETS2 introuvable dans les bibliotheques Steam : le diagnostic sera partiel.' }
[void]$win.ShowDialog()
$timer.Stop()
