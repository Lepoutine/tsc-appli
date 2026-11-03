// (c) 2026 Truck So Clean France. Tous droits reserves. TSC Sound Forge, by Truck So Clean France.
// Analyseur ETS2 : lit (en LECTURE SEULE, rien n'est jamais ecrit dans le jeu ni dans un mod) les archives du jeu et des mods,
// repere les camions, moteurs, definitions son (.sii/.sui), .soundref, banques FMOD (.bank) et .bank.guids, puis calcule
// la compatibilite et les conflits. Les fichiers chiffres ou proteges sont signales, jamais forces.
// C# 5 (Windows PowerShell 5.1 / Add-Type). Formats : dossier, HashFS v1, HashFS v2, zip.
using System; using System.IO; using System.IO.Compression; using System.Text; using System.Collections.Generic; using System.Globalization; using System.Text.RegularExpressions;

namespace TscSoundForge {

public static class SfHash {
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
  static void Weak(ulong w, ulong x, ulong y, ulong z, ref ulong a, ref ulong b) { a += w; b = Rot(b + a + z, 21); ulong c = a; a += x; a += y; b += Rot(a, 44); a += z; b += c; }
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
}

// Archive en lecture seule : 0 dossier, 1 HashFS v1, 2 HashFS v2, 3 zip
public class SfArchive : IDisposable {
  FileStream fs; public int Kind; string root;
  Dictionary<ulong, List<long[]>> v1;
  byte[] et, mt; Dictionary<ulong, List<int>> v2;
  Dictionary<string, long[]> zip; List<string> zipDirs;
  public bool ZipChiffre;                                   // au moins une entree zip chiffree (mod protege)
  public static SfArchive Open(string p) {
    var a = new SfArchive();
    if (Directory.Exists(p)) { a.Kind = 0; a.root = p; return a; }
    a.fs = new FileStream(p, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete);
    try {
      var h = a.At(0, (int)Math.Min(64, a.fs.Length));
      if (h.Length >= 6 && h[0] == 'S' && h[1] == 'C' && h[2] == 'S' && h[3] == '#') {
        int ver = BitConverter.ToUInt16(h, 4);
        if (ver == 1) { a.Kind = 1; a.LoadV1(h); return a; }
        if (ver == 2) { a.Kind = 2; a.LoadV2(h); return a; }
        throw new InvalidDataException("HashFS version " + ver + " inconnue");
      } else if (h.Length >= 4 && h[0] == 'P' && h[1] == 'K') { a.Kind = 3; a.LoadZip(); return a; }
    } catch { a.Dispose(); throw; }
    a.Dispose(); throw new InvalidDataException("format d'archive non reconnu");
  }
  public void Dispose() { if (fs != null) { fs.Dispose(); fs = null; } }
  byte[] At(long off, int len) {
    if (len < 0 || off < 0 || off + len > fs.Length) throw new InvalidDataException("lecture hors de l'archive");
    var b = new byte[len]; fs.Seek(off, SeekOrigin.Begin); int r = 0;
    while (r < len) { int k = fs.Read(b, r, len - r); if (k <= 0) throw new EndOfStreamException(); r += k; }
    return b;
  }
  static byte[] Zlib(byte[] d) {
    using (var ms = new MemoryStream(d, 2, d.Length - 2)) using (var ds = new DeflateStream(ms, CompressionMode.Decompress)) using (var o = new MemoryStream()) { ds.CopyTo(o); return o.ToArray(); }
  }
  static byte[] Raw(byte[] d) {
    using (var ms = new MemoryStream(d)) using (var ds = new DeflateStream(ms, CompressionMode.Decompress)) using (var o = new MemoryStream()) { ds.CopyTo(o); return o.ToArray(); }
  }
  void LoadV1(byte[] h) {
    uint n = BitConverter.ToUInt32(h, 12), start = BitConverter.ToUInt32(h, 16);
    if (n > 5000000) throw new InvalidDataException("table HashFS v1 invalide");
    var t = At(start, (int)n * 32); v1 = new Dictionary<ulong, List<long[]>>();
    for (int i = 0; i < n; i++) {
      ulong hs = BitConverter.ToUInt64(t, i * 32); List<long[]> l;
      if (!v1.TryGetValue(hs, out l)) v1[hs] = l = new List<long[]>();
      l.Add(new long[] { (long)BitConverter.ToUInt64(t, i * 32 + 8), BitConverter.ToUInt32(t, i * 32 + 16), BitConverter.ToUInt32(t, i * 32 + 24), BitConverter.ToUInt32(t, i * 32 + 28) });
    }
  }
  void LoadV2(byte[] h) {
    uint ec = BitConverter.ToUInt32(h, 12), ecs = BitConverter.ToUInt32(h, 16), mcs = BitConverter.ToUInt32(h, 24);
    long eo = (long)BitConverter.ToUInt64(h, 28), mo = (long)BitConverter.ToUInt64(h, 36);
    et = Zlib(At(eo, (int)ecs)); mt = Zlib(At(mo, (int)mcs)); v2 = new Dictionary<ulong, List<int>>();
    for (int i = 0; i < ec && (i + 1) * 16 <= et.Length; i++) {
      ulong hs = BitConverter.ToUInt64(et, i * 16); List<int> l;
      if (!v2.TryGetValue(hs, out l)) v2[hs] = l = new List<int>(); l.Add(i);
    }
  }
  void LoadZip() {
    long L = fs.Length; int tail = (int)Math.Min(L, 65557); var b = At(L - tail, tail); int e = -1;
    for (int i = tail - 22; i >= 0; i--) if (b[i] == 0x50 && b[i + 1] == 0x4B && b[i + 2] == 5 && b[i + 3] == 6) { e = i; break; }
    if (e < 0) throw new InvalidDataException("zip sans repertoire central");
    long cdo = BitConverter.ToUInt32(b, e + 16); int cds = (int)BitConverter.ToUInt32(b, e + 12); 
    var cd = At(cdo, cds); zip = new Dictionary<string, long[]>(); var dirs = new HashSet<string>(); int p = 0;
    for (int k = 0; k < 1000000 && p + 46 <= cd.Length; k++) {
      if (BitConverter.ToUInt32(cd, p) != 0x02014b50) break;
      int flags = BitConverter.ToUInt16(cd, p + 8), meth = BitConverter.ToUInt16(cd, p + 10); long cs = BitConverter.ToUInt32(cd, p + 20), us = BitConverter.ToUInt32(cd, p + 24);
      int nl = BitConverter.ToUInt16(cd, p + 28), xl = BitConverter.ToUInt16(cd, p + 30), cl = BitConverter.ToUInt16(cd, p + 32); long lho = BitConverter.ToUInt32(cd, p + 42);
      string name = Encoding.UTF8.GetString(cd, p + 46, nl).Replace('\\', '/').TrimStart('/').ToLowerInvariant();
      if ((flags & 1) != 0) ZipChiffre = true;
      if (name.EndsWith("/")) { dirs.Add(name.TrimEnd('/')); }
      else if (!zip.ContainsKey(name)) {
        zip[name] = new long[] { lho, meth, cs, us, flags };
        int s = name.LastIndexOf('/'); while (s > 0) { dirs.Add(name.Substring(0, s)); s = name.LastIndexOf('/', s - 1); }
      }
      p += 46 + nl + xl + cl;
    }
    zipDirs = new List<string>(dirs);
  }
  // noms des fichiers (dirs=false) ou sous-dossiers (dirs=true) d'un dossier
  public List<string> List(string dir, bool dirs) {
    dir = dir.Trim('/'); var o = new List<string>();
    if (Kind == 0) {
      var d = dir.Length == 0 ? root : Path.Combine(root, dir.Replace('/', Path.DirectorySeparatorChar));
      if (Directory.Exists(d)) foreach (var f in (dirs ? Directory.GetDirectories(d) : Directory.GetFiles(d))) o.Add(Path.GetFileName(f));
      return o;
    }
    if (Kind == 3) {
      string pre = dir.Length == 0 ? "" : dir.ToLowerInvariant() + "/";
      IEnumerable<string> src = dirs ? (IEnumerable<string>)zipDirs : zip.Keys;
      foreach (var k in src) if (k.StartsWith(pre, StringComparison.Ordinal) && k.Length > pre.Length && k.IndexOf('/', pre.Length) < 0) o.Add(k.Substring(pre.Length));
      return o;
    }
    ulong hs = SfHash.Hash(dir);
    if (Kind == 1) {
      List<long[]> l; if (!v1.TryGetValue(hs, out l)) return o;
      foreach (var x in l) {
        if ((x[1] & 1) == 0) continue; var raw = At(x[0], (int)((x[1] & 2) != 0 ? x[3] : x[2])); var d = (x[1] & 2) != 0 ? Zlib(raw) : raw;
        foreach (var n in Encoding.UTF8.GetString(d).Split('\n')) { var s = n.Trim('\r'); if (s.Length == 0) continue; bool isd = s[0] == '*'; if (isd == dirs) o.Add(isd ? s.Substring(1) : s); }
      }
      return o;
    }
    List<int> ent; if (!v2.TryGetValue(hs, out ent)) return o;
    foreach (int i in ent) {
      var d = V2Data(i, true); if (d == null || d.Length < 4) continue;
      int c = (int)BitConverter.ToUInt32(d, 0), q = 4 + c; if (c < 0 || 4 + c > d.Length) continue;
      for (int j = 0; j < c; j++) {
        int len = d[4 + j]; if (q + len > d.Length) break; var s = Encoding.UTF8.GetString(d, q, len); q += len;
        if (s.Length == 0) continue; bool isd = s[0] == '/'; if (isd == dirs) o.Add(isd ? s.Substring(1) : s);
      }
    }
    return o;
  }
  byte[] V2Data(int i, bool dirWanted) {
    int mi = (int)BitConverter.ToUInt32(et, i * 16 + 8), mc = BitConverter.ToUInt16(et, i * 16 + 12);
    for (int k = 0; k < Math.Max(1, mc); k++) {
      uint hd = BitConverter.ToUInt32(mt, (mi + k) * 4); int di = (int)(hd & 0xFFFFFF), ty = (int)(hd >> 24);
      if (ty != (dirWanted ? 0x81 : 0x80)) continue;
      uint cs = BitConverter.ToUInt32(mt, di * 4), sz = BitConverter.ToUInt32(mt, di * 4 + 4); ulong ob = BitConverter.ToUInt32(mt, di * 4 + 12);
      int comp = (int)(cs >> 28), csz = (int)(cs & 0xFFFFFFF), usz = (int)(sz & 0xFFFFFFF);
      var raw = At((long)(ob * 16), comp != 0 ? csz : usz);
      if (comp == 0) return raw; if (comp == 1) return Zlib(raw); return null;
    }
    return null;
  }
  public byte[] Read(string path) {
    path = path.Trim('/');
    if (Kind == 0) { var f = Path.Combine(root, path.Replace('/', Path.DirectorySeparatorChar)); return File.Exists(f) ? File.ReadAllBytes(f) : null; }
    if (Kind == 3) {
      long[] z; if (!zip.TryGetValue(path.ToLowerInvariant(), out z)) return null;
      if ((z[4] & 1) != 0) return null;                                    // entree chiffree : jamais forcee
      var lh = At(z[0], 30); int nl = BitConverter.ToUInt16(lh, 26), xl = BitConverter.ToUInt16(lh, 28);
      var raw = At(z[0] + 30 + nl + xl, (int)z[2]);
      if (z[1] == 0) return raw; if (z[1] == 8) return Raw(raw); return null;
    }
    ulong hs = SfHash.Hash(path);
    if (Kind == 1) {
      List<long[]> l; if (!v1.TryGetValue(hs, out l)) return null;
      foreach (var x in l) { if ((x[1] & 1) != 0) continue; var raw = At(x[0], (int)((x[1] & 2) != 0 ? x[3] : x[2])); return (x[1] & 2) != 0 ? Zlib(raw) : raw; }
      return null;
    }
    List<int> ent; if (!v2.TryGetValue(hs, out ent)) return null;
    foreach (int i in ent) { var d = V2Data(i, false); if (d != null) return d; }
    return null;
  }
  // lit seulement le debut d'un fichier (en-tete d'une banque)
  public byte[] ReadHead(string path, int n) {
    if (Kind == 0) {
      var f = Path.Combine(root, path.Trim('/').Replace('/', Path.DirectorySeparatorChar)); if (!File.Exists(f)) return null;
      using (var s = new FileStream(f, FileMode.Open, FileAccess.Read, FileShare.ReadWrite)) { var b = new byte[Math.Min(n, (int)Math.Min(int.MaxValue, s.Length))]; s.Read(b, 0, b.Length); return b; }
    }
    path = path.Trim('/');
    // fichier stocke sans compression (cas des banques FMOD) : on ne lit que l'en-tete, jamais toute la banque
    if (Kind == 3) {
      long[] z; if (!zip.TryGetValue(path.ToLowerInvariant(), out z) || (z[4] & 1) != 0) return null;
      if (z[1] == 0) { var lh = At(z[0], 30); int nl = BitConverter.ToUInt16(lh, 26), xl = BitConverter.ToUInt16(lh, 28); return At(z[0] + 30 + nl + xl, (int)Math.Min(n, z[2])); }
    } else if (Kind == 1) {
      List<long[]> l; if (v1.TryGetValue(SfHash.Hash(path), out l)) foreach (var x in l) { if ((x[1] & 1) != 0) continue; if ((x[1] & 2) == 0) return At(x[0], (int)Math.Min(n, x[2])); break; }
    } else if (Kind == 2) {
      List<int> ent; if (v2.TryGetValue(SfHash.Hash(path), out ent)) foreach (int i in ent) {
        int mi = (int)BitConverter.ToUInt32(et, i * 16 + 8), mc = BitConverter.ToUInt16(et, i * 16 + 12);
        for (int k = 0; k < Math.Max(1, mc); k++) {
          uint hd = BitConverter.ToUInt32(mt, (mi + k) * 4); int di = (int)(hd & 0xFFFFFF), ty = (int)(hd >> 24); if (ty != 0x80) continue;
          uint cs = BitConverter.ToUInt32(mt, di * 4), sz = BitConverter.ToUInt32(mt, di * 4 + 4); ulong ob = BitConverter.ToUInt32(mt, di * 4 + 12);
          if ((cs >> 28) == 0) return At((long)(ob * 16), (int)Math.Min(n, sz & 0xFFFFFFF));
        }
      }
    }
    var all = Read(path); if (all == null) return null; if (all.Length <= n) return all; var o = new byte[n]; Array.Copy(all, o, n); return o;
  }
}

// Resultat de l'analyse d'une source (archive du jeu ou mod), mis en cache en texte simple (une ligne par enregistrement)
public class SfSource {
  public string Id, Chemin, Role, Nom, Etat = "ok", Message = "", Cle = ""; public int Priorite; public bool Actif;
  public int Format;                                               // 0 dossier, 1 HashFS v1, 2 HashFS v2, 3 zip, -1 illisible
  public List<string[]> Fichiers = new List<string[]>();           // {chemin, nature, taille}
  public List<string[]> Unites = new List<string[]>();             // {chemin, type, nom, libelle}
  public List<string[]> Refs = new List<string[]>();               // {chemin, reference}
  public List<string[]> Includes = new List<string[]>();           // {chemin, include}
  public List<string[]> Evenements = new List<string[]>();         // {chemin .bank.guids, guid, chemin evenement/bus/...}
  public List<string[]> Banques = new List<string[]>();            // {chemin .bank, en-tete}
  public List<string> Camions = new List<string>();                // ids def/vehicle/truck/<id>

  static string Esc(string s) { return (s ?? "").Replace("\\", "\\\\").Replace("\t", "\\t").Replace("\n", "\\n").Replace("\r", ""); }
  static string Unesc(string s) {
    var b = new StringBuilder();
    for (int i = 0; i < s.Length; i++) { if (s[i] == '\\' && i + 1 < s.Length) { char c = s[++i]; b.Append(c == 't' ? '\t' : c == 'n' ? '\n' : c); } else b.Append(s[i]); }
    return b.ToString();
  }
  static void W(StringBuilder b, string tag, string[] v) { b.Append(tag); foreach (var x in v) { b.Append('\t'); b.Append(Esc(x)); } b.Append('\n'); }
  public string Serialiser() {
    var b = new StringBuilder(); W(b, "S", new string[] { Cle, Etat, Message, Format.ToString(CultureInfo.InvariantCulture) });
    foreach (var c in Camions) W(b, "C", new string[] { c });
    foreach (var x in Fichiers) W(b, "F", x); foreach (var x in Unites) W(b, "U", x); foreach (var x in Refs) W(b, "R", x);
    foreach (var x in Includes) W(b, "I", x); foreach (var x in Evenements) W(b, "E", x); foreach (var x in Banques) W(b, "B", x);
    return b.ToString();
  }
  public bool Charger(string texte, string cle) {
    var lignes = texte.Split('\n'); if (lignes.Length == 0) return false;
    foreach (var l in lignes) {
      if (l.Length == 0) continue; var p = l.Split('\t'); var v = new string[p.Length - 1]; for (int i = 1; i < p.Length; i++) v[i - 1] = Unesc(p[i]);
      switch (p[0]) {
        case "S": if (v.Length < 4 || v[0] != cle) return false; Etat = v[1]; Message = v[2]; Format = int.Parse(v[3], CultureInfo.InvariantCulture); break;
        case "C": Camions.Add(v[0]); break; case "F": Fichiers.Add(v); break; case "U": Unites.Add(v); break; case "R": Refs.Add(v); break;
        case "I": Includes.Add(v); break; case "E": Evenements.Add(v); break; case "B": Banques.Add(v); break;
      }
    }
    Cle = cle; return true;
  }
}

public static class SfAnalyse {
  public static volatile string Progression = "";
  public const int MaxTexte = 2 * 1024 * 1024;
  static readonly Regex RxUnite = new Regex(@"(?m)^[ \t]*([A-Za-z_][A-Za-z0-9_]*)[ \t]*:[ \t]*([A-Za-z0-9_.]+)[ \t]*\r?\n?[ \t]*\{", RegexOptions.Compiled);
  static readonly Regex RxRef = new Regex("\"([^\"\\r\\n]*?\\.(?:bank|soundref)(?:#[^\"\\r\\n]*)?)\"", RegexOptions.Compiled | RegexOptions.IgnoreCase);
  static readonly Regex RxInclude = new Regex("(?m)^[ \\t]*@include[ \\t]+\"([^\"]+)\"", RegexOptions.Compiled);
  static readonly Regex RxNom = new Regex("(?m)^[ \\t]*name[ \\t]*:[ \\t]*\"([^\"]*)\"", RegexOptions.Compiled);
  static readonly Regex RxGuid = new Regex(@"(?m)^\s*(\{[0-9a-fA-F-]{36}\})\s+(\S.*?)\s*$", RegexOptions.Compiled);

  public static string Nature(byte[] d) {
    if (d == null) return "absent";
    if (d.Length >= 4) {
      string m = Encoding.ASCII.GetString(d, 0, 4);
      if (m == "ScsC") return "chiffre";
      if (m == "BSII") return "binaire";
      if (d.Length >= 3 && d[0] == '3' && d[1] == 'n' && d[2] == 'K') return "brouille";
      if (m == "RIFF") return "riff";
    }
    return "texte";
  }
  static bool EstDefSon(string p) {
    string l = p.ToLowerInvariant();
    return l.EndsWith(".sii") || l.EndsWith(".sui") || l.EndsWith(".soundref");
  }

  // Parcourt une source et remplit le resultat (lecture seule)
  public static SfSource AnalyserSource(SfSource s) {
    SfArchive a = null;
    try { a = SfArchive.Open(s.Chemin); }
    catch (Exception e) { s.Etat = "illisible"; s.Format = -1; s.Message = "Archive non prise en charge (chiffree, protegee ou format inconnu) : " + e.Message; return s; }
    using (a) {
      s.Format = a.Kind;
      if (a.ZipChiffre) { s.Etat = "protege"; s.Message = "Le zip contient des fichiers chiffres : ils ne sont pas lus."; }
      try {
        // 1) camions : def/vehicle/truck/<id>/ (tous les fichiers de definitions, sur 4 niveaux)
        foreach (var id in a.List("def/vehicle/truck", true)) {
          int avant = s.Fichiers.Count;
          Parcourir(a, s, "def/vehicle/truck/" + id, 0, 4);
          if (s.Fichiers.Count > avant) s.Camions.Add(id);            // la source apporte un moteur ou un son a ce camion
        }
        // 2) sons : sound/ (banques, guids, soundref) et def/sound/
        Parcourir(a, s, "sound", 0, 8);
        Parcourir(a, s, "def/sound", 0, 4);
        // 3) fichiers .sii a la racine de def/vehicle/ qui touchent au son (rares, ex. sound_data globaux)
        foreach (var f in a.List("def/vehicle", false)) if (EstDefSon(f)) Lire(a, s, "def/vehicle/" + f);
      } catch (Exception e) {
        if (s.Etat == "ok") s.Etat = "partiel"; s.Message = (s.Message + " Lecture interrompue : " + e.Message).Trim();
      }
    }
    return s;
  }
  static void Parcourir(SfArchive a, SfSource s, string dir, int prof, int max) {
    Progression = s.Nom + " : " + dir;
    foreach (var f in a.List(dir, false)) {
      string p = dir + "/" + f, l = f.ToLowerInvariant();
      if (EstDefSon(l) || l.EndsWith(".bank") || l.EndsWith(".bank.guids") || l.EndsWith(".guids")) Lire(a, s, p);
    }
    if (prof >= max) return;
    foreach (var d in a.List(dir, true)) Parcourir(a, s, dir + "/" + d, prof + 1, max);
  }
  static void Lire(SfArchive a, SfSource s, string p) {
    string l = p.ToLowerInvariant();
    if (l.EndsWith(".bank")) {
      byte[] h = null; try { h = a.ReadHead(p, 64); } catch { }
      s.Fichiers.Add(new string[] { p, h == null ? "illisible" : Nature(h), h == null ? "-1" : "?" });
      s.Banques.Add(new string[] { p, EnteteBanque(h) });
      return;
    }
    byte[] d = null; try { d = a.Read(p); } catch { }
    string nat = d == null ? "illisible" : Nature(d), taille = d == null ? "-1" : d.Length.ToString(CultureInfo.InvariantCulture);
    bool nomSon = l.EndsWith(".sui") || l.EndsWith(".soundref") || l.EndsWith(".guids") || l.Contains("sound") || l.Contains("/engine/");
    if (d == null || nat != "texte" || d.Length > MaxTexte) { if (nomSon) s.Fichiers.Add(new string[] { p, nat, taille }); return; }   // illisible/chiffre : garde seulement si c'est un fichier son ou moteur
    string t = SansCommentaires(Encoding.UTF8.GetString(d));
    if (l.EndsWith(".guids")) {
      s.Fichiers.Add(new string[] { p, nat, taille });
      foreach (Match m in RxGuid.Matches(t)) s.Evenements.Add(new string[] { p, m.Groups[1].Value, m.Groups[2].Value });
      return;
    }
    var unites = new List<string[]>();
    foreach (Match m in RxUnite.Matches(t)) {
      string ty = m.Groups[1].Value; if (ty == "SiiNunit" || !UniteUtile(ty)) continue;
      string nom = ""; int fin = t.IndexOf('}', m.Index); if (fin > m.Index) { var n = RxNom.Match(t.Substring(m.Index, Math.Min(fin - m.Index, 20000))); if (n.Success) nom = n.Groups[1].Value; }
      unites.Add(new string[] { p, ty, m.Groups[2].Value, nom });
    }
    var refs = new List<string[]>(); var vus = new HashSet<string>(); string dossier = p.Contains("/") ? p.Substring(0, p.LastIndexOf('/')) : "";
    foreach (Match m in RxRef.Matches(t)) {
      string v = m.Groups[1].Value; int bar = v.LastIndexOf('|'); if (bar >= 0) v = v.Substring(bar + 1);   // entree .sui "nom|chemin"
      v = v.Trim(); if (v.Length == 0 || v.IndexOf('[') >= 0) continue;
      if (!v.StartsWith("/")) v = "/" + (dossier.Length > 0 ? dossier + "/" : "") + v;                   // chemin relatif au fichier
      if (vus.Add(v)) refs.Add(new string[] { p, v });
    }
    bool suiSon = l.EndsWith(".sui") && l.Substring(l.LastIndexOf('/') + 1).Contains("sound");
    if (unites.Count == 0 && refs.Count == 0 && !suiSon && !l.EndsWith(".soundref")) return;   // ni moteur ni son : ignore
    s.Fichiers.Add(new string[] { p, nat, taille }); s.Unites.AddRange(unites); s.Refs.AddRange(refs);
    foreach (Match m in RxInclude.Matches(t)) s.Includes.Add(new string[] { p, m.Groups[1].Value });
  }
  static bool UniteUtile(string ty) { return ty == "accessory_engine_data" || ty == "accessory_transmission_data" || ty.Contains("horn") || ty.Contains("sound"); }
  // retire les lignes de commentaire (# ou //) et les blocs /* */ : le texte d'aide des .sui ne doit pas compter comme reference
  public static string SansCommentaires(string t) {
    var b = new StringBuilder(t.Length); bool bloc = false;
    foreach (var brut in t.Split('\n')) {
      string l = brut;
      if (bloc) { int f = l.IndexOf("*/"); if (f < 0) continue; l = l.Substring(f + 2); bloc = false; }
      int o = l.IndexOf("/*"); if (o >= 0 && l.IndexOf('"') < 0) { int f = l.IndexOf("*/", o + 2); if (f < 0) { bloc = true; l = l.Substring(0, o); } else l = l.Substring(0, o) + l.Substring(f + 2); }
      string tr = l.TrimStart(); if (tr.StartsWith("#") || tr.StartsWith("//")) continue;
      b.Append(l).Append('\n');
    }
    return b.ToString();
  }
  // en-tete RIFF d'une banque FMOD : "RIFF <taille> FEV FMT <taille> <version> ..." (la version de format, jamais modifiee)
  public static string EnteteBanque(byte[] h) {
    if (h == null) return "illisible";
    if (h.Length < 12 || Encoding.ASCII.GetString(h, 0, 4) != "RIFF") return "pas une banque FMOD (en-tete " + (h.Length >= 4 ? Encoding.ASCII.GetString(h, 0, 4).Replace("\0", "") : "?") + ")";
    string forme = Encoding.ASCII.GetString(h, 8, 4);
    var b = new StringBuilder("RIFF " + forme.Trim());
    for (int i = 12; i + 8 <= h.Length; ) {
      string ck = Encoding.ASCII.GetString(h, i, 4); uint sz = BitConverter.ToUInt32(h, i + 4);
      if (ck == "FMT " && i + 12 <= h.Length) { b.Append(" format " + BitConverter.ToUInt32(h, i + 8).ToString(CultureInfo.InvariantCulture)); if (i + 16 <= h.Length) b.Append("." + BitConverter.ToUInt32(h, i + 12).ToString(CultureInfo.InvariantCulture)); break; }
      if (ck == "LIST") { i += 12; continue; }
      i += 8 + (int)sz + ((int)sz & 1);
    }
    return b.ToString();
  }

  // ---------- fusion : systeme de fichiers virtuel du jeu (la source la plus prioritaire gagne) ----------
  public class Entree { public string Chemin; public List<SfSource> Sources = new List<SfSource>(); public SfSource Gagnant; }

  public static string Json(string s) {
    if (s == null) return "null";
    var b = new StringBuilder("\"");
    foreach (char c in s) {
      if (c == '"') b.Append("\\\""); else if (c == '\\') b.Append("\\\\"); else if (c == '\n') b.Append("\\n"); else if (c == '\r') b.Append("\\r"); else if (c == '\t') b.Append("\\t");
      else if (c < 0x20) b.Append("\\u" + ((int)c).ToString("x4")); else b.Append(c);
    }
    return b.Append('"').ToString();
  }

  static string Norm(string p) { return p.Trim().Trim('/').ToLowerInvariant(); }

  // Fusionne les sources (deja triees : jeu puis mods actifs du moins au plus prioritaire, puis mods inactifs) et ecrit le JSON
  public static string Fusionner(List<SfSource> sources, string envJson) {
    var vfs = new Dictionary<string, Entree>();
    foreach (var s in sources) {
      if (s.Role == "inactif") continue;
      foreach (var f in s.Fichiers) {
        string k = Norm(f[0]); Entree e; if (!vfs.TryGetValue(k, out e)) vfs[k] = e = new Entree { Chemin = f[0] };
        e.Sources.Add(s); if (e.Gagnant == null || s.Priorite >= e.Gagnant.Priorite) e.Gagnant = s;
      }
    }
    // evenements connus par banque (d'apres le .bank.guids gagnant)
    var evts = new Dictionary<string, HashSet<string>>();
    foreach (var s in sources) foreach (var ev in s.Evenements) {
      string k = Norm(ev[0]); Entree e; if (!vfs.TryGetValue(k, out e) || e.Gagnant != s) continue;
      string banque = k.EndsWith(".bank.guids") ? k.Substring(0, k.Length - 6) : k;
      HashSet<string> h; if (!evts.TryGetValue(banque, out h)) evts[banque] = h = new HashSet<string>();
      h.Add(ev[2].Trim().ToLowerInvariant());
    }
    var J = new StringBuilder("{\n\"outil\": \"TSC Sound Forge - analyseur ETS2 (lecture seule)\",\n\"environnement\": " + envJson + ",\n");

    // sources
    J.Append("\"sources\": [\n"); bool first = true;
    foreach (var s in sources) {
      if (!first) J.Append(",\n"); first = false;
      J.Append("{\"id\":" + Json(s.Id) + ",\"nom\":" + Json(s.Nom) + ",\"chemin\":" + Json(s.Chemin) + ",\"role\":" + Json(s.Role) + ",\"priorite\":" + s.Priorite + ",\"format\":" + s.Format +
        ",\"etat\":" + Json(s.Etat) + ",\"message\":" + Json(s.Message) + ",\"camions\":" + s.Camions.Count + ",\"fichiers_son\":" + s.Fichiers.Count + ",\"banques\":" + s.Banques.Count + ",\"references\":" + s.Refs.Count +
        ",\"chiffres\":" + s.Fichiers.FindAll(x => x[1] == "chiffre" || x[1] == "brouille" || x[1] == "binaire").Count + "}");
    }
    J.Append("\n],\n");

    // camions (vue fusionnee)
    var camions = new SortedDictionary<string, List<SfSource>>(StringComparer.OrdinalIgnoreCase);
    foreach (var s in sources) foreach (var c in s.Camions) { List<SfSource> l; if (!camions.TryGetValue(c, out l)) camions[c] = l = new List<SfSource>(); l.Add(s); }
    int nIgnores = 0, nMoteurs = 0, nCompat = 0, nPartiel = 0, nNon = 0, nNonVerif = 0;
    J.Append("\"camions\": [\n"); first = true; int nCamions = 0;
    foreach (var kv in camions) {
      string id = kv.Key, pre = "def/vehicle/truck/" + id.ToLowerInvariant() + "/";
      bool jeu, actif = kv.Value.Exists(x => x.Role != "inactif");
      SfSource origine = null; int best = -1;                                   // la source qui apporte le plus de moteurs a ce camion
      foreach (var s in kv.Value) { if (s.Role == "inactif" && actif) continue; int nb = s.Unites.FindAll(u => u[1] == "accessory_engine_data" && u[0].ToLowerInvariant().StartsWith(pre)).Count + (s.Role == "jeu" ? 1 : 0); if (nb > best) { best = nb; origine = s; } }
      if (origine == null) origine = kv.Value[0];
      jeu = origine.Role == "jeu";
      var moteurs = new List<string>(); var sons = new List<string>(); var refs = new List<string[]>(); var chiffres = new List<string>(); var illisibles = new List<string>();
      var vusMot = new HashSet<string>();
      foreach (var s in kv.Value) {
        if (s.Role == "inactif" && actif) continue;                       // camion actif : les mods inactifs ne comptent pas
        foreach (var u in s.Unites) {
          if (!u[0].ToLowerInvariant().StartsWith(pre)) continue;
          Entree e; if (vfs.TryGetValue(Norm(u[0]), out e) && e.Gagnant != s) continue;     // remplace par une source plus prioritaire
          if (u[1] == "accessory_engine_data" && vusMot.Add(u[2])) moteurs.Add(u[2] + (u[3].Length > 0 ? " | " + u[3] : "") + " | " + u[0]);
        }
        foreach (var f in s.Fichiers) {
          if (!f[0].ToLowerInvariant().StartsWith(pre)) continue;
          Entree e; if (vfs.TryGetValue(Norm(f[0]), out e) && e.Gagnant != s) continue;
          if (f[1] == "chiffre" || f[1] == "brouille" || f[1] == "binaire") chiffres.Add(f[0] + " (" + f[1] + ", " + s.Nom + ")");
          if (f[1] == "illisible") illisibles.Add(f[0] + " (" + s.Nom + ")");
          if (f[0].ToLowerInvariant().Contains("sound")) sons.Add(f[0]);
        }
        foreach (var r in s.Refs) {
          if (!r[0].ToLowerInvariant().StartsWith(pre) || r[0].ToLowerInvariant().EndsWith(".soundref")) continue;   // les .soundref sont suivis par la chaine
          Entree e; if (vfs.TryGetValue(Norm(r[0]), out e) && e.Gagnant != s) continue;
          refs.Add(new string[] { r[0], r[1], s.Nom });
        }
      }
      bool structure = sons.Exists(x => { var q = x.ToLowerInvariant().Substring(pre.Length); return q.StartsWith("engine/") || q.StartsWith("cabin/") || q.StartsWith("chassis/") || q.StartsWith("interior/"); });
      if (moteurs.Count == 0 && !structure) { nIgnores++; continue; }   // dossier d'accessoires ou de sons d'un mod, pas un camion
      // verification de chaque reference son
      int ok = 0, manque = 0, nonverif = 0, accManque = 0; var details = new StringBuilder(); bool fd = true;
      foreach (var r in refs) {
        string etat, raison; Verifier(r[1], vfs, evts, sources, out etat, out raison);
        bool acc = r[0].ToLowerInvariant().Substring(pre.Length).StartsWith("accessory/");      // klaxons et accessoires optionnels
        if (etat == "ok") ok++; else if (acc) accManque++; else if (etat == "manquant") manque++; else nonverif++;
        if (!fd) details.Append(","); fd = false;
        details.Append("{\"fichier\":" + Json(r[0]) + ",\"reference\":" + Json(r[1]) + ",\"source\":" + Json(r[2]) + ",\"etat\":" + Json(etat) + ",\"raison\":" + Json(raison) + "}");
      }
      string compat, pourquoi;
      if (!actif) { compat = "non_verifie"; pourquoi = "Mod non actif dans le dernier profil charge : analyse donnee a titre indicatif."; }
      else if (chiffres.Count > 0 && moteurs.Count == 0) { compat = "non_pris_en_charge"; pourquoi = "Definitions chiffrees ou protegees : integration fiable impossible sans l'accord de l'auteur."; }
      else if (moteurs.Count == 0) { compat = "non_verifie"; pourquoi = "Aucun moteur trouve dans les definitions lisibles."; }
      else if (refs.Count == 0) { compat = "non_verifie"; pourquoi = "Moteurs trouves mais aucune reference son lisible dans le dossier du camion (sons peut-etre definis ailleurs)."; }
      else if (manque > 0) { compat = "partiel"; pourquoi = manque + " reference(s) son vers une banque ou un evenement introuvable."; }
      else if (nonverif > 0) { compat = "partiel"; pourquoi = nonverif + " reference(s) son non verifiable(s) (banque sans .bank.guids lisible)."; }
      else if (chiffres.Count > 0) { compat = "partiel"; pourquoi = "Certaines definitions sont chiffrees : " + chiffres.Count + " fichier(s)."; }
      else { compat = "compatible"; pourquoi = "Moteurs et references son trouves, banques et evenements presents (verification statique ; a confirmer en jeu)."; }
      if (accManque > 0) pourquoi += " " + accManque + " reference(s) d'accessoires optionnels (klaxons...) introuvable(s) : sans effet tant que l'accessoire n'est pas monte.";
      if (compat == "compatible") nCompat++; else if (compat == "partiel") nPartiel++; else if (compat == "non_pris_en_charge") nNon++; else nNonVerif++;
      nMoteurs += moteurs.Count; nCamions++;
      if (!first) J.Append(",\n"); first = false;
      J.Append("{\"id\":" + Json(id) + ",\"origine\":" + Json(jeu ? "jeu (" + origine.Nom + ")" : "mod (" + origine.Nom + ")") + ",\"actif\":" + (actif ? "true" : "false") +
        ",\"compatibilite\":" + Json(compat) + ",\"refs_ok\":" + ok + ",\"refs_manquantes\":" + manque + ",\"refs_non_verifiees\":" + nonverif + ",\"refs_accessoires_manquantes\":" + accManque + ",\"raison\":" + Json(pourquoi) + ",\"moteurs\":[" + string.Join(",", moteurs.ConvertAll(Json).ToArray()) + "]" +
        ",\"fichiers_son\":[" + string.Join(",", sons.ConvertAll(Json).ToArray()) + "],\"chiffres\":[" + string.Join(",", chiffres.ConvertAll(Json).ToArray()) + "]" +
        ",\"illisibles\":[" + string.Join(",", illisibles.ConvertAll(Json).ToArray()) + "],\"references\":[" + details + "]" +
        ",\"sources\":[" + string.Join(",", kv.Value.ConvertAll(x => Json(x.Nom)).ToArray()) + "]}");
    }
    J.Append("\n],\n");

    // banques visibles par le jeu
    J.Append("\"banques\": [\n"); first = true; int nBanques = 0;
    foreach (var s in sources) foreach (var b in s.Banques) {
      Entree e; bool gagne = vfs.TryGetValue(Norm(b[0]), out e) && e.Gagnant == s;
      string k = Norm(b[0]); HashSet<string> ev; int nev = evts.TryGetValue(k, out ev) ? ev.Count : -1;
      bool guids = vfs.ContainsKey(k + ".guids");
      if (s.Role != "inactif") nBanques++;
      if (!first) J.Append(",\n"); first = false;
      J.Append("{\"chemin\":" + Json(b[0]) + ",\"source\":" + Json(s.Nom) + ",\"role\":" + Json(s.Role) + ",\"utilisee\":" + (gagne ? "true" : "false") + ",\"entete\":" + Json(b[1]) +
        ",\"guids\":" + (guids ? "true" : "false") + ",\"evenements\":" + nev + "}");
    }
    J.Append("\n],\n");

    // conflits : meme fichier son fourni par plusieurs sources (hors jeu de base), ou fichier du jeu remplace par un mod
    J.Append("\"conflits\": [\n"); first = true; int nConf = 0, nRemp = 0;
    foreach (var e in vfs.Values) {
      var mods = e.Sources.FindAll(x => x.Role == "actif"); bool base_ = e.Sources.Exists(x => x.Role == "jeu");
      var prios = new HashSet<int>(); foreach (var m in mods) prios.Add(m.Priorite);       // plusieurs archives d'un meme mod = un seul mod
      if (prios.Count == 0 || (prios.Count < 2 && !base_)) continue;
      string type = prios.Count >= 2 ? "plusieurs_mods" : "remplace_le_jeu";
      if (type == "plusieurs_mods") nConf++; else if (++nRemp > 3000) continue;
      if (!first) J.Append(",\n"); first = false;
      J.Append("{\"chemin\":" + Json(e.Chemin) + ",\"type\":" + Json(type) + ",\"gagnant\":" + Json(e.Gagnant.Nom) + ",\"sources\":[" + string.Join(",", e.Sources.ConvertAll(x => Json(x.Nom)).ToArray()) + "]}");
    }
    J.Append("\n],\n");

    // fichiers .soundref visibles
    J.Append("\"soundref\": [\n"); first = true;
    foreach (var s in sources) foreach (var r in s.Refs) {
      if (!r[0].ToLowerInvariant().EndsWith(".soundref") || s.Role == "inactif") continue;
      Entree e; if (vfs.TryGetValue(Norm(r[0]), out e) && e.Gagnant != s) continue;
      string etat, raison; Verifier(r[1], vfs, evts, sources, out etat, out raison);
      if (!first) J.Append(",\n"); first = false;
      J.Append("{\"fichier\":" + Json(r[0]) + ",\"reference\":" + Json(r[1]) + ",\"source\":" + Json(s.Nom) + ",\"etat\":" + Json(etat) + ",\"raison\":" + Json(raison) + "}");
    }
    J.Append("\n],\n");

    J.Append("\"resume\": {\"camions\":" + nCamions + ",\"dossiers_accessoires_ignores\":" + nIgnores + ",\"moteurs\":" + nMoteurs + ",\"banques\":" + nBanques + ",\"mods_audio\":" + sources.FindAll(x => x.Role != "jeu" && x.Banques.Count + x.Refs.Count > 0).Count + ",\"mods_audio_actifs\":" + sources.FindAll(x => x.Role == "actif" && x.Banques.Count + x.Refs.Count > 0).Count +
      ",\"conflits\":" + nConf + ",\"remplacements_du_jeu\":" + nRemp + ",\"compatibles\":" + nCompat + ",\"partiels\":" + nPartiel + ",\"non_pris_en_charge\":" + nNon + ",\"non_verifies\":" + nNonVerif + "}\n}\n");
    return J.ToString();
  }

  // reference "/sound/x/y.bank#evenement/chemin" ou "/sound/x/y.soundref"
  static void Verifier(string reference, Dictionary<string, Entree> vfs, Dictionary<string, HashSet<string>> evts, List<SfSource> sources, out string etat, out string raison) { Verifier(reference, vfs, evts, sources, out etat, out raison, 0); }
  static void Verifier(string reference, Dictionary<string, Entree> vfs, Dictionary<string, HashSet<string>> evts, List<SfSource> sources, out string etat, out string raison, int profondeur) {
    string r = reference.Trim(); int h = r.IndexOf('#'); string fichier = Norm(h >= 0 ? r.Substring(0, h) : r), ev = h >= 0 ? r.Substring(h + 1).Trim().Trim('/').ToLowerInvariant() : "";
    if (!vfs.ContainsKey(fichier)) { etat = "manquant"; raison = "Fichier introuvable dans le jeu et les mods actifs : /" + fichier; return; }
    if (fichier.EndsWith(".soundref")) {
      string cible = null; Entree es = vfs[fichier];
      foreach (var r2 in es.Gagnant.Refs) if (Norm(r2[0]) == fichier) { cible = r2[1]; break; }
      if (cible == null) { etat = "non_verifie"; raison = "Le .soundref est present mais sa cible n'est pas lisible."; return; }
      if (profondeur > 3) { etat = "non_verifie"; raison = "Chaine de .soundref trop longue."; return; }
      string e2, r3; Verifier(cible, vfs, evts, sources, out e2, out r3, profondeur + 1);
      etat = e2; raison = ".soundref -> " + cible + " : " + r3; return;
    }
    if (ev.Length == 0) { etat = "ok"; raison = "Banque presente."; return; }
    HashSet<string> set;
    if (!evts.TryGetValue(fichier, out set)) {
      if (vfs.ContainsKey(fichier + ".guids")) { etat = "non_verifie"; raison = "Le .bank.guids existe mais n'est pas lisible (chiffre ou binaire)."; }
      else { etat = "non_verifie"; raison = "Banque sans .bank.guids : impossible de verifier l'evenement " + ev + "."; }
      return;
    }
    if (set.Contains("event:/" + ev) || set.Contains("snapshot:/" + ev) || set.Contains(ev)) { etat = "ok"; raison = "Evenement present dans le .bank.guids."; return; }
    etat = "manquant"; raison = "Evenement event:/" + ev + " absent du .bank.guids de la banque.";
  }

  // texte d'un fichier tel que le jeu le voit (source gagnante) : pour les echantillons d'etude (definitions texte seulement)
  public static string LireTexte(string archive, string chemin) {
    try { using (var a = SfArchive.Open(archive)) { var d = a.Read(chemin); if (d == null || Nature(d) != "texte" || d.Length > MaxTexte) return null; return Encoding.UTF8.GetString(d); } } catch { return null; }
  }
}
}
