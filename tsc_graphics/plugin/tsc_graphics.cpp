/* tsc-graphics.dll : TSC Neural Graphics, rendu temps reel dans ETS2 (DirectX 11). Plugin SDK SCS charge par le jeu
   (bin/win_x64/plugins). Copyright (c) 2026 Truck So Clean France. Sans CRT, sans SDK Windows (clang + lld).

   0.2 : branche sur le pipeline reel d'ETS2 1.61 releve par l'audit (sonde + RenderDoc, 03/11/2026) :
   rendu differe par vue (multi-ecran mode 4 = 3 vues 1280x1080) : G-buffer (4 cibles, la 1re RGBA16F), profondeur D32S8 en
   Z inverse (monde dans 0,01-0,9, cabine dans 0,9-1, ciel 0), eclairage dans une cible HDR RGBA16F, gouttes de pluie
   (cible R8G8B8A8_SNORM), puis exposition, tone mapping par vue et composition dans l'image 3840x1080 ou l'interface est
   dessinee en dernier.
   - EFFET PAR VUE, AVANT L'INTERFACE ET AVANT LE TONE MAPPING : quand le jeu quitte la cible HDR d'une vue, la profondeur de
     cette vue est encore intacte. On copie HDR + profondeur et on ajoute, dans la cible HDR du jeu, les reflets de la route
     mouillee calcules depuis la profondeur reelle : les lumieres gardent leur intensite HDR, l'interface n'est jamais
     touchee, la cabine (profondeur > 0,9) est exclue exactement.
   - HUMIDITE : la passe des gouttes du jeu sert de detecteur de pluie ; la route se mouille en ~40 s et seche en ~5 min.
   - Les entrees de la table du contexte que d'autres couches remettent a chaque image sont reposees a chaque Present.
   - SONDE : trace d'une image (Ctrl+Maj+T, et automatiquement apres 20 s) dans tsc-graphics-trace.log.
   - Ctrl+Maj+G : effet marche / arret. Ctrl+Maj+D : vue de controle suivante (profondeur, normales, masque mouille).
   - MESURES toutes les 2 s dans tsc-graphics.log : img/s, temps d'image moyen et pire, cout CPU et cout GPU (requetes
     horodatees autour de chacune de nos passes), vues traitees, pluie detectee, humidite, memoire video ajoutee.
   Toutes nos passes tournent dans notre propre etat de contexte (SwapDeviceContextState). Reglages : tsc-graphics.ini. */
typedef unsigned int UINT; typedef unsigned long DWORD; typedef int BOOL; typedef long HRESULT; typedef long LONG;
typedef void *HANDLE; typedef void *HMODULE; typedef unsigned long long SIZE_T; typedef unsigned short WORD;
typedef unsigned long long u64; typedef long long i64;
#define WINAPI __stdcall
extern "C" {
__declspec(dllimport) HMODULE WINAPI LoadLibraryA(const char *);
__declspec(dllimport) void *WINAPI GetProcAddress(HMODULE, const char *);
__declspec(dllimport) BOOL WINAPI VirtualProtect(void *, SIZE_T, DWORD, DWORD *);
__declspec(dllimport) HANDLE WINAPI CreateFileA(const char *, DWORD, DWORD, void *, DWORD, DWORD, HANDLE);
__declspec(dllimport) BOOL WINAPI ReadFile(HANDLE, void *, DWORD, DWORD *, void *);
__declspec(dllimport) BOOL WINAPI WriteFile(HANDLE, const void *, DWORD, DWORD *, void *);
__declspec(dllimport) DWORD WINAPI GetFileSize(HANDLE, DWORD *);
__declspec(dllimport) BOOL WINAPI CloseHandle(HANDLE);
__declspec(dllimport) DWORD WINAPI GetModuleFileNameA(HMODULE, char *, DWORD);
__declspec(dllimport) u64 WINAPI GetTickCount64(void);
__declspec(dllimport) BOOL WINAPI QueryPerformanceCounter(i64 *);
__declspec(dllimport) BOOL WINAPI QueryPerformanceFrequency(i64 *);
__declspec(dllimport) BOOL WINAPI GetModuleHandleExA(DWORD, const char *, HMODULE *);
__declspec(dllimport) short WINAPI GetAsyncKeyState(int);
__declspec(dllimport) WORD WINAPI RegisterClassExA(const void *);
__declspec(dllimport) BOOL WINAPI UnregisterClassA(const char *, HMODULE);
__declspec(dllimport) void *WINAPI CreateWindowExA(DWORD, const char *, const char *, DWORD, int, int, int, int, void *, void *, HMODULE, void *);
__declspec(dllimport) BOOL WINAPI DestroyWindow(void *);
__declspec(dllimport) i64 WINAPI DefWindowProcA(void *, UINT, u64, i64);
int _fltused = 0x9875;
void *memset(void *d, int c, SIZE_T n) { unsigned char *p = (unsigned char *)d; while (n--) *p++ = (unsigned char)c; return d; }
void *memcpy(void *d, const void *s, SIZE_T n) { unsigned char *a = (unsigned char *)d; const unsigned char *b = (const unsigned char *)s; while (n--) *a++ = *b++; return d; }
}
#define INVALID ((HANDLE)(long long)-1)
#define VT(o) (*(void ***)(o))
#define VERSION "tsc-graphics 0.2.0"
#define REL(o) do { if (o) { ((UINT (WINAPI *)(void *))VT(o)[2])(o); (o) = 0; } } while (0)

/* ---------- journal ---------- */
static HMODULE g_mod; static char g_dir[300];
static void cat(char *d, const char *s) { while (*d) d++; while ((*d++ = *s++)) {} }
static int lng(const char *s) { int n = 0; while (s[n]) n++; return n; }
struct Ligne { char t[600]; int n; void s(const char *a) { while (*a && n < 590) t[n++] = *a++; t[n] = 0; }
	void i(i64 v) { char b[24]; int k = 23; b[k] = 0; bool neg = v < 0; if (neg) v = -v; do { b[--k] = (char)('0' + v % 10); v /= 10; } while (v && k > 1); if (neg) b[--k] = '-'; s(b + k); }
	void f(double v, int dec = 2) { if (v < 0) { s("-"); v = -v; } i64 e = (i64)v; i(e); s("."); double r = v - (double)e; for (int k = 0; k < dec; k++) { r *= 10; int c = (int)r; char b[2] = {(char)('0' + c), 0}; s(b); r -= c; } }
	void x(u64 v) { char b[20]; int k = 19; b[k] = 0; do { int c = (int)(v & 15); b[--k] = (char)(c < 10 ? '0' + c : 'a' + c - 10); v >>= 4; } while (v && k); s("0x"); s(b + k); }
	Ligne() { n = 0; t[0] = 0; } };
static void ecrire(const char *fichier, const char *txt, int n) {
	char p[340] = {0}; cat(p, g_dir); cat(p, fichier);
	HANDLE f = CreateFileA(p, 4 /*FILE_APPEND_DATA*/, 1, 0, 4 /*OPEN_ALWAYS*/, 0x80, 0);
	if (f == INVALID) return; DWORD w; WriteFile(f, txt, (DWORD)n, &w, 0); CloseHandle(f);
}
static void journal(Ligne &l) { l.s("\r\n"); ecrire("tsc-graphics.log", l.t, l.n); }
static void logline(const char *a, i64 v = -1) { Ligne l; l.s(a); if (v >= 0) { l.s(" "); l.i(v); } journal(l); }
static int lire_fichier(const char *nom, char *buf, int max) {
	char p[340] = {0}; cat(p, g_dir); cat(p, nom);
	HANDLE f = CreateFileA(p, 0x80000000 /*GENERIC_READ*/, 3, 0, 3 /*OPEN_EXISTING*/, 0x80, 0);
	if (f == INVALID) return -1; DWORD n = 0; ReadFile(f, buf, (DWORD)(max - 1), &n, 0); CloseHandle(f); buf[n] = 0; return (int)n;
}

/* ---------- reglages (tsc-graphics.ini, cle = valeur, recharge a chaud) ---------- */

/* ---------- reglages (tsc-graphics.ini, cle = valeur, recharge a chaud) ---------- */
struct Reglages {
	float actif = 1, humidite = -1 /* -1 = auto (pluie du jeu) */, fov_v = 43, proche = 0.2f, plage_min = 0.01f, plage_max = 0.9f;
	float intensite = 1, rugosite = 0.12f, trainees = 1.5f, pas = 0.12f, epaisseur = 0.5f, f0 = 0.04f, assombrir = 0.35f;
	float vue = 0, seuil_gouttes = 500, mouille_s = 40, seche_s = 300, max_vues = 3;
};
static Reglages R; static u64 g_ini_hash;
static double nombre(const char *&p) { double s = 1, v = 0, d = 0.1; while (*p == ' ' || *p == '\t') p++; if (*p == '-') { s = -1; p++; }
	while (*p >= '0' && *p <= '9') v = v * 10 + (*p++ - '0'); if (*p == '.' || *p == ',') { p++; while (*p >= '0' && *p <= '9') { v += (*p++ - '0') * d; d *= 0.1; } } return v * s; }
static bool cle(const char *l, const char *k) { int i = 0; while (k[i] && l[i] == k[i]) i++; if (k[i]) return false; while (l[i] == ' ') i++; return l[i] == '='; }
static void lire_ini(bool force) {
	static char b[8192]; int n = lire_fichier("tsc-graphics.ini", b, sizeof b); if (n < 0) return;
	u64 h = 1469598103934665603ULL; for (int i = 0; i < n; i++) h = (h ^ (unsigned char)b[i]) * 1099511628211ULL;
	if (!force && h == g_ini_hash) return; g_ini_hash = h;
	struct { const char *k; float *v; } t[] = { {"actif", &R.actif}, {"humidite", &R.humidite}, {"fov_v", &R.fov_v}, {"proche", &R.proche},
		{"plage_min", &R.plage_min}, {"plage_max", &R.plage_max}, {"intensite", &R.intensite}, {"rugosite", &R.rugosite}, {"trainees", &R.trainees},
		{"pas", &R.pas}, {"epaisseur", &R.epaisseur}, {"f0", &R.f0}, {"assombrir", &R.assombrir}, {"vue", &R.vue}, {"seuil_gouttes", &R.seuil_gouttes},
		{"mouille_s", &R.mouille_s}, {"seche_s", &R.seche_s}, {"max_vues", &R.max_vues} };
	const char *p = b;
	while (*p) {
		while (*p == '\r' || *p == '\n' || *p == ' ') p++;
		if (*p != ';' && *p != '#' && *p != '[') for (auto &e : t) if (cle(p, e.k)) { const char *q = p; while (*q != '=') q++; q++; *e.v = (float)nombre(q); break; }
		while (*p && *p != '\n') p++;
	}
	Ligne l; l.s("reglages relus : actif "); l.f(R.actif, 0); l.s(", humidite "); l.f(R.humidite); l.s(", fov_v "); l.f(R.fov_v, 1); l.s(", proche "); l.f(R.proche, 3);
	l.s(", plage "); l.f(R.plage_min, 3); l.s("-"); l.f(R.plage_max, 3); l.s(", vue "); l.f(R.vue, 0); journal(l);
}

/* ---------- D3D11 : structures minimales ---------- */
struct GUIDx { DWORD a; WORD b, c; unsigned char d[8]; };
static const GUIDx IID_Tex2D = {0x6f15aaf2, 0xd208, 0x4e89, {0x9a, 0xb4, 0x48, 0x95, 0x35, 0xd3, 0x4f, 0x9c}};
static const GUIDx IID_Dev = {0xdb6f6ddb, 0xac77, 0x4e88, {0x82, 0x53, 0x81, 0x9d, 0xf9, 0xbb, 0xf1, 0x40}};
static const GUIDx IID_Dev1 = {0xa04bfb29, 0x08ef, 0x43d6, {0xa4, 0x9c, 0xa9, 0xbd, 0xbd, 0xcb, 0xe6, 0x86}};
static const GUIDx IID_Ctx1 = {0xbb2c6faa, 0xb5fb, 0x4082, {0x8e, 0x6b, 0x38, 0x8b, 0x8c, 0xfa, 0x90, 0xe1}};
struct TEX2D_DESC { UINT Width, Height, MipLevels, ArraySize, Format, SampleCount, SampleQuality, Usage, BindFlags, CPUAccessFlags, MiscFlags; };
struct DSV_DESC { UINT Format, ViewDimension, Flags, MipSlice, pad[2]; };
struct SRV_DESC { UINT Format, ViewDimension, MostDetailedMip, MipLevels, pad[2]; };
struct VIEWPORT { float x, y, w, h, zmin, zmax; };
struct BUF_DESC { UINT ByteWidth, Usage, BindFlags, CPUAccessFlags, MiscFlags, StructureByteStride; };
struct SAMP_DESC { UINT Filter, U, V, W; float MipLODBias; UINT MaxAniso, Comp; float Border[4], MinLOD, MaxLOD; };
struct QUERY_DESC { UINT Query, MiscFlags; };
struct DISJOINT { u64 Frequency; BOOL Disjoint; };
struct SWAP_DESC { UINT w, h, rn, rd, fmt, so, sc, cnt, q, usage, nbuf; void *hwnd; BOOL windowed; UINT effect, flags; };
struct WNDCLASSEXx { UINT cbSize, style; void *proc; int a, b; HMODULE inst; void *icon, *cur, *bg; const char *menu, *name; void *iconsm; };

/* indices des tables de fonctions (ordre des interfaces d3d11.h / dxgi.h) */
enum { D_CreateBuffer = 3, D_CreateTexture2D = 5, D_CreateSRV = 7, D_CreateRTV = 9, D_CreateDSV = 10, D_CreateVS = 12, D_CreatePS = 15,
	D_CreateSampler = 23, D_CreateQuery = 24, D_GetFeatureLevel = 37, D1_CreateDeviceContextState = 47 };
enum { C_VSSetCB = 7, C_PSSetSRV = 8, C_PSSetShader = 9, C_PSSetSamplers = 10, C_VSSetShader = 11, C_DrawIndexed = 12, C_Draw = 13, C_Map = 14, C_Unmap = 15,
	C_PSSetCB = 16, C_DrawIndexedInstanced = 20, C_DrawInstanced = 21, C_IASetTopology = 24, C_Begin = 27, C_End = 28, C_GetData = 29,
	C_OMSetRT = 33, C_RSSetViewports = 44, C_CopyResource = 47, C_UpdateSubresource = 48, C_ClearRTV = 50, C_ClearDSV = 53, C1_SwapState = 131 };
enum { S_GetDevice = 7, S_Present = 8, S_GetBuffer = 9, S_ResizeBuffers = 13, S1_Present1 = 22 };
enum { V_GetResource = 7, V_GetDesc = 8, T_GetDesc = 10 };

typedef HRESULT (WINAPI *PFN_PRESENT)(void *, UINT, UINT);
typedef HRESULT (WINAPI *PFN_PRESENT1)(void *, UINT, UINT, const void *);
typedef HRESULT (WINAPI *PFN_RESIZE)(void *, UINT, UINT, UINT, UINT, UINT);
typedef void (WINAPI *PFN_OMSRT)(void *, UINT, void *const *, void *);
typedef void (WINAPI *PFN_CLRDSV)(void *, void *, UINT, float, unsigned char);
typedef void (WINAPI *PFN_CLRRTV)(void *, void *, const float *);
typedef void (WINAPI *PFN_RSVP)(void *, UINT, const VIEWPORT *);
typedef void (WINAPI *PFN_DRAWIDX)(void *, UINT, UINT, int);
typedef void (WINAPI *PFN_DRAW)(void *, UINT, UINT);
typedef void (WINAPI *PFN_DRAWIDXI)(void *, UINT, UINT, UINT, int, UINT);
typedef void (WINAPI *PFN_DRAWI)(void *, UINT, UINT, UINT, UINT);
typedef HRESULT (WINAPI *PFN_CREATE_SC)(void *, int, HMODULE, UINT, const int *, UINT, UINT, const SWAP_DESC *, void **, void **, int *, void **);
typedef HRESULT (WINAPI *PFN_COMPILE)(const void *, SIZE_T, const char *, const void *, void *, const char *, const char *, UINT, UINT, void **, void **);

static PFN_PRESENT o_present; static PFN_PRESENT1 o_present1; static PFN_RESIZE o_resize; static PFN_OMSRT o_omsrt; static PFN_CLRDSV o_clrdsv;
static PFN_CLRRTV o_clrrtv; static PFN_RSVP o_rsvp; static PFN_DRAWIDX o_drawidx; static PFN_DRAW o_draw; static PFN_DRAWIDXI o_drawidxi; static PFN_DRAWI o_drawi;
static void **g_vt_sc, **g_vt_ctx; static int g_hooks;
static volatile int g_nous;   /* nos propres appels passent tout droit */

static bool poser(void **vt, int i, void *f, void **orig) {
	DWORD old; if (!VirtualProtect(&vt[i], sizeof(void *), 0x04, &old)) return false;
	*orig = vt[i]; vt[i] = f; VirtualProtect(&vt[i], sizeof(void *), old, &old); return true;
}
static void retirer(void **vt, int i, void *orig) {
	DWORD old; if (vt && orig && VirtualProtect(&vt[i], sizeof(void *), 0x04, &old)) { vt[i] = orig; VirtualProtect(&vt[i], sizeof(void *), old, &old); }
}
static void desc_tex(void *tex, TEX2D_DESC &d) { memset(&d, 0, sizeof d); ((void (WINAPI *)(void *, TEX2D_DESC *))VT(tex)[T_GetDesc])(tex, &d); }
static void *ressource(void *view) { void *r = 0; ((void (WINAPI *)(void *, void **))VT(view)[V_GetResource])(view, &r); return r; }   /* AddRef : rendre */
static const char *nom_format(UINT f) {
	switch (f) { case 2: return "R32G32B32A32_FLOAT"; case 10: return "R16G16B16A16_FLOAT"; case 11: return "R16G16B16A16_UNORM"; case 19: return "R32G8X24_TYPELESS";
	case 20: return "D32_FLOAT_S8X24_UINT"; case 24: return "R10G10B10A2_UNORM"; case 23: return "R10G10B10A2_TYPELESS"; case 26: return "R11G11B10_FLOAT";
	case 27: return "R8G8B8A8_TYPELESS"; case 28: return "R8G8B8A8_UNORM"; case 29: return "R8G8B8A8_UNORM_SRGB"; case 34: return "R16G16_FLOAT"; case 35: return "R16G16_UNORM";
	case 39: return "R32_TYPELESS"; case 40: return "D32_FLOAT"; case 41: return "R32_FLOAT"; case 44: return "R24G8_TYPELESS"; case 45: return "D24_UNORM_S8_UINT";
	case 53: return "R16_TYPELESS"; case 54: return "R16_FLOAT"; case 55: return "D16_UNORM"; case 56: return "R16_UNORM"; case 61: return "R8_UNORM"; case 49: return "R8G8_UNORM";
	case 87: return "B8G8R8A8_UNORM"; case 88: return "B8G8R8X8_UNORM"; case 90: return "B8G8R8A8_TYPELESS"; case 91: return "B8G8R8A8_UNORM_SRGB"; default: return 0; }
}
static void dire_tex(Ligne &l, void *tex) {
	if (!tex) { l.s("aucune"); return; } TEX2D_DESC d; desc_tex(tex, d);
	l.i(d.Width); l.s("x"); l.i(d.Height); l.s(" "); const char *n = nom_format(d.Format); if (n) l.s(n); else { l.s("format "); l.i(d.Format); }
	if (d.SampleCount > 1) { l.s(" MSAA x"); l.i(d.SampleCount); } if (d.ArraySize > 1) { l.s(" tableau "); l.i(d.ArraySize); }
	l.s(" liaisons "); l.x(d.BindFlags); l.s(" @"); l.x((u64)tex);
}


/* ---------- sonde ---------- */
static UINT g_bw, g_bh;
static int g_trace, g_trace_auto_fait; static i64 g_trace_dessins;
static char g_tbuf[1 << 20]; static int g_tn;
static void trace_txt(Ligne &l) { l.s("\r\n"); if (g_tn + l.n < (int)sizeof g_tbuf) { memcpy(g_tbuf + g_tn, l.t, l.n); g_tn += l.n; } }
static void trace_dessins() { if (g_trace && g_trace_dessins) { Ligne l; l.s("    dessins : "); l.i(g_trace_dessins); trace_txt(l); g_trace_dessins = 0; } }

/* ---------- suivi des vues du jeu ---------- */
enum { E_RIEN, E_GBUF, E_HDR };
static int g_etape;                       /* ou en est la vue en cours */
static void *g_hdr_tex, *g_vue_prof;      /* cible HDR et profondeur de la vue en cours (references gardees) */
static int g_vues_image, g_vues_traitees; /* vues vues / traitees sur l'image en cours */
static int g_dans_gouttes; static i64 g_gouttes, g_gouttes_rapport;
static float g_mouille = 0; static int g_pluie;
static i64 g_n_gbuf, g_n_hdr;             /* diagnostics */
static float g_val_effacement = -1;

/* ---------- nos ressources ---------- */
static void *g_dev, *g_ctx, *g_dev1, *g_ctx1, *g_etat, *g_vs, *g_ps, *g_cb, *g_samp_lin, *g_samp_pt;
static void *g_coul, *g_coul_srv; static UINT g_coul_w, g_coul_h, g_coul_fmt;
static void *g_prof, *g_prof_srv; static UINT g_prof_w, g_prof_h, g_prof_fmt;
struct Rtv { void *tex, *rtv; }; static Rtv g_rtv[8]; static int g_nrtv;
#define NQ 4
#define QV 4
static void *g_q_dis[NQ], *g_q_a[NQ][QV], *g_q_b[NQ][QV]; static int g_q_n[NQ], g_q_i, g_q_ouvert;
static PFN_COMPILE g_compile; static u64 g_hlsl_hash; static int g_shaders_ok;
static float g_effet_on = 1; static int g_vue = 0;
static i64 g_freq, g_t_prec; static double g_somme_ms, g_pire_ms, g_cpu_ms, g_gpu_ms; static int g_n_img, g_n_gpu; static u64 g_t_rapport; static i64 g_vues_rapport;
static u64 g_vram;

static void compter() {
	if (g_nous) return;
	if (g_trace) g_trace_dessins++;
	if (g_dans_gouttes) g_gouttes++;
}
static HRESULT dev_tex(const TEX2D_DESC *d, void **out) { return ((HRESULT (WINAPI *)(void *, const TEX2D_DESC *, const void *, void **))VT(g_dev)[D_CreateTexture2D])(g_dev, d, 0, out); }

static void compiler() {
	static char src[65536]; int n = lire_fichier("tsc-graphics.hlsl", src, sizeof src);
	if (n <= 0) { if (g_hlsl_hash != 1) logline("tsc-graphics.hlsl introuvable : effet coupe"); g_hlsl_hash = 1; g_shaders_ok = 0; return; }
	u64 h = 1469598103934665603ULL; for (int i = 0; i < n; i++) h = (h ^ (unsigned char)src[i]) * 1099511628211ULL;
	if (h == g_hlsl_hash) return; g_hlsl_hash = h;
	if (!g_compile) { HMODULE c = LoadLibraryA("d3dcompiler_47.dll"); if (c) g_compile = (PFN_COMPILE)GetProcAddress(c, "D3DCompile"); }
	if (!g_compile) { logline("d3dcompiler_47.dll introuvable : effet coupe"); g_shaders_ok = 0; return; }
	void *bv = 0, *bp = 0, *err = 0, *vs = 0, *ps = 0;
	const UINT fl = 1 << 15;
	if (g_compile(src, (SIZE_T)n, "tsc-graphics.hlsl", 0, 0, "vs_principal", "vs_5_0", fl, 0, &bv, &err) < 0) {
		Ligne l; l.s("erreur shader VS : "); if (err) l.s((const char *)((void *(WINAPI *)(void *))VT(err)[3])(err)); journal(l); REL(err); g_shaders_ok = 0; return; }
	REL(err);
	if (g_compile(src, (SIZE_T)n, "tsc-graphics.hlsl", 0, 0, "ps_principal", "ps_5_0", fl, 0, &bp, &err) < 0) {
		Ligne l; l.s("erreur shader PS : "); if (err) l.s((const char *)((void *(WINAPI *)(void *))VT(err)[3])(err)); journal(l); REL(err); REL(bv); g_shaders_ok = 0; return; }
	REL(err);
	typedef void *(WINAPI *PTR)(void *); typedef SIZE_T (WINAPI *TAILLE)(void *);
	HRESULT c1 = ((HRESULT (WINAPI *)(void *, const void *, SIZE_T, void *, void **))VT(g_dev)[D_CreateVS])(g_dev, ((PTR)VT(bv)[3])(bv), ((TAILLE)VT(bv)[4])(bv), 0, &vs);
	HRESULT c2 = ((HRESULT (WINAPI *)(void *, const void *, SIZE_T, void *, void **))VT(g_dev)[D_CreatePS])(g_dev, ((PTR)VT(bp)[3])(bp), ((TAILLE)VT(bp)[4])(bp), 0, &ps);
	REL(bv); REL(bp);
	if (c1 < 0 || c2 < 0) { REL(vs); REL(ps); logline("creation des shaders refusee"); g_shaders_ok = 0; return; }
	REL(g_vs); REL(g_ps); g_vs = vs; g_ps = ps; g_shaders_ok = 1; logline("shaders compiles (tsc-graphics.hlsl)");
}

static bool init_appareil(void *sc) {
	if (g_dev) return g_etat != 0;
	if (((HRESULT (WINAPI *)(void *, const GUIDx *, void **))VT(sc)[S_GetDevice])(sc, &IID_Dev, &g_dev) < 0 || !g_dev) { logline("GetDevice refuse"); g_dev = 0; return false; }
	((void (WINAPI *)(void *, void **))VT(g_dev)[40])(g_dev, &g_ctx);
	((HRESULT (WINAPI *)(void *, const GUIDx *, void **))VT(g_dev)[0])(g_dev, &IID_Dev1, &g_dev1);
	if (g_ctx) ((HRESULT (WINAPI *)(void *, const GUIDx *, void **))VT(g_ctx)[0])(g_ctx, &IID_Ctx1, &g_ctx1);
	if (!g_dev1 || !g_ctx1) { logline("D3D11.1 indisponible : effet impossible (sonde seule)"); return false; }
	int fl = ((int (WINAPI *)(void *))VT(g_dev)[D_GetFeatureLevel])(g_dev), choisi = 0;
	HRESULT hr = ((HRESULT (WINAPI *)(void *, UINT, const int *, UINT, UINT, const GUIDx *, int *, void **))VT(g_dev1)[D1_CreateDeviceContextState])(g_dev1, 0, &fl, 1, 7, &IID_Dev, &choisi, &g_etat);
	if (hr < 0 || !g_etat) { logline("CreateDeviceContextState refuse", hr & 0xffffffffLL); g_etat = 0; return false; }
	BUF_DESC bd = {128, 2, 4, 0x10000, 0, 0};
	((HRESULT (WINAPI *)(void *, const BUF_DESC *, const void *, void **))VT(g_dev)[D_CreateBuffer])(g_dev, &bd, 0, &g_cb);
	SAMP_DESC s = {0x15, 3, 3, 3, 0, 1, 1, {0, 0, 0, 0}, 0, 3.4e38f};
	((HRESULT (WINAPI *)(void *, const SAMP_DESC *, void **))VT(g_dev)[D_CreateSampler])(g_dev, &s, &g_samp_lin);
	s.Filter = 0; ((HRESULT (WINAPI *)(void *, const SAMP_DESC *, void **))VT(g_dev)[D_CreateSampler])(g_dev, &s, &g_samp_pt);
	for (int i = 0; i < NQ; i++) {
		QUERY_DESC q0 = {3 /*TIMESTAMP_DISJOINT*/, 0}, q1 = {2 /*TIMESTAMP*/, 0};
		((HRESULT (WINAPI *)(void *, const QUERY_DESC *, void **))VT(g_dev)[D_CreateQuery])(g_dev, &q0, &g_q_dis[i]);
		for (int v = 0; v < QV; v++) {
			((HRESULT (WINAPI *)(void *, const QUERY_DESC *, void **))VT(g_dev)[D_CreateQuery])(g_dev, &q1, &g_q_a[i][v]);
			((HRESULT (WINAPI *)(void *, const QUERY_DESC *, void **))VT(g_dev)[D_CreateQuery])(g_dev, &q1, &g_q_b[i][v]);
		}
	}
	logline("appareil du jeu pris, etat de contexte TSC cree, niveau", (i64)fl);
	compiler();
	return true;
}

static bool formats_prof(UINT f, UINT &tex, UINT &srv) {
	switch (f) {
	case 40: case 39: case 41: tex = 39; srv = 41; return true;
	case 45: case 44: tex = 44; srv = 46; return true;
	case 20: case 19: tex = 19; srv = 21; return true;
	case 55: case 53: case 56: tex = 53; srv = 56; return true;
	}
	return false;
}
static void *rtv_de(void *tex) {
	for (int i = 0; i < g_nrtv; i++) if (g_rtv[i].tex == tex) return g_rtv[i].rtv;
	void *r = 0;
	if (((HRESULT (WINAPI *)(void *, void *, const void *, void **))VT(g_dev)[D_CreateRTV])(g_dev, tex, 0, &r) < 0 || !r) return 0;
	if (g_nrtv == 8) { REL(g_rtv[0].rtv); ((UINT (WINAPI *)(void *))VT(g_rtv[0].tex)[2])(g_rtv[0].tex); for (int i = 1; i < 8; i++) g_rtv[i - 1] = g_rtv[i]; g_nrtv--; }
	((UINT (WINAPI *)(void *))VT(tex)[1])(tex);
	g_rtv[g_nrtv++] = {tex, r};
	Ligne l; l.s("vue de rendu creee sur la cible HDR du jeu : "); dire_tex(l, tex); journal(l);
	return r;
}
static bool copies_pretes(void *hdr, void *prof) {
	TEX2D_DESC h, d; desc_tex(hdr, h); desc_tex(prof, d);
	if (h.SampleCount > 1 || d.SampleCount > 1) { static int dit; if (!dit++) logline("cible MSAA : passe TSC sautee"); return false; }
	if (!g_coul || g_coul_w != h.Width || g_coul_h != h.Height || g_coul_fmt != h.Format) {
		REL(g_coul_srv); REL(g_coul);
		TEX2D_DESC n = {h.Width, h.Height, 1, 1, h.Format, 1, 0, 0, 8, 0, 0};
		if (dev_tex(&n, &g_coul) < 0) { g_coul = 0; return false; }
		((HRESULT (WINAPI *)(void *, void *, const void *, void **))VT(g_dev)[D_CreateSRV])(g_dev, g_coul, 0, &g_coul_srv);
		g_coul_w = h.Width; g_coul_h = h.Height; g_coul_fmt = h.Format;
	}
	UINT ft, fs; if (!formats_prof(d.Format, ft, fs)) { static int dit; if (!dit++) logline("format de profondeur inconnu", d.Format); return false; }
	if (!g_prof || g_prof_w != d.Width || g_prof_h != d.Height || g_prof_fmt != ft) {
		REL(g_prof_srv); REL(g_prof);
		TEX2D_DESC n = {d.Width, d.Height, 1, 1, ft, 1, 0, 0, 8, 0, 0};
		if (dev_tex(&n, &g_prof) < 0) { g_prof = 0; return false; }
		SRV_DESC sd = {fs, 4, 0, 1, {0, 0}};
		((HRESULT (WINAPI *)(void *, void *, const SRV_DESC *, void **))VT(g_dev)[D_CreateSRV])(g_dev, g_prof, &sd, &g_prof_srv);
		g_prof_w = d.Width; g_prof_h = d.Height; g_prof_fmt = ft;
		g_vram = (u64)h.Width * h.Height * 8 + (u64)d.Width * d.Height * 8;
		Ligne l; l.s("copies creees : HDR "); dire_tex(l, g_coul); l.s(" ; profondeur "); dire_tex(l, g_prof); l.s(" ; memoire video ajoutee ~"); l.i((i64)(g_vram >> 20)); l.s(" Mo"); journal(l);
	}
	return g_coul_srv && g_prof_srv;
}

/* passe TSC sur une vue : appelee quand le jeu quitte la cible HDR de la vue (profondeur encore intacte) */
static void passe_vue(void *hdr, void *prof) {
	if (!g_shaders_ok || !g_etat || g_vues_traitees >= (int)R.max_vues) return;
	if (!copies_pretes(hdr, prof)) return;
	void *rtv = rtv_de(hdr); if (!rtv) return;
	float tan_v; { float a = R.fov_v * 0.5f * 3.14159265f / 180.0f; float a2 = a * a; tan_v = (a * (1 - a2 / 6 + a2 * a2 / 120)) / (1 - a2 / 2 + a2 * a2 / 24 - a2 * a2 * a2 / 720); }
	float mouille = R.humidite >= 0 ? R.humidite : g_mouille;
	static float t; t += 0.016f;
	float cbv[32] = {
		(float)g_vue, mouille, tan_v, g_coul_h ? (float)g_coul_w / (float)g_coul_h : 1.0f,
		R.proche, R.plage_min, R.plage_max, t,
		(float)g_coul_w, (float)g_coul_h, g_coul_w ? 1.0f / g_coul_w : 0, g_coul_h ? 1.0f / g_coul_h : 0,
		R.intensite, R.rugosite, 1, R.trainees,
		0, R.pas, R.epaisseur, R.f0,
		(float)g_vues_traitees, R.assombrir, 0, 0 };
	void *old = 0;
	g_nous++;
	((void (WINAPI *)(void *, void *, void **))VT(g_ctx1)[C1_SwapState])(g_ctx1, g_etat, &old);
	int qi = g_q_i % NQ, qv = g_q_n[qi];
	if (qv < QV && g_q_dis[qi]) {
		if (!g_q_ouvert) { ((void (WINAPI *)(void *, void *))VT(g_ctx)[C_Begin])(g_ctx, g_q_dis[qi]); g_q_ouvert = 1; }
		((void (WINAPI *)(void *, void *))VT(g_ctx)[C_End])(g_ctx, g_q_a[qi][qv]);
	}
	((void (WINAPI *)(void *, void *, void *))VT(g_ctx)[C_CopyResource])(g_ctx, g_coul, hdr);
	((void (WINAPI *)(void *, void *, void *))VT(g_ctx)[C_CopyResource])(g_ctx, g_prof, prof);
	struct { void *p; UINT rp, dp; } map = {0, 0, 0};
	if (((HRESULT (WINAPI *)(void *, void *, UINT, UINT, UINT, void *))VT(g_ctx)[C_Map])(g_ctx, g_cb, 0, 4, 0, &map) >= 0 && map.p) { memcpy(map.p, cbv, sizeof cbv); ((void (WINAPI *)(void *, void *, UINT))VT(g_ctx)[C_Unmap])(g_ctx, g_cb, 0); }
	VIEWPORT vp = {0, 0, (float)g_coul_w, (float)g_coul_h, 0, 1};
	((void (WINAPI *)(void *, UINT, const VIEWPORT *))VT(g_ctx)[C_RSSetViewports])(g_ctx, 1, &vp);
	((void (WINAPI *)(void *, UINT, void *const *, void *))VT(g_ctx)[C_OMSetRT])(g_ctx, 1, &rtv, 0);
	((void (WINAPI *)(void *, UINT))VT(g_ctx)[C_IASetTopology])(g_ctx, 4);
	((void (WINAPI *)(void *, void *, void *const *, UINT))VT(g_ctx)[C_VSSetShader])(g_ctx, g_vs, 0, 0);
	((void (WINAPI *)(void *, void *, void *const *, UINT))VT(g_ctx)[C_PSSetShader])(g_ctx, g_ps, 0, 0);
	void *srv[2] = {g_coul_srv, g_prof_srv}; void *smp[2] = {g_samp_lin, g_samp_pt};
	((void (WINAPI *)(void *, UINT, UINT, void *const *))VT(g_ctx)[C_PSSetSRV])(g_ctx, 0, 2, srv);
	((void (WINAPI *)(void *, UINT, UINT, void *const *))VT(g_ctx)[C_PSSetSamplers])(g_ctx, 0, 2, smp);
	((void (WINAPI *)(void *, UINT, UINT, void *const *))VT(g_ctx)[C_PSSetCB])(g_ctx, 0, 1, &g_cb);
	((void (WINAPI *)(void *, UINT, UINT))VT(g_ctx)[C_Draw])(g_ctx, 3, 0);
	void *nul[2] = {0, 0}; ((void (WINAPI *)(void *, UINT, UINT, void *const *))VT(g_ctx)[C_PSSetSRV])(g_ctx, 0, 2, nul);
	void *nrt = 0; ((void (WINAPI *)(void *, UINT, void *const *, void *))VT(g_ctx)[C_OMSetRT])(g_ctx, 1, &nrt, 0);
	if (qv < QV && g_q_dis[qi]) { ((void (WINAPI *)(void *, void *))VT(g_ctx)[C_End])(g_ctx, g_q_b[qi][qv]); g_q_n[qi] = qv + 1; }
	((void (WINAPI *)(void *, void *, void **))VT(g_ctx1)[C1_SwapState])(g_ctx1, old, 0);
	REL(old);
	g_nous--;
	g_vues_traitees++;
}
static void fin_mesure_gpu() {
	if (!g_ctx || !g_q_ouvert) return;
	int qi = g_q_i % NQ;
	g_nous++; ((void (WINAPI *)(void *, void *))VT(g_ctx)[C_End])(g_ctx, g_q_dis[qi]); g_nous--;
	g_q_ouvert = 0; g_q_i++;
	int r = (g_q_i + 1) % NQ;   /* la plus ancienne */
	if (g_q_i >= NQ && g_q_n[r]) {
		typedef HRESULT (WINAPI *GD)(void *, void *, void *, UINT, UINT);
		DISJOINT dj; double ms = 0; int ok = ((GD)VT(g_ctx)[C_GetData])(g_ctx, g_q_dis[r], &dj, sizeof dj, 1) == 0 && !dj.Disjoint && dj.Frequency;
		for (int v = 0; ok && v < g_q_n[r]; v++) { u64 a = 0, b = 0; if (((GD)VT(g_ctx)[C_GetData])(g_ctx, g_q_a[r][v], &a, 8, 1) || ((GD)VT(g_ctx)[C_GetData])(g_ctx, g_q_b[r][v], &b, 8, 1) || b < a) ok = 0; else ms += (double)(b - a) * 1000.0 / (double)dj.Frequency; }
		if (ok) { g_gpu_ms += ms; g_n_gpu++; }
		g_q_n[r] = 0;
	}
	g_q_n[(g_q_i) % NQ] = 0;
}

static void quitter_vue() { REL(g_hdr_tex); REL(g_vue_prof); g_etape = E_RIEN; }

/* ---------- crochets du contexte ---------- */
static void WINAPI h_omsrt(void *ctx, UINT n, void *const *rtv, void *dsv) {
	if (!g_nous) {
		void *rt0 = n && rtv && rtv[0] ? ressource(rtv[0]) : 0;
		void *pt = dsv ? ressource(dsv) : 0;
		TEX2D_DESC d0; if (rt0) desc_tex(rt0, d0); else memset(&d0, 0, sizeof d0);
		/* l'eclairage HDR de la vue est fini quand le jeu quitte sa cible : passe TSC maintenant */
		if (g_etape == E_HDR && rt0 != g_hdr_tex) {
			if (g_hdr_tex && g_vue_prof && R.actif > 0.5f && g_effet_on > 0.5f && g_etat) passe_vue(g_hdr_tex, g_vue_prof);
			quitter_vue();
		}
		if (n >= 4 && rt0 && d0.Format == 10 && pt) { quitter_vue(); g_etape = E_GBUF; g_vues_image++; g_n_gbuf++; }
		else if (n == 1 && rt0 && d0.Format == 10 && pt && g_etape == E_GBUF) {
			TEX2D_DESC dp; desc_tex(pt, dp);
			if (dp.Width == d0.Width && dp.Height == d0.Height) {
				g_etape = E_HDR; g_n_hdr++;
				g_hdr_tex = rt0; ((UINT (WINAPI *)(void *))VT(rt0)[1])(rt0);
				g_vue_prof = pt; ((UINT (WINAPI *)(void *))VT(pt)[1])(pt);
			}
		}
		g_dans_gouttes = (rt0 && d0.Format == 31 /*R8G8B8A8_SNORM*/ && pt) ? 1 : 0;
		if (g_trace) {
			trace_dessins();
			Ligne l; l.s("  cibles : "); l.i(n); l.s(" couleur");
			for (UINT k = 0; k < n && k < 8; k++) { l.s(n > 1 ? "\r\n      c" : " "); if (n > 1) { l.i(k); l.s(" "); } void *r = rtv && rtv[k] ? ressource(rtv[k]) : 0; dire_tex(l, r); REL(r); }
			l.s("\r\n      profondeur "); dire_tex(l, pt); l.s(g_etape == E_GBUF ? "   [TSC : G-buffer]" : g_etape == E_HDR ? "   [TSC : HDR]" : ""); trace_txt(l);
		}
		REL(rt0); REL(pt);
	}
	o_omsrt(ctx, n, rtv, dsv);
}
static void WINAPI h_clrdsv(void *ctx, void *dsv, UINT fl, float z, unsigned char st) {
	if (!g_nous && dsv) {
		if (fl & 1) g_val_effacement = z;
		if (g_trace) { trace_dessins(); void *t = ressource(dsv); Ligne l; l.s("  effacement profondeur "); if (fl & 1) { l.s("z="); l.f(z, 3); } if (fl & 2) { l.s(" stencil="); l.i(st); } l.s(" sur "); dire_tex(l, t); trace_txt(l); REL(t); }
	}
	o_clrdsv(ctx, dsv, fl, z, st);
}
static void WINAPI h_clrrtv(void *ctx, void *rtv, const float *c) {
	if (!g_nous && g_trace && rtv) { trace_dessins(); void *t = ressource(rtv); Ligne l; l.s("  effacement couleur ("); for (int k = 0; k < 4; k++) { l.f(c[k], 2); if (k < 3) l.s(" "); } l.s(") sur "); dire_tex(l, t); trace_txt(l); REL(t); }
	o_clrrtv(ctx, rtv, c);
}
static void WINAPI h_rsvp(void *ctx, UINT n, const VIEWPORT *v) {
	if (!g_nous && g_trace && n && v) { trace_dessins(); Ligne l; l.s("  viewports "); l.i(n); l.s(" :"); for (UINT k = 0; k < n && k < 4; k++) { l.s(" ["); l.f(v[k].x, 0); l.s(","); l.f(v[k].y, 0); l.s(" "); l.f(v[k].w, 0); l.s("x"); l.f(v[k].h, 0); l.s(" z "); l.f(v[k].zmin, 3); l.s("-"); l.f(v[k].zmax, 3); l.s("]"); } trace_txt(l); }
	o_rsvp(ctx, n, v);
}
static void WINAPI h_drawidx(void *c, UINT a, UINT b, int d) { compter(); o_drawidx(c, a, b, d); }
static void WINAPI h_draw(void *c, UINT a, UINT b) { compter(); o_draw(c, a, b); }
static void WINAPI h_drawidxi(void *c, UINT a, UINT b, UINT d, int e, UINT f) { compter(); o_drawidxi(c, a, b, d, e, f); }
static void WINAPI h_drawi(void *c, UINT a, UINT b, UINT d, UINT e) { compter(); o_drawi(c, a, b, d, e); }

/* d'autres couches remettent certaines entrees a chaque image : on les repose (en enchainant sur ce qui est en place) */
struct Crochet { int i; void *f; void **o; };
static Crochet g_cr[] = {
	{C_OMSetRT, (void *)h_omsrt, (void **)&o_omsrt}, {C_ClearDSV, (void *)h_clrdsv, (void **)&o_clrdsv}, {C_ClearRTV, (void *)h_clrrtv, (void **)&o_clrrtv},
	{C_RSSetViewports, (void *)h_rsvp, (void **)&o_rsvp}, {C_DrawIndexed, (void *)h_drawidx, (void **)&o_drawidx}, {C_Draw, (void *)h_draw, (void **)&o_draw},
	{C_DrawIndexedInstanced, (void *)h_drawidxi, (void **)&o_drawidxi}, {C_DrawInstanced, (void *)h_drawi, (void **)&o_drawi} };
static i64 g_reposes;
static void reposer() {
	for (auto &c : g_cr) if (g_vt_ctx[c.i] != c.f) { if (poser(g_vt_ctx, c.i, c.f, c.o)) g_reposes++; }
}

/* ---------- par image ---------- */
static bool touche(int vk) { return (GetAsyncKeyState(vk) & 0x8000) != 0; }
static bool frappe(int vk, int &mem) { bool b = touche(0x11) && touche(0x10) && touche(vk); bool r = b && !mem; mem = b; return r; }

static void apres_image(void *sc) {
	i64 t0; QueryPerformanceCounter(&t0);
	if (!g_freq) QueryPerformanceFrequency(&g_freq);
	double dt = 0;
	if (g_t_prec) { double ms = (double)(t0 - g_t_prec) * 1000.0 / (double)g_freq; dt = ms / 1000.0; g_somme_ms += ms; if (ms > g_pire_ms) g_pire_ms = ms; g_n_img++; }
	g_t_prec = t0;
	if (g_etape == E_HDR) quitter_vue();
	fin_mesure_gpu();

	/* pluie : la passe des gouttes du jeu ; la route se mouille puis seche progressivement */
	g_pluie = g_gouttes > (i64)R.seuil_gouttes; g_gouttes_rapport = g_gouttes > g_gouttes_rapport ? g_gouttes : g_gouttes_rapport; g_gouttes = 0;
	if (dt > 0 && dt < 1) { if (g_pluie) g_mouille += (float)(dt / (R.mouille_s > 1 ? R.mouille_s : 1)); else g_mouille -= (float)(dt / (R.seche_s > 1 ? R.seche_s : 1)); }
	if (g_mouille < 0) g_mouille = 0; if (g_mouille > 1) g_mouille = 1;

	static int kg, kd, kt;
	if (frappe('G', kg)) { g_effet_on = g_effet_on > 0.5f ? 0 : 1; logline(g_effet_on > 0.5f ? "effet TSC : MARCHE" : "effet TSC : ARRET"); }
	if (frappe('D', kd)) { g_vue = (g_vue + 1) % 4; static const char *n[4] = {"vue normale", "vue de controle : profondeur", "vue de controle : normales", "vue de controle : masque mouille"}; logline(n[g_vue]); }
	if (frappe('T', kt) && !g_trace) { g_trace = 2; g_tn = 0; logline("trace d'une image demandee"); }

	static u64 t_ini; u64 now = GetTickCount64();
	if (now - t_ini > 1000) { t_ini = now; lire_ini(false); if (g_dev) compiler(); if ((int)R.vue > 0 && (int)R.vue < 4) g_vue = (int)R.vue; }
	if (!g_trace_auto_fait && g_n_img > 1200) { g_trace_auto_fait = 1; g_trace = 2; g_tn = 0; logline("trace automatique d'une image (20 s apres le debut)"); }

	init_appareil(sc);
	if (!g_bw) { void *bb = 0; if (((HRESULT (WINAPI *)(void *, UINT, const GUIDx *, void **))VT(sc)[S_GetBuffer])(sc, 0, &IID_Tex2D, &bb) >= 0 && bb) { TEX2D_DESC d; desc_tex(bb, d); g_bw = d.Width; g_bh = d.Height; Ligne l; l.s("image presentee : "); dire_tex(l, bb); journal(l); ((UINT (WINAPI *)(void *))VT(bb)[2])(bb); } }
	g_vues_rapport += g_vues_traitees;
	g_vues_image = 0; g_vues_traitees = 0;
	reposer();

	i64 t1; QueryPerformanceCounter(&t1); g_cpu_ms += (double)(t1 - t0) * 1000.0 / (double)g_freq;
	if (now - g_t_rapport > 2000 && g_n_img) {
		Ligne l; l.s("mesure : "); l.f(1000.0 * g_n_img / (g_somme_ms > 0 ? g_somme_ms : 1), 1); l.s(" img/s, image moy "); l.f(g_somme_ms / g_n_img); l.s(" ms, pire ");
		l.f(g_pire_ms); l.s(" ms, TSC CPU "); l.f(g_cpu_ms / g_n_img, 3); l.s(" ms, TSC GPU "); if (g_n_gpu) l.f(g_gpu_ms / g_n_gpu, 3); else l.s("-"); l.s(" ms ; vues traitees/image ");
		l.f((double)g_vues_rapport / g_n_img, 2); l.s(" ; effet "); l.s(g_effet_on > 0.5f && R.actif > 0.5f ? "marche" : "arret"); l.s(" ; pluie "); l.s(g_pluie ? "oui" : "non");
		l.s(" (gouttes max "); l.i(g_gouttes_rapport); l.s(") ; humidite "); l.f(R.humidite >= 0 ? R.humidite : g_mouille); l.s(" ; G-buffer vus "); l.i(g_n_gbuf); l.s(", HDR vus "); l.i(g_n_hdr);
		l.s(" ; effacement z="); l.f(g_val_effacement, 3); l.s(" ; crochets reposes "); l.i(g_reposes);
		journal(l);
		g_t_rapport = now; g_somme_ms = g_pire_ms = g_cpu_ms = g_gpu_ms = 0; g_n_img = g_n_gpu = 0; g_vues_rapport = 0; g_gouttes_rapport = 0; g_n_gbuf = g_n_hdr = 0;
	}
	if (g_trace) {
		if (--g_trace == 0) { Ligne l; l.s("=== fin de la trace ==="); trace_txt(l); ecrire("tsc-graphics-trace.log", g_tbuf, g_tn); logline("trace ecrite dans tsc-graphics-trace.log"); }
		else { g_tn = 0; Ligne l; l.s("=== trace d'une image, "); l.s(VERSION); l.s(", image "); l.i(g_bw); l.s("x"); l.i(g_bh); l.s(" ==="); trace_txt(l); }
	}
}

static HRESULT WINAPI h_present(void *sc, UINT sync, UINT fl) { if (!(fl & 1)) apres_image(sc); return o_present(sc, sync, fl); }
static HRESULT WINAPI h_present1(void *sc, UINT sync, UINT fl, const void *p) { if (!(fl & 1)) apres_image(sc); return o_present1(sc, sync, fl, p); }
static HRESULT WINAPI h_resize(void *sc, UINT n, UINT w, UINT h, UINT f, UINT fl) { g_bw = g_bh = 0; logline("changement de taille de l'image"); return o_resize(sc, n, w, h, f, fl); }

/* ---------- branchement ---------- */
static i64 WINAPI proc_fen(void *h, UINT m, u64 w, i64 l) { return DefWindowProcA(h, m, w, l); }
extern "C" int scs_telemetry_init(unsigned version, const void *params) {
	(void)version; (void)params;
	logline(VERSION " : demarrage");
	lire_ini(true);
	HMODULE d3d = LoadLibraryA("d3d11.dll"); if (!d3d) { logline("d3d11.dll introuvable"); return 0; }
	PFN_CREATE_SC cr = (PFN_CREATE_SC)GetProcAddress(d3d, "D3D11CreateDeviceAndSwapChain"); if (!cr) { logline("D3D11CreateDeviceAndSwapChain introuvable"); return 0; }
	WNDCLASSEXx wc; memset(&wc, 0, sizeof wc); wc.cbSize = sizeof wc; wc.proc = (void *)proc_fen; wc.inst = g_mod; wc.name = "TSCGraphicsSonde";
	RegisterClassExA(&wc);
	void *fen = CreateWindowExA(0, "TSCGraphicsSonde", "", 0, 0, 0, 64, 64, 0, 0, g_mod, 0);
	if (!fen) { logline("fenetre jetable impossible"); return 0; }
	SWAP_DESC sd; memset(&sd, 0, sizeof sd); sd.w = 64; sd.h = 64; sd.fmt = 28; sd.cnt = 1; sd.usage = 0x20; sd.nbuf = 1; sd.hwnd = fen; sd.windowed = 1;
	void *sc = 0, *dev = 0, *ctx = 0; int fl = 0;
	HRESULT hr = cr(0, 1, 0, 0, 0, 0, 7, &sd, &sc, &dev, &fl, &ctx);
	if (hr < 0 || !sc) { logline("appareil et chaine jetables impossibles", hr & 0xffffffffLL); DestroyWindow(fen); return 0; }
	g_vt_sc = VT(sc); g_vt_ctx = VT(ctx);
	int ok = 1;
	ok &= poser(g_vt_sc, S_Present, (void *)h_present, (void **)&o_present);
	ok &= poser(g_vt_sc, S_ResizeBuffers, (void *)h_resize, (void **)&o_resize);
	poser(g_vt_sc, S1_Present1, (void *)h_present1, (void **)&o_present1);
	for (auto &c : g_cr) ok &= poser(g_vt_ctx, c.i, c.f, c.o);
	g_hooks = 1;
	logline(ok ? "crochets poses (Present, ResizeBuffers, cibles, effacements, viewports, dessins)" : "certains crochets n'ont pas pu etre poses");
	REL(ctx); REL(dev); REL(sc); DestroyWindow(fen);
	HMODULE h; GetModuleHandleExA(5, (const char *)&scs_telemetry_init, &h);
	return 0;
}
extern "C" void scs_telemetry_shutdown(void) {
	if (!g_hooks) return;
	for (auto &c : g_cr) if (g_vt_ctx[c.i] == c.f) retirer(g_vt_ctx, c.i, *c.o);
	if (o_present1 && g_vt_sc[S1_Present1] == (void *)h_present1) retirer(g_vt_sc, S1_Present1, (void *)o_present1);
	if (g_vt_sc[S_ResizeBuffers] == (void *)h_resize) retirer(g_vt_sc, S_ResizeBuffers, (void *)o_resize);
	if (g_vt_sc[S_Present] == (void *)h_present) retirer(g_vt_sc, S_Present, (void *)o_present);
	g_hooks = 0; logline("crochets retires");
}
extern "C" BOOL WINAPI DllMain(HMODULE h, DWORD r, void *x) {
	(void)x;
	if (r == 1) { g_mod = h; GetModuleFileNameA(h, g_dir, 290); int i = lng(g_dir); while (i > 0 && g_dir[i - 1] != '\\' && g_dir[i - 1] != '/') i--; g_dir[i] = 0; }
	if (r == 0 && !x) scs_telemetry_shutdown();
	return 1;
}
