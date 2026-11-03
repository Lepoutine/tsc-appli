/*
 * TSC Clapet (tsc-clapet.dll) : clapet d'echappement sur touche, plugin de telemetrie ETS2 / ATS.
 * Copyright (c) 2026 Truck So Clean France. Tous droits reserves.
 * Construit sur le SCS SDK (c) SCS Software (licence MIT, sdk/LICENSE_SCS_SDK.txt).
 *
 * Fonctionnement :
 *  - le jeu appelle nos callbacks (regime, accelerateur, moteur, pause) : on recopie 4 nombres, rien d'autre ;
 *  - un fil a nous fait tout le reste : touche V, sons (XAudio2 de Windows), lecture des fichiers ;
 *  - les sons sont dans %LOCALAPPDATA%\TruckSoCleanFrance\TSC\clapet\ :
 *      c_<regime>.wav  couches "clapet ouvert" en boucle (PCM 16 bits), ex. c_1200.wav
 *      ouverture.wav   son ponctuel a l'ouverture (facultatif)
 *      fermeture.wav   son ponctuel a la fermeture (facultatif)
 *      reglages.ini    facultatif : volume=80 (0 a 150)
 *  - journal.txt (meme dossier) dit ce qui a ete charge.
 * Recette identique a Sound Forge (connaissances/fmod/06_tsc_clapet.md).
 * Si quelque chose manque (fichiers, XAudio2), le plugin reste muet, sans jamais gener le jeu.
 */
#include <stddef.h>
#include "scssdk_telemetry.h"
#include "eurotrucks2/scssdk_eut2.h"
#include "eurotrucks2/scssdk_telemetry_eut2.h"
#include "amtrucks/scssdk_ats.h"
#include "amtrucks/scssdk_telemetry_ats.h"
#include "common/scssdk_telemetry_common_channels.h"
#include "common/scssdk_telemetry_truck_common_channels.h"

#include "clapet_win.h"
#ifndef TSC_TEST
extern "C" int _fltused = 0x9875;
/* le compilateur peut appeler memset / memcpy meme sans CRT */
extern "C" void *memset(void *d, int c, size_t n) { volatile unsigned char *p = (volatile unsigned char *)d; while (n--) *p++ = (unsigned char)c; return d; }
extern "C" void *memcpy(void *d, const void *s, size_t n) { volatile unsigned char *p = (volatile unsigned char *)d; const unsigned char *q = (const unsigned char *)s; while (n--) *p++ = *q++; return d; }
#endif

/* ------------------------------------------------------------------ XAudio2 2.9 (xaudio2_9.dll, Windows 10+) */
#pragma pack(push, 1)
struct WAVEFORMATEX_ { unsigned short wFormatTag, nChannels; DWORD nSamplesPerSec, nAvgBytesPerSec; unsigned short nBlockAlign, wBitsPerSample, cbSize; };
struct XAUDIO2_BUFFER_ { UINT32 Flags, AudioBytes; const BYTE *pAudioData; UINT32 PlayBegin, PlayLength, LoopBegin, LoopLength, LoopCount; void *pContext; };
#pragma pack(pop)
#define XAUDIO2_END_OF_STREAM 0x0040
#define XAUDIO2_LOOP_INFINITE 255

struct IXAudio2Voice_ {
	virtual void WINAPI GetVoiceDetails(void *) = 0;
	virtual HRESULT WINAPI SetOutputVoices(const void *) = 0;
	virtual HRESULT WINAPI SetEffectChain(const void *) = 0;
	virtual HRESULT WINAPI EnableEffect(UINT32, UINT32) = 0;
	virtual HRESULT WINAPI DisableEffect(UINT32, UINT32) = 0;
	virtual void WINAPI GetEffectState(UINT32, BOOL *) = 0;
	virtual HRESULT WINAPI SetEffectParameters(UINT32, const void *, UINT32, UINT32) = 0;
	virtual HRESULT WINAPI GetEffectParameters(UINT32, void *, UINT32) = 0;
	virtual HRESULT WINAPI SetFilterParameters(const void *, UINT32) = 0;
	virtual void WINAPI GetFilterParameters(void *) = 0;
	virtual HRESULT WINAPI SetOutputFilterParameters(void *, const void *, UINT32) = 0;
	virtual void WINAPI GetOutputFilterParameters(void *, void *) = 0;
	virtual HRESULT WINAPI SetVolume(float, UINT32) = 0;
	virtual void WINAPI GetVolume(float *) = 0;
	virtual HRESULT WINAPI SetChannelVolumes(UINT32, const float *, UINT32) = 0;
	virtual void WINAPI GetChannelVolumes(UINT32, float *) = 0;
	virtual HRESULT WINAPI SetOutputMatrix(void *, UINT32, UINT32, const float *, UINT32) = 0;
	virtual void WINAPI GetOutputMatrix(void *, UINT32, UINT32, float *) = 0;
	virtual void WINAPI DestroyVoice() = 0;
};
struct IXAudio2SourceVoice_ : IXAudio2Voice_ {
	virtual HRESULT WINAPI Start(UINT32, UINT32) = 0;
	virtual HRESULT WINAPI Stop(UINT32, UINT32) = 0;
	virtual HRESULT WINAPI SubmitSourceBuffer(const XAUDIO2_BUFFER_ *, const void *) = 0;
	virtual HRESULT WINAPI FlushSourceBuffers() = 0;
	virtual HRESULT WINAPI Discontinuity() = 0;
	virtual HRESULT WINAPI ExitLoop(UINT32) = 0;
	virtual void WINAPI GetState(void *, UINT32) = 0;
	virtual HRESULT WINAPI SetFrequencyRatio(float, UINT32) = 0;
	virtual void WINAPI GetFrequencyRatio(float *) = 0;
	virtual HRESULT WINAPI SetSourceSampleRate(UINT32) = 0;
};
struct IXAudio2_ {
	virtual HRESULT WINAPI QueryInterface(const void *, void **) = 0;
	virtual unsigned long WINAPI AddRef() = 0;
	virtual unsigned long WINAPI Release() = 0;
	virtual HRESULT WINAPI RegisterForCallbacks(void *) = 0;
	virtual void WINAPI UnregisterForCallbacks(void *) = 0;
	virtual HRESULT WINAPI CreateSourceVoice(IXAudio2SourceVoice_ **, const WAVEFORMATEX_ *, UINT32, float, void *, const void *, const void *) = 0;
	virtual HRESULT WINAPI CreateSubmixVoice(void **, UINT32, UINT32, UINT32, UINT32, const void *, const void *) = 0;
	virtual HRESULT WINAPI CreateMasteringVoice(IXAudio2Voice_ **, UINT32, UINT32, UINT32, const WCHAR *, const void *, int) = 0;
	virtual HRESULT WINAPI StartEngine() = 0;
	virtual void WINAPI StopEngine() = 0;
	virtual HRESULT WINAPI CommitChanges(UINT32) = 0;
	virtual void WINAPI GetPerformanceData(void *) = 0;
	virtual void WINAPI SetDebugConfiguration(const void *, void *) = 0;
};
typedef HRESULT (WINAPI *XAudio2Create_t)(IXAudio2_ **, UINT32, UINT32);
typedef HRESULT (WINAPI *CoInitializeEx_t)(void *, DWORD);
typedef void (WINAPI *CoUninitialize_t)(void);
typedef short (WINAPI *GetAsyncKeyState_t)(int);
typedef HWND (WINAPI *GetForegroundWindow_t)(void);
typedef DWORD (WINAPI *GetWindowThreadProcessId_t)(HWND, DWORD *);

/* ------------------------------------------------------------------ etat partage (jeu -> notre fil) */
static volatile float g_rpm = 0.0f, g_gaz = 0.0f;
static volatile int g_moteur = 0, g_pause = 1, g_stop = 0;
static HANDLE g_fil = 0;

/* ------------------------------------------------------------------ petits outils */
static float bornes(float x, float a, float b) { return x < a ? a : (x > b ? b : x); }
static float sin_q(float x) /* sinus sur [0, pi/2] */
{ float x2 = x * x; return x * (1.0f - x2 / 6.0f * (1.0f - x2 / 20.0f * (1.0f - x2 / 42.0f))); }
static const float DEMI_PI = 1.5707963f;
static size_t wlen(const WCHAR *s) { size_t n = 0; while (s[n]) ++n; return n; }
static void wcat(WCHAR *d, size_t taille, const WCHAR *s) { size_t n = wlen(d); while (*s && n + 1 < taille) d[n++] = *s++; d[n] = 0; }
static void wcat_a(WCHAR *d, size_t taille, const char *s) { size_t n = wlen(d); while (*s && n + 1 < taille) d[n++] = (WCHAR)(unsigned char)*s++; d[n] = 0; }
static void *alloue(size_t n) { return HeapAlloc(GetProcessHeap(), 0, n); }
static void libere(void *p) { if (p) HeapFree(GetProcessHeap(), 0, p); }

static WCHAR g_dossier[300];
static char g_journal[2048]; static size_t g_jn = 0;
static void j(const char *s) { while (*s && g_jn + 1 < sizeof(g_journal)) g_journal[g_jn++] = *s++; g_journal[g_jn] = 0; }
static void jn(long v) { char b[24]; int i = 22; int neg = v < 0; unsigned long u = neg ? -v : v; b[23] = 0; do { b[i--] = (char)('0' + u % 10); u /= 10; } while (u && i >= 0); if (neg) b[i--] = '-'; j(&b[i + 1]); }
static void ecrit_journal(void)
{
	WCHAR ch[340]; ch[0] = 0; wcat(ch, 340, g_dossier); wcat_a(ch, 340, "journal.txt");
	HANDLE f = CreateFileW(ch, GENERIC_WRITE, FILE_SHARE_READ, 0, CREATE_ALWAYS, 0x80, 0);
	if (f == INVALID_HANDLE_VALUE) return;
	DWORD e; WriteFile(f, g_journal, (DWORD)g_jn, &e, 0); CloseHandle(f);
}

/* lit un fichier entier (max 64 Mo) */
static BYTE *lit(const WCHAR *ch, DWORD *taille, DWORD mini)
{
	HANDLE f = CreateFileW(ch, GENERIC_READ, FILE_SHARE_READ, 0, OPEN_EXISTING, 0x80, 0);
	if (f == INVALID_HANDLE_VALUE) return 0;
	DWORD n = GetFileSize(f, 0), e = 0;
	BYTE *b = (n >= mini && n > 0 && n < (64u << 20)) ? (BYTE *)alloue(n) : 0;
	if (b && (!ReadFile(f, b, n, &e, 0) || e != n)) { libere(b); b = 0; }
	CloseHandle(f); *taille = n; return b;
}

/* ------------------------------------------------------------------ sons */
struct Son {
	BYTE *fichier; const BYTE *pcm; UINT32 octets; WAVEFORMATEX_ fmt;
	IXAudio2SourceVoice_ *voix; float rpm; float vol;
};
#define MAX_COUCHES 24
static Son g_c[MAX_COUCHES]; static int g_nc = 0;
static Son g_ouv, g_ferm;

/* WAV PCM 16 bits : on garde le fichier, on pointe sur les donnees */
static int charge_wav(const WCHAR *ch, Son *s)
{
	DWORD n = 0; BYTE *b = lit(ch, &n, 45); size_t p = 12; int fmt_ok = 0;
	if (!b) return 0;
	if (!(b[0] == 'R' && b[1] == 'I' && b[2] == 'F' && b[3] == 'F' && b[8] == 'W' && b[9] == 'A' && b[10] == 'V' && b[11] == 'E')) { libere(b); return 0; }
	while (p + 8 <= n) {
		UINT32 t = b[p + 4] | (b[p + 5] << 8) | (b[p + 6] << 16) | ((UINT32)b[p + 7] << 24);
		if (t > n - p - 8) t = (UINT32)(n - p - 8);
		if (b[p] == 'f' && b[p + 1] == 'm' && b[p + 2] == 't' && t >= 16) {
			unsigned short tag = b[p + 8] | (b[p + 9] << 8);
			s->fmt.wFormatTag = 1; s->fmt.nChannels = b[p + 10] | (b[p + 11] << 8);
			s->fmt.nSamplesPerSec = b[p + 12] | (b[p + 13] << 8) | (b[p + 14] << 16) | ((DWORD)b[p + 15] << 24);
			s->fmt.wBitsPerSample = b[p + 22] | (b[p + 23] << 8);
			s->fmt.nBlockAlign = (unsigned short)(s->fmt.nChannels * s->fmt.wBitsPerSample / 8);
			s->fmt.nAvgBytesPerSec = s->fmt.nSamplesPerSec * s->fmt.nBlockAlign; s->fmt.cbSize = 0;
			fmt_ok = (tag == 1 || tag == 0xFFFE) && s->fmt.wBitsPerSample == 16 && s->fmt.nChannels >= 1 && s->fmt.nChannels <= 2 && s->fmt.nSamplesPerSec >= 8000;
		} else if (b[p] == 'd' && b[p + 1] == 'a' && b[p + 2] == 't' && b[p + 3] == 'a' && fmt_ok) {
			s->fichier = b; s->pcm = b + p + 8; s->octets = t - t % s->fmt.nBlockAlign;
			return s->octets > 0;
		}
		p += 8 + t + (t & 1);
	}
	libere(b); return 0;
}

static int cree_voix(IXAudio2_ *xa, Son *s, int boucle)
{
	if (xa->CreateSourceVoice(&s->voix, &s->fmt, 0, 2.0f, 0, 0, 0) < 0) { s->voix = 0; return 0; }
	s->voix->SetVolume(0.0f, 0);
	if (boucle) {
		XAUDIO2_BUFFER_ b; memset(&b, 0, sizeof b);
		b.Flags = XAUDIO2_END_OF_STREAM; b.AudioBytes = s->octets; b.pAudioData = s->pcm; b.LoopCount = XAUDIO2_LOOP_INFINITE;
		s->voix->SubmitSourceBuffer(&b, 0); s->voix->Start(0, 0);
	}
	return 1;
}
static void joue_une_fois(Son *s, float vol)
{
	if (!s->voix) return;
	s->voix->Stop(0, 0); s->voix->FlushSourceBuffers();
	XAUDIO2_BUFFER_ b; memset(&b, 0, sizeof b);
	b.Flags = XAUDIO2_END_OF_STREAM; b.AudioBytes = s->octets; b.pAudioData = s->pcm;
	s->voix->SetVolume(vol, 0); s->voix->SubmitSourceBuffer(&b, 0); s->voix->Start(0, 0);
}

static int nombre_du_nom(const WCHAR *n) /* c_1200.wav -> 1200 */
{ int v = 0; n += 2; while (*n >= '0' && *n <= '9') { v = v * 10 + (*n - '0'); ++n; } return v; }

static float lit_volume(void)
{
	WCHAR ch[340]; ch[0] = 0; wcat(ch, 340, g_dossier); wcat_a(ch, 340, "reglages.ini");
	DWORD n = 0; BYTE *b = lit(ch, &n, 1); float v = 0.8f;
	if (!b) return v;
	for (DWORD i = 0; i + 7 < n; ++i) if (b[i] == 'v' && b[i + 1] == 'o' && b[i + 2] == 'l' && b[i + 3] == 'u' && b[i + 4] == 'm' && b[i + 5] == 'e' && b[i + 6] == '=') {
		int x = 0; DWORD k = i + 7; while (k < n && b[k] >= '0' && b[k] <= '9') { x = x * 10 + (b[k] - '0'); ++k; }
		v = bornes(x / 100.0f, 0.0f, 1.5f); break;
	}
	libere(b); return v;
}

/* ------------------------------------------------------------------ fil du clapet */
static DWORD WINAPI fil(void *)
{
	HMODULE ole = LoadLibraryW(L"ole32.dll"), xdll = 0, u32 = LoadLibraryW(L"user32.dll");
	CoInitializeEx_t coinit = ole ? (CoInitializeEx_t)GetProcAddress(ole, "CoInitializeEx") : 0;
	CoUninitialize_t counit = ole ? (CoUninitialize_t)GetProcAddress(ole, "CoUninitialize") : 0;
	GetAsyncKeyState_t touche = u32 ? (GetAsyncKeyState_t)GetProcAddress(u32, "GetAsyncKeyState") : 0;
	GetForegroundWindow_t avant = u32 ? (GetForegroundWindow_t)GetProcAddress(u32, "GetForegroundWindow") : 0;
	GetWindowThreadProcessId_t proc = u32 ? (GetWindowThreadProcessId_t)GetProcAddress(u32, "GetWindowThreadProcessId") : 0;
	IXAudio2_ *xa = 0; IXAudio2Voice_ *maitre = 0; int co = 0;
	float volume = lit_volume();

	j("TSC Clapet 0.1\r\n");
	if (coinit && coinit(0, 0 /* COINIT_MULTITHREADED */) >= 0) co = 1;
	xdll = LoadLibraryW(L"xaudio2_9.dll");
	XAudio2Create_t cree = xdll ? (XAudio2Create_t)GetProcAddress(xdll, "XAudio2Create") : 0;
	if (!cree || (cree(&xa, 0, 0) < 0 && cree(&xa, 0, 0xFFFFFFFFu) < 0)) { xa = 0; j("XAudio2 indisponible : plugin muet.\r\n"); }
	if (xa && xa->CreateMasteringVoice(&maitre, 0, 0, 0, 0, 0, 6 /* AudioCategory_GameEffects */) < 0) { maitre = 0; j("Sortie audio indisponible : plugin muet.\r\n"); }

	if (xa && maitre) {
		/* couches c_<regime>.wav, triees par regime */
		WCHAR motif[340]; motif[0] = 0; wcat(motif, 340, g_dossier); wcat_a(motif, 340, "c_*.wav");
		static WIN32_FIND_DATAW_ fd; HANDLE h = FindFirstFileW(motif, &fd);
		if (h != INVALID_HANDLE_VALUE) {
			do {
				if (g_nc >= MAX_COUCHES) break;
				int r = nombre_du_nom(fd.cFileName); if (r < 300 || r > 4000) continue;
				WCHAR ch[340]; ch[0] = 0; wcat(ch, 340, g_dossier); wcat(ch, 340, fd.cFileName);
				Son s; memset(&s, 0, sizeof s); s.rpm = (float)r;
				if (!charge_wav(ch, &s)) { j("illisible (PCM 16 bits attendu) : couche "); jn(r); j("\r\n"); continue; }
				int i = g_nc++; while (i > 0 && g_c[i - 1].rpm > s.rpm) { g_c[i] = g_c[i - 1]; --i; } g_c[i] = s;
			} while (FindNextFileW(h, &fd));
			FindClose(h);
		}
		for (int i = 0; i < g_nc; ++i) cree_voix(xa, &g_c[i], 1);
		WCHAR ch[340];
		ch[0] = 0; wcat(ch, 340, g_dossier); wcat_a(ch, 340, "ouverture.wav"); if (charge_wav(ch, &g_ouv)) cree_voix(xa, &g_ouv, 0);
		ch[0] = 0; wcat(ch, 340, g_dossier); wcat_a(ch, 340, "fermeture.wav"); if (charge_wav(ch, &g_ferm)) cree_voix(xa, &g_ferm, 0);
		j("couches clapet : "); jn(g_nc); for (int i = 0; i < g_nc; ++i) { j(i ? ", " : " ("); jn((long)g_c[i].rpm); } j(g_nc ? ")\r\n" : "\r\n");
		j("ouverture : "); j(g_ouv.voix ? "oui" : "non"); j(", fermeture : "); j(g_ferm.voix ? "oui" : "non"); j("\r\n");
		j("volume : "); jn((long)(volume * 100.0f + 0.5f)); j(" ; touche : V seule (ignoree avec Ctrl, Maj ou Alt)\r\n");
	}
	ecrit_journal();

	/* boucle toutes les 10 ms : touche + volumes + vitesses de lecture */
	int ouvert = 0, appui = 0; float K = 0.0f, M = 0.0f; DWORD t0 = GetTickCount();
	while (!g_stop) {
		Sleep(10);
		DWORD t = GetTickCount(); float dt = (t - t0) / 1000.0f; t0 = t; if (dt > 0.1f) dt = 0.1f;
		if (!g_nc) continue;
		/* touche V : seulement si la fenetre du jeu est devant, sans Ctrl / Maj / Alt */
		int v = 0;
		if (touche && avant && proc) {
			DWORD pid = 0; HWND w = avant(); if (w) proc(w, &pid);
			if (pid == GetCurrentProcessId() && !g_pause)
				v = (touche(0x56) & 0x8000) && !(touche(0x10) & 0x8000) && !(touche(0x11) & 0x8000) && !(touche(0x12) & 0x8000);
		}
		if (v && !appui) {
			ouvert = !ouvert;
			if (g_moteur) joue_une_fois(ouvert ? &g_ouv : &g_ferm, volume);
		}
		appui = v;
		/* etat du clapet : ouverture 180 ms, fermeture 350 ms */
		K += ouvert ? dt / 0.18f : -dt / 0.35f; K = bornes(K, 0.0f, 1.0f);
		const float rpm = g_rpm, L = bornes(g_gaz, 0.0f, 1.0f);
		const float cible = (g_moteur && !g_pause) ? bornes(rpm / 400.0f, 0.0f, 1.0f) : 0.0f;
		M += (cible - M) * bornes(dt * 12.0f, 0.0f, 1.0f);
		const float base = volume * M * K * (0.55f + 0.45f * L);
		/* fondu a puissance constante entre les deux couches voisines */
		int i = 0; while (i < g_nc && g_c[i].rpm < rpm) ++i;
		for (int k = 0; k < g_nc; ++k) g_c[k].vol = 0.0f;
		if (i == 0) g_c[0].vol = 1.0f;
		else if (i == g_nc) g_c[g_nc - 1].vol = 1.0f;
		else { float u = bornes((rpm - g_c[i - 1].rpm) / (g_c[i].rpm - g_c[i - 1].rpm), 0.0f, 1.0f);
			g_c[i - 1].vol = sin_q((1.0f - u) * DEMI_PI); g_c[i].vol = sin_q(u * DEMI_PI); }
		for (int k = 0; k < g_nc; ++k) if (g_c[k].voix) {
			g_c[k].voix->SetVolume(base * g_c[k].vol, 0);
			g_c[k].voix->SetFrequencyRatio(bornes(rpm / g_c[k].rpm, 0.5f, 2.0f), 0);
		}
	}

	for (int k = 0; k < g_nc; ++k) { if (g_c[k].voix) g_c[k].voix->DestroyVoice(); libere(g_c[k].fichier); }
	if (g_ouv.voix) g_ouv.voix->DestroyVoice(); libere(g_ouv.fichier);
	if (g_ferm.voix) g_ferm.voix->DestroyVoice(); libere(g_ferm.fichier);
	if (maitre) maitre->DestroyVoice();
	if (xa) xa->Release();
	g_nc = 0; memset(&g_ouv, 0, sizeof g_ouv); memset(&g_ferm, 0, sizeof g_ferm);
	if (xdll) FreeLibrary(xdll);
	if (co && counit) counit();
	if (ole) FreeLibrary(ole);
	if (u32) FreeLibrary(u32);
	return 0;
}

/* ------------------------------------------------------------------ callbacks du jeu : on recopie, rien d'autre */
static SCSAPI_VOID c_float(const scs_string_t, const scs_u32_t, const scs_value_t *const v, const scs_context_t ctx)
{ if (ctx) *(volatile float *)ctx = (v && v->type == SCS_VALUE_TYPE_float) ? v->value_float.value : 0.0f; }
static SCSAPI_VOID c_bool(const scs_string_t, const scs_u32_t, const scs_value_t *const v, const scs_context_t ctx)
{ if (ctx) *(volatile int *)ctx = (v && v->type == SCS_VALUE_TYPE_bool && v->value_bool.value) ? 1 : 0; }
static SCSAPI_VOID e_pause(const scs_event_t e, const void *const, const scs_context_t)
{ g_pause = (e == SCS_TELEMETRY_EVENT_paused) ? 1 : 0; }

SCSAPI_RESULT scs_telemetry_init(const scs_u32_t version, const scs_telemetry_init_params_t *const params)
{
	const scs_telemetry_init_params_v100_t *p = (const scs_telemetry_init_params_v100_t *)params;
	if (version != SCS_TELEMETRY_VERSION_1_00 && version != SCS_TELEMETRY_VERSION_1_01) return SCS_RESULT_unsupported;
	if (!p || !p->register_for_channel || !p->register_for_event) return SCS_RESULT_generic_error;
	if (g_fil) return SCS_RESULT_generic_error;

	WCHAR la[260]; DWORD n = GetEnvironmentVariableW(L"LOCALAPPDATA", la, 260);
	if (!n || n >= 200) return SCS_RESULT_generic_error;
	g_dossier[0] = 0; wcat(g_dossier, 300, la); wcat_a(g_dossier, 300, "\\TruckSoCleanFrance\\TSC\\clapet\\");

	g_rpm = 0.0f; g_gaz = 0.0f; g_moteur = 0; g_pause = 1; g_stop = 0; g_jn = 0; g_journal[0] = 0;
	p->register_for_event(SCS_TELEMETRY_EVENT_paused, e_pause, 0);
	p->register_for_event(SCS_TELEMETRY_EVENT_started, e_pause, 0);
	p->register_for_channel(SCS_TELEMETRY_TRUCK_CHANNEL_engine_rpm, SCS_U32_NIL, SCS_VALUE_TYPE_float, SCS_TELEMETRY_CHANNEL_FLAG_none, c_float, (scs_context_t)&g_rpm);
	p->register_for_channel(SCS_TELEMETRY_TRUCK_CHANNEL_effective_throttle, SCS_U32_NIL, SCS_VALUE_TYPE_float, SCS_TELEMETRY_CHANNEL_FLAG_none, c_float, (scs_context_t)&g_gaz);
	p->register_for_channel(SCS_TELEMETRY_TRUCK_CHANNEL_engine_enabled, SCS_U32_NIL, SCS_VALUE_TYPE_bool, SCS_TELEMETRY_CHANNEL_FLAG_none, c_bool, (scs_context_t)&g_moteur);

	g_fil = CreateThread(0, 0, fil, 0, 0, 0);
	if (p->common.log) p->common.log(SCS_LOG_TYPE_message, g_fil ? "[TSC Clapet] 0.1 pret (touche V)" : "[TSC Clapet] fil non cree : plugin muet");
	return SCS_RESULT_ok;
}

SCSAPI_VOID scs_telemetry_shutdown(void)
{
	/* le jeu desinscrit lui-meme nos callbacks ; on arrete notre fil */
	g_stop = 1;
	if (g_fil) { WaitForSingleObject(g_fil, 3000); CloseHandle(g_fil); g_fil = 0; }
}

extern "C" BOOL WINAPI DllMain(HMODULE, DWORD, void *) { return 1; }
