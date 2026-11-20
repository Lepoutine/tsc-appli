# TSC GPS - Couleurs de carte « site » (palette du site TSC Driver Ecosystem)
# Genere TSC_GPS_Couleurs.scs : copie de def/map_data.sii de la carte source (jeu de base def.scs, ou mod de carte),
# seules les couleurs changent. Lecture seule de la source. Methode identique a l'appli TSC (Gps-ColPatch, lecteur HashFS).
# usage : powershell -ExecutionPolicy Bypass -File couleurs_site_2011.ps1 -Source <def.scs ou mod de carte> -Sortie <TSC_GPS_Couleurs.scs>
param([Parameter(Mandatory)][string]$Source, [Parameter(Mandatory)][string]$Sortie)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
$src = @'
using System; using System.IO; using System.IO.Compression; using System.Text; using System.Collections.Generic; using System.Threading; using System.Globalization;
// Lecture seule des archives HashFS du jeu (SCS# v1 et v2) : on lit un fichier precis, rien n'est jamais ecrit dans l'archive.
public static class TscScs {
  const ulong K0 = 0xc3a5c85c97cb3127UL, K1 = 0xb492b66fbe98f273UL, K2 = 0x9ae16a3b2f90404fUL, K3 = 0xc949d7c7509e6557UL, KM = 0x9ddfea08eb382d69UL;
  static ulong F64(byte[] s, int i) { return BitConverter.ToUInt64(s, i); }
  static ulong F32(byte[] s, int i) { return BitConverter.ToUInt32(s, i); }
  static ulong Rot(ulong v, int s) { return s == 0 ? v : (v >> s) | (v << (64 - s)); }
  static ulong Sm(ulong v) { return v ^ (v >> 47); }
  static ulong H16(ulong u, ulong v) { ulong a = (u ^ v) * KM; a ^= a >> 47; ulong b = (v ^ a) * KM; b ^= b >> 47; return b * KM; }
  static ulong H0to16(byte[] s) {
    int n = s.Length;
    if (n > 8) { ulong a = F64(s, 0), b = F64(s, n - 8); return H16(a, Rot(b + (ulong)n, n)) ^ b; }
    if (n >= 4) { ulong a = F32(s, 0); return H16((ulong)n + (a << 3), F32(s, n - 4)); }
    if (n > 0) { uint a = s[0], b = s[n >> 1], c = s[n - 1]; uint y = a + (b << 8), z = (uint)n + (c << 2); return Sm(((ulong)y * K2) ^ ((ulong)z * K3)) * K2; }
    return K2;
  }
  static ulong H17to32(byte[] s) {
    int n = s.Length; ulong a = F64(s, 0) * K1, b = F64(s, 8), c = F64(s, n - 8) * K2, d = F64(s, n - 16) * K0;
    return H16(Rot(a - b, 43) + Rot(c, 30) + d, a + Rot(b ^ K3, 20) - c + (ulong)n);
  }
  static void Weak(ulong w, ulong x, ulong y, ulong z, ref ulong a, ref ulong b) {
    a += w; b = Rot(b + a + z, 21); ulong c = a; a += x; a += y; b += Rot(a, 44); a += z; b += c;
  }
  static void WeakS(byte[] s, int i, ref ulong a, ref ulong b) { Weak(F64(s, i), F64(s, i + 8), F64(s, i + 16), F64(s, i + 24), ref a, ref b); }
  static ulong H33to64(byte[] s) {
    int n = s.Length; ulong z = F64(s, 24), a = F64(s, 0) + ((ulong)n + F64(s, n - 16)) * K0, b = Rot(a + z, 52), c = Rot(a, 37);
    a += F64(s, 8); c += Rot(a, 7); a += F64(s, 16); ulong vf = a + z, vs = b + Rot(a, 31) + c;
    a = F64(s, 16) + F64(s, n - 32); z = F64(s, n - 8); b = Rot(a + z, 52); c = Rot(a, 37); a += F64(s, n - 24); c += Rot(a, 7); a += F64(s, n - 16);
    ulong wf = a + z, ws = b + Rot(a, 31) + c, r = Sm((vf + ws) * K2 + (wf + vs) * K0);
    return Sm(r * K0 + vs) * K2;
  }
  public static ulong City64(byte[] s) {
    int n = s.Length;
    if (n <= 16) return H0to16(s);
    if (n <= 32) return H17to32(s);
    if (n <= 64) return H33to64(s);
    ulong x = F64(s, n - 40), y = F64(s, n - 16) + F64(s, n - 56), z = H16(F64(s, n - 48) + (ulong)n, F64(s, n - 24));
    ulong v0 = (ulong)n, v1 = z; WeakS(s, n - 64, ref v0, ref v1);
    ulong w0 = y + K1, w1 = x; WeakS(s, n - 32, ref w0, ref w1);
    x = x * K1 + F64(s, 0);
    int len = (n - 1) & ~63, i = 0;
    do {
      x = Rot(x + y + v0 + F64(s, i + 8), 37) * K1; y = Rot(y + v1 + F64(s, i + 48), 42) * K1;
      x ^= w1; y += v0 + F64(s, i + 40); z = Rot(z + w0, 33) * K1;
      ulong a = v1 * K1, b = x + w0; WeakS(s, i, ref a, ref b); v0 = a; v1 = b;
      a = z + w1; b = y + F64(s, i + 16); WeakS(s, i + 32, ref a, ref b); w0 = a; w1 = b;
      ulong t = z; z = x; x = t; i += 64; len -= 64;
    } while (len != 0);
    return H16(H16(v0, w0) + Sm(y) * K1 + z, H16(v1, w1) + x);
  }
  public static ulong Hash(string path) { return City64(Encoding.UTF8.GetBytes(path.Trim('/'))); }
  static byte[] Inflate(byte[] d) {
    using (var ms = new MemoryStream(d, 2, d.Length - 2)) using (var ds = new DeflateStream(ms, CompressionMode.Decompress)) using (var o = new MemoryStream()) { ds.CopyTo(o); return o.ToArray(); }
  }
  static byte[] ReadAt(FileStream fs, long off, int len) {
    var b = new byte[len]; fs.Seek(off, SeekOrigin.Begin); int r = 0;
    while (r < len) { int k = fs.Read(b, r, len - r); if (k <= 0) throw new EndOfStreamException(); r += k; }
    return b;
  }
  // "SCS#" + version (1 ou 2), 0 si ce n'est pas une archive HashFS
  public static int Version(string archive) {
    using (var fs = new FileStream(archive, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete)) {
      if (fs.Length < 16) return 0; var h = ReadAt(fs, 0, 8);
      if (h[0] != 'S' || h[1] != 'C' || h[2] != 'S' || h[3] != '#') return 0; return BitConverter.ToUInt16(h, 4);
    }
  }
  // contenu d'un fichier de l'archive (null s'il n'y est pas)
  public static byte[] Read(string archive, string path) {
    ulong want = Hash(path);
    using (var fs = new FileStream(archive, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete)) {
      var h = ReadAt(fs, 0, 64);
      if (h[0] != 'S' || h[1] != 'C' || h[2] != 'S' || h[3] != '#') return null;
      int ver = BitConverter.ToUInt16(h, 4);
      if (ver == 1) {
        uint n = BitConverter.ToUInt32(h, 12), start = BitConverter.ToUInt32(h, 16);
        if (n > 5000000) return null;
        var t = ReadAt(fs, start, (int)n * 32);
        for (int i = 0; i < n; i++) {
          if (BitConverter.ToUInt64(t, i * 32) != want) continue;
          long off = (long)BitConverter.ToUInt64(t, i * 32 + 8); uint fl = BitConverter.ToUInt32(t, i * 32 + 16);
          int size = (int)BitConverter.ToUInt32(t, i * 32 + 24), zs = (int)BitConverter.ToUInt32(t, i * 32 + 28);
          if ((fl & 1) != 0) return null;                                   // dossier
          var raw = ReadAt(fs, off, (fl & 2) != 0 ? zs : size);
          return (fl & 2) != 0 ? Inflate(raw) : raw;
        }
        return null;
      }
      if (ver == 2) {
        uint ec = BitConverter.ToUInt32(h, 12), ecs = BitConverter.ToUInt32(h, 16), mcs = BitConverter.ToUInt32(h, 24);
        long eo = (long)BitConverter.ToUInt64(h, 28), mo = (long)BitConverter.ToUInt64(h, 36);
        var et = Inflate(ReadAt(fs, eo, (int)ecs));
        int mi = -1;
        for (int i = 0; i < ec && (i + 1) * 16 <= et.Length; i++) {
          if (BitConverter.ToUInt64(et, i * 16) != want) continue;
          if ((BitConverter.ToUInt16(et, i * 16 + 14) & 1) != 0) return null;   // dossier
          mi = (int)BitConverter.ToUInt32(et, i * 16 + 8); break;
        }
        if (mi < 0) return null;
        var mt = Inflate(ReadAt(fs, mo, (int)mcs));
        uint hd = BitConverter.ToUInt32(mt, mi * 4); int di = (int)(hd & 0xFFFFFF); int ty = (int)(hd >> 24);
        if ((ty & 0x80) == 0) return null;                                   // pas un fichier simple (texture...)
        uint cs = BitConverter.ToUInt32(mt, di * 4), sz = BitConverter.ToUInt32(mt, di * 4 + 4); ulong ob = BitConverter.ToUInt32(mt, di * 4 + 12);
        int comp = (int)(cs >> 28); int csz = (int)(cs & 0xFFFFFFF), usz = (int)(sz & 0xFFFFFFF);
        var raw2 = ReadAt(fs, (long)(ob * 16), comp != 0 ? csz : usz);
        if (comp == 0) return raw2;
        if (comp == 1) return Inflate(raw2);
        return null;                                                          // autre compression (textures) : non gere
      }
      return null;
    }
  }
  public static string ReadText(string archive, string path) { var b = Read(archive, path); return b == null ? null : Encoding.UTF8.GetString(b); }
}

'@
Add-Type -TypeDefinition $src
function Lire([string]$p, [string]$inner) {
  $fs = [IO.File]::Open($p, 'Open', 'Read', 'ReadWrite'); $h = New-Object byte[] 4; [void]$fs.Read($h, 0, 4); $fs.Close()
  if ($h[0] -eq 0x50 -and $h[1] -eq 0x4B) {
    $z = [IO.Compression.ZipFile]::OpenRead($p)
    try { foreach ($e in $z.Entries) { if ((($e.FullName -replace '\\', '/').TrimStart('/')) -ieq $inner) { $r = New-Object IO.StreamReader($e.Open()); try { return $r.ReadToEnd() } finally { $r.Close() } } } } finally { $z.Dispose() }
    return $null }
  if ($h[0] -eq 0x53 -and $h[1] -eq 0x43 -and $h[2] -eq 0x53 -and $h[3] -eq 0x23) { return [TscScs]::ReadText($p, $inner) }
  return $null
}
function Abgr([string]$h) { $h = $h.TrimStart('#'); return '0x' + ('FF' + $h.Substring(4, 2) + $h.Substring(2, 2) + $h.Substring(0, 2)).ToUpper() }
# palette du site : fond #111114, panneaux #1a1a1f / #222228, lignes #303037, texte #f2eee9, rouge #ef625d, or #d8b77d, vert #8cc5a3
$P = [ordered]@{
  road_color = '#3A3A42'; road_discovered_color = '#5A5860'; world_road_color = '#46454D'; world_road_discovered_color = '#8E8B92'
  prefab_color = '#3A3A42'; prefab_obstacle_color = '#1A1A1F'; prefab_grass_color = '#17211B'
  prefab_discovered_color = '#5A5860'; prefab_obstacle_discovered_color = '#222228'; prefab_grass_discovered_color = '#1F2E25'
  outline_color = '#111114'; navigation_color = '#EF625D'; navigation_highlight_color = '#D8B77D'; navigation_fade_color = '#7A302D'; navigation_arrow_color = '#F2EEE9'
}
$A = [ordered]@{ Road = @('#3A3A42', '#5A5860'); Light = @('#3A3A42', '#5A5860'); Dark = @('#1A1A1F', '#222228'); Green = @('#17211B', '#1F2E25') }
$t = Lire $Source 'def/map_data.sii'; if (-not $t) { throw "def/map_data.sii introuvable dans $Source" }
$t = [regex]::Replace($t, '(?m)^\s*@include\s+"([^"]+)"\s*$', { param($m) $n = $m.Groups[1].Value.TrimStart('/'); if ($n -notmatch '/') { $n = 'def/' + $n }; $c = Lire $Source $n; if ($c) { $c } else { $m.Value } })
$n = 0
foreach ($k in $P.Keys) { $v = Abgr $P[$k]; $rx = [regex]('(?m)^(\s*' + $k + '\s*:\s*)0x[0-9A-Fa-f]{8}'); $n += $rx.Matches($t).Count; $t = $rx.Replace($t, { param($m) $m.Groups[1].Value + $v }) }
foreach ($a in $A.Keys) {
  $u = Abgr $A[$a][0]; $d = Abgr $A[$a][1]
  $rx = [regex]('(map_area_color_name\[\]:\s*"' + $a + '"\s*\r?\n\s*map_area_color\[\]:\s*)0x[0-9A-Fa-f]{8}(\s*\r?\n\s*map_area_discovered_color\[\]:\s*)0x[0-9A-Fa-f]{8}')
  $n += $rx.Matches($t).Count; $t = $rx.Replace($t, { param($m) $m.Groups[1].Value + $u + $m.Groups[2].Value + $d })
}
if ($n -lt 3) { throw "map_data non reconnu ($n couleurs)" }
$man = "SiiNunit`r`n{`r`nmod_package : .package_name`r`n{`r`n`tpackage_version: `"1.2`"`r`n`tdisplay_name: `"TSC GPS - Couleurs de carte`"`r`n`tauthor: `"Truck So Clean France`"`r`n`tcategory[]: `"ui`"`r`n`tdescription_file: `"description.txt`"`r`n`tcompatible_versions[]: `"1.62.*`"`r`n}`r`n}`r`n"
$desc = "Truck So Clean France - Couleurs de carte du GPS aux couleurs du site TSC Driver Ecosystem (itineraire rouge, surbrillance or).`r`nCopie du fichier de carte : seules les couleurs changent (limites et zoom conserves).`r`nA placer AU-DESSUS du mod de carte dans le gestionnaire de mods.`r`n"
$tmp = $Sortie + '.tmp'; if (Test-Path -LiteralPath $tmp) { Remove-Item -LiteralPath $tmp -Force }
$z = [IO.Compression.ZipFile]::Open($tmp, 'Create'); $u8 = New-Object Text.UTF8Encoding($false)
try { foreach ($kv in ([ordered]@{ 'manifest.sii' = $man; 'description.txt' = $desc; 'def/map_data.sii' = $t; 'tsc_source.txt' = ('site|' + [IO.Path]::GetFileName($Source) + '|' + (Get-Item -LiteralPath $Source).Length) }).GetEnumerator()) { $e = $z.CreateEntry($kv.Key, 'Optimal'); $w = New-Object IO.StreamWriter($e.Open(), $u8); $w.Write($kv.Value); $w.Close() } } finally { $z.Dispose() }
Move-Item -LiteralPath $tmp -Destination $Sortie -Force
"OK : $n couleurs remplacees -> $Sortie ; sha256 " + (Get-FileHash -LiteralPath $Sortie -Algorithm SHA256).Hash
