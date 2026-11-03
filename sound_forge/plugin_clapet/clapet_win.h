/* Les declarations Windows utilisees par tsc_clapet.cpp (construction sans SDK Windows).
   Le test sous Linux remplace ce fichier par test/clapet_win.h. */
#pragma once
typedef void *HANDLE; typedef void *HMODULE; typedef void *HWND; typedef int BOOL; typedef unsigned long DWORD;
typedef wchar_t WCHAR; typedef long HRESULT; typedef unsigned int UINT32; typedef unsigned char BYTE;
#define WINAPI __stdcall
#define INVALID_HANDLE_VALUE ((HANDLE)(long long)-1)
struct FILETIME_ { DWORD lo, hi; };
struct WIN32_FIND_DATAW_ {
	DWORD dwFileAttributes; FILETIME_ c, a, w; DWORD nFileSizeHigh, nFileSizeLow, r0, r1;
	WCHAR cFileName[260]; WCHAR cAlternateFileName[14];
};
extern "C" {
__declspec(dllimport) HANDLE WINAPI CreateThread(void *, size_t, DWORD (WINAPI *)(void *), void *, DWORD, DWORD *);
__declspec(dllimport) DWORD WINAPI WaitForSingleObject(HANDLE, DWORD);
__declspec(dllimport) BOOL WINAPI CloseHandle(HANDLE);
__declspec(dllimport) void WINAPI Sleep(DWORD);
__declspec(dllimport) HMODULE WINAPI LoadLibraryW(const WCHAR *);
__declspec(dllimport) BOOL WINAPI FreeLibrary(HMODULE);
__declspec(dllimport) void *WINAPI GetProcAddress(HMODULE, const char *);
__declspec(dllimport) HANDLE WINAPI GetProcessHeap(void);
__declspec(dllimport) void *WINAPI HeapAlloc(HANDLE, DWORD, size_t);
__declspec(dllimport) BOOL WINAPI HeapFree(HANDLE, DWORD, void *);
__declspec(dllimport) DWORD WINAPI GetEnvironmentVariableW(const WCHAR *, WCHAR *, DWORD);
__declspec(dllimport) HANDLE WINAPI CreateFileW(const WCHAR *, DWORD, DWORD, void *, DWORD, DWORD, HANDLE);
__declspec(dllimport) BOOL WINAPI ReadFile(HANDLE, void *, DWORD, DWORD *, void *);
__declspec(dllimport) BOOL WINAPI WriteFile(HANDLE, const void *, DWORD, DWORD *, void *);
__declspec(dllimport) DWORD WINAPI GetFileSize(HANDLE, DWORD *);
__declspec(dllimport) HANDLE WINAPI FindFirstFileW(const WCHAR *, WIN32_FIND_DATAW_ *);
__declspec(dllimport) BOOL WINAPI FindNextFileW(HANDLE, WIN32_FIND_DATAW_ *);
__declspec(dllimport) BOOL WINAPI FindClose(HANDLE);
__declspec(dllimport) DWORD WINAPI GetCurrentProcessId(void);
__declspec(dllimport) DWORD WINAPI GetTickCount(void);
}
#define GENERIC_READ 0x80000000u
#define GENERIC_WRITE 0x40000000u
#define FILE_SHARE_READ 1
#define OPEN_EXISTING 3
#define CREATE_ALWAYS 2


