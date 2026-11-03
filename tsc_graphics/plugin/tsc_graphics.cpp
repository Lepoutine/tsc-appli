/* tsc-graphics.dll : TSC Neural Graphics, rendu temps reel dans ETS2 (DirectX 11). Plugin SDK SCS charge par le jeu
   (bin/win_x64/plugins). Copyright (c) 2026 Truck So Clean France. Sans CRT, sans SDK Windows (clang + lld).

   0.4 : profileur TSC v1 : par image (Present a Present) temps d'image, temps GPU de toute l'image (requetes horodatees,
         anneau de 6 images, lecture sans attente), dessins, changements de cibles, vues G-buffer / traitees, lectures CPU
         bloquantes du jeu (Map en lecture, GetData), creations de shaders et de textures, memoire video (DXGI 1.4), ecrits
         dans tsc-profil.csv (tampon vide ~1 fois par seconde) ; verdict plafond / GPU / CPU / marge dans la ligne mesure.
   0.3 : route mouillee v1, calee sur les videos reelles (reflets en colonnes verticales floues, flou qui grandit avec la
         distance du rayon, asphalte mouille plus sombre, marquages mats) : copie HDR avec chaine de mips (GenerateMips).
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
__declspec(dllimport) BOOL WINAPI CreateDirectoryA(const char *, void *);
__declspec(dllimport) void *WINAPI VirtualAlloc(void *, SIZE_T, DWORD, DWORD);
__declspec(dllimport) BOOL WINAPI FlushInstructionCache(HANDLE, const void *, SIZE_T);
__declspec(dllimport) HANDLE WINAPI GetCurrentProcess(void);
__declspec(dllimport) HANDLE WINAPI FindFirstFileA(const char *, void *);
__declspec(dllimport) BOOL WINAPI FindNextFileA(HANDLE, void *);
__declspec(dllimport) BOOL WINAPI FindClose(HANDLE);
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
#define VERSION "tsc-graphics 0.13"
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
	float flou = 0.25f, etirement = 0.8f, peinture = 0.6f, decalage_z = -0.000194f, bascule_auto = 0;
	float vue = 0, seuil_gouttes = 500, mouille_s = 40, seche_s = 300, max_vues = 3;
	float profil = 1;   /* 1 = profileur : une ligne par image dans tsc-profil.csv */
	float camera = 1, brouillard = 0, diffusion = 0.3f, grain = 0.012f, sat_hautes = 0, ext_desat = 0.1f, ombres = 0.8f;   /* camera v1 (0.5) */
	/* 0.6 : modes (0 personnalise, 1 performance extreme, 2 photorealisme optimise), budget GPU, ambiances, eau sur vitre */
	float mode = 2, budget_ms = 4, ambiance_auto = 1, nuit_lum = 0.02f, jour_lum = 0.25f, vitre = 1, gouttes_taille = 1;
	/* 0.7 : T2 a montre une image quasi inchangee (< 1 point de luminosite) : devoile du jeu, contraste local, noirs, lumiere du soleil, vegetation */
	float devoile = 0.5f, clarte = 0.12f, noirs = 0.08f, chaleur = 0.12f, vegetation = 0.6f;
	/* 0.8 : T3 = image 10 % plus sombre, noirs bouches, vegetation jaune-olive, route brune ; le reel (mesures_reel.json) a une
	   route claire et neutre, des hautes lumieres plus hautes et plus saturees. Tout est reglable a chaud pour caler sans nouveau test. */
	float exposition = 1, gamma_monde = 0.1f, hautes = 0.35f, saturation = 1, veg_teinte = 0.6f, neutre = 0.5f;
	/* 0.9 : etage APRES l'auto-exposition et le tone mapping du jeu (cible 1280x1080 R8G8B8A8_UNORM_SRGB de chaque vue, avant
	   sa composition dans l'image 3840 et avant l'interface ; trace 0.8 du 03/11). L'auto-exposition ne peut plus l'annuler. */
	/* valeurs de depart d'apres mesures_reel_v2 (jour) contre le jeu : p50 0,49 -> 0,61, p99 0,84 -> 0,99, vegetation trop sombre et
	   trop saturee (75/94/40 contre 132/152/112), hautes lumieres PLUS saturees que le reel (0,26-0,29 contre 0,19 en HSV) */
	float ldr = 1, ldr_expo = 1.5f, ldr_contraste = 1, ldr_epaule = 0.75f, ldr_sat = 0.88f, ldr_sat_hautes = -0.3f, ldr_temperature = 0, ldr_teinte = 0, ldr_noirs = 0, ldr_verts = 0.4f;
	/* 0.9.2 : table de couleurs 3D apprise sur les videos reelles (tsc-graphics-lut.bin, 32x32x32 RGBA 16 bits), force 0-1 */
	float ldr_lut = 1;
	/* 0.9.3 : TSC Neural, donnees d'entrainement : changer ce nombre (N) = N images enregistrees, une toutes les 2 s, image du jeu
	   SANS effet TSC (HDR, profondeur, albedo+feuillage, vue 8 bits du jeu) dans plugins\\tsc_neural */
	float enregistre = 0;
	float textures_hd = 1;   /* 0.13 : remplacement a la volee par plugins\\tsc_textures_hd\\<empreinte>.dds (1 = marche, 0 = textures du jeu) */
	float vider_textures = 0;   /* 0.12 : TSC Textures, extraction du niveau 0 des textures de decor en .dds (Mo maximum ; 0 = coupe) -> plugins\\tsc_textures_brut */
	float sonde_textures = 1;   /* 0.10 : TSC Textures, releve des textures chargees par le jeu (empreinte + format) -> tsc-textures.csv */
	float trace = 0;   /* changer ce nombre (1, 2, 3...) dans l'ini = trace d'une image, sans touche */
	float taille_min = 512;   /* T1 03/11 : ignorer les petites vues (sondes de reflets 256x128/256x256), seulement les vues principales */
};
static Reglages R; static u64 g_ini_hash;
static float g_qualite = 1;   /* 0.6 : gestionnaire de budget GPU (0,4 a 1), ajuste toutes les 2 s */
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
		{"mouille_s", &R.mouille_s}, {"seche_s", &R.seche_s}, {"max_vues", &R.max_vues},
		{"flou", &R.flou}, {"etirement", &R.etirement}, {"peinture", &R.peinture}, {"decalage_z", &R.decalage_z}, {"bascule_auto", &R.bascule_auto},
		{"profil", &R.profil}, {"taille_min", &R.taille_min}, {"trace", &R.trace},
		{"camera", &R.camera}, {"brouillard", &R.brouillard}, {"diffusion", &R.diffusion}, {"grain", &R.grain}, {"sat_hautes", &R.sat_hautes},
		{"ext_desat", &R.ext_desat}, {"ombres", &R.ombres},
		{"mode", &R.mode}, {"budget_ms", &R.budget_ms}, {"ambiance_auto", &R.ambiance_auto}, {"nuit_lum", &R.nuit_lum},
		{"jour_lum", &R.jour_lum}, {"vitre", &R.vitre}, {"gouttes_taille", &R.gouttes_taille},
		{"devoile", &R.devoile}, {"clarte", &R.clarte}, {"noirs", &R.noirs}, {"chaleur", &R.chaleur}, {"vegetation", &R.vegetation},
		{"exposition", &R.exposition}, {"gamma_monde", &R.gamma_monde}, {"hautes", &R.hautes}, {"saturation", &R.saturation},
		{"veg_teinte", &R.veg_teinte}, {"neutre", &R.neutre},
		{"ldr", &R.ldr}, {"ldr_expo", &R.ldr_expo}, {"ldr_contraste", &R.ldr_contraste}, {"ldr_epaule", &R.ldr_epaule}, {"ldr_sat", &R.ldr_sat},
		{"ldr_sat_hautes", &R.ldr_sat_hautes}, {"ldr_temperature", &R.ldr_temperature}, {"ldr_teinte", &R.ldr_teinte}, {"ldr_noirs", &R.ldr_noirs}, {"ldr_verts", &R.ldr_verts}, {"ldr_lut", &R.ldr_lut}, {"enregistre", &R.enregistre}, {"sonde_textures", &R.sonde_textures}, {"vider_textures", &R.vider_textures}, {"textures_hd", &R.textures_hd} };
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
	C_OMSetRT = 33, C_RSSetViewports = 44, C_CopySubresourceRegion = 46, C_CopyResource = 47, C_UpdateSubresource = 48, C_ClearRTV = 50, C_ClearDSV = 53, C_GenerateMips = 54, C1_SwapState = 131,
	/* 0.4.3 : sauvegarde / restauration manuelle (T1c : SwapDeviceContextState faisait perdre au jeu la suite de l'image) */
	C_IASetInputLayout = 17, C_GSSetShader = 23, C_OMSetBlend = 35, C_OMSetDSS = 36, C_RSSetState = 43, C_RSSetScissor = 45,
	C_HSSetShader = 60, C_DSSetShader = 64,
	C_PSGetSRV = 73, C_PSGetShader = 74, C_PSGetSamplers = 75, C_VSGetShader = 76, C_PSGetCB = 77, C_IAGetInputLayout = 78,
	C_GSGetShader = 82, C_IAGetTopology = 83, C_OMGetRT = 89, C_OMGetBlend = 91, C_OMGetDSS = 92, C_RSGetState = 94, C_RSGetViewports = 95,
	C_RSGetScissor = 96, C_HSGetShader = 98, C_DSGetShader = 102 };
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
static void **g_vt_sc, **g_vt_ctx; static int g_hooks, g_arret;
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
static int g_vues_image, g_vues_traitees; static i64 g_n_petites;  /* G-buffer de petites vues ignorees (sondes) */ /* vues vues / traitees sur l'image en cours */
static int g_dans_gouttes; static i64 g_gouttes, g_gouttes_rapport;
static float g_mouille = 0; static int g_pluie;
static i64 g_n_gbuf, g_n_hdr;             /* diagnostics */
static float g_val_effacement = -1;

/* ---------- nos ressources ---------- */
static void *g_dev, *g_ctx, *g_dev1, *g_ctx1, *g_etat, *g_vs, *g_ps, *g_cb, *g_samp_lin, *g_samp_pt;
static void *g_ps_lm, *g_lm, *g_lm_srv, *g_lm_rtv;
static void *g_lut, *g_lut_srv; static u64 g_lut_hash;
static int g_enr_image, g_enr_reste, g_enr_num; static u64 g_enr_t;   /* 0.9.3 : enregistrement TSC Neural */   /* 0.9.2 : table de couleurs 3D */   /* 0.9.1 : reference de lumiere partagee par les 3 vues */
static void *g_ps_ldr, *g_ldr, *g_ldr_srv, *g_ldr_tex; static UINT g_ldr_w, g_ldr_h, g_ldr_fmt; static int g_ldr_n; static i64 g_n_ldr;   /* 0.9 */
static void *g_coul, *g_coul_srv; static UINT g_coul_w, g_coul_h, g_coul_fmt, g_coul_mips = 1;
static void *g_prof, *g_prof_srv; static UINT g_prof_w, g_prof_h, g_prof_fmt;
/* 0.7 : cible 2 du G-buffer de la vue (albedo RGB, alpha = masque du feuillage, audit socle v0.3) et sa copie */
static void *g_gb2_tex, *g_gb2, *g_gb2_srv; static UINT g_gb2_w, g_gb2_h, g_gb2_fmt; static bool g_gb2_valide;
struct Rtv { void *tex, *rtv; }; static Rtv g_rtv[8]; static int g_nrtv;
#define NQ 4
#define QV 4
static void *g_q_dis[NQ], *g_q_a[NQ][QV], *g_q_b[NQ][QV]; static int g_q_n[NQ], g_q_i, g_q_ouvert;
static PFN_COMPILE g_compile; static u64 g_hlsl_hash; static int g_shaders_ok;
static float g_effet_on = 1; static int g_vue = 0;
static i64 g_freq, g_t_prec; static double g_somme_ms, g_pire_ms, g_cpu_ms, g_gpu_ms; static int g_n_img, g_n_gpu; static u64 g_t_rapport; static i64 g_vues_rapport;
static u64 g_vram;

static i64 g_n_omsrt, g_n_dessins;

/* ---------- profileur TSC v1 : etat (tout en memoire statique, aucune allocation) ----------
   Temps GPU de toute l'image : horodatage juste apres le retour du Present (debut de l'image) et juste avant le Present
   suivant (fin), dans une requete TIMESTAMP_DISJOINT ; anneau de NP images ; lecture sans attente (GetData DONOTFLUSH)
   des images vieilles d'au moins 3 ; une requete pas encore prete quand son emplacement revient est abandonnee (jamais
   d'attente). Ce temps va du debut a la fin de l'image cote GPU : les trous ou le GPU attend (CPU en retard, file de
   presentation pleine sous synchro verticale) y sont inclus : c'est une borne haute de l'occupation du GPU.
   Les lignes du CSV restent NR images en memoire le temps que le temps GPU arrive, puis vont dans un tampon ecrit ~1 fois
   par seconde. */
#define NP 6
#define NR 8
struct ProfGpu { void *dis, *a, *b; i64 img; int etat; };   /* etat : 0 libre, 1 ouverte, 2 en attente du GPU */
static ProfGpu g_pg[NP]; static int g_pg_ok;
struct ProfLigne { i64 img, dessins, cibles, vues_g, vues_t, map_lect, getdata, ps, tex; double t_ms, image_ms, gpu_ms, map_ms, gd_ms, cree_ms; int vram_mo, effet, pleine; };
static ProfLigne g_pl[NR];
static i64 g_p_img = 1, g_p_t0;                                   /* image en cours (ouverte apres le Present precedent) */
static i64 g_pf_dessins, g_pf_cibles, g_pf_map, g_pf_map_t, g_pf_gd, g_pf_gd_t;   /* image en cours (contexte immediat, ticks QPC) */
static i64 g_cree_ps, g_cree_tex, g_cree_t;                       /* creations sur l'appareil, tous fils : operations atomiques */
static void *g_adapt3; static int g_vram_mo = -1, g_vram_budget_mo = -1;
static char g_csv[65536]; static int g_csv_n, g_csv_entete; static u64 g_csv_t;
/* fenetre du rapport (2 s) pour le verdict */
static int g_hist[500];                                           /* temps d'image par pas de 0,2 ms (0-100 ms) */
static int g_pw_n, g_pw_16, g_pw_33, g_pw_ngpu; static double g_pw_img, g_pw_gpu, g_pw_gpu_img, g_prof_cpu_ms;
static i64 g_pw_map, g_pw_gd, g_pw_cree; static double g_pw_map_ms, g_pw_gd_ms, g_pw_cree_ms;
static double ms_de(i64 t) { return g_freq ? (double)t * 1000.0 / (double)g_freq : 0; }

static void compter() {
	if (g_nous) return;
	g_n_dessins++; g_pf_dessins++;
	if (g_trace) g_trace_dessins++;
	if (g_dans_gouttes) g_gouttes++;
}
static HRESULT dev_tex(const TEX2D_DESC *d, void **out) {   /* g_nous : nos creations ne comptent pas dans le profileur */
	g_nous++; HRESULT hr = ((HRESULT (WINAPI *)(void *, const TEX2D_DESC *, const void *, void **))VT(g_dev)[D_CreateTexture2D])(g_dev, d, 0, out); g_nous--; return hr; }

/* 0.9.2 : table de couleurs 3D relue a chaud (comme l'ini) ; absente = etage sans table */
struct TEX3D_DESC { UINT Width, Height, Depth, MipLevels, Format, Usage, BindFlags, CPUAccessFlags, MiscFlags; };
struct SUBRES { const void *p; UINT pitch, slice; };
static void charger_lut() {
	enum { N = 32, TAILLE = N * N * N * 8 };
	static char b[TAILLE + 16]; int n = lire_fichier("tsc-graphics-lut.bin", b, sizeof b);
	if (n != TAILLE) { if (g_lut && n < 0) { REL(g_lut_srv); REL(g_lut); g_lut_hash = 0; logline("table de couleurs retiree"); } return; }
	u64 h = 1469598103934665603ULL; for (int i = 0; i < n; i++) h = (h ^ (unsigned char)b[i]) * 1099511628211ULL;
	if (h == g_lut_hash) return; g_lut_hash = h;
	REL(g_lut_srv); REL(g_lut);
	TEX3D_DESC d = {N, N, N, 1, 11 /*R16G16B16A16_UNORM*/, 0, 8, 0, 0};
	SUBRES sr = {b, N * 8, N * N * 8};
	g_nous++;
	HRESULT hr = ((HRESULT (WINAPI *)(void *, const TEX3D_DESC *, const SUBRES *, void **))VT(g_dev)[6 /*CreateTexture3D*/])(g_dev, &d, &sr, &g_lut);
	if (hr >= 0 && g_lut) ((HRESULT (WINAPI *)(void *, void *, const void *, void **))VT(g_dev)[D_CreateSRV])(g_dev, g_lut, 0, &g_lut_srv);
	g_nous--;
	if (hr < 0 || !g_lut_srv) { REL(g_lut); logline("table de couleurs refusee", hr); return; }
	logline("table de couleurs chargee (tsc-graphics-lut.bin, 32x32x32)");
}
/* 0.9.3 : copie GPU -> disque d'une texture (niveau 0), en-tete 32 octets : "TSCN", largeur, hauteur, format DXGI, pas de ligne */
static void vider_tex(void *src, const char *quoi, int vue) {
	TEX2D_DESC d; desc_tex(src, d);
	TEX2D_DESC n = {d.Width, d.Height, 1, 1, d.Format, 1, 0, 3 /*STAGING*/, 0, 0x20000 /*CPU_READ*/, 0};
	void *st = 0; if (dev_tex(&n, &st) < 0 || !st) { logline("enregistrement : texture de lecture refusee"); return; }
	((void (WINAPI *)(void *, void *, UINT, UINT, UINT, UINT, void *, UINT, const void *))VT(g_ctx)[C_CopySubresourceRegion])(g_ctx, st, 0, 0, 0, 0, src, 0, 0);
	struct { void *p; UINT rp, dp; } m = {0, 0, 0};
	if (((HRESULT (WINAPI *)(void *, void *, UINT, UINT, UINT, void *))VT(g_ctx)[C_Map])(g_ctx, st, 0, 1 /*READ*/, 0, &m) >= 0 && m.p) {
		char p[400] = {0}; cat(p, g_dir); cat(p, "tsc_neural"); CreateDirectoryA(p, 0);
		Ligne nm; nm.s("\\i"); { i64 v = g_enr_num; char b[8]; for (int k = 5; k >= 0; k--) { b[k] = (char)('0' + v % 10); v /= 10; } b[6] = 0; nm.s(b); }
		nm.s("_v"); nm.i(vue); nm.s("_"); nm.s(quoi); nm.s(".raw"); cat(p, nm.t);
		HANDLE f = CreateFileA(p, 0x40000000 /*GENERIC_WRITE*/, 0, 0, 2 /*CREATE_ALWAYS*/, 0x80, 0);
		if (f != INVALID) {
			UINT h[8] = {0x4E435354, d.Width, d.Height, d.Format, m.rp, 0, 0, 0}; DWORD w;
			WriteFile(f, h, sizeof h, &w, 0); WriteFile(f, m.p, m.rp * d.Height, &w, 0); CloseHandle(f);
		}
		((void (WINAPI *)(void *, void *, UINT))VT(g_ctx)[C_Unmap])(g_ctx, st, 0);
	}
	REL(st);
}
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
	g_nous++;
	HRESULT c1 = ((HRESULT (WINAPI *)(void *, const void *, SIZE_T, void *, void **))VT(g_dev)[D_CreateVS])(g_dev, ((PTR)VT(bv)[3])(bv), ((TAILLE)VT(bv)[4])(bv), 0, &vs);
	HRESULT c2 = ((HRESULT (WINAPI *)(void *, const void *, SIZE_T, void *, void **))VT(g_dev)[D_CreatePS])(g_dev, ((PTR)VT(bp)[3])(bp), ((TAILLE)VT(bp)[4])(bp), 0, &ps);
	g_nous--;
	REL(bv); REL(bp);
	if (c1 < 0 || c2 < 0) { REL(vs); REL(ps); logline("creation des shaders refusee"); g_shaders_ok = 0; return; }
	REL(g_vs); REL(g_ps); g_vs = vs; g_ps = ps; g_shaders_ok = 1; logline("shaders compiles (tsc-graphics.hlsl)");
	/* 0.9.1 : reference de lumiere commune ; sans elle chaque vue garde sa propre moyenne (comme en 0.8) */
	{
		void *bm = 0, *pm = 0;
		if (g_compile(src, (SIZE_T)n, "tsc-graphics.hlsl", 0, 0, "ps_lm", "ps_5_0", fl, 0, &bm, &err) < 0) { REL(err); REL(g_ps_lm); logline("ps_lm non compile : reference par vue"); }
		else {
			REL(err); g_nous++;
			HRESULT c4 = ((HRESULT (WINAPI *)(void *, const void *, SIZE_T, void *, void **))VT(g_dev)[D_CreatePS])(g_dev, ((PTR)VT(bm)[3])(bm), ((TAILLE)VT(bm)[4])(bm), 0, &pm);
			g_nous--; REL(bm);
			REL(g_ps_lm); if (c4 >= 0) g_ps_lm = pm; else REL(pm);
		}
	}
	/* 0.9 : etage apres tone mapping ; s'il ne compile pas, seul cet etage est coupe */
	void *bl = 0, *pl = 0;
	if (g_compile(src, (SIZE_T)n, "tsc-graphics.hlsl", 0, 0, "ps_ldr", "ps_5_0", fl, 0, &bl, &err) < 0) {
		Ligne l; l.s("erreur shader ps_ldr (etage apres tone mapping coupe) : "); if (err) l.s((const char *)((void *(WINAPI *)(void *))VT(err)[3])(err)); journal(l); REL(err); REL(g_ps_ldr); return; }
	REL(err);
	g_nous++;
	HRESULT c3 = ((HRESULT (WINAPI *)(void *, const void *, SIZE_T, void *, void **))VT(g_dev)[D_CreatePS])(g_dev, ((PTR)VT(bl)[3])(bl), ((TAILLE)VT(bl)[4])(bl), 0, &pl);
	g_nous--; REL(bl);
	if (c3 < 0) { REL(pl); REL(g_ps_ldr); logline("creation ps_ldr refusee"); return; }
	REL(g_ps_ldr); g_ps_ldr = pl; logline("etage apres tone mapping pret (ps_ldr)");
}

static void accrocher_contexte();
static void prof_init();
static void module_de(Ligne &l, void *adr) {
	HMODULE m = 0; char n[300]; n[0] = 0;
	if (adr && GetModuleHandleExA(6, (const char *)adr, &m) && m) GetModuleFileNameA(m, n, 299);
	l.s(n[0] ? n : "?");
}
static bool init_appareil(void *sc) {
	if (g_dev) return g_etat != 0;
	if (((HRESULT (WINAPI *)(void *, const GUIDx *, void **))VT(sc)[S_GetDevice])(sc, &IID_Dev, &g_dev) < 0 || !g_dev) { logline("GetDevice refuse"); g_dev = 0; return false; }
	((void (WINAPI *)(void *, void **))VT(g_dev)[40])(g_dev, &g_ctx);
	((HRESULT (WINAPI *)(void *, const GUIDx *, void **))VT(g_dev)[0])(g_dev, &IID_Dev1, &g_dev1);
	if (g_ctx) ((HRESULT (WINAPI *)(void *, const GUIDx *, void **))VT(g_ctx)[0])(g_ctx, &IID_Ctx1, &g_ctx1);
	prof_init();   /* profileur : ne depend pas de D3D11.1 */
	if (!g_dev1 || !g_ctx1) { logline("D3D11.1 indisponible : effet impossible (sonde seule)"); return false; }
	int fl = ((int (WINAPI *)(void *))VT(g_dev)[D_GetFeatureLevel])(g_dev), choisi = 0;
	HRESULT hr = ((HRESULT (WINAPI *)(void *, UINT, const int *, UINT, UINT, const GUIDx *, int *, void **))VT(g_dev1)[D1_CreateDeviceContextState])(g_dev1, 0, &fl, 1, 7, &IID_Dev, &choisi, &g_etat);
	if (hr < 0 || !g_etat) { logline("CreateDeviceContextState refuse", hr & 0xffffffffLL); g_etat = 0; return false; }
	BUF_DESC bd = {256, 2, 4, 0x10000, 0, 0};
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
	/* essai 0.3 du 03/11 : aucune passe vue -> le contexte du jeu n'utilise pas la table de l'appareil jetable
	   (autre classe, ou contexte enveloppe par une autre couche). On pose les crochets sur la table du VRAI contexte. */
	accrocher_contexte();
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
		/* copie HDR avec 6 niveaux de mips (SRV + RTV, GENERATE_MIPS) pour les reflets flous ; a defaut, un seul niveau */
		TEX2D_DESC n = {h.Width, h.Height, 6, 1, h.Format, 1, 0, 0, 8 | 32, 0, 1};
		g_coul_mips = 6;
		if (dev_tex(&n, &g_coul) < 0) {
			g_coul = 0; g_coul_mips = 1; logline("copie HDR avec mips refusee : reflets sans flou (un seul niveau)");
			TEX2D_DESC n1 = {h.Width, h.Height, 1, 1, h.Format, 1, 0, 0, 8, 0, 0};
			if (dev_tex(&n1, &g_coul) < 0) { g_coul = 0; return false; }
		}
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
		g_vram = (u64)h.Width * h.Height * 8 * (g_coul_mips > 1 ? 4 : 3) / 3 + (u64)d.Width * d.Height * 8;
		Ligne l; l.s("copies creees : HDR "); dire_tex(l, g_coul); l.s(" ; profondeur "); dire_tex(l, g_prof); l.s(" ; memoire video ajoutee ~"); l.i((i64)(g_vram >> 20)); l.s(" Mo"); journal(l);
	}
	if (!g_lm) {
		TEX2D_DESC n = {1, 1, 1, 1, 41 /*R32_FLOAT*/, 1, 0, 0, 8 | 32, 0, 0};
		if (dev_tex(&n, &g_lm) >= 0) {
			((HRESULT (WINAPI *)(void *, void *, const void *, void **))VT(g_dev)[D_CreateSRV])(g_dev, g_lm, 0, &g_lm_srv);
			((HRESULT (WINAPI *)(void *, void *, const void *, void **))VT(g_dev)[D_CreateRTV])(g_dev, g_lm, 0, &g_lm_rtv);
			logline("reference de lumiere commune creee (1x1)");
		} else g_lm = 0;
	}
	/* 0.7 : copie de l'albedo + masque du feuillage ; sans elle, la couche vegetation est simplement coupee (t2 vide) */
	g_gb2_valide = false;
	if (g_gb2_tex) {
		TEX2D_DESC g; desc_tex(g_gb2_tex, g);
		if (g.SampleCount > 1 || g.Width != h.Width || g.Height != h.Height) { /* pas la meme vue : on n'utilise pas */ }
		else if (!g_gb2 || g_gb2_w != g.Width || g_gb2_h != g.Height || g_gb2_fmt != g.Format) {
			REL(g_gb2_srv); REL(g_gb2);
			TEX2D_DESC n = {g.Width, g.Height, 1, 1, g.Format, 1, 0, 0, 8, 0, 0};
			if (dev_tex(&n, &g_gb2) < 0) g_gb2 = 0;
			else {
				((HRESULT (WINAPI *)(void *, void *, const void *, void **))VT(g_dev)[D_CreateSRV])(g_dev, g_gb2, 0, &g_gb2_srv);
				g_gb2_w = g.Width; g_gb2_h = g.Height; g_gb2_fmt = g.Format;
				Ligne l; l.s("copie du G-buffer (albedo + feuillage) creee : "); dire_tex(l, g_gb2); journal(l);
			}
		}
		if (g_gb2 && g_gb2_srv && g_gb2_w == g.Width && g_gb2_h == g.Height && g_gb2_fmt == g.Format && g.SampleCount <= 1) g_gb2_valide = true;
	}
	return g_coul_srv && g_prof_srv;
}


/* ---------- 0.4.3 : etat du jeu sauve puis remis a l'identique autour de la passe TSC ---------- */
struct EtatJeu {
	void *rtv[8], *dsv, *vs, *ps, *gs, *hs, *ds, *il, *bl, *dss, *rs, *srv[5], *smp[2], *cb;
	float bf[4]; UINT masque, sref, topo, nvp, nsc; VIEWPORT vp[16]; long sc[16][4];
};
typedef void (WINAPI *GetSh)(void *, void **, void **, UINT *);
typedef void (WINAPI *SetSh)(void *, void *, void *const *, UINT);
static void sauver(EtatJeu &e) {
	memset(&e, 0, sizeof e); void *c = g_ctx;
	((void (WINAPI *)(void *, UINT, void **, void **))VT(c)[C_OMGetRT])(c, 8, e.rtv, &e.dsv);
	UINT n = 0;
	((GetSh)VT(c)[C_VSGetShader])(c, &e.vs, 0, &n); n = 0;
	((GetSh)VT(c)[C_PSGetShader])(c, &e.ps, 0, &n); n = 0;
	((GetSh)VT(c)[C_GSGetShader])(c, &e.gs, 0, &n); n = 0;
	((GetSh)VT(c)[C_HSGetShader])(c, &e.hs, 0, &n); n = 0;
	((GetSh)VT(c)[C_DSGetShader])(c, &e.ds, 0, &n);
	((void (WINAPI *)(void *, void **))VT(c)[C_IAGetInputLayout])(c, &e.il);
	((void (WINAPI *)(void *, UINT *))VT(c)[C_IAGetTopology])(c, &e.topo);
	((void (WINAPI *)(void *, void **, float *, UINT *))VT(c)[C_OMGetBlend])(c, &e.bl, e.bf, &e.masque);
	((void (WINAPI *)(void *, void **, UINT *))VT(c)[C_OMGetDSS])(c, &e.dss, &e.sref);
	((void (WINAPI *)(void *, void **))VT(c)[C_RSGetState])(c, &e.rs);
	e.nvp = 16; ((void (WINAPI *)(void *, UINT *, VIEWPORT *))VT(c)[C_RSGetViewports])(c, &e.nvp, e.vp);
	e.nsc = 16; ((void (WINAPI *)(void *, UINT *, void *))VT(c)[C_RSGetScissor])(c, &e.nsc, e.sc);
	((void (WINAPI *)(void *, UINT, UINT, void **))VT(c)[C_PSGetSRV])(c, 0, 5, e.srv);
	((void (WINAPI *)(void *, UINT, UINT, void **))VT(c)[C_PSGetSamplers])(c, 0, 2, e.smp);
	((void (WINAPI *)(void *, UINT, UINT, void **))VT(c)[C_PSGetCB])(c, 0, 1, &e.cb);
}
static void remettre(EtatJeu &e) {
	void *c = g_ctx;
	((SetSh)VT(c)[C_VSSetShader])(c, e.vs, 0, 0);
	((SetSh)VT(c)[C_PSSetShader])(c, e.ps, 0, 0);
	((SetSh)VT(c)[C_GSSetShader])(c, e.gs, 0, 0);
	((SetSh)VT(c)[C_HSSetShader])(c, e.hs, 0, 0);
	((SetSh)VT(c)[C_DSSetShader])(c, e.ds, 0, 0);
	((void (WINAPI *)(void *, void *))VT(c)[C_IASetInputLayout])(c, e.il);
	((void (WINAPI *)(void *, UINT))VT(c)[C_IASetTopology])(c, e.topo);
	((void (WINAPI *)(void *, void *, const float *, UINT))VT(c)[C_OMSetBlend])(c, e.bl, e.bf, e.masque);
	((void (WINAPI *)(void *, void *, UINT))VT(c)[C_OMSetDSS])(c, e.dss, e.sref);
	((void (WINAPI *)(void *, void *))VT(c)[C_RSSetState])(c, e.rs);
	((void (WINAPI *)(void *, UINT, const VIEWPORT *))VT(c)[C_RSSetViewports])(c, e.nvp, e.vp);
	((void (WINAPI *)(void *, UINT, const void *))VT(c)[C_RSSetScissor])(c, e.nsc, e.sc);
	/* cibles d'abord, puis ressources (sinon le pilote delie une SRV encore liee en cible) */
	UINT nrt = 0; for (UINT k = 0; k < 8; k++) if (e.rtv[k]) nrt = k + 1;
	((void (WINAPI *)(void *, UINT, void *const *, void *))VT(c)[C_OMSetRT])(c, nrt, e.rtv, e.dsv);
	((void (WINAPI *)(void *, UINT, UINT, void *const *))VT(c)[C_PSSetSRV])(c, 0, 5, e.srv);
	((void (WINAPI *)(void *, UINT, UINT, void *const *))VT(c)[C_PSSetSamplers])(c, 0, 2, e.smp);
	((void (WINAPI *)(void *, UINT, UINT, void *const *))VT(c)[C_PSSetCB])(c, 0, 1, &e.cb);
	for (int k = 0; k < 8; k++) REL(e.rtv[k]);
	REL(e.dsv); REL(e.vs); REL(e.ps); REL(e.gs); REL(e.hs); REL(e.ds); REL(e.il); REL(e.bl); REL(e.dss); REL(e.rs);
	REL(e.srv[0]); REL(e.srv[1]); REL(e.srv[2]); REL(e.srv[3]); REL(e.srv[4]); REL(e.smp[0]); REL(e.smp[1]); REL(e.cb);
}
/* passe TSC sur une vue : appelee quand le jeu quitte la cible HDR de la vue (profondeur encore intacte) */
static void passe_vue(void *hdr, void *prof) {
	if (g_arret || !g_shaders_ok || !g_etat || g_vues_traitees >= (int)R.max_vues) return;
	if (!copies_pretes(hdr, prof)) return;
	void *rtv = rtv_de(hdr); if (!rtv) return;
	float tan_v; { float a = R.fov_v * 0.5f * 3.14159265f / 180.0f; float a2 = a * a; tan_v = (a * (1 - a2 / 6 + a2 * a2 / 120)) / (1 - a2 / 2 + a2 * a2 / 24 - a2 * a2 * a2 / 720); }
	float mouille = R.humidite >= 0 ? R.humidite : g_mouille;
	/* modes : 1 = performance extreme (route mouillee legere, camera reduite), 2 = photorealisme optimise (tout, sous budget),
	   0 = personnalise (valeurs de l'ini telles quelles) */
	float m_cam = R.camera, m_omb = R.ombres, m_dif = R.diffusion, m_gr = R.grain, m_vit = R.vitre, q = g_qualite;
	if ((int)R.mode == 1) { m_omb = 0; m_dif *= 0.5f; m_gr = 0; m_vit = 0; q = q < 0.5f ? q : 0.5f; }
	float m_veg = R.vegetation; if ((int)R.mode == 1) m_veg *= 0.5f;
	const bool gb2_ok = g_gb2_valide;
	float cbv[64] = {
		(float)g_vue, mouille, tan_v, g_coul_h ? (float)g_coul_w / (float)g_coul_h : 1.0f,
		R.proche, R.plage_min, R.plage_max, R.decalage_z,
		(float)g_coul_w, (float)g_coul_h, g_coul_w ? 1.0f / g_coul_w : 0, g_coul_h ? 1.0f / g_coul_h : 0,
		R.intensite, R.rugosite, R.flou, R.trainees,
		R.etirement, R.pas, R.epaisseur, R.f0,
		(float)g_vues_traitees, R.assombrir, R.peinture, (float)(g_coul_mips - 1),
		m_cam, R.brouillard, m_dif, m_gr,
		R.sat_hautes, R.ext_desat, m_omb, (float)((GetTickCount64() / 16) % 997),
		q, R.ambiance_auto, R.nuit_lum, R.jour_lum,
		m_vit, R.gouttes_taille, g_pluie ? 1.0f : 0.0f, (float)((GetTickCount64() / 1000) % 100000),
		R.devoile, R.clarte, R.noirs, R.chaleur,
		gb2_ok ? m_veg : 0.0f, R.veg_teinte, R.neutre, gb2_ok ? 1.0f : 0.0f,
		R.exposition, R.gamma_monde, R.hautes, R.saturation,
		R.ldr_expo, R.ldr_contraste, R.ldr_epaule, R.ldr_sat,
		R.ldr_sat_hautes, R.ldr_temperature, R.ldr_teinte, R.ldr_noirs };
	EtatJeu sv;
	g_nous++;
	sauver(sv);
	/* etats par defaut pour notre triangle plein ecran (melange, profondeur, rasterisation, autres etages) */
	((void (WINAPI *)(void *, void *, const float *, UINT))VT(g_ctx)[C_OMSetBlend])(g_ctx, 0, 0, 0xffffffff);
	((void (WINAPI *)(void *, void *, UINT))VT(g_ctx)[C_OMSetDSS])(g_ctx, 0, 0);
	((void (WINAPI *)(void *, void *))VT(g_ctx)[C_RSSetState])(g_ctx, 0);
	((void (WINAPI *)(void *, void *))VT(g_ctx)[C_IASetInputLayout])(g_ctx, 0);
	((SetSh)VT(g_ctx)[C_GSSetShader])(g_ctx, 0, 0, 0); ((SetSh)VT(g_ctx)[C_HSSetShader])(g_ctx, 0, 0, 0); ((SetSh)VT(g_ctx)[C_DSSetShader])(g_ctx, 0, 0, 0);
	/* la cible HDR du jeu ne doit pas etre liee en lecture pendant qu'on la copie / y ecrit */
	{ void *nr = 0; ((void (WINAPI *)(void *, UINT, void *const *, void *))VT(g_ctx)[C_OMSetRT])(g_ctx, 1, &nr, 0); }
	int qi = g_q_i % NQ, qv = g_q_n[qi];
	if (qv < QV && g_q_dis[qi]) {
		if (!g_q_ouvert) { ((void (WINAPI *)(void *, void *))VT(g_ctx)[C_Begin])(g_ctx, g_q_dis[qi]); g_q_ouvert = 1; }
		((void (WINAPI *)(void *, void *))VT(g_ctx)[C_End])(g_ctx, g_q_a[qi][qv]);
	}
	if (g_coul_mips > 1) {
		((void (WINAPI *)(void *, void *, UINT, UINT, UINT, UINT, void *, UINT, const void *))VT(g_ctx)[C_CopySubresourceRegion])(g_ctx, g_coul, 0, 0, 0, 0, hdr, 0, 0);
		((void (WINAPI *)(void *, void *))VT(g_ctx)[C_GenerateMips])(g_ctx, g_coul_srv);
	} else ((void (WINAPI *)(void *, void *, void *))VT(g_ctx)[C_CopyResource])(g_ctx, g_coul, hdr);
	((void (WINAPI *)(void *, void *, void *))VT(g_ctx)[C_CopyResource])(g_ctx, g_prof, prof);
	if (gb2_ok) ((void (WINAPI *)(void *, void *, void *))VT(g_ctx)[C_CopyResource])(g_ctx, g_gb2, g_gb2_tex);
	if (g_enr_image) {   /* image d'enregistrement : le jeu tel quel, sans effet TSC */
		vider_tex(g_coul, "hdr", g_vues_traitees); vider_tex(g_prof, "prof", g_vues_traitees);
		if (gb2_ok) vider_tex(g_gb2, "albedo", g_vues_traitees);
	}
	const bool lm_ok = g_ps_lm && g_lm_srv && g_lm_rtv;
	cbv[61] = lm_ok ? 1.0f : 0.0f;
	struct { void *p; UINT rp, dp; } map = {0, 0, 0};
	if (((HRESULT (WINAPI *)(void *, void *, UINT, UINT, UINT, void *))VT(g_ctx)[C_Map])(g_ctx, g_cb, 0, 4, 0, &map) >= 0 && map.p) { memcpy(map.p, cbv, sizeof cbv); ((void (WINAPI *)(void *, void *, UINT))VT(g_ctx)[C_Unmap])(g_ctx, g_cb, 0); }
	((void (WINAPI *)(void *, UINT))VT(g_ctx)[C_IASetTopology])(g_ctx, 4);
	((void (WINAPI *)(void *, void *, void *const *, UINT))VT(g_ctx)[C_VSSetShader])(g_ctx, g_vs, 0, 0);
	void *smp[2] = {g_samp_lin, g_samp_pt};
	((void (WINAPI *)(void *, UINT, UINT, void *const *))VT(g_ctx)[C_PSSetSamplers])(g_ctx, 0, 2, smp);
	((void (WINAPI *)(void *, UINT, UINT, void *const *))VT(g_ctx)[C_PSSetCB])(g_ctx, 0, 1, &g_cb);
	/* 0.9.1 : premiere vue de l'image -> mesure de la luminance moyenne dans la reference commune (1x1) */
	if (lm_ok && g_vues_traitees == 0) {
		VIEWPORT v1 = {0, 0, 1, 1, 0, 1};
		((void (WINAPI *)(void *, UINT, const VIEWPORT *))VT(g_ctx)[C_RSSetViewports])(g_ctx, 1, &v1);
		((void (WINAPI *)(void *, UINT, void *const *, void *))VT(g_ctx)[C_OMSetRT])(g_ctx, 1, &g_lm_rtv, 0);
		((void (WINAPI *)(void *, void *, void *const *, UINT))VT(g_ctx)[C_PSSetShader])(g_ctx, g_ps_lm, 0, 0);
		void *s1[1] = {g_coul_srv};
		((void (WINAPI *)(void *, UINT, UINT, void *const *))VT(g_ctx)[C_PSSetSRV])(g_ctx, 0, 1, s1);
		((void (WINAPI *)(void *, UINT, UINT))VT(g_ctx)[C_Draw])(g_ctx, 3, 0);
		void *nrt0 = 0; ((void (WINAPI *)(void *, UINT, void *const *, void *))VT(g_ctx)[C_OMSetRT])(g_ctx, 1, &nrt0, 0);
	}
	VIEWPORT vp = {0, 0, (float)g_coul_w, (float)g_coul_h, 0, 1};
	((void (WINAPI *)(void *, UINT, const VIEWPORT *))VT(g_ctx)[C_RSSetViewports])(g_ctx, 1, &vp);
	((void (WINAPI *)(void *, UINT, void *const *, void *))VT(g_ctx)[C_OMSetRT])(g_ctx, 1, &rtv, 0);
	((void (WINAPI *)(void *, void *, void *const *, UINT))VT(g_ctx)[C_PSSetShader])(g_ctx, g_ps, 0, 0);
	void *srv[4] = {g_coul_srv, g_prof_srv, gb2_ok ? g_gb2_srv : 0, lm_ok ? g_lm_srv : 0};
	((void (WINAPI *)(void *, UINT, UINT, void *const *))VT(g_ctx)[C_PSSetSRV])(g_ctx, 0, 4, srv);
	if (!g_enr_image) ((void (WINAPI *)(void *, UINT, UINT))VT(g_ctx)[C_Draw])(g_ctx, 3, 0);
	void *nul[4] = {0, 0, 0, 0}; ((void (WINAPI *)(void *, UINT, UINT, void *const *))VT(g_ctx)[C_PSSetSRV])(g_ctx, 0, 4, nul);
	void *nrt = 0; ((void (WINAPI *)(void *, UINT, void *const *, void *))VT(g_ctx)[C_OMSetRT])(g_ctx, 1, &nrt, 0);
	if (qv < QV && g_q_dis[qi]) { ((void (WINAPI *)(void *, void *))VT(g_ctx)[C_End])(g_ctx, g_q_b[qi][qv]); g_q_n[qi] = qv + 1; }
	remettre(sv);
	g_nous--;
	g_vues_traitees++;
	if (g_trace) { Ligne l; l.s("  >>> passe TSC sur la vue "); l.i(g_vues_traitees); l.s(" : "); dire_tex(l, hdr); trace_txt(l); }
}
/* 0.9 : etage apres l'auto-exposition et le tone mapping du jeu, sur la vue 8 bits sRGB, avant composition et interface */
static void passe_ldr(void *tex) {
	if (g_arret || !g_shaders_ok || !g_ps_ldr || !g_etat || R.ldr < 0.5f) return;
	TEX2D_DESC d; desc_tex(tex, d);
	if (d.SampleCount > 1) return;
	if (!g_ldr || g_ldr_w != d.Width || g_ldr_h != d.Height || g_ldr_fmt != d.Format) {
		REL(g_ldr_srv); REL(g_ldr);
		TEX2D_DESC n = {d.Width, d.Height, 1, 1, d.Format, 1, 0, 0, 8, 0, 0};
		if (dev_tex(&n, &g_ldr) < 0) { g_ldr = 0; static int dit; if (!dit++) logline("copie 8 bits refusee : etage apres tone mapping coupe"); return; }
		((HRESULT (WINAPI *)(void *, void *, const void *, void **))VT(g_dev)[D_CreateSRV])(g_dev, g_ldr, 0, &g_ldr_srv);
		g_ldr_w = d.Width; g_ldr_h = d.Height; g_ldr_fmt = d.Format;
		Ligne l; l.s("copie 8 bits creee (etage apres tone mapping) : "); dire_tex(l, g_ldr); journal(l);
	}
	if (!g_ldr_srv) return;
	void *rtv = rtv_de(tex); if (!rtv) return;
	float cbv[64]; memset(cbv, 0, sizeof cbv);
	cbv[8] = (float)d.Width; cbv[9] = (float)d.Height; cbv[10] = 1.0f / d.Width; cbv[11] = 1.0f / d.Height;
	cbv[52] = R.ldr_expo; cbv[53] = R.ldr_contraste; cbv[54] = R.ldr_epaule; cbv[55] = R.ldr_sat;
	cbv[56] = R.ldr_sat_hautes; cbv[57] = R.ldr_temperature; cbv[58] = R.ldr_teinte; cbv[59] = R.ldr_noirs; cbv[60] = R.ldr_verts;
	cbv[62] = R.ldr_lut; cbv[63] = g_lut_srv ? 32.0f : 0.0f;
	EtatJeu sv;
	g_nous++;
	sauver(sv);
	((void (WINAPI *)(void *, void *, const float *, UINT))VT(g_ctx)[C_OMSetBlend])(g_ctx, 0, 0, 0xffffffff);
	((void (WINAPI *)(void *, void *, UINT))VT(g_ctx)[C_OMSetDSS])(g_ctx, 0, 0);
	((void (WINAPI *)(void *, void *))VT(g_ctx)[C_RSSetState])(g_ctx, 0);
	((void (WINAPI *)(void *, void *))VT(g_ctx)[C_IASetInputLayout])(g_ctx, 0);
	((SetSh)VT(g_ctx)[C_GSSetShader])(g_ctx, 0, 0, 0); ((SetSh)VT(g_ctx)[C_HSSetShader])(g_ctx, 0, 0, 0); ((SetSh)VT(g_ctx)[C_DSSetShader])(g_ctx, 0, 0, 0);
	{ void *nr = 0; ((void (WINAPI *)(void *, UINT, void *const *, void *))VT(g_ctx)[C_OMSetRT])(g_ctx, 1, &nr, 0); }
	{ void *nul[3] = {0, 0, 0}; ((void (WINAPI *)(void *, UINT, UINT, void *const *))VT(g_ctx)[C_PSSetSRV])(g_ctx, 0, 3, nul); }
	((void (WINAPI *)(void *, void *, void *))VT(g_ctx)[C_CopyResource])(g_ctx, g_ldr, tex);
	if (g_enr_image) vider_tex(g_ldr, "jeu8", g_ldr_n - 1);
	struct { void *p; UINT rp, dp; } map = {0, 0, 0};
	if (((HRESULT (WINAPI *)(void *, void *, UINT, UINT, UINT, void *))VT(g_ctx)[C_Map])(g_ctx, g_cb, 0, 4, 0, &map) >= 0 && map.p) { memcpy(map.p, cbv, sizeof cbv); ((void (WINAPI *)(void *, void *, UINT))VT(g_ctx)[C_Unmap])(g_ctx, g_cb, 0); }
	VIEWPORT vp = {0, 0, (float)d.Width, (float)d.Height, 0, 1};
	((void (WINAPI *)(void *, UINT, const VIEWPORT *))VT(g_ctx)[C_RSSetViewports])(g_ctx, 1, &vp);
	((void (WINAPI *)(void *, UINT, void *const *, void *))VT(g_ctx)[C_OMSetRT])(g_ctx, 1, &rtv, 0);
	((void (WINAPI *)(void *, UINT))VT(g_ctx)[C_IASetTopology])(g_ctx, 4);
	((void (WINAPI *)(void *, void *, void *const *, UINT))VT(g_ctx)[C_VSSetShader])(g_ctx, g_vs, 0, 0);
	((void (WINAPI *)(void *, void *, void *const *, UINT))VT(g_ctx)[C_PSSetShader])(g_ctx, g_ps_ldr, 0, 0);
	void *srv[5] = {g_ldr_srv, 0, 0, 0, g_lut_srv}; void *smp[2] = {g_samp_lin, g_samp_pt};
	((void (WINAPI *)(void *, UINT, UINT, void *const *))VT(g_ctx)[C_PSSetSRV])(g_ctx, 0, 5, srv);
	((void (WINAPI *)(void *, UINT, UINT, void *const *))VT(g_ctx)[C_PSSetSamplers])(g_ctx, 0, 2, smp);
	((void (WINAPI *)(void *, UINT, UINT, void *const *))VT(g_ctx)[C_PSSetCB])(g_ctx, 0, 1, &g_cb);
	if (!g_enr_image) ((void (WINAPI *)(void *, UINT, UINT))VT(g_ctx)[C_Draw])(g_ctx, 3, 0);
	void *nul[5] = {0, 0, 0, 0, 0}; ((void (WINAPI *)(void *, UINT, UINT, void *const *))VT(g_ctx)[C_PSSetSRV])(g_ctx, 0, 5, nul);
	void *nrt = 0; ((void (WINAPI *)(void *, UINT, void *const *, void *))VT(g_ctx)[C_OMSetRT])(g_ctx, 1, &nrt, 0);
	remettre(sv);
	g_nous--;
	g_n_ldr++;
	if (g_trace) { Ligne l; l.s("  >>> etage TSC apres tone mapping : "); dire_tex(l, tex); trace_txt(l); }
}
static void fin_mesure_gpu() {
	if (!g_ctx || !g_q_ouvert) return;
	int qi = g_q_i % NQ;
	g_nous++; ((void (WINAPI *)(void *, void *))VT(g_ctx)[C_End])(g_ctx, g_q_dis[qi]); g_nous--;
	g_q_ouvert = 0; g_q_i++;
	int r = (g_q_i + 1) % NQ;   /* la plus ancienne */
	if (g_q_i >= NQ && g_q_n[r]) {
		typedef HRESULT (WINAPI *GD)(void *, void *, void *, UINT, UINT);
		g_nous++;   /* GetData est accroche (profileur) : nos lectures ne comptent pas comme celles du jeu */
		DISJOINT dj; double ms = 0; int ok = ((GD)VT(g_ctx)[C_GetData])(g_ctx, g_q_dis[r], &dj, sizeof dj, 1) == 0 && !dj.Disjoint && dj.Frequency;
		for (int v = 0; ok && v < g_q_n[r]; v++) { u64 a = 0, b = 0; if (((GD)VT(g_ctx)[C_GetData])(g_ctx, g_q_a[r][v], &a, 8, 1) || ((GD)VT(g_ctx)[C_GetData])(g_ctx, g_q_b[r][v], &b, 8, 1) || b < a) ok = 0; else ms += (double)(b - a) * 1000.0 / (double)dj.Frequency; }
		g_nous--;
		if (ok) { g_gpu_ms += ms; g_n_gpu++; }
		g_q_n[r] = 0;
	}
	g_q_n[(g_q_i) % NQ] = 0;
}

/* 0.11.2 : Mendy 03/11 17:29 « plus clair a gauche et de temps en temps la droite s'assombrit ». Avant, on prenait les 3 PREMIERES
   cibles 8 bits de la taille d'une vue apres l'eclairage : si le jeu en dessine une autre (retro, camera, reflet) avant le tone mapping
   de l'ecran droit, cet ecran sautait l'etage TSC certaines images = clignement. On apprend maintenant LES 3 cibles du tone mapping
   (celles qui reviennent a chaque image) et on ne traite qu'elles, une fois chacune par image. */
static void *g_lc_p[8]; static i64 g_lc_n[8]; static int g_lc_nb; static void *g_lt[3]; static int g_lt_ok; static unsigned g_lt_fait;   /* bit par cible traitee cette image */
static i64 g_ldr_saut, g_ldr_img3, g_ldr_imgpas3;
/* 0.11.3 : la trace 0.11.1 montre la 4e cible 8 bits de taille vue juste APRES la passe HDR de la vue 1 et AVANT celles des vues 2-3 ;
   le vrai tone mapping des 3 ecrans vient apres TOUTES les vues HDR. On n'accepte donc une cible 8 bits qu'une fois traitees autant
   de vues HDR qu'a l'image precedente (3 en multi-ecran, 1 sinon). */
static int g_vues_prec;
static bool ldr_accepte(void *rt) {
	if (g_lt_ok) { for (int k = 0; k < 3; k++) if (g_lt[k] == rt) { if (g_lt_fait & (1u << k)) return false; g_lt_fait |= 1u << k; return true; } g_ldr_saut++; return false; }
	int i = 0; for (; i < g_lc_nb; i++) if (g_lc_p[i] == rt) break;
	if (i == g_lc_nb && g_lc_nb < 8) { g_lc_p[g_lc_nb] = rt; g_lc_n[g_lc_nb++] = 0; }
	if (i < 8) g_lc_n[i]++;
	return g_ldr_n < 3;   /* pendant l'apprentissage : ancien comportement */
}
static void ldr_fin_image() {
	if (g_lt_ok) { if (g_lt_fait == 7) g_ldr_img3++; else g_ldr_imgpas3++; g_lt_fait = 0; return; }
	static int images; if (++images < 120) return;
	for (int k = 0; k < 3; k++) { int b = -1; for (int i = 0; i < g_lc_nb; i++) { bool pris = false; for (int j = 0; j < k; j++) if (g_lt[j] == g_lc_p[i]) pris = true; if (!pris && (b < 0 || g_lc_n[i] > g_lc_n[b])) b = i; } g_lt[k] = b >= 0 ? g_lc_p[b] : 0; }
	g_lt_ok = g_lt[0] && g_lt[1] && g_lt[2];
	Ligne l; l.s("etage apres tone mapping : cibles apprises "); l.s(g_lt_ok ? "(3)" : "(incomplet, ancien mode garde)"); for (int i = 0; i < g_lc_nb; i++) { l.s(" "); l.x((u64)g_lc_p[i]); l.s("="); l.i(g_lc_n[i]); } journal(l);
	if (!g_lt_ok) images = 0, g_lc_nb = 0;
}
static void quitter_vue() { REL(g_hdr_tex); REL(g_vue_prof); g_etape = E_RIEN; }

/* ---------- crochets du contexte ---------- */
static void WINAPI h_omsrt(void *ctx, UINT n, void *const *rtv, void *dsv) {
	if (!g_nous) {
		g_n_omsrt++; g_pf_cibles++;
		void *rt0 = n && rtv && rtv[0] ? ressource(rtv[0]) : 0;
		void *pt = dsv ? ressource(dsv) : 0;
		TEX2D_DESC d0; if (rt0) desc_tex(rt0, d0); else memset(&d0, 0, sizeof d0);
		/* l'eclairage HDR de la vue est fini quand le jeu quitte sa cible : passe TSC maintenant */
		if (g_etape == E_HDR && rt0 != g_hdr_tex) {
			if (g_hdr_tex && g_vue_prof && R.actif > 0.5f && g_effet_on > 0.5f && g_etat) passe_vue(g_hdr_tex, g_vue_prof);
			quitter_vue();
		}
		/* 0.9 : le jeu quitte la vue 8 bits qu'il vient de tone-mapper -> etage TSC apres tone mapping */
		if (g_ldr_tex && rt0 != g_ldr_tex) {
			if (R.actif > 0.5f && g_effet_on > 0.5f) passe_ldr(g_ldr_tex);
			REL(g_ldr_tex);
		}
		if (!g_ldr_tex && n == 1 && rt0 && (d0.Format == 29 || d0.Format == 28) && g_coul_w && d0.Width == g_coul_w && d0.Height == g_coul_h
			&& g_vues_traitees > 0 && g_vues_traitees >= g_vues_prec && d0.SampleCount <= 1 && ldr_accepte(rt0)) {
			g_ldr_tex = rt0; ((UINT (WINAPI *)(void *))VT(rt0)[1])(rt0); g_ldr_n++;
		}
		const bool grande = rt0 && d0.Width >= (UINT)R.taille_min && d0.Height >= (UINT)R.taille_min;
		if (n >= 4 && rt0 && d0.Format == 10 && pt) {
			quitter_vue();
			if (grande) {
				g_etape = E_GBUF; g_vues_image++;
				/* 0.7 : garder la cible 2 (albedo + masque du feuillage) de cette vue pour la couche vegetation */
				REL(g_gb2_tex); g_gb2_tex = rtv[2] ? ressource(rtv[2]) : 0;
			} else g_n_petites++;
			g_n_gbuf++;
		}
		else if (n == 1 && grande && d0.Format == 10 && pt && g_etape == E_GBUF) {
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
/* profileur : attentes CPU possibles du jeu sur le contexte immediat (Map en lecture : le CPU attend le GPU ; GetData) */
typedef HRESULT (WINAPI *PFN_MAP)(void *, void *, UINT, UINT, UINT, void *);
typedef HRESULT (WINAPI *PFN_GETDATA)(void *, void *, void *, UINT, UINT);
static PFN_MAP o_map; static PFN_GETDATA o_getdata;
typedef void (WINAPI *PFN_UPD)(void *, void *, UINT, const void *, const void *, UINT, UINT);
static PFN_UPD o_upd; static i64 g_tx_upd2;
/* 0.10 : textures 2D remplies APRES creation (UpdateSubresource) : si ce compte est grand, le remplacement devra se faire ici aussi */
static void releve_upd(void *r, UINT sub, const void *box, const void *data, UINT rp, UINT dp, const char *chemin);
static PFN_UPD o_upd_b;
static inline void corps_upd(PFN_UPD o, void *c, void *r, UINT sub, const void *box, const void *data, UINT rp, UINT dp) {
	if (!g_nous && r) { int dim = 0; ((void (WINAPI *)(void *, int *))VT(r)[7 /*GetType*/])(r, &dim); if (dim == 3) { __atomic_fetch_add(&g_tx_upd2, 1, __ATOMIC_RELAXED); releve_upd(r, sub, box, data, rp, dp, "upd"); } }
	o(c, r, sub, box, data, rp, dp);
}
static void WINAPI h_upd(void *c, void *r, UINT sub, const void *box, const void *data, UINT rp, UINT dp) { corps_upd(o_upd, c, r, sub, box, data, rp, dp); }
static void WINAPI h_upd_b(void *c, void *r, UINT sub, const void *box, const void *data, UINT rp, UINT dp) { corps_upd(o_upd_b, c, r, sub, box, data, rp, dp); }
/* 0.10.1 : la 0.10 a montre que le jeu cree TOUTES ses textures vides (2 531 en 2 min) et ne les remplit ni a la creation
   ni par UpdateSubresource. On surveille donc les autres chemins : Map en ecriture (textures staging / dynamic),
   Unmap (empreinte des donnees ecrites), CopyResource / CopySubresourceRegion(1) vers une texture de decor, UpdateSubresource1,
   et les contextes differents du contexte immediat. Releve seulement : rien n'est remplace. */
static volatile long g_tx_verrou; static i64 g_tx_lignes;
static u64 empreinte(const SUBRES *sr, const TEX2D_DESC *ds, u64 &taille);
typedef void (WINAPI *PFN_EXEC)(void *, void *, BOOL); static PFN_EXEC o_exec; static i64 g_exec_n;
typedef void (WINAPI *PFN_PSSRV)(void *, UINT, UINT, void *const *); static PFN_PSSRV o_pssrv; static i64 g_hd_rempl;
/* table texture du jeu -> vue HD, et vue du jeu -> texture du jeu (adressage ouvert, verrou court) */
enum { NT = 1 << 16 };
static void *g_t_cle[NT], *g_t_val[NT]; static void *g_v_cle[NT], *g_v_val[NT]; static volatile long g_tab_verrou;
static void tab_lock() { while (__atomic_exchange_n(&g_tab_verrou, 1, __ATOMIC_ACQUIRE)) {} }
static void tab_unlock() { __atomic_store_n(&g_tab_verrou, 0, __ATOMIC_RELEASE); }
static unsigned hp(void *p) { u64 v = (u64)p; v ^= v >> 17; v *= 0x9E3779B97F4A7C15ULL; return (unsigned)(v >> 40) & (NT - 1); }
static void tab_mettre(void **cle, void **val, void *k, void *v) {
	unsigned i = hp(k); for (int n = 0; n < 512; n++, i = (i + 1) & (NT - 1)) if (!cle[i] || cle[i] == k) { cle[i] = k; val[i] = v; return; }
}
static void *tab_lire(void **cle, void **val, void *k) {
	unsigned i = hp(k); for (int n = 0; n < 512; n++, i = (i + 1) & (NT - 1)) { if (cle[i] == k) return val[i]; if (!cle[i]) return 0; } return 0;
}
static volatile long g_hd_actif;   /* 1 des qu'au moins une texture HD est posee : sinon PSSetShaderResources passe tout droit */
static void WINAPI h_pssrv(void *c, UINT debut, UINT n, void *const *v) {
	if (g_nous || !__atomic_load_n(&g_hd_actif, __ATOMIC_ACQUIRE) || R.textures_hd <= 0 || !v || n == 0 || n > 128) { o_pssrv(c, debut, n, v); return; }
	void *loc[128]; bool chg = false;
	tab_lock();
	for (UINT k = 0; k < n; k++) { loc[k] = v[k]; if (!v[k]) continue; void *res = tab_lire(g_v_cle, g_v_val, v[k]); if (!res) continue; void *hd = tab_lire(g_t_cle, g_t_val, res); if (hd) { loc[k] = hd; chg = true; } }
	tab_unlock();
	if (chg) g_hd_rempl++;
	o_pssrv(c, debut, n, chg ? loc : v);
}
static void WINAPI h_exec(void *c, void *liste, BOOL rest) { if (!g_nous) g_exec_n++; o_exec(c, liste, rest); }
typedef void (WINAPI *PFN_UNMAP)(void *, void *, UINT);
typedef void (WINAPI *PFN_COPYRES)(void *, void *, void *);
typedef void (WINAPI *PFN_COPYSUB)(void *, void *, UINT, UINT, UINT, UINT, void *, UINT, const void *);
typedef void (WINAPI *PFN_COPYSUB1)(void *, void *, UINT, UINT, UINT, UINT, void *, UINT, const void *, UINT);
typedef void (WINAPI *PFN_UPD1)(void *, void *, UINT, const void *, const void *, UINT, UINT, UINT);
static PFN_UNMAP o_unmap; static PFN_COPYRES o_copyres; static PFN_COPYSUB o_copysub; static PFN_COPYSUB1 o_copysub1; static PFN_UPD1 o_upd1;
static i64 g_mx[8];   /* Map texture 2D par type : 0 autre, 1 READ, 2 WRITE, 3 READ_WRITE, 4 WRITE_DISCARD, 5 WRITE_NO_OVERWRITE */
static i64 g_mx_usage[4], g_mx_autre_ctx, g_cp_res, g_cp_sub, g_cp_sub1, g_cp_vers_decor, g_upd1_2d;
static void *g_ctx_vus[8]; static int g_ctx_n;
static void ctx_vu(void *c) { if (c == g_ctx) return; for (int i = 0; i < g_ctx_n; i++) if (g_ctx_vus[i] == c) return; if (g_ctx_n < 8) g_ctx_vus[g_ctx_n++] = c; }
static bool est_tex2d(void *r) { if (!r) return false; int dim = 0; ((void (WINAPI *)(void *, int *))VT(r)[7 /*GetType*/])(r, &dim); return dim == 3; }
static volatile long g_ec_verrou;
struct Ecrit { void *r; UINT sub; SUBRES m; u64 h; };
static Ecrit g_ec[512]; static int g_ec_n;   /* textures ecrites par le CPU : derniere empreinte connue par (ressource, sous-ressource) */
static void ec_lock() { while (__atomic_exchange_n(&g_ec_verrou, 1, __ATOMIC_ACQUIRE)) {} }
static void ec_unlock() { __atomic_store_n(&g_ec_verrou, 0, __ATOMIC_RELEASE); }
static Ecrit *ec_trouver(void *r, UINT sub, bool creer) {
	for (int i = 0; i < g_ec_n; i++) if (g_ec[i].r == r && g_ec[i].sub == sub) return &g_ec[i];
	if (!creer) return 0; Ecrit *e = &g_ec[g_ec_n < 512 ? g_ec_n++ : (int)(GetTickCount64() & 511)]; e->r = r; e->sub = sub; e->h = 0; return e;
}
static void tx_ligne(Ligne &l) {
	while (__atomic_exchange_n(&g_tx_verrou, 1, __ATOMIC_ACQUIRE)) {}
	if (g_tx_lignes == 0) { const char *t = "# " VERSION " : chemin;empreinte;largeur;hauteur;niveaux;tableau;format;usage;bind;niveau;octets;tick_ms\r\n"; ecrire("tsc-textures.csv", t, lng(t)); }
	if (g_tx_lignes < 40000) { g_tx_lignes++; ecrire("tsc-textures.csv", l.t, l.n); }
	__atomic_store_n(&g_tx_verrou, 0, __ATOMIC_RELEASE);
}
static void tx_desc(Ligne &l, const TEX2D_DESC &d, UINT niveau) { l.i(d.Width); l.s(";"); l.i(d.Height); l.s(";"); l.i(d.MipLevels); l.s(";"); l.i(d.ArraySize); l.s(";");
	l.i(d.Format); l.s(";"); l.i(d.Usage); l.s(";"); l.i(d.BindFlags); l.s(";"); l.i(niveau); l.s(";"); }
static void WINAPI h_unmap(void *c, void *r, UINT sub) {
	if (!g_nous && R.sonde_textures > 0 && est_tex2d(r)) {
		ec_lock(); Ecrit *e = ec_trouver(r, sub, false); Ecrit copie; bool ok = false; if (e && e->m.p) { copie = *e; ok = true; e->m.p = 0; } ec_unlock();
		if (ok) {
			TEX2D_DESC d; desc_tex(r, d); UINT mips = d.MipLevels ? d.MipLevels : 1, niv = sub % mips;
			TEX2D_DESC dn = d; dn.Width = d.Width >> niv ? d.Width >> niv : 1; dn.Height = d.Height >> niv ? d.Height >> niv : 1;
			if (dn.Width >= 16 && dn.Height >= 16) {
				u64 taille; u64 h = empreinte(&copie.m, &dn, taille);
				ec_lock(); Ecrit *e2 = ec_trouver(r, sub, false); if (e2) e2->h = h; ec_unlock();
				if (niv == 0) { Ligne l; l.s("ecrit;"); l.x(h); l.s(";"); tx_desc(l, d, niv); l.i((i64)taille); l.s(";"); l.i((i64)GetTickCount64()); l.s("\r\n"); tx_ligne(l); }
			}
		}
	}
	o_unmap(c, r, sub);
}
static bool decor(void *r, TEX2D_DESC &d) { if (!est_tex2d(r)) return false; desc_tex(r, d); return (d.BindFlags & 0x8) && !(d.BindFlags & 0xA0) && d.Usage == 0; }
static void copie_vers(void *dst, UINT dsub, void *src, UINT ssub, const char *chemin) {
	TEX2D_DESC d; if (!decor(dst, d)) return; g_cp_vers_decor++;
	if (R.sonde_textures <= 0) return;
	u64 h = 0; if (src) { ec_lock(); Ecrit *e = ec_trouver(src, ssub, false); if (e) h = e->h; ec_unlock(); }
	UINT mips = d.MipLevels ? d.MipLevels : 1, niv = dsub % mips; if (niv) return;   /* une ligne par texture : le niveau 0 */
	TEX2D_DESC ds; if (src && est_tex2d(src)) desc_tex(src, ds); else memset(&ds, 0, sizeof ds);
	Ligne l; l.s(chemin); l.s(";"); l.x(h); l.s(";"); tx_desc(l, d, niv); l.s("src "); l.i(ds.Width); l.s("x"); l.i(ds.Height); l.s(" u"); l.i(ds.Usage); l.s(";"); l.i((i64)GetTickCount64()); l.s("\r\n"); tx_ligne(l);
}
/* 0.11.1 : la 0.11 a vu 43 733 UpdateSubresource1 2D sans aucune ligne : la condition « pas de boite » etait trop stricte.
   On accepte une boite qui couvre tout le niveau 0, et les 300 premiers appels sont notes BRUTS (description, boite, pas) pour comprendre. */
struct BOXx { UINT l, t, f, r, b, k; };
/* 0.12 : extraction. Pour fabriquer les versions HD, il faut l'image d'origine de chaque texture : a son premier remplissage
   (niveau 0 complet), on l'ecrit telle quelle (compressee BC ou 8 bits) en .dds nomme par son empreinte. Une seule fois par empreinte,
   plafond en Mo par la cle vider_textures. Usage prive (fabrication du cache HD), jamais redistribue. */
static bool format_bloc(UINT f, UINT &octets);
static u64 g_vu_h[16384]; static volatile long g_vu_verrou; static i64 g_vide_octets, g_vide_n, g_vide_refus;
static bool deja_vu(u64 h) {
	if (!h) h = 1; unsigned i = (unsigned)(h ^ (h >> 32)) & 16383; bool r = false;
	while (__atomic_exchange_n(&g_vu_verrou, 1, __ATOMIC_ACQUIRE)) {}
	for (int k = 0; k < 64; k++) { unsigned j = (i + k) & 16383; if (g_vu_h[j] == h) { r = true; break; } if (!g_vu_h[j]) { g_vu_h[j] = h; break; } }
	__atomic_store_n(&g_vu_verrou, 0, __ATOMIC_RELEASE); return r;
}
static UINT octets_pixel(UINT f) { switch (f) { case 28: case 29: case 87: case 88: case 91: case 24: case 26: case 41: return 4; case 49: case 54: case 56: return 2; case 61: case 65: return 1; case 10: case 34: return 8; default: return 0; } }
static void vider_dds(u64 h, const TEX2D_DESC &d, const void *data, UINT rp) {
	if (R.vider_textures <= 0 || d.ArraySize != 1) return;
	UINT ob, lignes, serre; if (format_bloc(d.Format, ob)) { lignes = (d.Height + 3) / 4; serre = ((d.Width + 3) / 4) * ob; } else { UINT b = octets_pixel(d.Format); if (!b) { g_vide_refus++; return; } lignes = d.Height; serre = d.Width * b; }
	if (serre > rp) return;
	i64 total = (i64)serre * lignes;
	if (g_vide_octets + total > (i64)R.vider_textures * 1048576) return;
	if (deja_vu(h)) return;
	__atomic_fetch_add(&g_vide_octets, total, __ATOMIC_RELAXED);
	char p[400] = {0}; cat(p, g_dir); cat(p, "tsc_textures_brut"); CreateDirectoryA(p, 0); cat(p, "\\");
	char nom[24]; static const char hx[] = "0123456789abcdef"; for (int k = 0; k < 16; k++) nom[k] = hx[(h >> (60 - 4 * k)) & 15]; nom[16] = 0; cat(p, nom); cat(p, ".dds");
	HANDLE f = CreateFileA(p, 0x40000000 /*GENERIC_WRITE*/, 0, 0, 1 /*CREATE_NEW*/, 0x80, 0); if (f == INVALID) return;
	UINT e[32 + 5]; memset(e, 0, sizeof e);
	e[0] = 0x20534444; e[1] = 124; e[2] = 0x1 | 0x2 | 0x4 | 0x1000 | 0x80000; e[3] = d.Height; e[4] = d.Width; e[5] = (UINT)total; e[7] = 1;
	e[19] = 32; e[20] = 0x4; e[21] = 0x30315844 /*DX10*/; e[27] = 0x1000;
	e[32] = d.Format; e[33] = 3; e[34] = 0; e[35] = 1; e[36] = 0;
	DWORD w; WriteFile(f, e, sizeof e, &w, 0);
	const unsigned char *q = (const unsigned char *)data; for (UINT y = 0; y < lignes; y++) WriteFile(f, q + (u64)y * rp, serre, &w, 0);
	CloseHandle(f); __atomic_fetch_add(&g_vide_n, 1, __ATOMIC_RELAXED);
}
/* ---------- 0.13 : TSC Textures HD, remplacement a la volee (rien dans les fichiers du jeu) ----------
   1) au demarrage : liste des .dds de plugins\tsc_textures_hd (nom = empreinte 16 hex) ;
   2) au remplissage du niveau 0 d'une texture de decor (UpdateSubresource1) : si son empreinte a une version HD, on cree la texture HD
      (avec tous ses niveaux) et sa vue, et on note : texture du jeu -> vue HD ;
   3) quand le jeu attache ses textures au pixel shader (PSSetShaderResources), on remplace la vue du jeu par la vue HD.
   Le jeu garde ses objets : couper (textures_hd = 0) rend instantanement les textures d'origine. Format HD accepte : le meme que
   le jeu, ou son equivalent non compresse (BC1/2/3 -> RGBA8, BC4 -> R8, BC5 -> R8G8, meme espace sRGB). */
static u64 g_hd_liste[4096]; static int g_hd_n; static i64 g_hd_crees, g_hd_refus;
static bool hd_existe(u64 h) { for (int i = 0; i < g_hd_n; i++) if (g_hd_liste[i] == h) return true; return false; }
static u64 hex16(const char *n) { u64 v = 0; for (int k = 0; k < 16; k++) { char c = n[k]; int d = c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : c >= 'A' && c <= 'F' ? c - 'A' + 10 : -1; if (d < 0) return 0; v = v << 4 | (u64)d; } return v; }
static void hd_lister() {
	char p[400] = {0}; cat(p, g_dir); cat(p, "tsc_textures_hd\\*.dds"); unsigned char fd[600];
	HANDLE f = FindFirstFileA(p, fd); g_hd_n = 0;
	if (f != INVALID) { do { const char *n = (const char *)fd + 44; u64 h = hex16(n); if (h && g_hd_n < 4096) g_hd_liste[g_hd_n++] = h; } while (FindNextFileA(f, fd)); FindClose(f); }
	Ligne l; l.s("TSC Textures HD : "); l.i(g_hd_n); l.s(" textures HD disponibles"); journal(l);
}
static bool hd_format_ok(UINT jeu, UINT hd) {
	if (jeu == hd) return true;
	switch (jeu) { case 72: case 75: case 78: return hd == 29 || hd == 91; case 71: case 74: case 77: return hd == 28 || hd == 87; case 80: return hd == 61; case 83: return hd == 49; default: return false; }
}
static void hd_charger(void *tex_jeu, const TEX2D_DESC &dj, u64 h) {
	char p[400] = {0}; cat(p, g_dir); cat(p, "tsc_textures_hd\\"); char nom[24]; static const char hx[] = "0123456789abcdef";
	for (int k = 0; k < 16; k++) nom[k] = hx[(h >> (60 - 4 * k)) & 15]; nom[16] = 0; cat(p, nom); cat(p, ".dds");
	HANDLE f = CreateFileA(p, 0x80000000, 1, 0, 3, 0x80, 0); if (f == INVALID) { g_hd_refus++; return; }
	DWORD hi = 0, taille = GetFileSize(f, &hi); if (hi || taille < 148 || taille > 512u * 1048576u) { CloseHandle(f); g_hd_refus++; return; }
	unsigned char *b = (unsigned char *)VirtualAlloc(0, taille, 0x3000, 0x04); if (!b) { CloseHandle(f); g_hd_refus++; return; }
	DWORD lu = 0; ReadFile(f, b, taille, &lu, 0); CloseHandle(f);
	const UINT *e = (const UINT *)b; Ligne l; l.s("TSC Textures HD "); l.s(nom); l.s(" : ");
	if (lu != taille || e[0] != 0x20534444 || e[21] != 0x30315844) { l.s("dds invalide (en-tete DX10 attendu)"); journal(l); g_hd_refus++; return; }
	UINT H = e[3], W = e[4], mips = e[7] ? e[7] : 1, fmt = e[32];
	if (!hd_format_ok(dj.Format, fmt) || W < dj.Width || (u64)W * dj.Height != (u64)H * dj.Width) { l.s("refusee (format "); l.i(fmt); l.s(" "); l.i(W); l.s("x"); l.i(H); l.s(" contre jeu "); l.i(dj.Format); l.s(" "); l.i(dj.Width); l.s("x"); l.i(dj.Height); l.s(")"); journal(l); g_hd_refus++; return; }
	SUBRES sr[16]; u64 o = 148; UINT ob; bool bloc = format_bloc(fmt, ob); UINT bp = bloc ? 0 : octets_pixel(fmt); if (mips > 16) mips = 16;
	for (UINT m = 0; m < mips; m++) {
		UINT w = W >> m ? W >> m : 1, hh = H >> m ? H >> m : 1;
		UINT pitch = bloc ? ((w + 3) / 4) * ob : w * bp, lignes = bloc ? (hh + 3) / 4 : hh;
		if (!pitch || o + (u64)pitch * lignes > taille) { mips = m; break; }
		sr[m].p = b + o; sr[m].pitch = pitch; sr[m].slice = pitch * lignes; o += (u64)pitch * lignes;
	}
	if (!mips) { l.s("aucun niveau lisible"); journal(l); g_hd_refus++; return; }
	TEX2D_DESC d; memset(&d, 0, sizeof d); d.Width = W; d.Height = H; d.MipLevels = mips; d.ArraySize = 1; d.Format = fmt; d.SampleCount = 1; d.Usage = 1 /*IMMUTABLE*/; d.BindFlags = 0x8;
	void *t = 0, *v = 0;
	g_nous++; HRESULT hr = ((HRESULT (WINAPI *)(void *, const TEX2D_DESC *, const void *, void **))VT(g_dev)[D_CreateTexture2D])(g_dev, &d, sr, &t);
	if (hr >= 0 && t) ((HRESULT (WINAPI *)(void *, void *, const void *, void **))VT(g_dev)[D_CreateSRV])(g_dev, t, 0, &v);
	g_nous--;
	if (!v) { REL(t); l.s("creation refusee "); l.x((u64)(hr & 0xffffffff)); journal(l); g_hd_refus++; return; }
	REL(t);   /* la vue garde la texture */
	tab_lock(); tab_mettre(g_t_cle, g_t_val, tex_jeu, v); tab_unlock();
	__atomic_store_n(&g_hd_actif, 1, __ATOMIC_RELEASE); g_hd_crees++;
	l.s("posee "); l.i(W); l.s("x"); l.i(H); l.s(" "); l.i(mips); l.s(" niveaux, format "); l.i(fmt); l.s(" (jeu "); l.i(dj.Width); l.s("x"); l.i(dj.Height); l.s(")"); journal(l);
}
static i64 g_brut, g_upd_decor, g_upd_boite_part, g_upd_niv;
static void releve_upd(void *r, UINT sub, const void *box, const void *data, UINT rp, UINT dp, const char *chemin) {
	if (R.sonde_textures <= 0 || !data || !rp) return;
	TEX2D_DESC d; desc_tex(r, d); UINT mips = d.MipLevels ? d.MipLevels : 1, niv = sub % mips;
	UINT w = d.Width >> niv ? d.Width >> niv : 1, h0 = d.Height >> niv ? d.Height >> niv : 1;
	const BOXx *b = (const BOXx *)box;
	if (__atomic_fetch_add(&g_brut, 1, __ATOMIC_RELAXED) < 300) {
		Ligne l; l.s("brut_"); l.s(chemin); l.s(";;"); tx_desc(l, d, niv); l.s("sub "); l.i(sub); l.s(" pas "); l.i(rp); l.s("/"); l.i(dp);
		if (b) { l.s(" boite "); l.i(b->l); l.s(","); l.i(b->t); l.s("-"); l.i(b->r); l.s(","); l.i(b->b); } l.s(" misc "); l.i(d.MiscFlags); l.s(" cpu "); l.i(d.CPUAccessFlags); l.s(";"); l.i((i64)GetTickCount64()); l.s("\r\n"); tx_ligne(l);
	}
	if (!(d.BindFlags & 0x8) || (d.BindFlags & 0xA0) || d.Usage != 0) return;
	__atomic_fetch_add(&g_upd_decor, 1, __ATOMIC_RELAXED);
	if (b && (b->l || b->t || b->r < w || b->b < h0)) { __atomic_fetch_add(&g_upd_boite_part, 1, __ATOMIC_RELAXED); return; }
	if (niv) { __atomic_fetch_add(&g_upd_niv, 1, __ATOMIC_RELAXED); return; }
	if (d.Width < 16 || d.Height < 16) return;
	SUBRES m = {data, rp, dp}; u64 taille; u64 hh = empreinte(&m, &d, taille);
	vider_dds(hh, d, data, rp);
	if (g_hd_n && g_dev && hd_existe(hh)) { tab_lock(); void *deja = tab_lire(g_t_cle, g_t_val, r); tab_unlock(); if (!deja) hd_charger(r, d, hh); }
	Ligne l; l.s(chemin); l.s(";"); l.x(hh); l.s(";"); tx_desc(l, d, 0); l.i((i64)taille); l.s(";"); l.i((i64)GetTickCount64()); l.s("\r\n"); tx_ligne(l);
}
static void WINAPI h_copyres(void *c, void *dst, void *src) {
	if (!g_nous) { g_cp_res++; ctx_vu(c); copie_vers(dst, 0, src, 0, "copie_res"); }
	o_copyres(c, dst, src);
}
static PFN_COPYSUB o_copysub_b; static PFN_COPYSUB1 o_copysub1_b; static PFN_UPD1 o_upd1_b;
static inline void corps_copysub(PFN_COPYSUB o, void *c, void *dst, UINT dsub, UINT x, UINT y, UINT z, void *src, UINT ssub, const void *box) {
	if (!g_nous) { __atomic_fetch_add(&g_cp_sub, 1, __ATOMIC_RELAXED); ctx_vu(c); copie_vers(dst, dsub, src, ssub, "copie_sub"); }
	o(c, dst, dsub, x, y, z, src, ssub, box);
}
static inline void corps_copysub1(PFN_COPYSUB1 o, void *c, void *dst, UINT dsub, UINT x, UINT y, UINT z, void *src, UINT ssub, const void *box, UINT fl) {
	if (!g_nous) { __atomic_fetch_add(&g_cp_sub1, 1, __ATOMIC_RELAXED); ctx_vu(c); copie_vers(dst, dsub, src, ssub, "copie_sub1"); }
	o(c, dst, dsub, x, y, z, src, ssub, box, fl);
}
static inline void corps_upd1(PFN_UPD1 o, void *c, void *r, UINT sub, const void *box, const void *data, UINT rp, UINT dp, UINT fl) {
	if (!g_nous && est_tex2d(r)) { __atomic_fetch_add(&g_upd1_2d, 1, __ATOMIC_RELAXED); ctx_vu(c); releve_upd(r, sub, box, data, rp, dp, "upd1"); }
	o(c, r, sub, box, data, rp, dp, fl);
}
static void WINAPI h_copysub(void *c, void *dst, UINT dsub, UINT x, UINT y, UINT z, void *src, UINT ssub, const void *box) { corps_copysub(o_copysub, c, dst, dsub, x, y, z, src, ssub, box); }
static void WINAPI h_copysub_b(void *c, void *dst, UINT dsub, UINT x, UINT y, UINT z, void *src, UINT ssub, const void *box) { corps_copysub(o_copysub_b, c, dst, dsub, x, y, z, src, ssub, box); }
static void WINAPI h_copysub1(void *c, void *dst, UINT dsub, UINT x, UINT y, UINT z, void *src, UINT ssub, const void *box, UINT fl) { corps_copysub1(o_copysub1, c, dst, dsub, x, y, z, src, ssub, box, fl); }
static void WINAPI h_copysub1_b(void *c, void *dst, UINT dsub, UINT x, UINT y, UINT z, void *src, UINT ssub, const void *box, UINT fl) { corps_copysub1(o_copysub1_b, c, dst, dsub, x, y, z, src, ssub, box, fl); }
static void WINAPI h_upd1(void *c, void *r, UINT sub, const void *box, const void *data, UINT rp, UINT dp, UINT fl) { corps_upd1(o_upd1, c, r, sub, box, data, rp, dp, fl); }
static void WINAPI h_upd1_b(void *c, void *r, UINT sub, const void *box, const void *data, UINT rp, UINT dp, UINT fl) { corps_upd1(o_upd1_b, c, r, sub, box, data, rp, dp, fl); }
static HRESULT WINAPI h_map(void *c, void *r, UINT sub, UINT type, UINT fl, void *m) {
	if (!g_nous && est_tex2d(r)) {
		g_mx[type < 6 ? type : 0]++; if (c != g_ctx) { g_mx_autre_ctx++; ctx_vu(c); }
		TEX2D_DESC d; desc_tex(r, d); g_mx_usage[d.Usage & 3]++;
		if (type == 2 || type == 4 || type == 5) {
			HRESULT hr = o_map(c, r, sub, type, fl, m);
			if (hr >= 0 && m && R.sonde_textures > 0 && d.Usage == 3 /*STAGING seulement : la memoire dynamique est lente a relire*/) { ec_lock(); Ecrit *e = ec_trouver(r, sub, true); e->m = *(SUBRES *)m; ec_unlock(); }
			return hr;
		}
	}
	if (g_nous || c != g_ctx || (type != 1 /*READ*/ && type != 3 /*READ_WRITE*/)) return o_map(c, r, sub, type, fl, m);
	i64 a, b; QueryPerformanceCounter(&a); HRESULT hr = o_map(c, r, sub, type, fl, m); QueryPerformanceCounter(&b);
	g_pf_map++; g_pf_map_t += b - a; return hr;
}
static HRESULT WINAPI h_getdata(void *c, void *q, void *d, UINT n, UINT fl) {
	if (g_nous || c != g_ctx) return o_getdata(c, q, d, n, fl);
	i64 a, b; QueryPerformanceCounter(&a); HRESULT hr = o_getdata(c, q, d, n, fl); QueryPerformanceCounter(&b);
	g_pf_gd++; g_pf_gd_t += b - a; return hr;
}

/* d'autres couches remettent certaines entrees a chaque image : on les repose (en enchainant sur ce qui est en place) */
struct Crochet { int i; void *f; void **o; };
static Crochet g_cr[] = {
	{C_OMSetRT, (void *)h_omsrt, (void **)&o_omsrt}, {C_ClearDSV, (void *)h_clrdsv, (void **)&o_clrdsv}, {C_ClearRTV, (void *)h_clrrtv, (void **)&o_clrrtv},
	{C_RSSetViewports, (void *)h_rsvp, (void **)&o_rsvp}, {C_DrawIndexed, (void *)h_drawidx, (void **)&o_drawidx}, {C_Draw, (void *)h_draw, (void **)&o_draw},
	{C_DrawIndexedInstanced, (void *)h_drawidxi, (void **)&o_drawidxi}, {C_DrawInstanced, (void *)h_drawi, (void **)&o_drawi},
	{C_Map, (void *)h_map, (void **)&o_map}, {C_GetData, (void *)h_getdata, (void **)&o_getdata},
	{C_Unmap, (void *)h_unmap, (void **)&o_unmap}, {C_PSSetSRV, (void *)h_pssrv, (void **)&o_pssrv}, {C_CopyResource, (void *)h_copyres, (void **)&o_copyres}, {58 /*ExecuteCommandList*/, (void *)h_exec, (void **)&o_exec} };
/* 0.11 : crochets EN LIGNE. La 0.10.3 a montre que le moteur (ou d3d11) remet ~150 fois/s les entrees 12 13 20 21 46 47 48 50 53 115 116
   de la table : entre deux reposes, les appels passent par l'original et la sonde ne les voit pas. Pour UpdateSubresource(1) et
   CopySubresourceRegion(1), on detourne donc le DEBUT DU CODE de d3d11.dll (saut absolu de 14 octets vers notre fonction ;
   les instructions deplacees vont dans un trampoline qui continue la fonction). On ne touche au code QUE si ses premiers octets
   sont exactement ceux releves sur ce PC (Windows 03/11/2026) : sinon rien n'est pose et le journal le dit. Retire a l'arret. */
struct EnLigne { int i; void *f; void **o; const char *nom; int n; unsigned char attendu[24]; unsigned char sauve[24]; unsigned char *cible; int actif; };
static EnLigne g_el[] = {
	{C_UpdateSubresource, (void *)h_upd, (void **)&o_upd, "UpdateSubresource", 20, {0x40,0x53,0x55,0x56,0x57,0x41,0x54,0x41,0x55,0x41,0x56,0x41,0x57,0x48,0x81,0xec,0xb8,0x00,0x00,0x00}, {0}, 0, 0},
	{C_CopySubresourceRegion, (void *)h_copysub, (void **)&o_copysub, "CopySubresourceRegion", 15, {0x48,0x8b,0xc4,0x48,0x89,0x58,0x08,0x48,0x89,0x68,0x10,0x48,0x89,0x70,0x18}, {0}, 0, 0},
	{115, (void *)h_copysub1, (void **)&o_copysub1, "CopySubresourceRegion1", 20, {0x48,0x89,0x5c,0x24,0x08,0x57,0x48,0x83,0xec,0x60,0x4c,0x8b,0xd2,0x48,0x8d,0x99,0x28,0xff,0xff,0xff}, {0}, 0, 0},
	{116, (void *)h_upd1, (void **)&o_upd1, "UpdateSubresource1", 18, {0x40,0x55,0x53,0x56,0x57,0x41,0x54,0x41,0x55,0x41,0x56,0x41,0x57,0x48,0x8d,0x6c,0x24,0xf9}, {0}, 0, 0} };
static unsigned char *g_mem_el; static void octets_de(Ligne &l, const void *f);
static void ecrire_saut(unsigned char *a, const void *vers) { a[0] = 0xff; a[1] = 0x25; a[2] = a[3] = a[4] = a[5] = 0; u64 v = (u64)vers; for (int k = 0; k < 8; k++) a[6 + k] = (unsigned char)(v >> (8 * k)); }
static void poser_en_ligne(void **vt) {
	static unsigned char *mem; if (!mem) mem = (unsigned char *)VirtualAlloc(0, 4096, 0x3000, 0x40 /*PAGE_EXECUTE_READWRITE*/); g_mem_el = mem;
	if (!mem) { logline("crochets en ligne : memoire refusee"); return; }
	int k = 0;
	for (auto &e : g_el) {
		unsigned char *c = (unsigned char *)vt[e.i]; e.cible = c; int pareil = 1;
		for (int j = 0; j < e.n; j++) if (c[j] != e.attendu[j]) pareil = 0;
		Ligne l; l.s("crochet en ligne "); l.s(e.nom); l.s(" "); l.x((u64)c);
		if (!pareil) { l.s(" : octets differents de ceux attendus, NON pose (table gardee : "); l.s(poser(vt, e.i, e.f, e.o) ? "ok)" : "echec)"); journal(l); continue; }
		unsigned char *t = mem + 64 * k++; for (int j = 0; j < e.n; j++) t[j] = c[j]; ecrire_saut(t + e.n, c + e.n);
		FlushInstructionCache(GetCurrentProcess(), t, 64);
		*e.o = (void *)t; for (int j = 0; j < e.n; j++) e.sauve[j] = c[j];
		DWORD old; if (!VirtualProtect(c, e.n, 0x40, &old)) { l.s(" : protection refusee"); journal(l); continue; }
		unsigned char s14[14]; ecrire_saut(s14, e.f);
		c[0] = 0xeb; c[1] = 0xfe;   /* le temps d'ecrire : un fil qui arrive ici attend sur place */
		for (int j = 2; j < 14; j++) c[j] = s14[j]; for (int j = 14; j < e.n; j++) c[j] = 0x90;
		__atomic_store_n((unsigned short *)c, (unsigned short)(s14[0] | (s14[1] << 8)), __ATOMIC_SEQ_CST);
		VirtualProtect(c, e.n, old, &old); FlushInstructionCache(GetCurrentProcess(), c, e.n);
		e.actif = 1; l.s(" : pose ("); l.i(e.n); l.s(" octets deplaces)"); journal(l);
	}
}
static void retirer_en_ligne() {
	for (auto &e : g_el) if (e.actif) {
		DWORD old; if (!VirtualProtect(e.cible, e.n, 0x40, &old)) continue;
		e.cible[0] = 0xeb; e.cible[1] = 0xfe; for (int j = 2; j < e.n; j++) e.cible[j] = e.sauve[j];
		__atomic_store_n((unsigned short *)e.cible, (unsigned short)(e.sauve[0] | (e.sauve[1] << 8)), __ATOMIC_SEQ_CST);
		VirtualProtect(e.cible, e.n, old, &old); FlushInstructionCache(GetCurrentProcess(), e.cible, e.n); e.actif = 0;
	}
}
/* diagnostic : la table pointe-t-elle parfois vers une AUTRE fonction (variante) pour ces entrees ? */
static void *g_var[4][4]; static int g_var_n[4];
/* 0.11.1 : la 0.11 a vu une 2e implementation (variante) pour chacune des 4 fonctions : la table alterne entre les deux.
   On accroche aussi la variante en ligne, avec un petit decodeur de longueur d'instructions limite aux prologues usuels
   (push, mov/lea/sub/test/xor avec modrm, sans adresse relative a RIP ni saut) : toute autre instruction = on ne pose pas. */
static int longueur_instr(const unsigned char *p) {
	int n = 0; if ((p[0] & 0xf0) == 0x40) n = 1; unsigned char op = p[n++];
	if (op >= 0x50 && op <= 0x57) return n;
	int imm = 0;
	switch (op) { case 0x89: case 0x8b: case 0x8d: case 0x85: case 0x33: case 0x31: case 0x3b: case 0x39: case 0x2b: case 0x03: case 0x29: case 0x01: break;
	case 0x83: imm = 1; break; case 0x81: case 0xc7: imm = 4; break; default: return 0; }
	unsigned char m = p[n++]; int mod = m >> 6, rm = m & 7;
	if (mod != 3 && rm == 4) { unsigned char sib = p[n++]; if (mod == 0 && (sib & 7) == 5) n += 4; }
	if (mod == 0 && rm == 5) return 0;   /* relatif a RIP : on refuse */
	if (mod == 1) n += 1; else if (mod == 2) n += 4;
	return n + imm;
}
struct Variante { void *f; void **o; unsigned char *cible; unsigned char sauve[24]; int n, actif, tente; };
static Variante g_vb[4] = { {(void *)h_upd_b, (void **)&o_upd_b, 0, {0}, 0, 0, 0}, {(void *)h_copysub_b, (void **)&o_copysub_b, 0, {0}, 0, 0, 0},
	{(void *)h_copysub1_b, (void **)&o_copysub1_b, 0, {0}, 0, 0, 0}, {(void *)h_upd1_b, (void **)&o_upd1_b, 0, {0}, 0, 0, 0} };
static void poser_variante(int k, unsigned char *c) {
	Variante &v = g_vb[k]; if (v.tente) return; v.tente = 1;
	Ligne l; l.s("crochet en ligne variante "); l.s(g_el[k].nom); l.s(" "); l.x((u64)c); l.s(" "); module_de(l, c); l.s(" : "); octets_de(l, c);
	int n = 0; while (n < 14) { int k2 = longueur_instr(c + n); if (!k2) { n = -1; break; } n += k2; }
	if (n < 14 || n > 24 || !g_mem_el) { l.s(" -> NON pose (instruction inconnue)"); journal(l); return; }
	unsigned char *t = g_mem_el + 64 * (4 + k); for (int j = 0; j < n; j++) t[j] = c[j]; ecrire_saut(t + n, c + n); FlushInstructionCache(GetCurrentProcess(), t, 64);
	*v.o = (void *)t; for (int j = 0; j < n; j++) v.sauve[j] = c[j];
	DWORD old; if (!VirtualProtect(c, n, 0x40, &old)) { l.s(" -> protection refusee"); journal(l); return; }
	unsigned char s14[14]; ecrire_saut(s14, v.f);
	c[0] = 0xeb; c[1] = 0xfe; for (int j = 2; j < 14; j++) c[j] = s14[j]; for (int j = 14; j < n; j++) c[j] = 0x90;
	__atomic_store_n((unsigned short *)c, (unsigned short)(s14[0] | (s14[1] << 8)), __ATOMIC_SEQ_CST);
	VirtualProtect(c, n, old, &old); FlushInstructionCache(GetCurrentProcess(), c, n);
	v.cible = c; v.n = n; v.actif = 1; l.s(" -> pose ("); l.i(n); l.s(" octets)"); journal(l);
}
static void noter_variantes() {
	if (!g_vt_ctx) return;
	for (int k = 0; k < 4; k++) { void *f = g_vt_ctx[g_el[k].i]; if (f == g_el[k].f) continue; int vu = 0;
		for (int j = 0; j < g_var_n[k]; j++) if (g_var[k][j] == f) vu = 1;
		if (!vu && g_var_n[k] < 4) g_var[k][g_var_n[k]++] = f;
		if (f != (void *)g_el[k].cible && g_el[k].actif && R.sonde_textures > 0) poser_variante(k, (unsigned char *)f); }
}
static void retirer_variantes() {
	for (auto &v : g_vb) if (v.actif) {
		DWORD old; if (!VirtualProtect(v.cible, v.n, 0x40, &old)) continue;
		v.cible[0] = 0xeb; v.cible[1] = 0xfe; for (int j = 2; j < v.n; j++) v.cible[j] = v.sauve[j];
		__atomic_store_n((unsigned short *)v.cible, (unsigned short)(v.sauve[0] | (v.sauve[1] << 8)), __ATOMIC_SEQ_CST);
		VirtualProtect(v.cible, v.n, old, &old); FlushInstructionCache(GetCurrentProcess(), v.cible, v.n); v.actif = 0;
	}
}
static void accrocher_contexte() {
	if (g_ctx && VT(g_ctx) != g_vt_ctx) {
		for (auto &c : g_cr) if (g_vt_ctx[c.i] == c.f) retirer(g_vt_ctx, c.i, *c.o);
		g_vt_ctx = VT(g_ctx);
		int ok = 1; for (auto &c : g_cr) ok &= poser(g_vt_ctx, c.i, c.f, c.o);
		Ligne l; l.s("contexte du jeu different de l'appareil jetable : crochets poses sur sa table ("); l.s(ok ? "ok" : "partiel"); l.s(") ; module "); module_de(l, g_vt_ctx[C_OMSetRT]); journal(l);
	} else { Ligne l; l.s("contexte du jeu = table deja accrochee ; module "); module_de(l, (void *)o_omsrt); journal(l); }
}
static i64 g_reposes, g_repose_i[140];
/* 0.10.3 : diagnostic du chemin de remplissage cache. Ecrit une fois : les 32 premiers octets du code de chaque fonction
   d'ecriture du contexte (pour preparer un crochet en ligne exact) et le module ; puis, toutes les 30 s, quelles entrees de table
   sont remises par quelqu'un d'autre (et combien de fois). */
static void octets_de(Ligne &l, const void *f) {
	const unsigned char *p = (const unsigned char *)f; static const char hx[] = "0123456789abcdef";
	for (int i = 0; i < 32; i++) { char b[3] = {hx[p[i] >> 4], hx[p[i] & 15], 0}; l.s(b); }
}
static void journal_prologues() {
	if (!g_vt_ctx) return;
	struct { int i; const char *n; } t[] = { {C_Map, "Map"}, {C_Unmap, "Unmap"}, {C_CopySubresourceRegion, "CopySubresourceRegion"}, {C_CopyResource, "CopyResource"},
		{C_UpdateSubresource, "UpdateSubresource"}, {115, "CopySubresourceRegion1"}, {116, "UpdateSubresource1"} };
	for (auto &e : t) {
		Crochet *c = 0; for (auto &k : g_cr) if (k.i == e.i) c = &k;
		void *f = c && *c->o ? *c->o : g_vt_ctx[e.i];
		Ligne l; l.s("prologue "); l.s(e.n); l.s(" "); l.x((u64)f); l.s(" "); module_de(l, f); l.s(" : "); octets_de(l, f); journal(l);
	}
}
/* profileur : creations sur la table du VRAI appareil du jeu (prise dans init_appareil), appelees depuis tous les fils */
typedef HRESULT (WINAPI *PFN_CTEX)(void *, const TEX2D_DESC *, const void *, void **);
typedef HRESULT (WINAPI *PFN_CPS)(void *, const void *, SIZE_T, void *, void **);
static PFN_CTEX o_ctex; static PFN_CPS o_cps; static void **g_vt_dev;
static void ajouter_creation(i64 *n, i64 t) { __atomic_fetch_add(n, 1, __ATOMIC_RELAXED); __atomic_fetch_add(&g_cree_t, t, __ATOMIC_RELAXED); }
/* 0.10 TSC Textures, etape 1 : RELEVE seulement (rien n'est remplace). Pour chaque texture du jeu creee avec ses donnees
   (textures de decor : pas de cible de rendu), on note une empreinte du niveau 0, la taille, le format, les niveaux.
   Sert a savoir (1) si le jeu envoie ses textures a la creation ou plus tard (UpdateSubresource, compte a part),
   (2) quelles empreintes reviennent d'une partie a l'autre (cle du cache HD). Plafond 40 000 lignes. */
static i64 g_tx_vides, g_tx_avec, g_vide_usage[4], g_vide_bc, g_vide_mips, g_vide_cpu;
static bool format_bloc(UINT f, UINT &octets) {
	if (f >= 70 && f <= 72) { octets = 8; return true; }     /* BC1 */
	if (f >= 73 && f <= 78) { octets = 16; return true; }    /* BC2, BC3 */
	if (f >= 79 && f <= 81) { octets = 8; return true; }     /* BC4 */
	if (f >= 82 && f <= 84) { octets = 16; return true; }    /* BC5 */
	if (f >= 94 && f <= 99) { octets = 16; return true; }    /* BC6H, BC7 */
	return false;
}
static u64 empreinte(const SUBRES *sr, const TEX2D_DESC *ds, u64 &taille) {
	UINT ob; UINT lignes = format_bloc(ds->Format, ob) ? (ds->Height + 3) / 4 : ds->Height;
	taille = (u64)sr->pitch * lignes; const unsigned char *p = (const unsigned char *)sr->p;
	u64 h = 1469598103934665603ULL ^ taille;
	/* au plus 4096 blocs de 16 octets repartis sur tout le niveau 0 : rapide et assez sur pour reconnaitre une texture */
	u64 pas = taille / 4096; if (pas < 16) pas = 16;
	for (u64 o = 0; o + 16 <= taille; o += pas) { const u64 *q = (const u64 *)(p + o); h = (h ^ q[0]) * 1099511628211ULL; h = (h ^ q[1]) * 1099511628211ULL; h ^= h >> 29; }
	return h;
}
static void releve_texture(const TEX2D_DESC *ds, const void *init) {
	if (!ds || (ds->BindFlags & 0x8 /*SHADER_RESOURCE*/) == 0 || (ds->BindFlags & 0xA0 /*RT|DS*/)) return;
	if (!init) { __atomic_fetch_add(&g_tx_vides, 1, __ATOMIC_RELAXED); __atomic_fetch_add(&g_vide_usage[ds->Usage & 3], 1, __ATOMIC_RELAXED);
		UINT ob; if (format_bloc(ds->Format, ob)) __atomic_fetch_add(&g_vide_bc, 1, __ATOMIC_RELAXED); if (ds->MipLevels != 1) __atomic_fetch_add(&g_vide_mips, 1, __ATOMIC_RELAXED);
		if (ds->CPUAccessFlags) __atomic_fetch_add(&g_vide_cpu, 1, __ATOMIC_RELAXED); return; }
	__atomic_fetch_add(&g_tx_avec, 1, __ATOMIC_RELAXED);
	if (R.sonde_textures <= 0 || ds->Width < 16 || ds->Height < 16) return;
	const SUBRES *sr = (const SUBRES *)init; if (!sr->p || !sr->pitch) return;
	u64 taille; u64 h = empreinte(sr, ds, taille);
	Ligne l; l.s("cree;"); l.x(h); l.s(";"); tx_desc(l, *ds, 0); l.i((i64)taille); l.s(";"); l.i((i64)GetTickCount64()); l.s("\r\n"); tx_ligne(l);
}
static HRESULT WINAPI h_ctex(void *d, const TEX2D_DESC *ds, const void *init, void **out) {
	if (g_nous) return o_ctex(d, ds, init, out);
	i64 a, b; QueryPerformanceCounter(&a); releve_texture(ds, init); HRESULT hr = o_ctex(d, ds, init, out); QueryPerformanceCounter(&b);
	if (hr >= 0 && out && *out && g_hd_actif) { tab_lock(); if (tab_lire(g_t_cle, g_t_val, *out)) tab_mettre(g_t_cle, g_t_val, *out, 0); tab_unlock(); }   /* adresse reutilisee : oublier l'ancienne HD */
	ajouter_creation(&g_cree_tex, b - a); return hr;
}
static HRESULT WINAPI h_cps(void *d, const void *code, SIZE_T n, void *lien, void **out) {
	if (g_nous) return o_cps(d, code, n, lien, out);
	i64 a, b; QueryPerformanceCounter(&a); HRESULT hr = o_cps(d, code, n, lien, out); QueryPerformanceCounter(&b);
	ajouter_creation(&g_cree_ps, b - a); return hr;
}
/* 0.10.2 : la 0.10.1 n'a vu AUCUN remplissage (ni Update, ni Copy, ni Map ecriture) sur le contexte immediat pour 3 544 textures vides.
   On regarde donc : contextes differes (fil de chargement : UpdateSubresource enregistre puis ExecuteCommandList),
   ID3D11Device3::CreateTexture2D1 (54) et WriteToSubresource (63), et le detail des textures vides. */
typedef HRESULT (WINAPI *PFN_CDEF)(void *, UINT, void **);
typedef HRESULT (WINAPI *PFN_CTEX1)(void *, const void *, const void *, void **);
typedef void (WINAPI *PFN_W2S)(void *, void *, UINT, const void *, const void *, UINT, UINT);
static PFN_CDEF o_cdef; static PFN_CTEX1 o_ctex1; static PFN_W2S o_w2s; static i64 g_cdef_n, g_cdef_autre_table, g_ctex1_n, g_ctex1_data, g_w2s_n;
static void **g_vt_def;   /* table d'un contexte differe, si differente de celle du contexte immediat */
static PFN_UPD d_upd; static PFN_MAP d_map; static PFN_COPYRES d_copyres; static PFN_COPYSUB d_copysub;
static i64 g_d_upd2, g_d_map_w, g_d_copy_decor, g_d_appels;
static void WINAPI hd_upd(void *c, void *r, UINT sub, const void *box, const void *data, UINT rp, UINT dp) {
	__atomic_fetch_add(&g_d_appels, 1, __ATOMIC_RELAXED);
	if (!g_nous && est_tex2d(r)) {
		__atomic_fetch_add(&g_d_upd2, 1, __ATOMIC_RELAXED);
		TEX2D_DESC d; if (R.sonde_textures > 0 && data && rp && !box && decor(r, d)) {
			UINT mips = d.MipLevels ? d.MipLevels : 1, niv = sub % mips;
			if (niv == 0 && d.Width >= 16 && d.Height >= 16) { SUBRES m = {data, rp, dp}; u64 taille; u64 h = empreinte(&m, &d, taille);
				Ligne l; l.s("differe_upd;"); l.x(h); l.s(";"); tx_desc(l, d, 0); l.i((i64)taille); l.s(";"); l.i((i64)GetTickCount64()); l.s("\r\n"); tx_ligne(l); }
		}
	}
	d_upd(c, r, sub, box, data, rp, dp);
}
static HRESULT WINAPI hd_map(void *c, void *r, UINT sub, UINT type, UINT fl, void *m) {
	__atomic_fetch_add(&g_d_appels, 1, __ATOMIC_RELAXED);
	if (!g_nous && (type == 2 || type == 4 || type == 5) && est_tex2d(r)) __atomic_fetch_add(&g_d_map_w, 1, __ATOMIC_RELAXED);
	return d_map(c, r, sub, type, fl, m);
}
static void WINAPI hd_copyres(void *c, void *dst, void *src) {
	__atomic_fetch_add(&g_d_appels, 1, __ATOMIC_RELAXED); TEX2D_DESC d; if (!g_nous && decor(dst, d)) __atomic_fetch_add(&g_d_copy_decor, 1, __ATOMIC_RELAXED);
	d_copyres(c, dst, src);
}
static void WINAPI hd_copysub(void *c, void *dst, UINT dsub, UINT x, UINT y, UINT z, void *src, UINT ssub, const void *box) {
	__atomic_fetch_add(&g_d_appels, 1, __ATOMIC_RELAXED); TEX2D_DESC d; if (!g_nous && decor(dst, d)) __atomic_fetch_add(&g_d_copy_decor, 1, __ATOMIC_RELAXED);
	d_copysub(c, dst, dsub, x, y, z, src, ssub, box);
}
static volatile long g_def_verrou;
static void accrocher_differe(void *ctx) {
	if (!ctx) return; void **vt = VT(ctx);
	if (vt == g_vt_ctx) return;   /* meme table que le contexte immediat : nos crochets 0.10.1 l'auraient vu */
	__atomic_fetch_add(&g_cdef_autre_table, 1, __ATOMIC_RELAXED);
	while (__atomic_exchange_n(&g_def_verrou, 1, __ATOMIC_ACQUIRE)) {}
	if (!g_vt_def) {
		g_vt_def = vt; int ok = 1;
		ok &= poser(vt, C_UpdateSubresource, (void *)hd_upd, (void **)&d_upd); ok &= poser(vt, C_Map, (void *)hd_map, (void **)&d_map);
		ok &= poser(vt, C_CopyResource, (void *)hd_copyres, (void **)&d_copyres); ok &= poser(vt, C_CopySubresourceRegion, (void *)hd_copysub, (void **)&d_copysub);
		Ligne l; l.s("TSC Textures : contexte differe avec sa propre table, crochets "); l.s(ok ? "ok" : "partiel"); l.s(" ; module "); module_de(l, (void *)d_upd); journal(l);
	}
	__atomic_store_n(&g_def_verrou, 0, __ATOMIC_RELEASE);
}
static HRESULT WINAPI h_cdef(void *d, UINT fl, void **out) {
	HRESULT hr = o_cdef(d, fl, out); if (!g_nous) { __atomic_fetch_add(&g_cdef_n, 1, __ATOMIC_RELAXED); if (hr >= 0 && out) accrocher_differe(*out); } return hr;
}
static HRESULT WINAPI h_ctex1(void *d, const void *ds, const void *init, void **out) {
	if (!g_nous) { __atomic_fetch_add(&g_ctex1_n, 1, __ATOMIC_RELAXED); if (init) __atomic_fetch_add(&g_ctex1_data, 1, __ATOMIC_RELAXED); }
	return o_ctex1(d, ds, init, out);
}
static void WINAPI h_w2s(void *d, void *r, UINT sub, const void *box, const void *src, UINT rp, UINT dp) { if (!g_nous) __atomic_fetch_add(&g_w2s_n, 1, __ATOMIC_RELAXED); o_w2s(d, r, sub, box, src, rp, dp); }
typedef HRESULT (WINAPI *PFN_QI)(void *, const GUIDx *, void **);
static const GUIDx IID_Dev3 = {0xa05c8c37, 0xd2c6, 0x4732, {0xb3, 0xa0, 0x9c, 0xe0, 0xb0, 0xdc, 0x9a, 0xe6}};
static void accrocher_dev3() {
	void *d3 = 0; if (((PFN_QI)VT(g_dev)[0])(g_dev, &IID_Dev3, &d3) < 0 || !d3) { logline("TSC Textures : ID3D11Device3 absent"); return; }
	void **vt = VT(d3); int ok = (int)poser(vt, 54, (void *)h_ctex1, (void **)&o_ctex1); ok &= (int)poser(vt, 63, (void *)h_w2s, (void **)&o_w2s);
	Ligne l; l.s("TSC Textures : ID3D11Device3 CreateTexture2D1/WriteToSubresource accroches "); l.s(ok ? "ok" : "non"); l.s(vt == g_vt_dev ? " (meme table)" : " (autre table)"); journal(l);
	REL(d3);
}
typedef HRESULT (WINAPI *PFN_CSRV)(void *, void *, const void *, void **); static PFN_CSRV o_csrv;
static HRESULT WINAPI h_csrv(void *d, void *res, const void *desc, void **out) {
	HRESULT hr = o_csrv(d, res, desc, out);
	if (hr >= 0 && out && *out) { tab_lock(); tab_mettre(g_v_cle, g_v_val, *out, g_nous ? 0 : res); tab_unlock(); }   /* nos vues : jamais remplacees (adresse reutilisee) */
	return hr;
}
static Crochet g_cr_dev[] = { {D_CreateSRV, (void *)h_csrv, (void **)&o_csrv}, {D_CreateTexture2D, (void *)h_ctex, (void **)&o_ctex}, {D_CreatePS, (void *)h_cps, (void **)&o_cps}, {27 /*CreateDeferredContext*/, (void *)h_cdef, (void **)&o_cdef} };
static void reposer() {
	noter_variantes();
	for (auto &c : g_cr) if (g_vt_ctx[c.i] != c.f) { if (poser(g_vt_ctx, c.i, c.f, c.o)) { g_reposes++; if (c.i < 140) g_repose_i[c.i]++; } }
	if (g_vt_dev) for (auto &c : g_cr_dev) if (g_vt_dev[c.i] != c.f) { if (poser(g_vt_dev, c.i, c.f, c.o)) g_reposes++; }
}

/* ---------- profileur TSC v1 ---------- */
/* DXGI 1.4 (dxgi1_4.h) : IDXGIDevice = 54ec77fa-1377-44e6-8c32-88fd5f44c84c, IDXGIAdapter3 = 645967a4-1392-4310-a798-8053ce3e93fd.
   Tables : IUnknown 0-2, IDXGIObject 3-6 (SetPrivateData, SetPrivateDataInterface, GetPrivateData, GetParent),
   IDXGIDevice::GetAdapter 7 (confiance elevee) ; IDXGIAdapter 7-9 (EnumOutputs, GetDesc, CheckInterfaceSupport),
   IDXGIAdapter1::GetDesc1 10, IDXGIAdapter2::GetDesc2 11, IDXGIAdapter3 : RegisterHardwareContentProtectionTeardownStatusEvent 12,
   UnregisterHardwareContentProtectionTeardownStatus 13, QueryVideoMemoryInfo 14, SetVideoMemoryReservation 15
   (confiance elevee : ordre de declaration de dxgi1_4.h ; en cas d'erreur l'appel echoue et le profileur l'ecrit une fois). */
static const GUIDx IID_DxgiDev = {0x54ec77fa, 0x1377, 0x44e6, {0x8c, 0x32, 0x88, 0xfd, 0x5f, 0x44, 0xc8, 0x4c}};
static const GUIDx IID_Adapt3 = {0x645967a4, 0x1392, 0x4310, {0xa7, 0x98, 0x80, 0x53, 0xce, 0x3e, 0x93, 0xfd}};
enum { G_GetAdapter = 7, A3_QueryVideoMemoryInfo = 14 };
struct MEMVID { u64 Budget, CurrentUsage, AvailableForReservation, CurrentReservation; };

static void prof_init() {
	static int fait; if (fait || !g_dev || !g_ctx) return; fait = 1;
	/* requetes GPU de toute l'image (objets distincts de g_q_dis / g_q_a / g_q_b) */
	int ok = 1;
	for (int i = 0; i < NP; i++) {
		QUERY_DESC q0 = {3 /*TIMESTAMP_DISJOINT*/, 0}, q1 = {2 /*TIMESTAMP*/, 0};
		typedef HRESULT (WINAPI *CQ)(void *, const QUERY_DESC *, void **);
		if (((CQ)VT(g_dev)[D_CreateQuery])(g_dev, &q0, &g_pg[i].dis) < 0) g_pg[i].dis = 0;
		if (((CQ)VT(g_dev)[D_CreateQuery])(g_dev, &q1, &g_pg[i].a) < 0) g_pg[i].a = 0;
		if (((CQ)VT(g_dev)[D_CreateQuery])(g_dev, &q1, &g_pg[i].b) < 0) g_pg[i].b = 0;
		if (!g_pg[i].dis || !g_pg[i].a || !g_pg[i].b) ok = 0;
	}
	if (!ok) { for (int i = 0; i < NP; i++) { REL(g_pg[i].dis); REL(g_pg[i].a); REL(g_pg[i].b); } logline("profileur : requetes GPU refusees, gpu_ms vide"); }
	g_pg_ok = ok;
	/* memoire video : IDXGIDevice -> GetAdapter -> IDXGIAdapter3 */
	void *dx = 0, *ad = 0;
	if (((PFN_QI)VT(g_dev)[0])(g_dev, &IID_DxgiDev, &dx) >= 0 && dx) {
		if (((HRESULT (WINAPI *)(void *, void **))VT(dx)[G_GetAdapter])(dx, &ad) >= 0 && ad) {
			if (((PFN_QI)VT(ad)[0])(ad, &IID_Adapt3, &g_adapt3) < 0) g_adapt3 = 0;
			REL(ad);
		}
		REL(dx);
	}
	if (!g_adapt3) logline("profileur : IDXGIAdapter3 indisponible, vram_mo vide");
	/* creations de shaders et de textures : table du vrai appareil */
	g_vt_dev = VT(g_dev);
	int okd = 1; for (auto &c : g_cr_dev) okd &= poser(g_vt_dev, c.i, c.f, c.o);
	accrocher_dev3();
	Ligne l; l.s("profileur TSC v1 : requetes GPU "); l.s(g_pg_ok ? "ok" : "non"); l.s(", memoire video "); l.s(g_adapt3 ? "ok" : "non");
	l.s(", crochets de creation "); l.s(okd ? "ok" : "partiel"); l.s(" ; module de l'appareil "); module_de(l, (void *)o_ctex); journal(l);
}
static HRESULT prof_lire(void *q, void *p, UINT n) {   /* jamais d'attente : DONOTFLUSH, S_FALSE (1) = pas pret */
	g_nous++; HRESULT hr = ((PFN_GETDATA)VT(g_ctx)[C_GetData])(g_ctx, q, p, n, 1 /*D3D11_ASYNC_GETDATA_DONOTFLUSH*/); g_nous--; return hr;
}
static void prof_fin_q(void *q) { ((void (WINAPI *)(void *, void *))VT(g_ctx)[C_End])(g_ctx, q); }
/* juste apres le retour du Present : debut de l'image g_p_img cote GPU */
static void prof_debut_image() {
	if (!g_ctx || !g_pg_ok || g_arret || !g_freq) return;
	i64 a; QueryPerformanceCounter(&a);
	ProfGpu &s = g_pg[g_p_img % NP];
	if (!(s.etat == 1 && s.img == g_p_img)) {   /* une requete encore en attente ici est abandonnee */
		g_nous++; ((void (WINAPI *)(void *, void *))VT(g_ctx)[C_Begin])(g_ctx, s.dis); prof_fin_q(s.a); g_nous--;
		s.etat = 1; s.img = g_p_img;
	}
	i64 b; QueryPerformanceCounter(&b); double ms = ms_de(b - a); g_cpu_ms += ms; g_prof_cpu_ms += ms;
}
static void prof_vider() { if (g_csv_n) { ecrire("tsc-profil.csv", g_csv, g_csv_n); g_csv_n = 0; } }
static void prof_ajouter(Ligne &l) { if (g_csv_n + l.n > (int)sizeof g_csv) prof_vider(); memcpy(g_csv + g_csv_n, l.t, l.n); g_csv_n += l.n; }
static void prof_emettre(ProfLigne &r) {
	r.pleine = 0;
	if (R.profil < 0.5f) return;
	if (!g_csv_entete) {
		g_csv_entete = 1;
		Ligne e; e.s("# "); e.s(VERSION); e.s(" ; session demarree au tick "); e.i((i64)GetTickCount64()); e.s(" ms ; QPC "); e.i(g_freq); e.s(" Hz\r\n"); prof_ajouter(e);
		Ligne c; c.s("image;t_ms;image_ms;gpu_ms;dessins;cibles;vues_gbuffer;vues_tsc;map_lect;map_ms;getdata_jeu;getdata_ms;shaders_crees;textures_creees;creation_ms;vram_mo;effet\r\n"); prof_ajouter(c);
	}
	Ligne l; l.i(r.img); l.s(";"); l.f(r.t_ms, 1); l.s(";"); l.f(r.image_ms, 3); l.s(";"); if (r.gpu_ms >= 0) l.f(r.gpu_ms, 3);
	l.s(";"); l.i(r.dessins); l.s(";"); l.i(r.cibles); l.s(";"); l.i(r.vues_g); l.s(";"); l.i(r.vues_t);
	l.s(";"); l.i(r.map_lect); l.s(";"); l.f(r.map_ms, 3); l.s(";"); l.i(r.getdata); l.s(";"); l.f(r.gd_ms, 3);
	l.s(";"); l.i(r.ps); l.s(";"); l.i(r.tex); l.s(";"); l.f(r.cree_ms, 3); l.s(";"); if (r.vram_mo >= 0) l.i(r.vram_mo); l.s(";"); l.i(r.effet); l.s("\r\n");
	prof_ajouter(l);
}
/* juste avant le Present : fin de l'image g_p_img (cote GPU et compteurs), lecture des anciennes, CSV */
static void prof_fin_image(i64 t0, double image_ms, int vues_g, int vues_t, u64 now) {
	i64 a; QueryPerformanceCounter(&a);
	if (!g_p_t0) g_p_t0 = t0;
	const i64 F = g_p_img;
	ProfGpu &s = g_pg[F % NP];
	if (g_ctx && g_pg_ok && s.etat == 1 && s.img == F) { g_nous++; prof_fin_q(s.b); prof_fin_q(s.dis); g_nous--; s.etat = 2; }
	/* ligne de l'image F */
	ProfLigne &L = g_pl[F % NR];
	if (L.pleine) prof_emettre(L);
	i64 ps = __atomic_exchange_n(&g_cree_ps, 0, __ATOMIC_RELAXED), tx = __atomic_exchange_n(&g_cree_tex, 0, __ATOMIC_RELAXED), ct = __atomic_exchange_n(&g_cree_t, 0, __ATOMIC_RELAXED);
	if (image_ms > 0) {
		L.img = F; L.t_ms = ms_de(t0 - g_p_t0); L.image_ms = image_ms; L.gpu_ms = -1;
		L.dessins = g_pf_dessins; L.cibles = g_pf_cibles; L.vues_g = vues_g; L.vues_t = vues_t;
		L.map_lect = g_pf_map; L.map_ms = ms_de(g_pf_map_t); L.getdata = g_pf_gd; L.gd_ms = ms_de(g_pf_gd_t);
		L.ps = ps; L.tex = tx; L.cree_ms = ms_de(ct); L.vram_mo = g_vram_mo; L.effet = g_effet_on > 0.5f && R.actif > 0.5f; L.pleine = 1;
		g_pw_n++; g_pw_img += image_ms; int k = (int)(image_ms / 0.2); if (k >= 0 && k < 500) g_hist[k]++;
		if (image_ms > 16.667 - 0.3 && image_ms < 16.667 + 0.3) g_pw_16++;
		if (image_ms > 33.333 - 0.3 && image_ms < 33.333 + 0.3) g_pw_33++;
		g_pw_map += g_pf_map; g_pw_map_ms += L.map_ms; g_pw_gd += g_pf_gd; g_pw_gd_ms += L.gd_ms; g_pw_cree += ps + tx; g_pw_cree_ms += L.cree_ms;
	}
	g_pf_dessins = g_pf_cibles = g_pf_map = g_pf_map_t = g_pf_gd = g_pf_gd_t = 0;
	/* lecture sans attente des images vieilles d'au moins 3 */
	if (g_ctx && g_pg_ok) for (int k = 0; k < NP; k++) {
		ProfGpu &q = g_pg[k]; if (q.etat != 2 || q.img > F - 3) continue;
		DISJOINT dj = {0, 0}; u64 ta = 0, tb = 0;
		HRESULT h = prof_lire(q.dis, &dj, sizeof dj); if (h == 0) h = prof_lire(q.a, &ta, 8); if (h == 0) h = prof_lire(q.b, &tb, 8);
		if (h == 1) continue;   /* pas pret : on reessaiera, ou l'emplacement sera repris */
		q.etat = 0;
		double g = h == 0 && !dj.Disjoint && dj.Frequency && tb >= ta ? (double)(tb - ta) * 1000.0 / (double)dj.Frequency : -1;
		ProfLigne &r = g_pl[q.img % NR];
		if (g >= 0 && r.pleine && r.img == q.img) { r.gpu_ms = g; g_pw_gpu += g; g_pw_gpu_img += r.image_ms; g_pw_ngpu++; }
	}
	/* une ligne est definitive quand son emplacement GPU ne peut plus etre lu (NP - 1 images plus tard) */
	for (i64 j = F - NR + 1; j <= F - (NP - 1); j++) if (j > 0) { ProfLigne &r = g_pl[j % NR]; if (r.pleine && r.img == j) prof_emettre(r); }
	/* memoire video une fois par seconde, tampon CSV vide une fois par seconde */
	static u64 t_vram; static int vram_err;
	if (g_adapt3 && now - t_vram >= 1000) {
		t_vram = now; MEMVID m; memset(&m, 0, sizeof m);
		HRESULT h = ((HRESULT (WINAPI *)(void *, UINT, UINT, MEMVID *))VT(g_adapt3)[A3_QueryVideoMemoryInfo])(g_adapt3, 0, 0 /*LOCAL*/, &m);
		if (h >= 0) { g_vram_mo = (int)(m.CurrentUsage >> 20); g_vram_budget_mo = (int)(m.Budget >> 20); }
		else { g_vram_mo = g_vram_budget_mo = -1; if (!vram_err++) logline("profileur : QueryVideoMemoryInfo refuse", h & 0xffffffffLL); }
	}
	if (now - g_csv_t >= 1000) { g_csv_t = now; prof_vider(); }
	g_p_img++;
	i64 b; QueryPerformanceCounter(&b); g_prof_cpu_ms += ms_de(b - a);   /* deja compte dans le CPU TSC d'apres_image */
}
/* verdict sur la fenetre du rapport (2 s), ajoute a la ligne mesure :
   - occupation GPU = temps GPU moyen / temps d'image moyen (sur les images dont le temps GPU est arrive) ;
   - "plafond" : plus de 80 % des images a 0,3 ms pres de 16,67 ms, de 33,33 ms, ou du mode (le mode seulement si
     l'occupation est <= 85 %, car une image limitee par le GPU mais stable se groupe aussi autour de son mode) ;
   - sinon "GPU" si occupation > 85 % ; "CPU" si occupation < 60 % et image > 18 ms ; sinon "marge". */
static void prof_rapport(Ligne &l, int n_img) {
	double occ = g_pw_ngpu && g_pw_gpu_img > 0 ? g_pw_gpu / g_pw_gpu_img : -1;
	int km = 0; for (int k = 1; k < 500; k++) if (g_hist[k] > g_hist[km]) km = k;
	int nm = g_hist[km] + (km > 0 ? g_hist[km - 1] : 0) + (km < 499 ? g_hist[km + 1] : 0);   /* mode +/- 0,3 ms */
	int np = g_pw_16 >= g_pw_33 ? g_pw_16 : g_pw_33; double centre = g_pw_16 >= g_pw_33 ? 16.67 : 33.33;
	if ((occ < 0 || occ <= 0.85) && nm > np) { np = nm; centre = (km + 0.5) * 0.2; }
	double fp = g_pw_n ? (double)np / g_pw_n : 0, moy = g_pw_n ? g_pw_img / g_pw_n : 0;
	const char *v = fp > 0.8 ? "plafond" : occ < 0 ? "inconnu" : occ > 0.85 ? "GPU" : (occ < 0.60 && moy > 18) ? "CPU" : "marge";
	l.s(" ; gpu image moy "); if (g_pw_ngpu) l.f(g_pw_gpu / g_pw_ngpu, 2); else l.s("-"); l.s(" ms, gpu occupe "); if (occ >= 0) l.f(occ * 100, 0); else l.s("-");
	l.s(" % ; verdict "); l.s(v); l.s(" (groupees "); l.f(fp * 100, 0); l.s(" % autour de "); l.f(centre, 2);
	l.s(" ms) ; map lecture "); l.i(g_pw_map); l.s(" ("); l.f(g_pw_map_ms, 2); l.s(" ms), getdata jeu "); l.i(g_pw_gd); l.s(" ("); l.f(g_pw_gd_ms, 2);
	l.s(" ms), creations "); l.i(g_pw_cree); l.s(" ("); l.f(g_pw_cree_ms, 2); l.s(" ms) ; vram "); if (g_vram_mo >= 0) { l.i(g_vram_mo); l.s(" / budget "); l.i(g_vram_budget_mo); l.s(" Mo"); } else l.s("-");
	l.s(" ; profileur CPU "); l.f(n_img ? g_prof_cpu_ms / n_img : 0, 3); l.s(" ms");
	memset(g_hist, 0, sizeof g_hist); g_pw_n = g_pw_16 = g_pw_33 = g_pw_ngpu = 0; g_pw_img = g_pw_gpu = g_pw_gpu_img = g_prof_cpu_ms = 0;
	g_pw_map = g_pw_gd = g_pw_cree = 0; g_pw_map_ms = g_pw_gd_ms = g_pw_cree_ms = 0;
}

/* ---------- par image ---------- */
static bool touche(int vk) { return (GetAsyncKeyState(vk) & 0x8000) != 0; }
static bool frappe(int vk, int &mem) { bool b = touche(0x11) && touche(0x10) && touche(vk); bool r = b && !mem; mem = b; return r; }

static void apres_image(void *sc) {
	i64 t0; QueryPerformanceCounter(&t0);
	if (!g_freq) QueryPerformanceFrequency(&g_freq);
	double dt = 0, image_ms = 0;
	if (g_t_prec) { double ms = (double)(t0 - g_t_prec) * 1000.0 / (double)g_freq; dt = ms / 1000.0; image_ms = ms; g_somme_ms += ms; if (ms > g_pire_ms) g_pire_ms = ms; g_n_img++; }
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

	static u64 t_ini, t_bascule; u64 now = GetTickCount64();
	/* essai sans les mains : effet coupe / active tout seul toutes les bascule_auto secondes (0 = touche seulement) */
	if (R.bascule_auto >= 2) {
		if (!t_bascule) t_bascule = now;
		if (now - t_bascule >= (u64)(R.bascule_auto * 1000)) { t_bascule = now; g_effet_on = g_effet_on > 0.5f ? 0 : 1; logline(g_effet_on > 0.5f ? "effet TSC : MARCHE (bascule auto)" : "effet TSC : ARRET (bascule auto)"); }
	} else t_bascule = 0;
	{ static u64 t_tx; if (!t_tx) t_tx = now; if (now - t_tx > 30000) { t_tx = now; Ligne l; l.s("TSC Textures (releve) : creees avec donnees "); l.i(g_tx_avec);
		l.s(", creees vides "); l.i(g_tx_vides); l.s(", remplies apres (UpdateSubresource 2D) "); l.i(g_tx_upd2); l.s(", lignes tsc-textures.csv "); l.i(g_tx_lignes); journal(l);
		Ligne m; m.s("TSC Textures (chemins) : Map tex2D READ "); m.i(g_mx[1]); m.s(" WRITE "); m.i(g_mx[2]); m.s(" READ_WRITE "); m.i(g_mx[3]); m.s(" WRITE_DISCARD "); m.i(g_mx[4]);
		m.s(" NO_OVERWRITE "); m.i(g_mx[5]); m.s(" ; usage default/immutable/dynamic/staging "); m.i(g_mx_usage[0]); m.s("/"); m.i(g_mx_usage[1]); m.s("/"); m.i(g_mx_usage[2]); m.s("/"); m.i(g_mx_usage[3]);
		m.s(" ; CopyResource "); m.i(g_cp_res); m.s(" CopySubresourceRegion "); m.i(g_cp_sub); m.s(" CSR1 "); m.i(g_cp_sub1); m.s(" dont vers texture de decor "); m.i(g_cp_vers_decor);
		m.s(" ; UpdateSubresource1 2D "); m.i(g_upd1_2d); m.s(" ; Map hors contexte immediat "); m.i(g_mx_autre_ctx); m.s(" ; autres contextes vus "); m.i(g_ctx_n); journal(m);
		Ligne v; v.s("TSC Textures (vides) : usage default/immutable/dynamic/staging "); v.i(g_vide_usage[0]); v.s("/"); v.i(g_vide_usage[1]); v.s("/"); v.i(g_vide_usage[2]); v.s("/"); v.i(g_vide_usage[3]);
		v.s(" ; compressees BC "); v.i(g_vide_bc); v.s(" ; avec niveaux "); v.i(g_vide_mips); v.s(" ; acces CPU "); v.i(g_vide_cpu);
		v.s(" ; contextes differes crees "); v.i(g_cdef_n); v.s(" (autre table "); v.i(g_cdef_autre_table); v.s(") appels "); v.i(g_d_appels); v.s(" Update2D "); v.i(g_d_upd2); v.s(" MapW "); v.i(g_d_map_w); v.s(" Copy decor "); v.i(g_d_copy_decor);
		v.s(" ; ExecuteCommandList "); v.i(g_exec_n); v.s(" ; CreateTexture2D1 "); v.i(g_ctex1_n); v.s(" (avec donnees "); v.i(g_ctex1_data); v.s(") ; WriteToSubresource "); v.i(g_w2s_n); journal(v);
		static int prol; if (!prol) { prol = 1; journal_prologues(); }
		Ligne q; q.s("TSC Textures (en ligne) :"); for (int k = 0; k < 4; k++) { q.s(" "); q.s(g_el[k].nom); q.s(g_el[k].actif ? "=pose" : "=non"); q.s(" variantes "); q.i(g_var_n[k]);
			for (int j = 0; j < g_var_n[k]; j++) { q.s(" "); q.x((u64)g_var[k][j]); q.s(g_var[k][j] == (void *)g_el[k].cible ? "(=accrochee)" : "(AUTRE)"); } } journal(q);
		{ Ligne z; z.s("etage apres tone mapping : images avec les 3 ecrans "); z.i(g_ldr_img3); z.s(", images incompletes "); z.i(g_ldr_imgpas3); z.s(", autres cibles 8 bits ignorees "); z.i(g_ldr_saut); journal(z); }
		Ligne u; u.s("TSC Textures (tri) : updates vers decor "); u.i(g_upd_decor); u.s(", dont boite partielle "); u.i(g_upd_boite_part); u.s(", niveaux >0 "); u.i(g_upd_niv);
		u.s(" ; variantes en ligne"); for (int k = 0; k < 4; k++) { u.s(" "); u.s(g_vb[k].actif ? "oui" : (g_vb[k].tente ? "refus" : "-")); } u.s(" ; lignes csv "); u.i(g_tx_lignes); u.s(" ; extraites "); u.i(g_vide_n); u.s(" ("); u.i(g_vide_octets >> 20); u.s(" Mo, formats refuses "); u.i(g_vide_refus); u.s(")"); journal(u);
		{ Ligne x; x.s("TSC Textures HD : disponibles "); x.i(g_hd_n); x.s(", posees "); x.i(g_hd_crees); x.s(", refusees "); x.i(g_hd_refus); x.s(", appels remplaces "); x.i(g_hd_rempl); x.s(R.textures_hd > 0 ? " (marche)" : " (coupe)"); journal(x); }
		Ligne w; w.s("TSC Textures (entrees remises) :"); for (int i = 0; i < 140; i++) if (g_repose_i[i]) { w.s(" "); w.i(i); w.s("="); w.i(g_repose_i[i]); } journal(w); } }
	if (now - t_ini > 1000) { t_ini = now; lire_ini(false); if (g_dev) { compiler(); charger_lut(); } if ((int)R.vue > 0 && (int)R.vue < 4) g_vue = (int)R.vue; }
	static i64 n_total; n_total++;
	{ static float prec = -1; if (prec < 0) prec = R.trace; else if (R.trace != prec) { prec = R.trace; if (!g_trace) { g_trace = 2; g_tn = 0; logline("trace d'une image demandee par l'ini"); } } }
	{ static float prec = -1; if (prec < 0) prec = R.enregistre; else if (R.enregistre != prec) { prec = R.enregistre; if (R.enregistre > 0) { g_enr_reste = (int)R.enregistre; g_enr_t = 0; Ligne l; l.s("TSC Neural : enregistrement de "); l.i(g_enr_reste); l.s(" images (une toutes les 2 s, sans effet)"); journal(l); } } }
	if (g_enr_image) { g_enr_image = 0; Ligne l; l.s("TSC Neural : image "); l.i(g_enr_num); l.s(" enregistree"); journal(l); }
	if (g_enr_reste > 0 && now - g_enr_t >= 2000) { g_enr_t = now; g_enr_reste--; g_enr_num++; g_enr_image = 1; }
	if (!g_trace_auto_fait && n_total > 1200) { g_trace_auto_fait = 1; g_trace = 2; g_tn = 0; logline("trace automatique d'une image (20 s apres le debut)"); }

	init_appareil(sc);
	if (!g_bw) { void *bb = 0; if (((HRESULT (WINAPI *)(void *, UINT, const GUIDx *, void **))VT(sc)[S_GetBuffer])(sc, 0, &IID_Tex2D, &bb) >= 0 && bb) { TEX2D_DESC d; desc_tex(bb, d); g_bw = d.Width; g_bh = d.Height; Ligne l; l.s("image presentee : "); dire_tex(l, bb); journal(l); ((UINT (WINAPI *)(void *))VT(bb)[2])(bb); } }
	g_vues_rapport += g_vues_traitees;
	int vues_g = g_vues_image, vues_t = g_vues_traitees;
	g_vues_prec = g_vues_traitees; g_vues_image = 0; g_vues_traitees = 0; g_ldr_n = 0; ldr_fin_image();
	reposer();
	prof_fin_image(t0, image_ms, vues_g, vues_t, now);   /* en dernier : son horodatage GPU est la fin de l'image */

	i64 t1; QueryPerformanceCounter(&t1); g_cpu_ms += (double)(t1 - t0) * 1000.0 / (double)g_freq;
	if (now - g_t_rapport > 2000 && g_n_img) {
		Ligne l; l.s("mesure : "); l.f(1000.0 * g_n_img / (g_somme_ms > 0 ? g_somme_ms : 1), 1); l.s(" img/s, image moy "); l.f(g_somme_ms / g_n_img); l.s(" ms, pire ");
		l.f(g_pire_ms); l.s(" ms, TSC CPU (profileur compris) "); l.f(g_cpu_ms / g_n_img, 3); l.s(" ms, TSC GPU "); if (g_n_gpu) l.f(g_gpu_ms / g_n_gpu, 3); else l.s("-"); l.s(" ms ; vues traitees/image ");
		l.f((double)g_vues_rapport / g_n_img, 2); l.s(" ; effet "); l.s(g_effet_on > 0.5f && R.actif > 0.5f ? "marche" : "arret"); l.s(" ; pluie "); l.s(g_pluie ? "oui" : "non");
		l.s(" (gouttes max "); l.i(g_gouttes_rapport); l.s(") ; humidite "); l.f(R.humidite >= 0 ? R.humidite : g_mouille); l.s(" ; G-buffer vus "); l.i(g_n_gbuf); l.s(" (petites vues ignorees "); l.i(g_n_petites); l.s(")"); l.s(", HDR vus "); l.i(g_n_hdr);
		l.s(" ; effacement z="); l.f(g_val_effacement, 3); l.s(" ; crochets reposes "); l.i(g_reposes); l.s(" ; changements de cibles "); l.i(g_n_omsrt); l.s(", dessins "); l.i(g_n_dessins);
		prof_rapport(l, g_n_img);
		journal(l);
		if (g_n_gpu && (int)R.mode != 0) {   /* gestionnaire de budget : garder le cout TSC sous budget_ms */
			double c = g_gpu_ms / g_n_gpu;
			if (c > R.budget_ms && g_qualite > 0.4f) { g_qualite *= 0.85f; if (g_qualite < 0.4f) g_qualite = 0.4f; Ligne b; b.s("budget : TSC GPU "); b.f(c, 2); b.s(" ms > "); b.f(R.budget_ms, 2); b.s(" ms -> qualite "); b.f(g_qualite, 2); journal(b); }
			else if (c < R.budget_ms * 0.6 && g_qualite < 1) { g_qualite *= 1.05f; if (g_qualite > 1) g_qualite = 1; }
		}
		g_t_rapport = now; g_somme_ms = g_pire_ms = g_cpu_ms = g_gpu_ms = 0; g_n_img = g_n_gpu = 0; g_vues_rapport = 0; g_gouttes_rapport = 0; g_n_gbuf = g_n_hdr = 0; g_n_petites = 0; g_n_omsrt = g_n_dessins = 0;
	}
	if (g_trace) {
		if (--g_trace == 0) { Ligne l; l.s("=== fin de la trace ==="); trace_txt(l); ecrire("tsc-graphics-trace.log", g_tbuf, g_tn); logline("trace ecrite dans tsc-graphics-trace.log"); }
		else { g_tn = 0; Ligne l; l.s("=== trace d'une image, "); l.s(VERSION); l.s(", image "); l.i(g_bw); l.s("x"); l.i(g_bh); l.s(" ==="); trace_txt(l); }
	}
}

/* DXGI_PRESENT_TEST (1) : rien n'est presente, ce n'est pas une image */
static HRESULT WINAPI h_present(void *sc, UINT sync, UINT fl) {
	if (fl & 1) return o_present(sc, sync, fl);
	apres_image(sc); HRESULT hr = o_present(sc, sync, fl); prof_debut_image(); return hr;
}
static HRESULT WINAPI h_present1(void *sc, UINT sync, UINT fl, const void *p) {
	if (fl & 1) return o_present1(sc, sync, fl, p);
	apres_image(sc); HRESULT hr = o_present1(sc, sync, fl, p); prof_debut_image(); return hr;
}
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
	poser_en_ligne(g_vt_ctx);
	hd_lister();
	g_hooks = 1;
	logline(ok ? "crochets poses (Present, ResizeBuffers, cibles, effacements, viewports, dessins, Map, GetData)" : "certains crochets n'ont pas pu etre poses");
	REL(ctx); REL(dev); REL(sc); DestroyWindow(fen);
	HMODULE h; GetModuleHandleExA(5, (const char *)&scs_telemetry_init, &h);
	return 0;
}
extern "C" void scs_telemetry_shutdown(void) {
	if (!g_hooks) return;
	for (auto &c : g_cr) if (g_vt_ctx[c.i] == c.f) retirer(g_vt_ctx, c.i, *c.o);
	retirer_variantes(); retirer_en_ligne();
	for (auto &e : g_el) if (!e.actif && g_vt_ctx[e.i] == e.f) retirer(g_vt_ctx, e.i, *e.o);
	if (g_vt_dev) for (auto &c : g_cr_dev) if (g_vt_dev[c.i] == c.f) retirer(g_vt_dev, c.i, *c.o);
	for (i64 j = g_p_img - NR + 1; j <= g_p_img; j++) if (j > 0) { ProfLigne &r = g_pl[j % NR]; if (r.pleine && r.img == j) prof_emettre(r); }
	prof_vider();
	if (o_present1 && g_vt_sc[S1_Present1] == (void *)h_present1) retirer(g_vt_sc, S1_Present1, (void *)o_present1);
	if (g_vt_sc[S_ResizeBuffers] == (void *)h_resize) retirer(g_vt_sc, S_ResizeBuffers, (void *)o_resize);
	if (g_vt_sc[S_Present] == (void *)h_present) retirer(g_vt_sc, S_Present, (void *)o_present);
	g_hooks = 0; g_arret = 1; logline("crochets retires");
}
extern "C" BOOL WINAPI DllMain(HMODULE h, DWORD r, void *x) {
	(void)x;
	if (r == 1) { g_mod = h; GetModuleFileNameA(h, g_dir, 290); int i = lng(g_dir); while (i > 0 && g_dir[i - 1] != '\\' && g_dir[i - 1] != '/') i--; g_dir[i] = 0; }
	if (r == 0 && !x) scs_telemetry_shutdown();
	return 1;
}
