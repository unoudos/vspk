/*
 * vspk.h — GUI nativa para C usando vspk (WebView) como ventana. Single-header, sin dependencias.
 *
 * El programa abre un puente HTTP+SSE en 127.0.0.1 (puerto aleatorio), escribe un .htv temporal y lanza
 * vspk(.exe). Mientras la ventana está abierta, vspk_run() atiende los clics (/cb/<id>), los eventos
 * (/event/<nombre>) y los valores de los campos enlazados, y empuja los cambios de estado por SSE.
 * spork.css y spork.js los sirve el propio vspk (van incrustados).
 *
 *   #include "vspk.h"
 *   static void mas(void *ud) { vspk_inc((VspkState*)ud, 1); }
 *   int main(void) {
 *       VspkApp *app = vspk_app("Contador", 400, 300);
 *       VspkState *n = vspk_state_int(app, "n", 0);
 *       vspk_add(app, vspk_h1(vspk_ref(n)), vspk_button(app, "+", mas, n));
 *       return vspk_run(app);
 *   }
 *
 * Compilar:  Linux/macOS  gcc demo.c -o demo -lpthread
 *            Windows/MinGW gcc demo.c -o demo.exe -lws2_32     (MSVC: cl demo.c, enlaza ws2_32 solo)
 *
 * Qué hay:
 *   · ids de callback y eventos internos con token (otra web local no puede dispararlos)
 *   · vspk_button(app, texto, fn, ud) ejecuta fn en C; vspk_button_js(texto, js) es JS puro en la página
 *   · todos los callbacks (clics, teclas, temporizadores...) se ejecutan serializados (un solo candado):
 *     no hace falta sincronizar el estado propio entre ellos
 *   · vspk_on_key, vspk_on_close, vspk_pick_file/save_file/pick_folder, vspk_run_every/run_after,
 *     vspk_set_title/notify/copy_text/quit/toast/eval
 *   · vspk_canvas(app, id, w, h)  ·  vspk_menubar/menu/menu_item/menu_sep  ·  vspk_window (ventanas extra)
 *
 * Los widgets devuelven `const char*` (HTML) que posee la app: no hay que liberarlos. Las listas de hijos se
 * pasan como argumentos variables: vspk_row(a, b, c). Se usa una app "actual" (la última creada) para los
 * widgets que no reciben `app`.
 */
#ifndef VSPK_H
#define VSPK_H

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdint.h>
#include <time.h>
#include <ctype.h>

#ifdef _WIN32
  #ifndef WIN32_LEAN_AND_MEAN
  #define WIN32_LEAN_AND_MEAN
  #endif
  #include <winsock2.h>
  #include <ws2tcpip.h>
  #include <windows.h>
  #ifdef _MSC_VER
  #pragma comment(lib, "ws2_32.lib")
  #pragma comment(lib, "advapi32.lib")
  #endif
  typedef SOCKET vspk_sock;
  #define VSPK_BADSOCK INVALID_SOCKET
  #define VSPK_MSG_NOSIGNAL 0
  typedef CRITICAL_SECTION vspk_mutex;
  #define VSPK_THREAD_FN(name) static DWORD WINAPI name(LPVOID arg)
  #define VSPK_THREAD_END return 0
  typedef DWORD (WINAPI *vspk_thrfn)(LPVOID);
  BOOLEAN NTAPI SystemFunction036(PVOID, ULONG);   /* RtlGenRandom */
#else
  #include <unistd.h>
  #include <errno.h>
  #include <signal.h>
  #include <fcntl.h>
  #include <pthread.h>
  #include <sys/types.h>
  #include <sys/time.h>
  #include <sys/socket.h>
  #include <sys/wait.h>
  #include <netinet/in.h>
  #include <arpa/inet.h>
  typedef int vspk_sock;
  #define VSPK_BADSOCK (-1)
  #ifdef MSG_NOSIGNAL
  #define VSPK_MSG_NOSIGNAL MSG_NOSIGNAL
  #else
  #define VSPK_MSG_NOSIGNAL 0
  #endif
  typedef pthread_mutex_t vspk_mutex;
  #define VSPK_THREAD_FN(name) static void *name(void *arg)
  #define VSPK_THREAD_END return NULL
  typedef void *(*vspk_thrfn)(void *);
#endif

#if defined(__GNUC__)
#pragma GCC diagnostic ignored "-Wunused-function"
#endif

#ifdef __cplusplus
extern "C" {
#endif

/* ── Tipos públicos ───────────────────────────────────────────────────────── */

typedef struct VspkApp    VspkApp;
typedef struct VspkState  VspkState;
typedef struct VspkCanvas VspkCanvas;
typedef struct VspkWin    VspkWin;

typedef void (*VspkFn)(void *ud);                                          /* clic */
typedef int  (*VspkTimerFn)(void *ud);                                     /* 0 = cancelar el temporizador */
typedef int  (*VspkCloseFn)(void *ud);                                     /* 0 = cancelar el cierre */
typedef void (*VspkKeyFn)(const char *key, const char *json, void *ud);    /* json: {key,code,ctrl,shift,alt,meta} */
typedef void (*VspkPathFn)(const char *path, void *ud);                    /* path == NULL si se cancela */
typedef void (*VspkMouseFn)(const char *type, int x, int y, int button, void *ud);  /* down|up|move|click */
typedef void (*VspkChangeFn)(const char *value, void *ud);
typedef void (*VspkEventFn)(const char *body, void *ud);                   /* /event/<nombre> */

/* ── Utilidades portables ─────────────────────────────────────────────────── */

static void vspk__sleep_ms(int ms) {
#ifdef _WIN32
    Sleep((DWORD)ms);
#else
    struct timespec ts; ts.tv_sec = ms / 1000; ts.tv_nsec = (long)(ms % 1000) * 1000000L; nanosleep(&ts, NULL);
#endif
}
static long long vspk__now_ms(void) {
#ifdef _WIN32
    return (long long)GetTickCount64();
#else
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts); return (long long)ts.tv_sec * 1000 + ts.tv_nsec / 1000000;
#endif
}
static void vspk__mx_init(vspk_mutex *m) {
#ifdef _WIN32
    InitializeCriticalSection(m);
#else
    pthread_mutex_init(m, NULL);
#endif
}
static void vspk__mx_lock(vspk_mutex *m) {
#ifdef _WIN32
    EnterCriticalSection(m);
#else
    pthread_mutex_lock(m);
#endif
}
static void vspk__mx_unlock(vspk_mutex *m) {
#ifdef _WIN32
    LeaveCriticalSection(m);
#else
    pthread_mutex_unlock(m);
#endif
}
static void vspk__sock_close(vspk_sock s) {
#ifdef _WIN32
    closesocket(s);
#else
    close(s);
#endif
}
static void vspk__sock_shutdown(vspk_sock s) {
#ifdef _WIN32
    shutdown(s, SD_BOTH);
#else
    shutdown(s, SHUT_RDWR);
#endif
}
static void vspk__random_hex(char *out, int n) {   /* n caracteres hex + '\0' */
    unsigned char b[32]; int i; int ok = 0;
    if (n / 2 + 1 > (int)sizeof b) n = (int)sizeof b * 2 - 2;
#ifdef _WIN32
    ok = SystemFunction036(b, (ULONG)(n / 2 + 1)) ? 1 : 0;
#else
    { FILE *f = fopen("/dev/urandom", "rb"); if (f) { ok = fread(b, 1, (size_t)(n / 2 + 1), f) == (size_t)(n / 2 + 1); fclose(f); } }
#endif
    if (!ok) { srand((unsigned)(time(NULL) ^ (unsigned)vspk__now_ms())); for (i = 0; i < n / 2 + 1; i++) b[i] = (unsigned char)(rand() & 0xff); }
    for (i = 0; i < n; i++) out[i] = "0123456789abcdef"[(i & 1 ? b[i / 2] & 15 : b[i / 2] >> 4)];
    out[n] = 0;
}

/* ── Buffer dinámico ──────────────────────────────────────────────────────── */

typedef struct { char *p; size_t len, cap; } VspkBuf;

static void vspk__bgrow(VspkBuf *b, size_t add) {
    if (b->len + add + 1 > b->cap) {
        size_t c = b->cap ? b->cap : 256;
        while (c < b->len + add + 1) c *= 2;
        b->p = (char *)realloc(b->p, c); b->cap = c;
    }
}
static void vspk__bcatn(VspkBuf *b, const char *s, size_t n) {
    vspk__bgrow(b, n); memcpy(b->p + b->len, s, n); b->len += n; b->p[b->len] = 0;
}
static void vspk__bcat(VspkBuf *b, const char *s) { if (s) vspk__bcatn(b, s, strlen(s)); }
static void vspk__bc(VspkBuf *b, char c) { vspk__bcatn(b, &c, 1); }
static void vspk__bf(VspkBuf *b, const char *fmt, ...) {
    va_list ap, ap2; int n;
    va_start(ap, fmt); va_copy(ap2, ap);
    n = vsnprintf(NULL, 0, fmt, ap); va_end(ap);
    if (n > 0) { vspk__bgrow(b, (size_t)n); vsnprintf(b->p + b->len, (size_t)n + 1, fmt, ap2); b->len += (size_t)n; }
    va_end(ap2);
}
static const char *vspk__bstr(VspkBuf *b) { return b->p ? b->p : ""; }
static char *vspk__bdetach(VspkBuf *b) { char *r = b->p ? b->p : (char *)calloc(1, 1); b->p = NULL; b->len = b->cap = 0; return r; }
static char *vspk__strdup(const char *s) { size_t n = strlen(s); char *r = (char *)malloc(n + 1); memcpy(r, s, n + 1); return r; }

static void vspk__besc(VspkBuf *b, const char *s) {       /* HTML */
    for (; s && *s; s++) {
        switch (*s) {
            case '&': vspk__bcat(b, "&amp;"); break;
            case '<': vspk__bcat(b, "&lt;"); break;
            case '>': vspk__bcat(b, "&gt;"); break;
            case '"': vspk__bcat(b, "&quot;"); break;
            case '\'': vspk__bcat(b, "&#39;"); break;
            default: vspk__bc(b, *s);
        }
    }
}
static void vspk__bjs(VspkBuf *b, const char *s) {        /* literal de cadena JSON/JS, seguro dentro de <script> */
    vspk__bc(b, '"');
    for (; s && *s; s++) {
        unsigned char c = (unsigned char)*s;
        switch (c) {
            case '"': vspk__bcat(b, "\\\""); break;
            case '\\': vspk__bcat(b, "\\\\"); break;
            case '\n': vspk__bcat(b, "\\n"); break;
            case '\r': vspk__bcat(b, "\\r"); break;
            case '\t': vspk__bcat(b, "\\t"); break;
            case '<': vspk__bcat(b, "\\u003c"); break;
            case '>': vspk__bcat(b, "\\u003e"); break;
            case '&': vspk__bcat(b, "\\u0026"); break;
            default:
                if (c < 0x20) vspk__bf(b, "\\u%04x", c); else vspk__bc(b, (char)c);
        }
    }
    vspk__bc(b, '"');
}
static char *vspk__repl(char *s, const char *find, const char *rep) {   /* consume s */
    VspkBuf b = {0}; size_t fl = strlen(find); char *p = s, *q;
    while ((q = strstr(p, find)) != NULL) { vspk__bcatn(&b, p, (size_t)(q - p)); vspk__bcat(&b, rep); p = q + fl; }
    vspk__bcat(&b, p); free(s);
    return vspk__bdetach(&b);
}
static const char *vspk__ifind(const char *h, const char *n) {          /* strcasestr portable */
    size_t nl = strlen(n); if (!nl) return h;
    for (; *h; h++) { size_t i = 0; while (i < nl && h[i] && tolower((unsigned char)h[i]) == tolower((unsigned char)n[i])) i++; if (i == nl) return h; }
    return NULL;
}

/* ── JSON mínimo (objetos planos que genera la propia página) ─────────────── */

static const char *vspk__jskip(const char *p) { while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++; return p; }
static const char *vspk__jend_str(const char *p) {      /* p apunta a la comilla de apertura; devuelve la posición tras la de cierre */
    p++; while (*p && *p != '"') { if (*p == '\\' && p[1]) p++; p++; }
    return *p ? p + 1 : p;
}
static const char *vspk__jvalue_end(const char *p) {    /* fin de un valor (cualquiera) */
    p = vspk__jskip(p);
    if (*p == '"') return vspk__jend_str(p);
    if (*p == '{' || *p == '[') {
        int d = 0;
        while (*p) {
            if (*p == '"') { p = vspk__jend_str(p); continue; }
            if (*p == '{' || *p == '[') d++;
            if (*p == '}' || *p == ']') { d--; if (d == 0) return p + 1; }
            p++;
        }
        return p;
    }
    while (*p && *p != ',' && *p != '}' && *p != ']' && *p != ' ' && *p != '\n') p++;
    return p;
}
/* Devuelve el inicio del valor de `key` en el objeto json (nivel 1) o NULL. */
static const char *vspk__jfind(const char *json, const char *key) {
    const char *p = json ? vspk__jskip(json) : NULL; size_t kl = strlen(key);
    if (!p || *p != '{') return NULL;
    p++;
    for (;;) {
        const char *ks, *ke;
        p = vspk__jskip(p);
        while (*p == ',') p = vspk__jskip(p + 1);
        if (*p != '"') return NULL;
        ks = p + 1; ke = vspk__jend_str(p);
        p = vspk__jskip(ke);
        if (*p != ':') return NULL;
        p = vspk__jskip(p + 1);
        if ((size_t)(ke - 1 - ks) == kl && strncmp(ks, key, kl) == 0) return p;
        p = vspk__jvalue_end(p);
        if (!*p) return NULL;
    }
}
static void vspk__utf8(VspkBuf *b, unsigned cp) {
    if (cp < 0x80) vspk__bc(b, (char)cp);
    else if (cp < 0x800) { vspk__bc(b, (char)(0xC0 | (cp >> 6))); vspk__bc(b, (char)(0x80 | (cp & 0x3F))); }
    else if (cp < 0x10000) { vspk__bc(b, (char)(0xE0 | (cp >> 12))); vspk__bc(b, (char)(0x80 | ((cp >> 6) & 0x3F))); vspk__bc(b, (char)(0x80 | (cp & 0x3F))); }
    else { vspk__bc(b, (char)(0xF0 | (cp >> 18))); vspk__bc(b, (char)(0x80 | ((cp >> 12) & 0x3F))); vspk__bc(b, (char)(0x80 | ((cp >> 6) & 0x3F))); vspk__bc(b, (char)(0x80 | (cp & 0x3F))); }
}
/* Cadena JSON → malloc'd sin comillas (desescapada). NULL si el valor no es una cadena. */
static char *vspk__junq(const char *v) {
    VspkBuf b = {0};
    if (!v || *v != '"') return NULL;
    for (v++; *v && *v != '"'; v++) {
        if (*v != '\\') { vspk__bc(&b, *v); continue; }
        v++;
        switch (*v) {
            case 'n': vspk__bc(&b, '\n'); break;
            case 'r': vspk__bc(&b, '\r'); break;
            case 't': vspk__bc(&b, '\t'); break;
            case 'b': vspk__bc(&b, '\b'); break;
            case 'f': vspk__bc(&b, '\f'); break;
            case 'u': {
                unsigned cp = 0; int i;
                for (i = 1; i <= 4 && isxdigit((unsigned char)v[i]); i++) cp = cp * 16 + (unsigned)(isdigit((unsigned char)v[i]) ? v[i] - '0' : (tolower((unsigned char)v[i]) - 'a' + 10));
                v += 4;
                if (cp >= 0xD800 && cp < 0xDC00 && v[1] == '\\' && v[2] == 'u') {
                    unsigned lo = 0;
                    for (i = 3; i <= 6 && isxdigit((unsigned char)v[i]); i++) lo = lo * 16 + (unsigned)(isdigit((unsigned char)v[i]) ? v[i] - '0' : (tolower((unsigned char)v[i]) - 'a' + 10));
                    cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00); v += 6;
                }
                vspk__utf8(&b, cp); break;
            }
            case 0: v--; break;
            default: vspk__bc(&b, *v);
        }
    }
    return vspk__bdetach(&b);
}
static char *vspk__jstr(const char *json, const char *key) { return vspk__junq(vspk__jfind(json, key)); }
static double vspk__jnum(const char *json, const char *key, double def) {
    const char *v = vspk__jfind(json, key); return v && *v != '"' ? atof(v) : def;
}

/* ── Estructuras internas ─────────────────────────────────────────────────── */

struct VspkState {
    char name[64]; int kind;                 /* 0 texto, 1 número, 2 booleano */
    char *val;                               /* texto, o número/booleano en formato JSON */
    VspkApp *app; VspkChangeFn onchange; void *onchange_ud;
};
typedef struct { char id[80]; VspkFn fn; void *ud; } VspkCb;
enum { VSPK_EV_VALUE = 1, VSPK_EV_KEY, VSPK_EV_CLOSE, VSPK_EV_WINCLOSE, VSPK_EV_DIALOG, VSPK_EV_MOUSE, VSPK_EV_USER };
typedef struct { char name[120]; int kind; void *fn; void *ud; void *ctx; } VspkEv;
typedef struct { int ms, once, cancelled; long long next; VspkTimerFn fn; void *ud; } VspkTimer;
typedef struct { vspk_sock s; int alive; } VspkClient;
typedef struct {
    int started;
#ifdef _WIN32
    HANDLE h;
#else
    pid_t pid; int done;
#endif
} VspkProc;

struct VspkCanvas { VspkApp *app; char id[64]; int w, h; VspkBuf log; };
struct VspkWin {
    VspkApp *app; char id[16]; char title[128]; int width, height;
    VspkBuf body; VspkProc proc; char htv[600]; int want, close_on; char *close_js;
};

struct VspkApp {
    char title[128]; int width, height, devtools;
    char theme[16], primary[32], bg[32], surface[32], font[64], exe[512];
    char token[20]; int port; vspk_sock lsock;
    VspkBuf root;
    VspkState **states; int nstates;
    VspkCb *cbs; int ncbs; int counter;
    VspkEv *evs; int nevs;
    VspkTimer *timers; int ntimers;
    VspkClient **clients; int nclients;
    VspkCanvas **cvs; int ncvs; VspkBuf cvmouse;
    VspkWin **wins; int nwins;
    char **arena; int narena;
    int key_on, close_on, running, quit, stopping, nthr, htvn;
    VspkProc proc;
    vspk_mutex ulock, slock, alock, tlock;
};

static VspkApp *vspk__cur = NULL;

#define VSPK_MASK_PUSH(arr, n, T, v) do { (arr) = (T *)realloc((arr), sizeof(T) * (size_t)((n) + 1)); (arr)[(n)++] = (v); } while (0)

/* ── Arena de HTML ────────────────────────────────────────────────────────── */

static const char *vspk__keep(char *s) {
    VspkApp *a = vspk__cur;
    vspk__mx_lock(&a->alock);
    VSPK_MASK_PUSH(a->arena, a->narena, char *, s);
    vspk__mx_unlock(&a->alock);
    return s;
}
static const char *vspk__keepb(VspkBuf *b) { return vspk__keep(vspk__bdetach(b)); }

/* ── Procesos ─────────────────────────────────────────────────────────────── */

static int vspk__proc_spawn(VspkProc *p, const char *exe, const char *arg) {
    memset(p, 0, sizeof *p);
#ifdef _WIN32
    {
        STARTUPINFOA si; PROCESS_INFORMATION pi; char cmd[2048];
        memset(&si, 0, sizeof si); si.cb = sizeof si;
        snprintf(cmd, sizeof cmd, "\"%s\" \"%s\"", exe, arg);
        if (!CreateProcessA(NULL, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) return -1;
        CloseHandle(pi.hThread); p->h = pi.hProcess; p->started = 1; return 0;
    }
#else
    {
        pid_t pid = fork();
        if (pid < 0) return -1;
        if (pid == 0) { execlp(exe, exe, arg, (char *)NULL); _exit(127); }
        p->pid = pid; p->started = 1; return 0;
    }
#endif
}
static int vspk__proc_alive(VspkProc *p) {
    if (!p->started) return 0;
#ifdef _WIN32
    return WaitForSingleObject(p->h, 0) == WAIT_TIMEOUT;
#else
    if (p->done) return 0;
    { int st; pid_t r = waitpid(p->pid, &st, WNOHANG); if (r == p->pid || r < 0) { p->done = 1; return 0; } }
    return 1;
#endif
}
static void vspk__proc_kill(VspkProc *p) {
    if (!p->started) return;
#ifdef _WIN32
    if (vspk__proc_alive(p)) TerminateProcess(p->h, 0);
    CloseHandle(p->h); p->started = 0;
#else
    if (vspk__proc_alive(p)) { int st; kill(p->pid, SIGTERM); vspk__sleep_ms(50); if (waitpid(p->pid, &st, WNOHANG) == 0) { kill(p->pid, SIGKILL); waitpid(p->pid, &st, 0); } }
    p->done = 1;
#endif
}

static int vspk__file_exists(const char *p) { FILE *f = fopen(p, "rb"); if (f) { fclose(f); return 1; } return 0; }

static void vspk__find_exe(VspkApp *app, char *out, size_t n) {
    const char *env = getenv("VSPK_EXE");
    if (app->exe[0]) { snprintf(out, n, "%s", app->exe); return; }
    if (env && *env) { snprintf(out, n, "%s", env); return; }
#ifdef _WIN32
    if (vspk__file_exists("vspk.exe")) { snprintf(out, n, "%s", ".\\vspk.exe"); return; }
    if (vspk__file_exists("C:\\spork\\vspk.exe")) { snprintf(out, n, "%s", "C:\\spork\\vspk.exe"); return; }
    if (vspk__file_exists("C:\\spork_studio\\vspk.exe")) { snprintf(out, n, "%s", "C:\\spork_studio\\vspk.exe"); return; }
    snprintf(out, n, "%s", "vspk.exe");
#else
    if (vspk__file_exists("./vspk")) { snprintf(out, n, "%s", "./vspk"); return; }
    snprintf(out, n, "%s", "vspk");
#endif
}

/* ── Estado ───────────────────────────────────────────────────────────────── */

static void vspk__sse(VspkApp *app, const char *event, const char *data_json);

static void vspk__state_json(VspkState *st, VspkBuf *b) {
    if (st->kind == 0) vspk__bjs(b, st->val);
    else vspk__bcat(b, st->val[0] ? st->val : (st->kind == 2 ? "false" : "0"));
}
static void vspk__push_state(VspkState *st, const char *src) {
    VspkApp *app = st->app; VspkBuf b = {0};
    if (!app->running) return;
    vspk__bcat(&b, "{\"name\":"); vspk__bjs(&b, st->name); vspk__bcat(&b, ",\"value\":"); vspk__state_json(st, &b);
    if (src) { vspk__bcat(&b, ",\"src\":"); vspk__bjs(&b, src); }
    vspk__bc(&b, '}'); vspk__sse(app, "state", vspk__bstr(&b)); free(b.p);
}
static void vspk__set_raw(VspkState *st, int kind, const char *text) {
    char *nv = vspk__strdup(text);
    free(st->val); st->val = nv; st->kind = kind;
}
static VspkState *vspk__state_new(VspkApp *app, const char *name, int kind, const char *text) {
    int i; VspkState *st;
    for (i = 0; i < app->nstates; i++) if (strcmp(app->states[i]->name, name) == 0) return app->states[i];
    st = (VspkState *)calloc(1, sizeof *st);
    snprintf(st->name, sizeof st->name, "%s", name); st->app = app; st->kind = kind; st->val = vspk__strdup(text);
    VSPK_MASK_PUSH(app->states, app->nstates, VspkState *, st);
    return st;
}
static char *vspk__numstr(double v) { char t[48]; snprintf(t, sizeof t, "%.15g", v); return vspk__strdup(t); }

static VspkState *vspk_state_str(VspkApp *app, const char *name, const char *init) { return vspk__state_new(app, name, 0, init ? init : ""); }
static VspkState *vspk_state_num(VspkApp *app, const char *name, double init) { char *t = vspk__numstr(init); VspkState *s = vspk__state_new(app, name, 1, t); free(t); return s; }
static VspkState *vspk_state_int(VspkApp *app, const char *name, int init) { return vspk_state_num(app, name, init); }
static VspkState *vspk_state_bool(VspkApp *app, const char *name, int init) { return vspk__state_new(app, name, 2, init ? "true" : "false"); }

static void vspk_set_str(VspkState *st, const char *v)  { vspk__set_raw(st, 0, v ? v : ""); vspk__push_state(st, NULL); }
static void vspk_set_num(VspkState *st, double v)       { char *t = vspk__numstr(v); vspk__set_raw(st, 1, t); free(t); vspk__push_state(st, NULL); }
static void vspk_set_int(VspkState *st, int v)          { vspk_set_num(st, v); }
static void vspk_set_bool(VspkState *st, int v)         { vspk__set_raw(st, 2, v ? "true" : "false"); vspk__push_state(st, NULL); }
static const char *vspk_get_str(VspkState *st)          { return st->val; }
static double vspk_get_num(VspkState *st) {
    if (st->kind == 2) return st->val[0] == 't';
    return atof(st->val);
}
static int vspk_get_int(VspkState *st)                  { return (int)vspk_get_num(st); }
static int vspk_get_bool(VspkState *st) {
    if (st->kind == 2) return st->val[0] == 't';
    if (st->kind == 1) return atof(st->val) != 0;
    return strcmp(st->val, "true") == 0 || strcmp(st->val, "1") == 0;
}
static void vspk_inc(VspkState *st, double by) { vspk_set_num(st, vspk_get_num(st) + by); }
static void vspk_dec(VspkState *st, double by) { vspk_inc(st, -by); }
/* fn(valor) cada vez que el usuario cambia el campo enlazado a este estado */
static void vspk_on_change(VspkState *st, VspkChangeFn fn, void *ud) { st->onchange = fn; st->onchange_ud = ud; }

/* Span reactivo: úsalo como contenido de vspk_h3(...), vspk_p(...), etc. */
static const char *vspk_ref(VspkState *st) {
    VspkBuf b = {0};
    vspk__bcat(&b, "<span data-spork-text=\""); vspk__besc(&b, st->name); vspk__bcat(&b, "\">"); vspk__besc(&b, st->val); vspk__bcat(&b, "</span>");
    return vspk__keepb(&b);
}

/* ── Callbacks y eventos ──────────────────────────────────────────────────── */

static void vspk__evname(VspkApp *app, char *out, size_t n, const char *name) { snprintf(out, n, "__%s_%s", name, app->token); }
static void vspk__postjs(VspkApp *app, VspkBuf *b, const char *name, const char *body_expr) {
    vspk__bf(b, "fetch('http://127.0.0.1:%d/event/%s',{method:'POST',mode:'no-cors',headers:{'Content-Type':'text/plain'},body:%s})", app->port, name, body_expr);
}
static VspkEv *vspk__ev_add(VspkApp *app, const char *name, int kind, void *fn, void *ud, void *ctx) {
    VspkEv e; memset(&e, 0, sizeof e);
    snprintf(e.name, sizeof e.name, "%s", name); e.kind = kind; e.fn = fn; e.ud = ud; e.ctx = ctx;
    VSPK_MASK_PUSH(app->evs, app->nevs, VspkEv, e);
    return &app->evs[app->nevs - 1];
}
/* Registra fn (se ejecuta en C) y devuelve el JS para dispararla desde un onclick. */
static const char *vspk_on_click(VspkApp *app, VspkFn fn, void *ud) {
    VspkCb c; VspkBuf b = {0};
    memset(&c, 0, sizeof c);
    snprintf(c.id, sizeof c.id, "cb_%s_%d", app->token, ++app->counter); c.fn = fn; c.ud = ud;
    VSPK_MASK_PUSH(app->cbs, app->ncbs, VspkCb, c);
    vspk__bf(&b, "fetch('http://127.0.0.1:%d/cb/%s',{mode:'no-cors'})", app->port, c.id);
    return vspk__keepb(&b);
}
/* Handler para eventos enviados desde la página: fetch('http://127.0.0.1:PUERTO/event/nombre', {method:'POST', body: ...}) */
static void vspk_on_event(VspkApp *app, const char *event, VspkEventFn fn, void *ud) { vspk__ev_add(app, event, VSPK_EV_USER, (void *)fn, ud, NULL); }

/* ── SSE ──────────────────────────────────────────────────────────────────── */

static int vspk__send_all(vspk_sock s, const char *d, size_t n) {
    while (n > 0) {
        int r = (int)send(s, d, (int)n, VSPK_MSG_NOSIGNAL);
        if (r <= 0) return -1;
        d += r; n -= (size_t)r;
    }
    return 0;
}
static void vspk__sse(VspkApp *app, const char *event, const char *data_json) {
    VspkBuf b = {0}; int i;
    vspk__bf(&b, "event: %s\ndata: %s\n\n", event, data_json);
    vspk__mx_lock(&app->slock);
    for (i = 0; i < app->nclients; i++) {
        VspkClient *c = app->clients[i];
        if (c->alive && vspk__send_all(c->s, b.p, b.len) != 0) c->alive = 0;
    }
    vspk__mx_unlock(&app->slock);
    free(b.p);
}
/* Ejecuta JS en la ventana principal. */
static void vspk_eval(VspkApp *app, const char *code) {
    VspkBuf b = {0}; vspk__bjs(&b, code); vspk__sse(app, "eval", vspk__bstr(&b)); free(b.p);
}

/* ── Utilidades de ventana ────────────────────────────────────────────────── */

static void vspk_toast(VspkApp *app, const char *msg, const char *variant, int ms) {
    VspkBuf b = {0};
    vspk__bcat(&b, "window.__toast("); vspk__bjs(&b, msg); vspk__bc(&b, ','); vspk__bjs(&b, variant ? variant : ""); vspk__bf(&b, ",%d)", ms > 0 ? ms : 3000);
    vspk_eval(app, vspk__bstr(&b)); free(b.p);
}
static void vspk_set_title(VspkApp *app, const char *t) {
    VspkBuf b = {0}; vspk__bcat(&b, "__vspk.setTitle("); vspk__bjs(&b, t); vspk__bc(&b, ')');
    vspk_eval(app, vspk__bstr(&b)); free(b.p);
}
static void vspk_notify(VspkApp *app, const char *title, const char *body) {
    VspkBuf b = {0}; vspk__bcat(&b, "__vspk.notify("); vspk__bjs(&b, title); vspk__bc(&b, ','); vspk__bjs(&b, body ? body : ""); vspk__bc(&b, ')');
    vspk_eval(app, vspk__bstr(&b)); free(b.p);
}
static void vspk_copy_text(VspkApp *app, const char *text) {
    VspkBuf b = {0}; vspk__bcat(&b, "__vspk.clipboard.write("); vspk__bjs(&b, text); vspk__bc(&b, ')');
    vspk_eval(app, vspk__bstr(&b)); free(b.p);
}
static void vspk_quit(VspkApp *app) { app->quit = 1; vspk__proc_kill(&app->proc); }

/* fn recibe la tecla y el JSON {key, code, ctrl, shift, alt, meta}. Llamar antes de vspk_run(). */
static void vspk_on_key(VspkApp *app, VspkKeyFn fn, void *ud) {
    char n[64]; vspk__evname(app, n, sizeof n, "k"); app->key_on = 1; vspk__ev_add(app, n, VSPK_EV_KEY, (void *)fn, ud, NULL);
}
/* fn devuelve 0 para cancelar el cierre de la ventana. Llamar antes de vspk_run(). */
static void vspk_on_close(VspkApp *app, VspkCloseFn fn, void *ud) {
    char n[64]; vspk__evname(app, n, sizeof n, "c"); app->close_on = 1; vspk__ev_add(app, n, VSPK_EV_CLOSE, (void *)fn, ud, NULL);
}
static void vspk__dialog(VspkApp *app, const char *kind, const char *title, VspkPathFn fn, void *ud) {
    char nm[64], tag[24]; VspkBuf b = {0}, body = {0};
    snprintf(tag, sizeof tag, "d%d", ++app->counter); vspk__evname(app, nm, sizeof nm, tag);
    vspk__ev_add(app, nm, VSPK_EV_DIALOG, (void *)fn, ud, NULL);
    vspk__bcat(&b, "__vspk.dialog({kind:"); vspk__bjs(&b, kind); vspk__bcat(&b, ",title:"); vspk__bjs(&b, title); vspk__bcat(&b, "}).then(function(p){");
    vspk__postjs(app, &body, nm, "JSON.stringify({path:p})"); vspk__bcat(&b, vspk__bstr(&body)); vspk__bcat(&b, "})");
    vspk_eval(app, vspk__bstr(&b)); free(b.p); free(body.p);
}
static void vspk_pick_file(VspkApp *app, const char *title, VspkPathFn fn, void *ud)   { vspk__dialog(app, "open", title, fn, ud); }
static void vspk_save_file(VspkApp *app, const char *title, VspkPathFn fn, void *ud)   { vspk__dialog(app, "save", title, fn, ud); }
static void vspk_pick_folder(VspkApp *app, const char *title, VspkPathFn fn, void *ud) { vspk__dialog(app, "folder", title, fn, ud); }

/* Temporizadores (activos mientras vspk_run() esté en marcha). fn devuelve 0 para cancelar. */
static void vspk__timer_add(VspkApp *app, int ms, int once, VspkTimerFn fn, void *ud) {
    VspkTimer t; memset(&t, 0, sizeof t); t.ms = ms; t.once = once; t.fn = fn; t.ud = ud;
    t.next = app->running ? vspk__now_ms() + ms : -1;
    VSPK_MASK_PUSH(app->timers, app->ntimers, VspkTimer, t);
}
static void vspk_run_after(VspkApp *app, int ms, VspkTimerFn fn, void *ud) { vspk__timer_add(app, ms, 1, fn, ud); }
static void vspk_run_every(VspkApp *app, int ms, VspkTimerFn fn, void *ud) { vspk__timer_add(app, ms, 0, fn, ud); }

/* ── Diálogos modales (mensaje / confirmación / pedir texto) ──────────────── */

typedef void (*VspkConfirmFn)(int ok, void *ud);
typedef struct { int kind; void *fn; void *ud; } VspkTramp;   /* 1 mensaje, 2 confirmar, 3 pedir texto */
static void vspk__tramp(const char *body, void *ud) {
    VspkTramp *t = (VspkTramp *)ud;
    if (t->kind == 1) { if (t->fn) ((VspkFn)t->fn)(t->ud); }
    else if (t->kind == 2) { const char *v = vspk__jfind(body, "v"); ((VspkConfirmFn)t->fn)(v && strncmp(v, "true", 4) == 0, t->ud); }
    else if (t->kind == 3) { char *v = vspk__jstr(body, "v"); ((VspkPathFn)t->fn)(v, t->ud); free(v); }
}
static void vspk__modal(VspkApp *app, const char *call, int kind, void *fn, void *ud) {
    char nm[64], tag[24]; VspkBuf b = {0}, body = {0}; VspkTramp *t = (VspkTramp *)calloc(1, sizeof *t);
    t->kind = kind; t->fn = fn; t->ud = ud;
    snprintf(tag, sizeof tag, "m%d", ++app->counter); vspk__evname(app, nm, sizeof nm, tag);
    vspk__ev_add(app, nm, VSPK_EV_USER, (void *)vspk__tramp, t, NULL);
    vspk__bf(&b, "Promise.resolve(%s).then(function(v){", call);
    vspk__postjs(app, &body, nm, "JSON.stringify({v:v})"); vspk__bcat(&b, vspk__bstr(&body)); vspk__bcat(&b, "})");
    vspk_eval(app, vspk__bstr(&b)); free(b.p); free(body.p);
}
/* Diálogo modal con un botón Aceptar. fn (puede ser NULL) se llama al cerrarlo. */
static void vspk_message(VspkApp *app, const char *text, VspkFn fn, void *ud) {
    VspkBuf c = {0}; vspk__bcat(&c, "alert("); vspk__bjs(&c, text); vspk__bc(&c, ')');
    vspk__modal(app, vspk__bstr(&c), 1, (void *)fn, ud); free(c.p);
}
/* Modal Aceptar/Cancelar: fn(ok, ud) con ok = 1 o 0. */
static void vspk_confirm(VspkApp *app, const char *text, VspkConfirmFn fn, void *ud) {
    VspkBuf c = {0}; vspk__bcat(&c, "confirm("); vspk__bjs(&c, text); vspk__bc(&c, ')');
    vspk__modal(app, vspk__bstr(&c), 2, (void *)fn, ud); free(c.p);
}
/* Modal que pide un texto: fn(texto, ud), con texto == NULL si se cancela. */
static void vspk_prompt(VspkApp *app, const char *text, const char *def, VspkPathFn fn, void *ud) {
    VspkBuf c = {0}; vspk__bcat(&c, "prompt("); vspk__bjs(&c, text); vspk__bc(&c, ','); vspk__bjs(&c, def ? def : ""); vspk__bc(&c, ')');
    vspk__modal(app, vspk__bstr(&c), 3, (void *)fn, ud); free(c.p);
}

/* ── Tabla, árbol, lista (se hidratan en la página; ver vspk_ui.js incrustado en vspk.exe) ──
 *
 *   const char *cols[]  = {"Nombre", "Edad", NULL};
 *   const char *cells[] = {"Ana", "31", "Luis", "28", NULL};      (por filas; nº de celdas múltiplo de las columnas)
 *   vspk_add(app, vspk_table(app, "tabla", cols, cells, 0, NULL, on_select, NULL, NULL, NULL), NULL);
 *
 * Los callbacks reciben el JSON del evento: Table → {index,row:[..],indexes:[..],rows:[[..]]}, sort → {col,dir},
 * Tree → {path:[..],label,id}. Para leerlo: vspk_json_str / vspk_json_num / vspk_json_item.
 */
enum { VSPK_T_NOSORT = 1, VSPK_T_MULTI = 2, VSPK_T_NOHEADER = 4, VSPK_T_NOSTRIPE = 8 };

/* Texto del campo `key` (malloc: libéralo con free) o NULL. */
static char *vspk_json_str(const char *json, const char *key) { return vspk__jstr(json, key); }
static double vspk_json_num(const char *json, const char *key, double def) { return vspk__jnum(json, key, def); }
/* Elemento i del array `key` como texto (malloc) o NULL: vspk_json_item(json, "row", 0) → "Ana". */
static char *vspk_json_item(const char *json, const char *key, int i) {
    const char *p = vspk__jfind(json, key); char *r = NULL;
    if (!p || *p != '[') return NULL;
    p = vspk__jskip(p + 1);
    for (; *p && *p != ']'; ) {
        const char *e = vspk__jvalue_end(p);
        if (i-- == 0) {
            if (*p == '"') r = vspk__junq(p);
            else { r = (char *)malloc((size_t)(e - p) + 1); memcpy(r, p, (size_t)(e - p)); r[e - p] = 0; }
            return r;
        }
        p = vspk__jskip(e); if (*p == ',') p = vspk__jskip(p + 1);
    }
    return NULL;
}

static void vspk__vt_event(VspkApp *app, VspkBuf *attrs, const char *attr, VspkEventFn fn, void *ud) {
    char nm[64], tag[24]; VspkBuf body = {0};
    if (!fn) return;
    snprintf(tag, sizeof tag, "v%d", ++app->counter); vspk__evname(app, nm, sizeof nm, tag);
    vspk__ev_add(app, nm, VSPK_EV_USER, (void *)fn, ud, NULL);
    vspk__postjs(app, &body, nm, "JSON.stringify(p)");
    vspk__bf(attrs, " %s=\"", attr); vspk__besc(attrs, vspk__bstr(&body)); vspk__bc(attrs, '"'); free(body.p);
}
static int vspk__vt_count(const char **a) { int n = 0; while (a && a[n]) n++; return n; }
static void vspk__vt_rows(VspkBuf *b, const char **cells, int ncols) {
    int n = vspk__vt_count(cells), i; vspk__bc(b, '[');
    for (i = 0; i < n; i++) {
        if (ncols > 0 && i % ncols == 0) { if (i) vspk__bcat(b, "],"); vspk__bc(b, '['); }
        else if (i) vspk__bc(b, ',');
        vspk__bjs(b, cells[i]);
    }
    if (n) vspk__bc(b, ']');
    vspk__bc(b, ']');
}
static const char *vspk__vt_html(VspkApp *app, const char *cls, const char *prefix, const char *id, VspkBuf *cfg, VspkBuf *attrs, const char *style) {
    VspkBuf b = {0}; char gen[40];
    if (!id || !*id) { snprintf(gen, sizeof gen, "%s%d", prefix, ++app->counter); id = gen; }
    vspk__bf(&b, "<div id=\""); vspk__besc(&b, id); vspk__bf(&b, "\" class=\"%s\" data-vt=\"", cls); vspk__besc(&b, vspk__bstr(cfg)); vspk__bc(&b, '"');
    if (style && *style) { vspk__bcat(&b, " style=\""); vspk__besc(&b, style); vspk__bc(&b, '"'); }
    vspk__bcat(&b, vspk__bstr(attrs)); vspk__bcat(&b, "></div>");
    free(cfg->p); free(attrs->p);
    return vspk__keepb(&b);
}
/* Tabla con orden por columna (clic en la cabecera) y selección. id puede ser NULL (pero hace falta para vspk_table_set).
 * cols y cells terminan en NULL. opts: VSPK_T_*. height: "240px" (scroll) o NULL. Los tres callbacks pueden ser NULL. */
static const char *vspk_table(VspkApp *app, const char *id, const char **cols, const char **cells, int opts, const char *height,
                              VspkEventFn on_select, VspkEventFn on_dblclick, VspkEventFn on_sort, void *ud) {
    VspkBuf cfg = {0}, at = {0}; int i, nc = vspk__vt_count(cols);
    vspk__bcat(&cfg, "{\"cols\":[");
    for (i = 0; i < nc; i++) { if (i) vspk__bc(&cfg, ','); vspk__bjs(&cfg, cols[i]); }
    vspk__bcat(&cfg, "],\"rows\":"); vspk__vt_rows(&cfg, cells, nc);
    vspk__bf(&cfg, ",\"sortable\":%s,\"multi\":%s,\"striped\":%s,\"header\":%s,\"selected\":-1",
             (opts & VSPK_T_NOSORT) ? "false" : "true", (opts & VSPK_T_MULTI) ? "true" : "false",
             (opts & VSPK_T_NOSTRIPE) ? "false" : "true", (opts & VSPK_T_NOHEADER) ? "false" : "true");
    if (height && *height) { vspk__bcat(&cfg, ",\"height\":"); vspk__bjs(&cfg, height); }
    vspk__bc(&cfg, '}');
    vspk__vt_event(app, &at, "data-on-select", on_select, ud);
    vspk__vt_event(app, &at, "data-on-dblclick", on_dblclick, ud);
    vspk__vt_event(app, &at, "data-on-sort", on_sort, ud);
    return vspk__vt_html(app, "vspk-table", "vt", id, &cfg, &at, NULL);
}
/* Lista de una columna sin cabecera (items termina en NULL). on_select: item = vspk_json_item(json, "row", 0). */
static const char *vspk_listbox(VspkApp *app, const char *id, const char **items, const char *height,
                                VspkEventFn on_select, VspkEventFn on_dblclick, void *ud) {
    VspkBuf cfg = {0}, at = {0}; int i, n = vspk__vt_count(items);
    vspk__bcat(&cfg, "{\"cols\":[\"\"],\"rows\":[");
    for (i = 0; i < n; i++) { if (i) vspk__bc(&cfg, ','); vspk__bc(&cfg, '['); vspk__bjs(&cfg, items[i]); vspk__bc(&cfg, ']'); }
    vspk__bcat(&cfg, "],\"sortable\":false,\"multi\":false,\"striped\":false,\"header\":false,\"selected\":-1");
    if (height && *height) { vspk__bcat(&cfg, ",\"height\":"); vspk__bjs(&cfg, height); }
    vspk__bc(&cfg, '}');
    vspk__vt_event(app, &at, "data-on-select", on_select, ud);
    vspk__vt_event(app, &at, "data-on-dblclick", on_dblclick, ud);
    return vspk__vt_html(app, "vspk-table", "vt", id, &cfg, &at, NULL);
}
/* Árbol. nodes_json: [{"label":"src","open":true,"children":[{"label":"main.rs","id":7}]}, {"label":"README"}] */
static const char *vspk_tree(VspkApp *app, const char *id, const char *nodes_json, const char *height,
                             VspkEventFn on_select, VspkEventFn on_dblclick, void *ud) {
    VspkBuf cfg = {0}, at = {0}, st = {0};
    vspk__bf(&cfg, "{\"nodes\":%s}", nodes_json);
    vspk__vt_event(app, &at, "data-on-select", on_select, ud);
    vspk__vt_event(app, &at, "data-on-dblclick", on_dblclick, ud);
    if (height && *height) { vspk__bcat(&st, "max-height:"); vspk__bcat(&st, height); }
    { const char *r = vspk__vt_html(app, "vspk-tree", "vtree", id, &cfg, &at, st.p ? vspk__bstr(&st) : NULL); free(st.p); return r; }
}
/* JS para cambiar las filas de una tabla: vspk_eval(app, js)  /  vspk_win_eval(ventana, js). */
static const char *vspk_table_set_js(const char *id, const char **cells, int ncols) {
    VspkBuf b = {0}; vspk__bcat(&b, "window.__vspk_table_set("); vspk__bjs(&b, id); vspk__bcat(&b, ",null,");
    vspk__vt_rows(&b, cells, ncols); vspk__bc(&b, ')'); return vspk__keepb(&b);
}
static void vspk_table_set(VspkApp *app, const char *id, const char **cells, int ncols) { vspk_eval(app, vspk_table_set_js(id, cells, ncols)); }
static void vspk_table_select(VspkApp *app, const char *id, int index) {
    VspkBuf b = {0}; vspk__bcat(&b, "window.__vspk_table_select("); vspk__bjs(&b, id); vspk__bf(&b, ",%d)", index); vspk_eval(app, vspk__bstr(&b)); free(b.p);
}
static void vspk_table_sort(VspkApp *app, const char *id, int col, int desc) {
    VspkBuf b = {0}; vspk__bcat(&b, "window.__vspk_table_sort("); vspk__bjs(&b, id); vspk__bf(&b, ",%d,%d)", col, desc ? -1 : 1); vspk_eval(app, vspk__bstr(&b)); free(b.p);
}
static void vspk_tree_set(VspkApp *app, const char *id, const char *nodes_json) {
    VspkBuf b = {0}; vspk__bcat(&b, "window.__vspk_tree_set("); vspk__bjs(&b, id); vspk__bf(&b, ",%s)", nodes_json); vspk_eval(app, vspk__bstr(&b)); free(b.p);
}

/* ── Widgets ──────────────────────────────────────────────────────────────── */

static const char *vspk__group(const char *tag, const char *cls, const char **kids) {
    VspkBuf b = {0}; int i;
    vspk__bf(&b, "<%s class=\"%s\">\n", tag, cls);
    for (i = 0; kids[i]; i++) { vspk__bcat(&b, kids[i]); vspk__bc(&b, '\n'); }
    vspk__bf(&b, "</%s>", tag);
    return vspk__keepb(&b);
}
static const char *vspk__text(const char *tag, const char *cls, const char *html) {
    VspkBuf b = {0};
    vspk__bf(&b, "<%s class=\"%s\">\n%s\n</%s>", tag, cls, html ? html : "", tag);
    return vspk__keepb(&b);
}
#define vspk_row(...)  vspk__group("div", "sz-row", (const char *[]){__VA_ARGS__, NULL})
#define vspk_col(...)  vspk__group("div", "sz-col sz-center", (const char *[]){__VA_ARGS__, NULL})
#define vspk_card(...) vspk__group("div", "sz-card", (const char *[]){__VA_ARGS__, NULL})
#define vspk_grid(...) vspk__group("div", "sz-grid", (const char *[]){__VA_ARGS__, NULL})
#define vspk_nav(...)  vspk__group("nav", "sz-nav", (const char *[]){__VA_ARGS__, NULL})
static const char *vspk_hr(void)     { return vspk__keep(vspk__strdup("<hr class=\"sz-divider\">")); }
static const char *vspk_spacer(void) { return vspk__keep(vspk__strdup("<div class=\"sz-grow\"></div>")); }

static const char *vspk_h1(const char *t)    { return vspk__text("h1", "sz-h1", t); }
static const char *vspk_h2(const char *t)    { return vspk__text("h2", "sz-h2", t); }
static const char *vspk_h3(const char *t)    { return vspk__text("h3", "sz-h3", t); }
static const char *vspk_h4(const char *t)    { return vspk__text("h4", "sz-h4", t); }
static const char *vspk_p(const char *t)     { return vspk__text("p", "sz-p", t); }
static const char *vspk_label(const char *t) { return vspk__text("label", "sz-label", t); }
static const char *vspk_badge(const char *t) { return vspk__text("span", "sz-badge", t); }
static const char *vspk_chip(const char *t, int primary) { return vspk__text("span", primary ? "sz-chip sz-chip-primary" : "sz-chip", t); }
static const char *vspk_alert(const char *t, const char *variant) {
    VspkBuf c = {0}; const char *r;
    vspk__bcat(&c, "sz-alert"); if (variant && *variant) { vspk__bcat(&c, " sz-alert-"); vspk__bcat(&c, variant); }
    r = vspk__text("div", vspk__bstr(&c), t); free(c.p); return r;
}
/* HTML propio tal cual */
static const char *vspk_raw(const char *html) { return vspk__keep(vspk__strdup(html)); }
/* Texto literal (se escapa) para meterlo dentro de h1..p */
static const char *vspk_text(const char *s) { VspkBuf b = {0}; vspk__besc(&b, s); return vspk__keepb(&b); }

static const char *vspk__button(const char *label, const char *variant, const char *onclick) {
    VspkBuf b = {0};
    vspk__bf(&b, "<button class=\"sz-btn sz-btn-%s\" ", variant && *variant ? variant : "filled");
    if (onclick) { vspk__bcat(&b, "onclick=\""); vspk__besc(&b, onclick); vspk__bcat(&b, "\" "); }
    vspk__bcat(&b, "data-ripple=\"\">"); vspk__bcat(&b, label); vspk__bcat(&b, "</button>");
    return vspk__keepb(&b);
}
/* Botón cuyo clic ejecuta fn(ud) en C. variant: "filled", "outlined", "text"... */
static const char *vspk_button_v(VspkApp *app, const char *label, const char *variant, VspkFn fn, void *ud) { return vspk__button(label, variant, vspk_on_click(app, fn, ud)); }
static const char *vspk_button(VspkApp *app, const char *label, VspkFn fn, void *ud) { return vspk_button_v(app, label, "filled", fn, ud); }
/* Botón con JS puro en la página (instantáneo, sin pasar por C). */
static const char *vspk_button_js(const char *label, const char *variant, const char *js) { return vspk__button(label, variant, js); }

static void vspk__bind(VspkBuf *b, VspkState *st) { if (st) { vspk__bcat(b, " data-spork-bind=\""); vspk__besc(b, st->name); vspk__bc(b, '"'); } }
static const char *vspk_input(VspkState *bind, const char *placeholder) {
    VspkBuf b = {0};
    vspk__bcat(&b, "<input class=\"sz-input\"");
    if (placeholder && *placeholder) { vspk__bcat(&b, " placeholder=\""); vspk__besc(&b, placeholder); vspk__bc(&b, '"'); }
    if (bind && bind->val[0]) { vspk__bcat(&b, " value=\""); vspk__besc(&b, bind->val); vspk__bc(&b, '"'); }
    vspk__bind(&b, bind); vspk__bc(&b, '>');
    return vspk__keepb(&b);
}
static const char *vspk__input_type(VspkState *bind, const char *type) {
    VspkBuf b = {0}; vspk__bf(&b, "<input class=\"sz-input\" type=\"%s\"", type); vspk__bind(&b, bind); vspk__bc(&b, '>'); return vspk__keepb(&b);
}
/* Selectores nativos de color y de fecha (o fecha y hora con with_time) enlazados a un estado. */
static const char *vspk_color_picker(VspkState *bind) { return vspk__input_type(bind, "color"); }
static const char *vspk_date_picker(VspkState *bind, int with_time) { return vspk__input_type(bind, with_time ? "datetime-local" : "date"); }
static const char *vspk_textarea(VspkState *bind, const char *placeholder, int rows) {
    VspkBuf b = {0};
    vspk__bcat(&b, "<textarea class=\"sz-textarea\"");
    if (placeholder && *placeholder) { vspk__bcat(&b, " placeholder=\""); vspk__besc(&b, placeholder); vspk__bc(&b, '"'); }
    vspk__bf(&b, " rows=\"%d\"", rows > 0 ? rows : 4); vspk__bind(&b, bind); vspk__bc(&b, '>');
    if (bind) vspk__besc(&b, bind->val);
    vspk__bcat(&b, "</textarea>");
    return vspk__keepb(&b);
}
static const char *vspk_slider(VspkState *bind, double min, double max, double step) {
    VspkBuf b = {0};
    vspk__bf(&b, "<input class=\"sz-slider\" type=\"range\" min=\"%g\" max=\"%g\" step=\"%g\" value=\"", min, max, step);
    if (bind) vspk__besc(&b, bind->val); else vspk__bf(&b, "%g", min);
    vspk__bc(&b, '"'); vspk__bind(&b, bind); vspk__bc(&b, '>');
    return vspk__keepb(&b);
}
/* opciones: pares {valor, etiqueta, valor, etiqueta, ..., NULL} */
static const char *vspk__select(VspkState *bind, const char **opts) {
    VspkBuf b = {0}; int i;
    vspk__bcat(&b, "<select class=\"sz-select\""); vspk__bind(&b, bind); vspk__bc(&b, '>');
    for (i = 0; opts[i] && opts[i + 1]; i += 2) {
        vspk__bcat(&b, "<option value=\""); vspk__besc(&b, opts[i]); vspk__bc(&b, '"');
        if (bind && strcmp(bind->val, opts[i]) == 0) vspk__bcat(&b, " selected");
        vspk__bc(&b, '>'); vspk__besc(&b, opts[i + 1]); vspk__bcat(&b, "</option>");
    }
    vspk__bcat(&b, "</select>");
    return vspk__keepb(&b);
}
#define vspk_select(bind, ...) vspk__select((bind), (const char *[]){__VA_ARGS__, NULL})
/* Interruptor (sz-switch) enlazado a un estado booleano */
static const char *vspk_checkbox(const char *label, VspkState *bind) {
    VspkBuf b = {0};
    vspk__bcat(&b, "<label class=\"sz-switch\"><input type=\"checkbox\"");
    if (bind && vspk_get_bool(bind)) vspk__bcat(&b, " checked");
    vspk__bind(&b, bind);
    vspk__bcat(&b, "><span class=\"sz-switch-track\"><span class=\"sz-switch-thumb\"></span></span><span class=\"sz-switch-label\">");
    vspk__besc(&b, label); vspk__bcat(&b, "</span></label>");
    return vspk__keepb(&b);
}
static const char *vspk_img(const char *src, const char *alt) {
    VspkBuf b = {0};
    vspk__bcat(&b, "<img class=\"sz-img\" src=\""); vspk__besc(&b, src); vspk__bcat(&b, "\" alt=\""); vspk__besc(&b, alt ? alt : ""); vspk__bcat(&b, "\">");
    return vspk__keepb(&b);
}
/* Barra de progreso que se mueve sola cuando cambia el estado (valor / max). */
static const char *vspk_progress(VspkState *st, double max) {
    VspkBuf b = {0}, sty = {0}; double pct;
    if (max <= 0) max = 100;
    pct = vspk_get_num(st) / max * 100; if (pct < 0) pct = 0; if (pct > 100) pct = 100;
    vspk__bcat(&sty, "{\"width\":(Math.min(100,Math.max(0,(+window.__state[");
    vspk__bjs(&sty, st->name); vspk__bf(&sty, "]||0)/%g*100)).toFixed(1)+\"%%\")}", max);
    vspk__bf(&b, "<div class=\"sz-progress\"><div class=\"sz-progress-bar\" style=\"width:%.1f%%\" data-spork-style=\"", pct);
    vspk__besc(&b, vspk__bstr(&sty)); vspk__bcat(&b, "\"></div></div>");
    free(sty.p);
    return vspk__keepb(&b);
}

/* ── Canvas ───────────────────────────────────────────────────────────────── */
/*   VspkCanvas *cv = vspk_canvas(app, "lienzo", 400, 300);
 *   vspk_cv_color(cv, "#6750A4"); vspk_cv_rect(cv, 10, 10, 100, 60); vspk_cv_circle(cv, 200, 60, 40);
 *   vspk_cv_text(cv, 10, 280, "hola"); vspk_cv_erase(cv); vspk_cv_on_mouse(app, cv, fn, ud);
 *   vspk_add(app, vspk_canvas_html(cv));                                                         */

static VspkCanvas *vspk_canvas(VspkApp *app, const char *id, int w, int h) {
    VspkCanvas *c = (VspkCanvas *)calloc(1, sizeof *c);
    c->app = app; snprintf(c->id, sizeof c->id, "%s", id); c->w = w; c->h = h;
    VSPK_MASK_PUSH(app->cvs, app->ncvs, VspkCanvas *, c);
    return c;
}
static const char *vspk_canvas_html(VspkCanvas *c) {
    VspkBuf b = {0};
    vspk__bcat(&b, "<canvas id=\""); vspk__besc(&b, c->id);
    vspk__bf(&b, "\" width=\"%d\" height=\"%d\" style=\"width:%dpx;max-width:100%%;height:auto;border:1px solid rgba(128,128,128,.4);border-radius:8px;touch-action:none\"></canvas>", c->w, c->h, c->w);
    return vspk__keepb(&b);
}
static void vspk__cv(VspkCanvas *c, const char *op, const char *args_json) {
    VspkBuf code = {0};
    vspk__bcat(&code, "__cv("); vspk__bjs(&code, c->id); vspk__bc(&code, ','); vspk__bjs(&code, op); vspk__bc(&code, ','); vspk__bcat(&code, args_json); vspk__bc(&code, ')');
    if (strcmp(op, "clear") == 0) { free(c->log.p); memset(&c->log, 0, sizeof c->log); }
    vspk__bcat(&c->log, vspk__bstr(&code)); vspk__bc(&c->log, ';');
    if (c->app->running) { VspkBuf j = {0}; vspk__bjs(&j, vspk__bstr(&code)); vspk__sse(c->app, "all", vspk__bstr(&j)); free(j.p); }
    free(code.p);
}
static void vspk__cvn(VspkCanvas *c, const char *op, int n, const double *v) {
    VspkBuf a = {0}; int i;
    vspk__bc(&a, '[');
    for (i = 0; i < n; i++) vspk__bf(&a, "%s%.15g", i ? "," : "", v[i]);
    vspk__bc(&a, ']'); vspk__cv(c, op, vspk__bstr(&a)); free(a.p);
}
static void vspk_cv_color(VspkCanvas *c, const char *color) { VspkBuf a = {0}; vspk__bc(&a, '['); vspk__bjs(&a, color); vspk__bc(&a, ']'); vspk__cv(c, "color", vspk__bstr(&a)); free(a.p); }
static void vspk_cv_line_width(VspkCanvas *c, double w) { vspk__cvn(c, "lw", 1, &w); }
static void vspk_cv_font(VspkCanvas *c, double size)    { vspk__cvn(c, "font", 1, &size); }
static void vspk_cv_line(VspkCanvas *c, double x1, double y1, double x2, double y2)  { double v[4]; v[0]=x1; v[1]=y1; v[2]=x2; v[3]=y2; vspk__cvn(c, "line", 4, v); }
static void vspk_cv_rect(VspkCanvas *c, double x, double y, double w, double h)      { double v[4]; v[0]=x; v[1]=y; v[2]=w; v[3]=h; vspk__cvn(c, "rect", 4, v); }
static void vspk_cv_frame(VspkCanvas *c, double x, double y, double w, double h)     { double v[4]; v[0]=x; v[1]=y; v[2]=w; v[3]=h; vspk__cvn(c, "frame", 4, v); }
static void vspk_cv_circle(VspkCanvas *c, double x, double y, double r)              { double v[3]; v[0]=x; v[1]=y; v[2]=r; vspk__cvn(c, "circle", 3, v); }
static void vspk_cv_ring(VspkCanvas *c, double x, double y, double r)                { double v[3]; v[0]=x; v[1]=y; v[2]=r; vspk__cvn(c, "ring", 3, v); }
static void vspk_cv_text(VspkCanvas *c, double x, double y, const char *s) {
    VspkBuf a = {0}; vspk__bf(&a, "[%.15g,%.15g,", x, y); vspk__bjs(&a, s); vspk__bc(&a, ']'); vspk__cv(c, "text", vspk__bstr(&a)); free(a.p);
}
/* xy: x0,y0,x1,y1,... (n puntos) */
static void vspk_cv_poly(VspkCanvas *c, const double *xy, int n) {
    VspkBuf a = {0}; int i; vspk__bcat(&a, "[[");
    for (i = 0; i < n; i++) vspk__bf(&a, "%s[%.15g,%.15g]", i ? "," : "", xy[2 * i], xy[2 * i + 1]);
    vspk__bcat(&a, "]]"); vspk__cv(c, "poly", vspk__bstr(&a)); free(a.p);
}
static void vspk_cv_erase(VspkCanvas *c) { vspk__cv(c, "clear", "[]"); }
/* JS crudo con (ctx, canvas) en el ámbito */
static void vspk_cv_draw(VspkCanvas *c, const char *code) { VspkBuf a = {0}; vspk__bc(&a, '['); vspk__bjs(&a, code); vspk__bc(&a, ']'); vspk__cv(c, "draw", vspk__bstr(&a)); free(a.p); }
static void vspk_cv_on_mouse(VspkApp *app, VspkCanvas *c, VspkMouseFn fn, void *ud) {
    char nm[64], tag[24]; VspkBuf post = {0}, code = {0};
    snprintf(tag, sizeof tag, "m%d", ++app->counter); vspk__evname(app, nm, sizeof nm, tag);
    vspk__ev_add(app, nm, VSPK_EV_MOUSE, (void *)fn, ud, NULL);
    vspk__postjs(app, &post, nm, "JSON.stringify({type:t,x:Math.round((e.clientX-r.left)*c.width/r.width),y:Math.round((e.clientY-r.top)*c.height/r.height),button:e.button})");
    vspk__bcat(&code, "(function(){var c=document.getElementById("); vspk__bjs(&code, c->id);
    vspk__bcat(&code, ");if(!c)return;function p(t,e){if(t==='move'){var n=Date.now();if(n-(c.__lm||0)<30)return;c.__lm=n;}var r=c.getBoundingClientRect();");
    vspk__bcat(&code, vspk__bstr(&post));
    vspk__bcat(&code, "}['down','up','move','click'].forEach(function(t){c.addEventListener(t==='down'?'mousedown':t==='up'?'mouseup':t==='move'?'mousemove':'click',function(e){p(t,e)})})})();");
    vspk__bcat(&app->cvmouse, vspk__bstr(&code));
    if (app->running) { VspkBuf j = {0}; vspk__bjs(&j, vspk__bstr(&code)); vspk__sse(app, "all", vspk__bstr(&j)); free(j.p); }
    free(post.p); free(code.p);
}

/* ── Menús (barra de menú HTML con atajos de teclado) ─────────────────────── */
/*   vspk_add(app, vspk_menubar(
 *       vspk_menu("Archivo", vspk_menu_item("Abrir...", vspk_on_click(app, abrir, NULL), "ctrl+o"), vspk_menu_sep(),
 *                            vspk_menu_item("Salir", vspk_on_click(app, salir, NULL), "")),
 *       vspk_menu("Ayuda", vspk_menu_item("Acerca de", vspk_on_click(app, acerca, NULL), ""))), ...resto, NULL)
 *   Atajos: "ctrl+o", "ctrl+shift+s", "alt+x", "f5"... (orden: ctrl, shift, alt, tecla).                      */

static const char VSPK__MENU_A[] =
"<style>.sz-menubar{position:fixed;top:0;left:0;right:0;z-index:1000;display:flex;gap:2px;padding:3px 6px;background:var(--sz-surface,#fff);color:var(--sz-on-surface,#1d1b20);border-bottom:1px solid rgba(128,128,128,.3);font-size:14px}.sz-menubar-space{height:38px;width:100%;flex:none}.sz-menu{position:relative}.sz-menu-title{background:none;border:0;padding:6px 10px;border-radius:6px;color:inherit;font:inherit;cursor:pointer}.sz-menu-title:hover,.sz-menu.sz-open>.sz-menu-title{background:rgba(128,128,128,.18)}.sz-menu-list{display:none;position:absolute;top:100%;left:0;min-width:210px;padding:4px;background:var(--sz-surface,#fff);color:inherit;border:1px solid rgba(128,128,128,.35);border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.2)}.sz-menu.sz-open>.sz-menu-list{display:block}.sz-menu-item{display:flex;justify-content:space-between;gap:24px;width:100%;background:none;border:0;padding:6px 10px;border-radius:6px;color:inherit;font:inherit;cursor:pointer;text-align:left}.sz-menu-item:hover{background:rgba(128,128,128,.18)}.sz-menu-item kbd{opacity:.6;font:inherit;font-size:12px}.sz-menu-sep{height:1px;margin:4px 6px;background:rgba(128,128,128,.3)}.sz-native .sz-menubar,.sz-native .sz-menubar-space{display:none!important}</style><div class=\"sz-menubar\">";
static const char VSPK__MENU_B[] =
"</div><div class=\"sz-menubar-space\"></div><script>(function(){if(window.__menu)return;window.__menu=1;var bar=document.querySelector('.sz-menubar');function menus(){return bar.querySelectorAll(':scope > .sz-menu')}window.__vspk_menu_click=function(id){var p=id.split('.');var m=menus()[+p[0]];if(m)m.querySelector('.sz-menu-list').children[+p[1]].click()};window.__vspk_menu_ok=function(){document.documentElement.classList.add('sz-native')};if(bar&&window.ipc&&window.__vspk_native_menu_ok){var ms=[];Array.prototype.forEach.call(menus(),function(m,mi){var items=[];Array.prototype.forEach.call(m.querySelector('.sz-menu-list').children,function(c,ii){if(c.classList.contains('sz-menu-sep'))items.push({sep:true});else items.push({id:mi+'.'+ii,label:(c.querySelector('span')||c).textContent,accel:c.getAttribute('data-accel')||''})});ms.push({label:m.querySelector('.sz-menu-title').textContent,items:items})});window.ipc.postMessage(JSON.stringify({cmd:'setMenu',menu:ms}))}function closeAll(except){document.querySelectorAll('.sz-menu.sz-open').forEach(function(m){if(m!==except)m.classList.remove('sz-open')})}document.addEventListener('click',function(e){var t=e.target.closest?e.target.closest('.sz-menu-title'):null;closeAll(t?t.parentNode:null);if(t)t.parentNode.classList.toggle('sz-open');var it=e.target.closest?e.target.closest('.sz-menu-item'):null;if(it)closeAll(null)});document.addEventListener('mouseover',function(e){var t=e.target.closest?e.target.closest('.sz-menu-title'):null;var o=document.querySelector('.sz-menu.sz-open');if(t&&o&&o!==t.parentNode){closeAll(t.parentNode);t.parentNode.classList.add('sz-open')}});document.addEventListener('keydown',function(e){if(e.key==='Escape'){closeAll(null);return}if(document.documentElement.classList.contains('sz-native')&&!/Win/.test(navigator.platform))return;var k=(e.ctrlKey?'ctrl+':'')+(e.shiftKey?'shift+':'')+(e.altKey?'alt+':'')+e.key.toLowerCase();var items=document.querySelectorAll('.sz-menu-item[data-accel]');for(var i=0;i<items.length;i++){var a=items[i].getAttribute('data-accel');if(a&&a.toLowerCase()===k){e.preventDefault();items[i].click();return}}})})();</script>";

static const char *vspk_menu_item(const char *label, const char *onclick_js, const char *shortcut) {
    VspkBuf b = {0};
    if (!shortcut) shortcut = "";
    vspk__bcat(&b, "<button type=\"button\" class=\"sz-menu-item\" onclick=\"");
    vspk__besc(&b, onclick_js ? onclick_js : "");
    vspk__bcat(&b, "\" data-accel=\""); vspk__besc(&b, shortcut); vspk__bcat(&b, "\"><span>"); vspk__besc(&b, label); vspk__bcat(&b, "</span>");
    if (*shortcut) { vspk__bcat(&b, "<kbd>"); vspk__besc(&b, shortcut); vspk__bcat(&b, "</kbd>"); }
    vspk__bcat(&b, "</button>");
    return vspk__keepb(&b);
}
static const char *vspk_menu_sep(void) { return vspk__keep(vspk__strdup("<div class=\"sz-menu-sep\"></div>")); }
static const char *vspk__menu(const char *title, const char **items) {
    VspkBuf b = {0}; int i;
    vspk__bcat(&b, "<div class=\"sz-menu\"><button type=\"button\" class=\"sz-menu-title\">"); vspk__besc(&b, title);
    vspk__bcat(&b, "</button><div class=\"sz-menu-list\">");
    for (i = 0; items[i]; i++) vspk__bcat(&b, items[i]);
    vspk__bcat(&b, "</div></div>");
    return vspk__keepb(&b);
}
static const char *vspk__menubar(const char **menus) {
    VspkBuf b = {0}; int i;
    vspk__bcat(&b, VSPK__MENU_A);
    for (i = 0; menus[i]; i++) vspk__bcat(&b, menus[i]);
    vspk__bcat(&b, VSPK__MENU_B);
    return vspk__keepb(&b);
}
#define vspk_menu(title, ...) vspk__menu((title), (const char *[]){__VA_ARGS__, NULL})
#define vspk_menubar(...)     vspk__menubar((const char *[]){__VA_ARGS__, NULL})

/* ── Página ───────────────────────────────────────────────────────────────── */

static const char VSPK__PAGE_JS[] =
"window.__state = %STATE%;\n"
"window.__win = %WIN%;\n"
"window.__set = function(name, value) {\n"
"  window.__state[name] = value;\n"
"  document.querySelectorAll('[data-spork-text=\"' + name + '\"]').forEach(function(el) { el.textContent = value; });\n"
"  document.querySelectorAll('[data-spork-bind=\"' + name + '\"]').forEach(function(el) {\n"
"    if (el.type === 'checkbox') el.checked = !!value;\n"
"    else if (el.value != value) el.value = value;\n"
"  });\n"
"  var ev = function(code) { return new Function('return (' + code + ')')(); };\n"
"  document.querySelectorAll('[data-spork-style]').forEach(function(el) { try { Object.assign(el.style, ev(el.dataset.sporkStyle)); } catch(_) {} });\n"
"  document.querySelectorAll('[data-spork-if]').forEach(function(el) { try { el.style.display = ev(el.dataset.sporkIf) ? '' : 'none'; } catch(_) {} });\n"
"  document.querySelectorAll('[data-spork-class]').forEach(function(el) { try { var c = ev(el.dataset.sporkClass); if (typeof c === 'string') el.className = (el.dataset.sporkBase || (el.dataset.sporkBase = el.className)) + ' ' + c; } catch(_) {} });\n"
"};\n"
"// Valor que el usuario escribe/elige → a PHP (State::get() lo ve) y a los demás widgets enlazados.\n"
"window.__sync = function(n, v) {\n"
"  try { fetch('http://127.0.0.1:%PORT%/event/%VEV%', {method: 'POST', mode: 'no-cors', headers: {'Content-Type': 'text/plain'}, body: JSON.stringify({n: n, v: v, w: window.__win})}); } catch(_) {}\n"
"};\n"
"(function() {\n"
"  function onUser(e) {\n"
"    var el = e.target && e.target.closest ? e.target.closest('[data-spork-bind]') : null;\n"
"    if (!el) return;\n"
"    var v = el.type === 'checkbox' ? el.checked : (el.type === 'range' || el.type === 'number') ? Number(el.value) : el.value;\n"
"    var n = el.getAttribute('data-spork-bind');\n"
"    window.__set(n, v);\n"
"    window.__sync(n, v);\n"
"  }\n"
"  document.addEventListener('input', onUser);\n"
"  document.addEventListener('change', onUser);\n"
"})();\n"
"document.addEventListener('click', function(e) {      // Tabs\n"
"  var b = e.target.closest ? e.target.closest('[data-ttarget]') : null;\n"
"  if (!b) return;\n"
"  var g = b.dataset.ttarget, i = +b.dataset.tidx;\n"
"  document.querySelectorAll('[data-tpanel]').forEach(function(p) { if (p.dataset.tpanel === g) p.classList.toggle('sz-active', +p.dataset.tidx === i); });\n"
"  document.querySelectorAll('[data-ttarget]').forEach(function(x) { if (x.dataset.ttarget === g) x.classList.toggle('sz-active', +x.dataset.tidx === i); });\n"
"});\n"
"window.__toast = function(msg, v, ms) {\n"
"  var c = document.getElementById('__vspk_toasts');\n"
"  if (!c) { c = document.createElement('div'); c.className = 'sz-toast-container'; c.id = '__vspk_toasts'; document.body.appendChild(c); }\n"
"  var t = document.createElement('div'); t.className = 'sz-toast' + (v ? ' sz-toast-' + v : ''); t.textContent = msg; c.appendChild(t);\n"
"  setTimeout(function() { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; setTimeout(function() { t.remove(); }, 300); }, ms || 3000);\n"
"};\n"
"window.__vspk_cmd = function(cmd, a, b) {\n"
"  try {\n"
"    if (cmd === 'close' || cmd === 'fullscreen') window.ipc && window.ipc.postMessage(JSON.stringify({cmd: cmd === 'close' ? 'close' : 'toggleFullscreen'}));\n"
"    else if (cmd === 'setTitle' && window.__vspk_api) window.__vspk_api.setTitle(a);\n"
"    else if (cmd === 'setTitle' && typeof __vspk !== 'undefined') __vspk.setTitle(a);\n"
"    else if (cmd === 'notify' && typeof __vspk !== 'undefined') __vspk.notify(a, b);\n"
"  } catch(err) { console.error(err); }\n"
"};\n"
"window.__cv = function(id, op, a) {\n"
"  var c = document.getElementById(id); if (!c) return;\n"
"  var x = c.getContext('2d');\n"
"  if (op === 'clear') { x.clearRect(0, 0, c.width, c.height); }\n"
"  else if (op === 'color') { x.fillStyle = a[0]; x.strokeStyle = a[0]; }\n"
"  else if (op === 'lw') { x.lineWidth = a[0]; }\n"
"  else if (op === 'font') { x.font = a[0] + 'px sans-serif'; }\n"
"  else if (op === 'line') { x.beginPath(); x.moveTo(a[0], a[1]); x.lineTo(a[2], a[3]); x.stroke(); }\n"
"  else if (op === 'rect') { x.fillRect(a[0], a[1], a[2], a[3]); }\n"
"  else if (op === 'frame') { x.strokeRect(a[0], a[1], a[2], a[3]); }\n"
"  else if (op === 'circle') { x.beginPath(); x.arc(a[0], a[1], a[2], 0, 6.283185307); x.fill(); }\n"
"  else if (op === 'ring') { x.beginPath(); x.arc(a[0], a[1], a[2], 0, 6.283185307); x.stroke(); }\n"
"  else if (op === 'text') { x.fillText(a[2], a[0], a[1]); }\n"
"  else if (op === 'poly') { var p = a[0]; x.beginPath(); x.moveTo(p[0][0], p[0][1]); for (var i = 1; i < p.length; i++) x.lineTo(p[i][0], p[i][1]); x.closePath(); x.fill(); }\n"
"  else if (op === 'draw') { new Function('ctx', 'canvas', a[0])(x, c); }\n"
"};\n"
"Object.keys(window.__state).forEach(function(k) { window.__set(k, window.__state[k]); });\n"
"(function connectSSE() {\n"
"  var es = new EventSource('http://127.0.0.1:%PORT%/events');\n"
"  es.addEventListener('state', function(e) { var d = JSON.parse(e.data); if (d.src && d.src === window.__win) return; window.__set(d.name, d.value); });\n"
"  [%EVALEV%, 'all'].forEach(function(n) { es.addEventListener(n, function(e) { try { (0, eval)(JSON.parse(e.data)); } catch(err) { console.error(err); } }); });\n"
"  es.onerror = function() { es.close(); setTimeout(connectSSE, 1000); };\n"
"})();\n";
#define VSPK_CSS_CDN "https://cdn.jsdelivr.net/gh/unoudos/spork-ui@main/spork.css"
#define VSPK_JS_CDN  "https://cdn.jsdelivr.net/gh/unoudos/spork-ui@main/spork.js"

static char *vspk__page(VspkApp *app, const char *title, const char *body, const char *evalev, int is_main, const char *child_close) {
    VspkBuf st = {0}, out = {0}, tail = {0}, wj = {0}, vev = {0}; char *code; char port[16], evn[64]; int i;
    vspk__bc(&st, '{');
    for (i = 0; i < app->nstates; i++) { if (i) vspk__bc(&st, ','); vspk__bjs(&st, app->states[i]->name); vspk__bc(&st, ':'); vspk__state_json(app->states[i], &st); }
    vspk__bc(&st, '}');
    snprintf(port, sizeof port, "%d", app->port);
    vspk__evname(app, evn, sizeof evn, "v");
    vspk__bjs(&wj, evalev);
    code = vspk__strdup(VSPK__PAGE_JS);
    code = vspk__repl(code, "%PORT%", port);
    code = vspk__repl(code, "%VEV%", evn);
    code = vspk__repl(code, "%WIN%", vspk__bstr(&wj));
    code = vspk__repl(code, "%EVALEV%", vspk__bstr(&wj));
    code = vspk__repl(code, "%STATE%", vspk__bstr(&st));     /* el último: el contenido del usuario no se vuelve a sustituir */

    vspk__bcat(&tail, "\n");
    if (is_main && app->key_on) {
        char n[64]; VspkBuf p = {0}; vspk__evname(app, n, sizeof n, "k");
        vspk__postjs(app, &p, n, "JSON.stringify({key:e.key,code:e.code,ctrl:e.ctrlKey,shift:e.shiftKey,alt:e.altKey,meta:e.metaKey})");
        vspk__bcat(&tail, "document.addEventListener(\"keydown\",function(e){"); vspk__bcat(&tail, vspk__bstr(&p)); vspk__bcat(&tail, "});"); free(p.p);
    }
    if (child_close) vspk__bcat(&tail, child_close);
    if (is_main && app->close_on) {
        char n[64]; VspkBuf p = {0}; vspk__evname(app, n, sizeof n, "c");
        vspk__postjs(app, &p, n, "\"{}\"");
        vspk__bcat(&tail, "window.addEventListener(\"vspk:closeRequested\",function(){"); vspk__bcat(&tail, vspk__bstr(&p)); vspk__bcat(&tail, "});"); free(p.p);
    }
    for (i = 0; i < app->ncvs; i++) vspk__bcat(&tail, vspk__bstr(&app->cvs[i]->log));
    vspk__bcat(&tail, vspk__bstr(&app->cvmouse));

    vspk__bcat(&out, "<!DOCTYPE html>\n<html data-theme=\""); vspk__bcat(&out, strcmp(app->theme, "dark") == 0 ? "dark" : "light");
    vspk__bcat(&out, "\">\n<head>\n  <meta charset=\"UTF-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n  <title>");
    vspk__besc(&out, title);
    vspk__bcat(&out, "</title>\n  <link rel=\"icon\" href=\"data:,\">\n  <link rel=\"stylesheet\" href=\"spork.css\" onerror=\"this.onerror=null;this.href='" VSPK_CSS_CDN "'\">\n  <style>:root {\n");
    vspk__bf(&out, "  --sz-primary: %s;", app->primary);
    if (app->bg[0])      vspk__bf(&out, "\n  --sz-bg: %s;", app->bg);
    if (app->surface[0]) vspk__bf(&out, "\n  --sz-surface: %s;", app->surface);
    if (app->font[0])    vspk__bf(&out, "\n  --sz-font: %s, system-ui, sans-serif;", app->font);
    vspk__bcat(&out, "\n}</style>\n</head>\n<body class=\"sz-body\">\n\n<div id=\"__app\" class=\"sz-page\">\n");
    vspk__bcat(&out, body);
    vspk__bcat(&out, "\n</div>\n\n<script>\n"); vspk__bcat(&out, code); vspk__bcat(&out, vspk__bstr(&tail));
    vspk__bcat(&out, "\n</script>\n<script src=\"spork.js\" onerror=\"var s=document.createElement('script');s.src='" VSPK_JS_CDN "';document.body.appendChild(s)\"></script>\n</body>\n</html>");
    free(code); free(st.p); free(tail.p); free(wj.p); free(vev.p);
    return vspk__bdetach(&out);
}

/* ── Ventanas adicionales ─────────────────────────────────────────────────── */
/*   VspkWin *aj = vspk_window(app, "Ajustes", 360, 240);
 *   vspk_win_add(aj, vspk_col(vspk_h4("Ajustes"), vspk_input(nombre, "Nombre")));   // los estados se comparten
 *   vspk_win_show(aj);  vspk_win_close(aj);  vspk_win_on_close(aj, fn, ud);  vspk_win_set_title(aj, "...");  */

static VspkWin *vspk_window(VspkApp *app, const char *title, int w, int h) {
    VspkWin *x = (VspkWin *)calloc(1, sizeof *x);
    x->app = app; snprintf(x->id, sizeof x->id, "w%d", app->nwins + 1); snprintf(x->title, sizeof x->title, "%s", title);
    x->width = w > 0 ? w : 480; x->height = h > 0 ? h : 360;
    VSPK_MASK_PUSH(app->wins, app->nwins, VspkWin *, x);
    return x;
}
static void vspk__win_add(VspkWin *w, const char **items) { int i; for (i = 0; items[i]; i++) { vspk__bcat(&w->body, items[i]); vspk__bc(&w->body, '\n'); } }
#define vspk_win_add(w, ...) vspk__win_add((w), (const char *[]){__VA_ARGS__, NULL})
static void vspk__win_eval(VspkWin *w, const char *code) {
    char ev[32]; VspkBuf b = {0};
    snprintf(ev, sizeof ev, "eval_%s", w->id); vspk__bjs(&b, code); vspk__sse(w->app, ev, vspk__bstr(&b)); free(b.p);
}
static int vspk_win_is_open(VspkWin *w) { return vspk__proc_alive(&w->proc); }
static void vspk_win_close(VspkWin *w) { vspk__win_eval(w, "__vspk.close()"); }
static void vspk_win_eval(VspkWin *w, const char *code) { vspk__win_eval(w, code); }
static void vspk_win_set_title(VspkWin *w, const char *t) {
    VspkBuf b = {0}; vspk__bcat(&b, "__vspk.setTitle("); vspk__bjs(&b, t); vspk__bc(&b, ')'); vspk__win_eval(w, vspk__bstr(&b)); free(b.p);
}
static void vspk_win_on_close(VspkWin *w, VspkCloseFn fn, void *ud) {
    VspkApp *app = w->app; char tag[24], nm[64]; VspkBuf b = {0}, p = {0};
    snprintf(tag, sizeof tag, "c%s", w->id); vspk__evname(app, nm, sizeof nm, tag);
    vspk__ev_add(app, nm, VSPK_EV_WINCLOSE, (void *)fn, ud, w);
    w->close_on = 1;
    vspk__postjs(app, &p, nm, "'{}'");
    vspk__bcat(&b, "window.addEventListener('vspk:closeRequested',function(){"); vspk__bcat(&b, vspk__bstr(&p)); vspk__bcat(&b, "});");
    free(w->close_js); w->close_js = vspk__bdetach(&b); free(p.p);
}

static void vspk__tmpdir(char *out, size_t n) {
#ifdef _WIN32
    DWORD l = GetTempPathA((DWORD)n, out); if (l == 0 || l >= n) snprintf(out, n, ".\\");
#else
    const char *t = getenv("TMPDIR"); snprintf(out, n, "%s/", t && *t ? t : "/tmp");
#endif
}
static int vspk__write_htv(VspkApp *app, char *path, size_t pn, const char *head, const char *html) {
    FILE *f; char dir[400];
    vspk__tmpdir(dir, sizeof dir);
    snprintf(path, pn, "%svspk_%s_%d.htv", dir, app->token, ++app->htvn);
    f = fopen(path, "wb"); if (!f) return -1;
    fputs(head, f); fputc('\n', f); fputs(html, f); fclose(f);
    return 0;
}
static void vspk__find_icon(char *out, size_t n);
static void vspk__win_open(VspkWin *w) {
    VspkApp *app = w->app; char exe[520], icon[300]; char *page; VspkBuf head = {0};
    if (vspk__proc_alive(&w->proc)) return;
    if (w->htv[0]) remove(w->htv);
    page = vspk__page(app, w->title, vspk__bstr(&w->body), (snprintf(exe, sizeof exe, "eval_%s", w->id), exe), 0, w->close_js);
    vspk__bf(&head, "title: %s\nwidth: %d\nheight: %d\ndevtools: true\n%s", w->title, w->width, w->height, w->close_on ? "on_close: confirm\n" : "");
    vspk__find_icon(icon, sizeof icon); if (icon[0]) vspk__bf(&head, "icon: %s\n", icon);
    if (vspk__write_htv(app, w->htv, sizeof w->htv, vspk__bstr(&head), page) == 0) {
        vspk__find_exe(app, exe, sizeof exe);
        vspk__proc_spawn(&w->proc, exe, w->htv);
    }
    free(page); free(head.p);
}
static void vspk_win_show(VspkWin *w) { if (w->app->running) vspk__win_open(w); else w->want = 1; }

/* ── Servidor HTTP (puente) ───────────────────────────────────────────────── */

#define VSPK_CORS "Access-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET, POST, OPTIONS\r\nAccess-Control-Allow-Headers: *\r\n"

static void vspk__thr_inc(VspkApp *a) { vspk__mx_lock(&a->tlock); a->nthr++; vspk__mx_unlock(&a->tlock); }
static void vspk__thr_dec(VspkApp *a) { vspk__mx_lock(&a->tlock); a->nthr--; vspk__mx_unlock(&a->tlock); }
static void vspk__spawn_thread(vspk_thrfn fn, void *arg) {
#ifdef _WIN32
    HANDLE h = CreateThread(NULL, 0, fn, arg, 0, NULL); if (h) CloseHandle(h);
#else
    pthread_t t; pthread_attr_t at; pthread_attr_init(&at); pthread_attr_setdetachstate(&at, PTHREAD_CREATE_DETACHED);
    pthread_create(&t, &at, fn, arg); pthread_attr_destroy(&at);
#endif
}

static void vspk__ev_result(VspkApp *app, VspkWin *w, int ok) {
    if (w) vspk__win_eval(w, ok ? "__vspk.confirmClose()" : "__vspk.cancelClose()");
    else   vspk_eval(app, ok ? "__vspk.confirmClose()" : "__vspk.cancelClose()");
}

static void vspk__dispatch_cb(VspkApp *app, const char *id) {
    int i; VspkFn fn = NULL; void *ud = NULL;
    vspk__mx_lock(&app->ulock);
    for (i = 0; i < app->ncbs; i++) if (strcmp(app->cbs[i].id, id) == 0) { fn = app->cbs[i].fn; ud = app->cbs[i].ud; break; }
    if (fn) fn(ud);                     /* id sin token válido → no existe → no hace nada */
    vspk__mx_unlock(&app->ulock);
}
static void vspk__dispatch_ev(VspkApp *app, const char *name, const char *body) {
    int i; VspkEv *e = NULL, copy;
    vspk__mx_lock(&app->ulock);
    for (i = 0; i < app->nevs; i++) if (strcmp(app->evs[i].name, name) == 0) { copy = app->evs[i]; e = &copy; break; }
    if (e) {
        switch (e->kind) {
        case VSPK_EV_KEY: {
            char *k = vspk__jstr(body, "key"); ((VspkKeyFn)e->fn)(k ? k : "", body, e->ud); free(k); break;
        }
        case VSPK_EV_CLOSE: case VSPK_EV_WINCLOSE: {
            int ok = ((VspkCloseFn)e->fn)(e->ud) != 0;
            vspk__ev_result(app, (VspkWin *)e->ctx, ok); break;
        }
        case VSPK_EV_DIALOG: {
            char *p = vspk__jstr(body, "path"); ((VspkPathFn)e->fn)(p, e->ud); free(p); break;
        }
        case VSPK_EV_MOUSE: {
            char *t = vspk__jstr(body, "type");
            ((VspkMouseFn)e->fn)(t ? t : "", (int)vspk__jnum(body, "x", 0), (int)vspk__jnum(body, "y", 0), (int)vspk__jnum(body, "button", 0), e->ud); free(t); break;
        }
        case VSPK_EV_USER: ((VspkEventFn)e->fn)(body, e->ud); break;
        }
    } else {
        char evn[64]; vspk__evname(app, evn, sizeof evn, "v");
        if (strcmp(name, evn) == 0) {                   /* valor de un campo enlazado: {n, v, w} */
            char *n = vspk__jstr(body, "n"), *w = vspk__jstr(body, "w"); const char *v = vspk__jfind(body, "v");
            VspkState *st = NULL;
            if (n) for (i = 0; i < app->nstates; i++) if (strcmp(app->states[i]->name, n) == 0) st = app->states[i];
            if (st && v) {
                if (*v == '"') { char *s = vspk__junq(v); vspk__set_raw(st, 0, s ? s : ""); free(s); }
                else if (strncmp(v, "true", 4) == 0) vspk__set_raw(st, 2, "true");
                else if (strncmp(v, "false", 5) == 0) vspk__set_raw(st, 2, "false");
                else { char *t = vspk__numstr(atof(v)); vspk__set_raw(st, 1, t); free(t); }
                if (app->nwins) vspk__push_state(st, w ? w : "");
                if (st->onchange) st->onchange(st->val, st->onchange_ud);
            }
            free(n); free(w);
        }
    }
    vspk__mx_unlock(&app->ulock);
}

static int vspk__hex(int c) { return isdigit(c) ? c - '0' : (tolower(c) - 'a' + 10); }
static void vspk__urldecode(char *s) {
    char *o = s;
    for (; *s; s++) {
        if (*s == '%' && isxdigit((unsigned char)s[1]) && isxdigit((unsigned char)s[2])) { *o++ = (char)(vspk__hex((unsigned char)s[1]) * 16 + vspk__hex((unsigned char)s[2])); s += 2; }
        else *o++ = *s;
    }
    *o = 0;
}
static void vspk__reply(vspk_sock s, const char *status, const char *body) {
    char h[400]; int n = snprintf(h, sizeof h, "HTTP/1.1 %s\r\n" VSPK_CORS "Content-Type: text/plain\r\nContent-Length: %d\r\nConnection: close\r\n\r\n", status, (int)strlen(body));
    vspk__send_all(s, h, (size_t)n); if (*body) vspk__send_all(s, body, strlen(body));
}

typedef struct { VspkApp *app; vspk_sock s; } VspkConn;

VSPK_THREAD_FN(vspk__client_thread) {
    VspkConn *cn = (VspkConn *)arg; VspkApp *app = cn->app; vspk_sock s = cn->s;
    VspkBuf rq = {0}; char tmp[4096]; char method[16] = "", path[1500] = ""; const char *hend = NULL; size_t need = 0; int i;
    free(cn);
#ifdef _WIN32
    { DWORD tv = 5000; setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, (const char *)&tv, sizeof tv); }
#else
    { struct timeval tv; tv.tv_sec = 5; tv.tv_usec = 0; setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof tv); }
#endif
    for (;;) {                                   /* cabeceras + cuerpo */
        int r;
        if (!hend && rq.len) { hend = strstr(rq.p, "\r\n\r\n"); if (hend) {
            const char *cl = vspk__ifind(rq.p, "content-length:");
            need = (size_t)(hend - rq.p) + 4 + (cl && cl < hend ? (size_t)atol(cl + 15) : 0);
            if (need > (size_t)4 * 1024 * 1024) goto done;
        } }
        if (hend && rq.len >= need) break;
        r = (int)recv(s, tmp, sizeof tmp, 0);
        if (r <= 0) goto done;
        vspk__bcatn(&rq, tmp, (size_t)r);
        if (rq.len > (size_t)4 * 1024 * 1024) goto done;
    }
    sscanf(rq.p, "%15s %1499s", method, path);
    { char *q = strchr(path, '?'); if (q) *q = 0; }
    vspk__urldecode(path);

    if (strcmp(method, "OPTIONS") == 0) { vspk__reply(s, "204 No Content", ""); goto done; }
    if (strcmp(path, "/events") == 0) {
        VspkClient *c = (VspkClient *)calloc(1, sizeof *c); long long lastping = vspk__now_ms();
        static const char hdr[] = "HTTP/1.1 200 OK\r\n" VSPK_CORS "Content-Type: text/event-stream\r\nCache-Control: no-cache\r\nConnection: close\r\n\r\n: conectado\n\n";
        c->s = s; c->alive = 1;
        if (vspk__send_all(s, hdr, sizeof hdr - 1) != 0) { free(c); goto done; }
        vspk__mx_lock(&app->slock); VSPK_MASK_PUSH(app->clients, app->nclients, VspkClient *, c); vspk__mx_unlock(&app->slock);
        while (c->alive && !app->stopping) {
            vspk__sleep_ms(100);
            if (vspk__now_ms() - lastping > 15000) {
                lastping = vspk__now_ms();
                vspk__mx_lock(&app->slock); if (c->alive && vspk__send_all(s, ": ping\n\n", 8) != 0) c->alive = 0; vspk__mx_unlock(&app->slock);
            }
        }
        vspk__mx_lock(&app->slock);
        for (i = 0; i < app->nclients; i++) if (app->clients[i] == c) { app->clients[i] = app->clients[--app->nclients]; break; }
        vspk__mx_unlock(&app->slock);
        free(c); goto done;
    }
    if (strcmp(path, "/favicon.ico") == 0) { vspk__reply(s, "204 No Content", ""); goto done; }
    if (strncmp(path, "/cb/", 4) == 0) {
        vspk__reply(s, "200 OK", "ok"); vspk__sock_close(s); s = VSPK_BADSOCK;
        vspk__dispatch_cb(app, path + 4); goto done;
    }
    if (strncmp(path, "/event/", 7) == 0 && strcmp(method, "POST") == 0) {
        vspk__reply(s, "200 OK", "ok"); vspk__sock_close(s); s = VSPK_BADSOCK;
        vspk__dispatch_ev(app, path + 7, hend + 4); goto done;
    }
    vspk__reply(s, "404 Not Found", "not found");
done:
    if (s != VSPK_BADSOCK) vspk__sock_close(s);
    free(rq.p);
    vspk__thr_dec(app);
    VSPK_THREAD_END;
}

VSPK_THREAD_FN(vspk__accept_thread) {
    VspkApp *app = (VspkApp *)arg;
    while (!app->stopping) {
        vspk_sock c = accept(app->lsock, NULL, NULL);
        if (c == VSPK_BADSOCK) { if (app->stopping) break; vspk__sleep_ms(5); continue; }
        { VspkConn *cn = (VspkConn *)malloc(sizeof *cn); cn->app = app; cn->s = c; vspk__thr_inc(app); vspk__spawn_thread(vspk__client_thread, cn); }
    }
    vspk__thr_dec(app);
    VSPK_THREAD_END;
}

/* ── App ──────────────────────────────────────────────────────────────────── */

static VspkApp *vspk_app(const char *title, int width, int height) {
    VspkApp *app = (VspkApp *)calloc(1, sizeof *app); struct sockaddr_in addr; int one = 1;
#ifdef _WIN32
    WSADATA wsa; WSAStartup(MAKEWORD(2, 2), &wsa);
#else
    signal(SIGPIPE, SIG_IGN);
#endif
    snprintf(app->title, sizeof app->title, "%s", title ? title : "App");
    app->width = width > 0 ? width : 1024; app->height = height > 0 ? height : 768;
    snprintf(app->theme, sizeof app->theme, "light"); snprintf(app->primary, sizeof app->primary, "#6750A4");
    vspk__random_hex(app->token, 16);
    vspk__mx_init(&app->ulock); vspk__mx_init(&app->slock); vspk__mx_init(&app->alock); vspk__mx_init(&app->tlock);
    vspk__cur = app;
    app->lsock = socket(AF_INET, SOCK_STREAM, 0);
    setsockopt(app->lsock, SOL_SOCKET, SO_REUSEADDR, (const char *)&one, sizeof one);
    memset(&addr, 0, sizeof addr); addr.sin_family = AF_INET; addr.sin_port = 0; addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (bind(app->lsock, (struct sockaddr *)&addr, sizeof addr) != 0 || listen(app->lsock, 64) != 0) { fprintf(stderr, "[vspk] no se pudo abrir el puerto local\n"); exit(1); }
    { socklen_t l = sizeof addr; getsockname(app->lsock, (struct sockaddr *)&addr, &l); app->port = ntohs(addr.sin_port); }
    vspk__thr_inc(app); vspk__spawn_thread(vspk__accept_thread, app);     /* el puerto se conoce ya, antes de construir los widgets */
    return app;
}
static void vspk_theme(VspkApp *a, const char *t)     { snprintf(a->theme, sizeof a->theme, "%s", t); }
static void vspk_primary(VspkApp *a, const char *c)   { snprintf(a->primary, sizeof a->primary, "%s", c); }
static void vspk_background(VspkApp *a, const char *c){ snprintf(a->bg, sizeof a->bg, "%s", c); }
static void vspk_surface(VspkApp *a, const char *c)   { snprintf(a->surface, sizeof a->surface, "%s", c); }
static void vspk_font(VspkApp *a, const char *f)      { snprintf(a->font, sizeof a->font, "%s", f); }
static void vspk_devtools(VspkApp *a, int on)         { a->devtools = on; }
static void vspk_exe(VspkApp *a, const char *path)    { snprintf(a->exe, sizeof a->exe, "%s", path); }

static void vspk__add(VspkApp *app, const char **items) { int i; for (i = 0; items[i]; i++) { vspk__bcat(&app->root, items[i]); vspk__bc(&app->root, '\n'); } }
/* Añade widgets a la página (en orden). */
#define vspk_add(app, ...) vspk__add((app), (const char *[]){__VA_ARGS__, NULL})

static void vspk_free(VspkApp *app) {
    int i;
    if (!app) return;
    for (i = 0; i < app->narena; i++) free(app->arena[i]);
    for (i = 0; i < app->nstates; i++) { free(app->states[i]->val); free(app->states[i]); }
    for (i = 0; i < app->ncvs; i++) { free(app->cvs[i]->log.p); free(app->cvs[i]); }
    for (i = 0; i < app->nwins; i++) { free(app->wins[i]->body.p); free(app->wins[i]->close_js); free(app->wins[i]); }
    free(app->arena); free(app->states); free(app->cvs); free(app->wins); free(app->cbs); free(app->evs); free(app->timers); free(app->clients);
    free(app->root.p); free(app->cvmouse.p);
    if (vspk__cur == app) vspk__cur = NULL;
    free(app);
}

static void vspk__find_icon(char *out, size_t n) {
    static const char *names[] = { "icon.ico", "icon.png", "favicon.ico", "favicon.png", NULL }; int i;
    out[0] = 0;
    for (i = 0; names[i]; i++) if (vspk__file_exists(names[i])) { snprintf(out, n, "%s", names[i]); return; }
}

/* Abre vspk con un .htv temporal y atiende eventos hasta que se cierra la ventana. Devuelve 0 (1 si no pudo lanzar vspk). */
static int vspk_run(VspkApp *app) {
    char exe[520], icon[300], htv[600]; char *html; VspkBuf head = {0}; int i, rc = 0; long long t0;
    vspk__find_exe(app, exe, sizeof exe);
    html = vspk__page(app, app->title, vspk__bstr(&app->root), "eval", 1, NULL);
    vspk__find_icon(icon, sizeof icon);
    vspk__bf(&head, "title: %s\nwidth: %d\nheight: %d\n%s", app->title, app->width, app->height, app->devtools ? "devtools: true\n" : "");
    if (icon[0]) vspk__bf(&head, "icon: %s\n", icon);
    if (app->close_on) vspk__bcat(&head, "on_close: confirm\n");
    if (vspk__write_htv(app, htv, sizeof htv, vspk__bstr(&head), html) != 0) { fprintf(stderr, "[vspk] no se pudo escribir el .htv\n"); free(html); free(head.p); return 1; }
    free(html); free(head.p);

    if (vspk__proc_spawn(&app->proc, exe, htv) != 0) { fprintf(stderr, "[vspk] no se pudo lanzar %s\n", exe); remove(htv); return 1; }
    app->running = 1;
    vspk__mx_lock(&app->ulock);
    for (i = 0; i < app->nwins; i++) if (app->wins[i]->want) vspk__win_open(app->wins[i]);
    t0 = vspk__now_ms();
    for (i = 0; i < app->ntimers; i++) if (app->timers[i].next < 0) app->timers[i].next = t0 + app->timers[i].ms;
    vspk__mx_unlock(&app->ulock);

    while (!app->quit && vspk__proc_alive(&app->proc)) {
        long long now = vspk__now_ms();
        vspk__mx_lock(&app->ulock);
        for (i = 0; i < app->ntimers; i++) {
            VspkTimer *t = &app->timers[i];
            if (t->cancelled || t->next < 0 || now < t->next) continue;
            { VspkTimerFn fn = t->fn; void *ud = t->ud; int once = t->once, ms = t->ms, keep;
              keep = fn(ud);                              /* fn puede añadir temporizadores: t puede haberse movido */
              t = &app->timers[i];
              if (once || !keep) t->cancelled = 1; else t->next = vspk__now_ms() + ms; }
        }
        vspk__mx_unlock(&app->ulock);
        vspk__sleep_ms(10);
    }

    vspk__mx_lock(&app->ulock);
    app->running = 0;
    vspk__mx_unlock(&app->ulock);
    /* Al cerrar la principal se cierran las demás. */
    for (i = 0; i < app->nwins; i++) if (vspk__proc_alive(&app->wins[i]->proc)) vspk__win_eval(app->wins[i], "__vspk.close()");
    if (app->nwins) vspk__sleep_ms(300);
    for (i = 0; i < app->nwins; i++) {
        vspk__proc_kill(&app->wins[i]->proc);
        if (app->wins[i]->htv[0]) remove(app->wins[i]->htv);
    }
    vspk__proc_kill(&app->proc);
    remove(htv);
    /* apaga el puente */
    app->stopping = 1;
    vspk__mx_lock(&app->slock);
    for (i = 0; i < app->nclients; i++) { app->clients[i]->alive = 0; vspk__sock_shutdown(app->clients[i]->s); }
    vspk__mx_unlock(&app->slock);
    vspk__sock_shutdown(app->lsock); vspk__sock_close(app->lsock);
    for (i = 0; i < 40; i++) { int n; vspk__mx_lock(&app->tlock); n = app->nthr; vspk__mx_unlock(&app->tlock); if (n <= 0) break; vspk__sleep_ms(50); }
    return rc;
}

#ifdef __cplusplus
}
#endif
#endif /* VSPK_H */
