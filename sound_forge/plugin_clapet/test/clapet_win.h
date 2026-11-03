/* Faux Windows pour tester tsc_clapet.cpp sous Linux (fichiers reels, faux XAudio2, fausse touche). */
#pragma once
#include <pthread.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dirent.h>
#include <fnmatch.h>
#include <time.h>
#include <string>
typedef void *HANDLE; typedef void *HMODULE; typedef void *HWND; typedef int BOOL; typedef unsigned long DWORD;
typedef wchar_t WCHAR; typedef long HRESULT; typedef unsigned int UINT32; typedef unsigned char BYTE;
#define WINAPI
#define INVALID_HANDLE_VALUE ((HANDLE)(long long)-1)
struct FILETIME_ { DWORD lo, hi; };
struct WIN32_FIND_DATAW_ { DWORD dwFileAttributes; FILETIME_ c, a, w; DWORD nFileSizeHigh, nFileSizeLow, r0, r1; WCHAR cFileName[260]; WCHAR cAlternateFileName[14]; };
#define GENERIC_READ 0x80000000u
#define GENERIC_WRITE 0x40000000u
#define FILE_SHARE_READ 1
#define OPEN_EXISTING 3
#define CREATE_ALWAYS 2
extern std::string t_appdata; extern int t_touches[256]; extern DWORD t_pid_avant;
void *t_proc(const char *n);
static inline std::string nar(const WCHAR *w) { std::string s; while (*w) { s += (*w == L'\\') ? '/' : (char)*w; ++w; } return s; }
struct T_fil { int genre; pthread_t t; DWORD (*f)(void *); void *a; };
static inline void *t_tramp(void *x) { T_fil *f = (T_fil *)x; f->f(f->a); return 0; }
static inline HANDLE CreateThread(void *, size_t, DWORD (*f)(void *), void *a, DWORD, DWORD *) { T_fil *x = new T_fil{1, 0, f, a}; pthread_create(&x->t, 0, t_tramp, x); return x; }
static inline DWORD WaitForSingleObject(HANDLE h, DWORD) { pthread_join(((T_fil *)h)->t, 0); return 0; }
static inline BOOL CloseHandle(HANDLE h);
static inline void Sleep(DWORD ms) { usleep(ms * 1000); }
static inline HMODULE LoadLibraryW(const WCHAR *n) { return (HMODULE)strdup(nar(n).c_str()); }
static inline BOOL FreeLibrary(HMODULE m) { free(m); return 1; }
static inline void *GetProcAddress(HMODULE, const char *n) { return t_proc(n); }
static inline HANDLE GetProcessHeap(void) { return (HANDLE)1; }
static inline void *HeapAlloc(HANDLE, DWORD, size_t n) { return malloc(n); }
static inline BOOL HeapFree(HANDLE, DWORD, void *p) { free(p); return 1; }
static inline DWORD GetEnvironmentVariableW(const WCHAR *, WCHAR *b, DWORD n) { size_t i = 0; for (; i < t_appdata.size() && i + 1 < n; ++i) b[i] = t_appdata[i]; b[i] = 0; return (DWORD)i; }
struct T_f { int genre; FILE *f; int dossier; DIR *d; std::string motif; };
static inline HANDLE CreateFileW(const WCHAR *ch, DWORD acc, DWORD, void *, DWORD, DWORD, HANDLE) { FILE *f = fopen(nar(ch).c_str(), (acc & GENERIC_WRITE) ? "wb" : "rb"); if (!f) return INVALID_HANDLE_VALUE; return new T_f{2, f, 0, 0, ""}; }
static inline BOOL ReadFile(HANDLE h, void *b, DWORD n, DWORD *e, void *) { *e = (DWORD)fread(b, 1, n, ((T_f *)h)->f); return 1; }
static inline BOOL WriteFile(HANDLE h, const void *b, DWORD n, DWORD *e, void *) { *e = (DWORD)fwrite(b, 1, n, ((T_f *)h)->f); return 1; }
static inline DWORD GetFileSize(HANDLE h, DWORD *) { FILE *f = ((T_f *)h)->f; long p = ftell(f); fseek(f, 0, SEEK_END); long n = ftell(f); fseek(f, p, SEEK_SET); return (DWORD)n; }
static inline BOOL CloseHandle(HANDLE h) { if (*(int *)h == 1) { delete (T_fil *)h; return 1; } T_f *f = (T_f *)h; if (f->f) fclose(f->f); delete f; return 1; }
static inline BOOL FindNextFileW(HANDLE h, WIN32_FIND_DATAW_ *fd) { T_f *f = (T_f *)h; while (dirent *e = readdir(f->d)) if (!fnmatch(f->motif.c_str(), e->d_name, 0)) { size_t i = 0; for (; e->d_name[i] && i < 259; ++i) fd->cFileName[i] = e->d_name[i]; fd->cFileName[i] = 0; return 1; } return 0; }
static inline HANDLE FindFirstFileW(const WCHAR *m, WIN32_FIND_DATAW_ *fd) { std::string s = nar(m); size_t k = s.rfind('/'); DIR *d = opendir(s.substr(0, k).c_str()); if (!d) return INVALID_HANDLE_VALUE; T_f *f = new T_f{3, 0, 1, d, s.substr(k + 1)}; if (!FindNextFileW(f, fd)) { closedir(d); delete f; return INVALID_HANDLE_VALUE; } return f; }
static inline BOOL FindClose(HANDLE h) { T_f *f = (T_f *)h; closedir(f->d); delete f; return 1; }
static inline DWORD GetCurrentProcessId(void) { return 42; }
static inline DWORD GetTickCount(void) { timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return (DWORD)(t.tv_sec * 1000 + t.tv_nsec / 1000000); }
