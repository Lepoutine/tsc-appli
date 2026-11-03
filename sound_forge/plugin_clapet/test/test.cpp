/* Test de tsc_clapet.cpp : faux jeu, faux Windows, faux XAudio2 ; controle memoire par ASan. */
#include "clapet_win.h"
#include <vector>
#include <map>
#include <cmath>
#include "scssdk_telemetry.h"
#include "eurotrucks2/scssdk_eut2.h"
#include "common/scssdk_telemetry_truck_common_channels.h"
#pragma pack(push, 1)
struct WF { unsigned short tag, ch; DWORD sr, abps; unsigned short ba, bits, cb; };
struct XB { UINT32 Flags, AudioBytes; const BYTE *p; UINT32 PB, PL, LB, LL, LC; void *ctx; };
#pragma pack(pop)
std::string t_appdata; int t_touches[256]; DWORD t_pid_avant = 42;
struct Voix { int id; float vol = -1, ratio = 1; int starts = 0, submits = 0, boucle = 0, detruite = 0; unsigned sr = 0, ch = 0; };
std::vector<Voix *> voix; pthread_mutex_t mx = PTHREAD_MUTEX_INITIALIZER;
struct FauxV {
	virtual void GetVoiceDetails(void *) {} virtual HRESULT SetOutputVoices(const void *) { return 0; } virtual HRESULT SetEffectChain(const void *) { return 0; }
	virtual HRESULT EnableEffect(UINT32, UINT32) { return 0; } virtual HRESULT DisableEffect(UINT32, UINT32) { return 0; } virtual void GetEffectState(UINT32, BOOL *) {}
	virtual HRESULT SetEffectParameters(UINT32, const void *, UINT32, UINT32) { return 0; } virtual HRESULT GetEffectParameters(UINT32, void *, UINT32) { return 0; }
	virtual HRESULT SetFilterParameters(const void *, UINT32) { return 0; } virtual void GetFilterParameters(void *) {}
	virtual HRESULT SetOutputFilterParameters(void *, const void *, UINT32) { return 0; } virtual void GetOutputFilterParameters(void *, void *) {}
	virtual HRESULT SetVolume(float v, UINT32) { pthread_mutex_lock(&mx); d->vol = v; pthread_mutex_unlock(&mx); return 0; } virtual void GetVolume(float *) {}
	virtual HRESULT SetChannelVolumes(UINT32, const float *, UINT32) { return 0; } virtual void GetChannelVolumes(UINT32, float *) {}
	virtual HRESULT SetOutputMatrix(void *, UINT32, UINT32, const float *, UINT32) { return 0; } virtual void GetOutputMatrix(void *, UINT32, UINT32, float *) {}
	virtual void DestroyVoice() { d->detruite++; }
	virtual HRESULT Start(UINT32, UINT32) { d->starts++; return 0; } virtual HRESULT Stop(UINT32, UINT32) { return 0; }
	virtual HRESULT SubmitSourceBuffer(const XB *b, const void *) { d->submits++; d->boucle = b->LC == 255; if (!b->p || !b->AudioBytes || b->ctx) d->id = -999; return 0; }
	virtual HRESULT FlushSourceBuffers() { return 0; } virtual HRESULT Discontinuity() { return 0; } virtual HRESULT ExitLoop(UINT32) { return 0; } virtual void GetState(void *, UINT32) {}
	virtual HRESULT SetFrequencyRatio(float r, UINT32) { pthread_mutex_lock(&mx); d->ratio = r; pthread_mutex_unlock(&mx); return 0; } virtual void GetFrequencyRatio(float *) {} virtual HRESULT SetSourceSampleRate(UINT32) { return 0; }
	Voix *d; virtual ~FauxV() {}
};
std::vector<FauxV *> tas;
struct FauxXA {
	virtual HRESULT QueryInterface(const void *, void **) { return 0; } virtual unsigned long AddRef() { return 1; } virtual unsigned long Release() { rel++; return 0; }
	virtual HRESULT RegisterForCallbacks(void *) { return 0; } virtual void UnregisterForCallbacks(void *) {}
	virtual HRESULT CreateSourceVoice(FauxV **pv, const WF *f, UINT32, float, void *, const void *, const void *) { Voix *v = new Voix; v->id = (int)voix.size(); v->sr = f->sr; v->ch = f->ch; voix.push_back(v); FauxV *x = new FauxV; x->d = v; tas.push_back(x); *pv = x; return 0; }
	virtual HRESULT CreateSubmixVoice(void **, UINT32, UINT32, UINT32, UINT32, const void *, const void *) { return -1; }
	virtual HRESULT CreateMasteringVoice(FauxV **pv, UINT32, UINT32, UINT32, const WCHAR *, const void *, int cat) { Voix *v = new Voix; v->id = 1000 + cat; FauxV *x = new FauxV; x->d = v; tas.push_back(x); *pv = x; maitre = v; maitres.push_back(v); return 0; }
	virtual HRESULT StartEngine() { return 0; } virtual void StopEngine() {} virtual HRESULT CommitChanges(UINT32) { return 0; } virtual void GetPerformanceData(void *) {} virtual void SetDebugConfiguration(const void *, void *) {}
	int rel = 0; Voix *maitre = 0; std::vector<Voix *> maitres; virtual ~FauxXA() {}
} xa;
HRESULT f_xcreate(FauxXA **p, UINT32, UINT32) { *p = &xa; return 0; }
HRESULT f_coinit(void *, DWORD) { return 0; } void f_counit() {}
short f_touche(int k) { return t_touches[k & 255] ? (short)0x8000 : 0; }
HWND f_avant() { return (HWND)1; } DWORD f_pid(HWND, DWORD *p) { *p = t_pid_avant; return 1; }
void *t_proc(const char *n) {
	std::map<std::string, void *> m = {{"XAudio2Create", (void *)f_xcreate}, {"CoInitializeEx", (void *)f_coinit}, {"CoUninitialize", (void *)f_counit},
		{"GetAsyncKeyState", (void *)f_touche}, {"GetForegroundWindow", (void *)f_avant}, {"GetWindowThreadProcessId", (void *)f_pid}};
	return m.count(n) ? m[n] : 0;
}
/* faux jeu */
struct Ch { std::string n; scs_telemetry_channel_callback_t cb; scs_context_t ctx; };
std::vector<Ch> chans; std::map<int, scs_telemetry_event_callback_t> evs;
SCSAPI_RESULT regev(const scs_event_t e, const scs_telemetry_event_callback_t cb, const scs_context_t) { evs[e] = cb; return SCS_RESULT_ok; }
SCSAPI_RESULT regch(const scs_string_t n, const scs_u32_t, const scs_value_type_t, const scs_u32_t, const scs_telemetry_channel_callback_t cb, const scs_context_t c) { chans.push_back({n, cb, c}); return SCS_RESULT_ok; }
std::string journal_jeu; void logf(const scs_log_type_t, const scs_string_t m) { journal_jeu += m; }
void setf(const char *n, float f) { scs_value_t v; v.type = SCS_VALUE_TYPE_float; v.value_float.value = f; for (auto &c : chans) if (c.n == n) c.cb(n, SCS_U32_NIL, &v, c.ctx); }
void setb(const char *n, int b) { scs_value_t v; v.type = SCS_VALUE_TYPE_bool; v.value_bool.value = b; for (auto &c : chans) if (c.n == n) c.cb(n, SCS_U32_NIL, &v, c.ctx); }
int fails = 0; void ok(bool b, const char *m) { printf("%s %s\n", b ? "OK " : "ERR", m); if (!b) fails++; }
void wav(const std::string &f, int sr, int ch, int bits, float hz, float dur) {
	FILE *o = fopen(f.c_str(), "wb"); int n = (int)(sr * dur), ba = ch * bits / 8, data = n * ba;
	auto u32 = [&](unsigned v) { fwrite(&v, 4, 1, o); }; auto u16 = [&](unsigned short v) { fwrite(&v, 2, 1, o); };
	fwrite("RIFF", 1, 4, o); u32(36 + 26 + data); fwrite("WAVE", 1, 4, o);
	fwrite("LIST", 1, 4, o); u32(18); fwrite("INFOISFT\x06\0\0\0TSC!\0\0", 1, 18, o); /* morceau en plus, a sauter */
	fwrite("fmt ", 1, 4, o); u32(16); u16(1); u16(ch); u32(sr); u32(sr * ba); u16(ba); u16(bits);
	fwrite("data", 1, 4, o); u32(data);
	for (int i = 0; i < n; ++i) for (int c = 0; c < ch; ++c) { short s = (short)(8000 * sin(2 * M_PI * hz * i / sr)); if (bits == 16) fwrite(&s, 2, 1, o); else fputc(128, o); }
	fclose(o);
}
Voix *couche(unsigned i) { return i < voix.size() ? voix[i] : 0; }
float vol(int i) { pthread_mutex_lock(&mx); float v = voix[i]->vol; pthread_mutex_unlock(&mx); return v; }
float rat(int i) { pthread_mutex_lock(&mx); float v = voix[i]->ratio; pthread_mutex_unlock(&mx); return v; }
void appuie(int k, std::vector<int> mods = {}) { for (int m : mods) t_touches[m] = 1; t_touches[k] = 1; Sleep(60); t_touches[k] = 0; for (int m : mods) t_touches[m] = 0; Sleep(30); }
int main() {
	char tmpl[] = "/tmp/clapet_testXXXXXX"; t_appdata = mkdtemp(tmpl);
	std::string d = t_appdata + "/TruckSoCleanFrance/TSC/clapet/";
	system(("mkdir -p '" + d + "'").c_str());
	wav(d + "c_1800.wav", 48000, 2, 16, 90, 0.5f); wav(d + "c_600.wav", 48000, 2, 16, 30, 0.5f); wav(d + "c_1200.wav", 44100, 1, 16, 60, 0.5f);
	wav(d + "c_900.wav", 48000, 1, 8, 45, 0.2f); /* 8 bits : refuse */
	wav(d + "ouverture.wav", 48000, 1, 16, 300, 0.1f); wav(d + "fermeture.wav", 48000, 1, 16, 200, 0.1f);
	{ FILE *o = fopen((d + "c_abc.wav").c_str(), "wb"); fputs("pas un wav", o); fclose(o); }
	{ FILE *o = fopen((d + "reglages.ini").c_str(), "wb"); fputs("volume=100\n", o); fclose(o); }

	scs_telemetry_init_params_v101_t p; memset(&p, 0, sizeof p);
	p.common.log = logf; p.common.game_id = SCS_GAME_ID_EUT2; p.common.game_version = SCS_MAKE_VERSION(1, 18); p.register_for_event = regev; p.register_for_channel = regch;
	ok(scs_telemetry_init(SCS_TELEMETRY_VERSION_1_01, (const scs_telemetry_init_params_t *)&p) == SCS_RESULT_ok, "init");
	ok(scs_telemetry_init(SCS_TELEMETRY_VERSION_1_01, (const scs_telemetry_init_params_t *)&p) != SCS_RESULT_ok, "2e init refusee");
	ok(chans.size() == 3 && evs.size() == 2, "3 canaux + pause/reprise");
	ok(journal_jeu.find("[TSC Clapet] 0.1") != std::string::npos, "message dans le journal du jeu");
	Sleep(200);
	FILE *jf = fopen((d + "journal.txt").c_str(), "rb"); char jt[2048] = {0}; if (jf) { fread(jt, 1, 2047, jf); fclose(jf); }
	printf("--- journal.txt ---\n%s-------------------\n", jt);
	ok(strstr(jt, "couches clapet : 3 (600, 1200, 1800)") != 0, "3 couches triees, 8 bits et c_abc refusees");
	ok(strstr(jt, "ouverture : oui, fermeture : oui") && strstr(jt, "volume : 100"), "effets + reglages lus");
	ok(voix.size() == 5 && couche(0)->boucle && couche(1)->boucle && couche(2)->boucle && couche(0)->starts == 1, "3 voix en boucle demarrees + 2 effets");
	ok(couche(1)->sr == 44100 && couche(1)->ch == 1, "format de chaque fichier respecte");
	ok(xa.maitre && xa.maitre->id == 1006, "sortie en categorie GameEffects");

	/* jeu en pause : rien ne sonne meme moteur en marche */
	setb("truck.engine.enabled", 1); setf("truck.engine.rpm", 900); setf("truck.effective.throttle", 1);
	appuie(0x56); Sleep(300);
	ok(vol(0) == 0 && vol(1) == 0, "pause : V ignore, silence");
	evs[SCS_TELEMETRY_EVENT_started](SCS_TELEMETRY_EVENT_started, 0, 0); Sleep(50);
	ok(vol(0) == 0, "reprise, clapet ferme : silence");
	appuie(0x56); Sleep(400);
	printf("   900 tr/min, pied au plancher : v600=%.3f v1200=%.3f v1800=%.3f r600=%.2f r1200=%.2f\n", vol(0), vol(1), vol(2), rat(0), rat(1));
	ok(fabs(vol(0) - 0.7071f) < 0.02f && fabs(vol(1) - 0.7071f) < 0.02f && vol(2) == 0, "V : clapet ouvert, fondu a puissance constante 600/1200");
	ok(fabs(rat(0) - 1.5f) < 0.01f && fabs(rat(1) - 0.75f) < 0.01f, "vitesse = regime / regime de la couche");
	ok(couche(3)->starts == 1 && couche(4)->starts == 0, "son d'ouverture joue une fois");
	setf("truck.effective.throttle", 0); setf("truck.engine.rpm", 2500); Sleep(100);
	ok(fabs(vol(2) - 0.55f) < 0.02f && rat(2) <= 2.0f && fabs(rat(2) - 2500.0f / 1800) < 0.01f, "lever de pied a 2500 : couche haute a 55 %");
	setf("truck.engine.rpm", 200); setf("truck.effective.throttle", 1); Sleep(400);
	ok(vol(0) > 0.45f && vol(0) < 0.55f && rat(0) == 0.5f, "200 tr/min : volume moitie (sous 400), vitesse bornee a 0,5");
	setf("truck.engine.rpm", 1200); Sleep(300);
	appuie(0x56, {0x11}); Sleep(100); ok(vol(1) > 0.9f, "Ctrl+V ignore (coller)");
	appuie(0x56, {0x10}); Sleep(100); ok(vol(1) > 0.9f, "Maj+V ignore (marche avant)");
	t_pid_avant = 7; appuie(0x56); Sleep(100); ok(vol(1) > 0.9f, "autre fenetre devant : ignore"); t_pid_avant = 42;
	appuie(0x56); Sleep(500);
	ok(vol(1) == 0 && couche(4)->starts == 1, "V : clapet ferme, son de fermeture");
	appuie(0x56); Sleep(100); setb("truck.engine.enabled", 0); Sleep(400);
	ok(vol(1) < 0.01f, "moteur coupe : silence");
	{ scs_value_t v; v.type = SCS_VALUE_TYPE_bool; v.value_bool.value = 1; for (auto &c : chans) if (c.n == "truck.engine.rpm") c.cb(c.n.c_str(), SCS_U32_NIL, &v, c.ctx);
	  for (auto &c : chans) c.cb(c.n.c_str(), SCS_U32_NIL, nullptr, c.ctx); ok(true, "valeur nulle / mauvais type sans plantage"); }
	scs_telemetry_shutdown();
	ok(couche(0)->detruite && couche(4)->detruite && xa.maitre->detruite && xa.rel == 1, "arret : voix detruites, XAudio2 libere");
	ok(scs_telemetry_init(SCS_TELEMETRY_VERSION_1_01, (const scs_telemetry_init_params_t *)&p) == SCS_RESULT_ok, "rechargement du plugin");
	Sleep(150); scs_telemetry_shutdown();
	for (auto *v : voix) delete v; for (auto *x : tas) delete x; for (auto *m : xa.maitres) delete m;
	system(("rm -rf '" + t_appdata + "'").c_str());
	printf(fails ? "\n%d ECHEC(S)\n" : "\nTOUT EST BON\n", fails); return fails != 0;
}
