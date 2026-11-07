/*
 * tu_tiempo.c — App del tiempo para Málaga usando vspk.h
 * Compilar Windows:
 *   gcc tu_tiempo.c -o tu_tiempo.exe -lws2_32 -lwininet -mwindows
 */

#define VSPK_IMPLEMENTATION
#include "vspk.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>

#ifdef _WIN32
#  include <wininet.h>
#  pragma comment(lib, "wininet.lib")
#else
#  include <sys/socket.h>
#  include <netdb.h>
#  include <unistd.h>
#endif

static int http_get(const char *url, char *out, int out_size) {
#ifdef _WIN32
    HINTERNET hi  = InternetOpenA("vspk/1.0", INTERNET_OPEN_TYPE_PRECONFIG, NULL, NULL, 0);
    HINTERNET hurl = InternetOpenUrlA(hi, url, NULL, 0,
        INTERNET_FLAG_RELOAD | INTERNET_FLAG_NO_CACHE_WRITE, 0);
    if (!hurl) { InternetCloseHandle(hi); return 0; }
    DWORD read = 0, total = 0;
    while (InternetReadFile(hurl, out + total, out_size - total - 1, &read) && read > 0)
        total += read;
    out[total] = '\0';
    InternetCloseHandle(hurl);
    InternetCloseHandle(hi);
    return (int)total;
#else
    char cmd[512], tmp[64];
    snprintf(tmp, sizeof(tmp), "/tmp/vspk_wx_%d.xml", (int)getpid());
    snprintf(cmd, sizeof(cmd), "wget -q -O '%s' '%s'", tmp, url);
    if (system(cmd) != 0) return 0;
    FILE *f = fopen(tmp, "r");
    if (!f) return 0;
    int n = (int)fread(out, 1, out_size - 1, f);
    out[n] = '\0';
    fclose(f);
    unlink(tmp);
    return n;
#endif
}

static int xml_get(const char *src, const char *tag, char *dst, int dst_size) {
    char open[64], close[64];
    snprintf(open,  sizeof(open),  "<%s>",  tag);
    snprintf(close, sizeof(close), "</%s>", tag);
    const char *s = strstr(src, open);
    if (!s) return 0;
    s += strlen(open);
    const char *e = strstr(s, close);
    if (!e) return 0;
    int len = (int)(e - s);
    if (len >= dst_size) len = dst_size - 1;
    memcpy(dst, s, len);
    dst[len] = '\0';
    return len;
}

static const char *xml_nth(const char *src, const char *tag, int n) {
    char open[64];
    snprintf(open, sizeof(open), "<%s>", tag);
    const char *p = src;
    for (int i = 0; i <= n; i++) {
        p = strstr(p, open);
        if (!p) return NULL;
        if (i < n) p += strlen(open);
    }
    return p + strlen(open);
}

#define XML_URL "http://xml.tutiempo.net/xml/3589.xml"

typedef struct {
    char ciudad[128];
    char fecha_larga[128];
    char temp_actual[16];
    char temp_max[16];
    char temp_min[16];
    char humedad[16];
    char viento[16];
    char dir_viento[32];
    char icono[64];
    char ico_luna[64];
} WeatherData;

static char xml_buf[131072];

static int load_weather(WeatherData *d) {
    memset(d, 0, sizeof(*d));
    if (http_get(XML_URL, xml_buf, sizeof(xml_buf)) <= 0)
        return 0;

    char loc[4096] = {0};
    xml_get(xml_buf, "localidad", loc, sizeof(loc));
    xml_get(loc, "nombre", d->ciudad, sizeof(d->ciudad));

    const char *dia1 = xml_nth(xml_buf, "dia", 0);
    if (dia1) {
        xml_get(dia1, "fecha_larga", d->fecha_larga, sizeof(d->fecha_larga));
        xml_get(dia1, "temp_maxima", d->temp_max,    sizeof(d->temp_max));
        xml_get(dia1, "temp_minima", d->temp_min,    sizeof(d->temp_min));
        xml_get(dia1, "humedad",     d->humedad,     sizeof(d->humedad));
        xml_get(dia1, "viento",      d->viento,      sizeof(d->viento));
        xml_get(dia1, "dir_viento",  d->dir_viento,  sizeof(d->dir_viento));
        xml_get(dia1, "icono",       d->icono,       sizeof(d->icono));
        xml_get(dia1, "ico_fase_luna", d->ico_luna,  sizeof(d->ico_luna));
    }

    const char *hora1 = xml_nth(xml_buf, "hora", 0);
    if (hora1)
        xml_get(hora1, "temperatura", d->temp_actual, sizeof(d->temp_actual));
    else
        strcpy(d->temp_actual, "N/A");

    return 1;
}

static void fmt_weather_icon(const char *ico, char *out, int out_size) {
    char base[64];
    strncpy(base, ico, sizeof(base) - 1);
    char *p;
    if ((p = strstr(base, ".png"))) *p = '\0';
    if ((p = strstr(base, ".svg"))) *p = '\0';
    if (strncmp(base, "http", 4) == 0)
        snprintf(out, out_size, "%s", base);
    else
        snprintf(out, out_size, "https://v5i.tutiempo.net/wi/01/50/%s.png", base);
}

static void fmt_moon_icon(const char *ico, char *out, int out_size) {
    char base[64];
    strncpy(base, ico, sizeof(base) - 1);
    char *p;
    if ((p = strstr(base, ".png"))) *p = '\0';
    if ((p = strstr(base, ".svg"))) *p = '\0';
    if (strncmp(base, "http", 4) == 0)
        snprintf(out, out_size, "%s", base);
    else
        snprintf(out, out_size, "https://v5i.tutiempo.net/wmi/01/%s.png", base);
}

static VspkApp    *g_app;
static VspkState  *s_ciudad, *s_fecha, *s_temp, *s_maxmin;
static VspkState  *s_humedad, *s_viento, *s_img_dia, *s_img_luna;

static void update_ui(const WeatherData *d) {
    char buf[256];

    vspk_state_set_str(g_app, s_ciudad, d->ciudad);
    vspk_state_set_str(g_app, s_fecha,  d->fecha_larga);

    snprintf(buf, sizeof(buf), "Temperatura actual: %s °C", d->temp_actual);
    vspk_state_set_str(g_app, s_temp, buf);

    snprintf(buf, sizeof(buf), "%s °C  |  %s °C", d->temp_max, d->temp_min);
    vspk_state_set_str(g_app, s_maxmin, buf);

    snprintf(buf, sizeof(buf), "Humedad: %s%%", d->humedad);
    vspk_state_set_str(g_app, s_humedad, buf);

    snprintf(buf, sizeof(buf), "Viento: %s km/h - %s", d->viento, d->dir_viento);
    vspk_state_set_str(g_app, s_viento, buf);

    char url[256];
    fmt_weather_icon(d->icono,   url, sizeof(url));
    vspk_state_set_str(g_app, s_img_dia, url);

    fmt_moon_icon(d->ico_luna, url, sizeof(url));
    vspk_state_set_str(g_app, s_img_luna, url);
}

int main(void) {
    g_app = vspk_app("Pronóstico del Tiempo - Málaga", 450, 560);
    strncpy(g_app->primary, "#0284c7", sizeof(g_app->primary) - 1);

    s_ciudad   = vspk_state_str(g_app, "ciudad",   "Cargando clima...");
    s_fecha    = vspk_state_str(g_app, "fecha",    "--");
    s_temp     = vspk_state_str(g_app, "temp",     "--");
    s_maxmin   = vspk_state_str(g_app, "maxmin",   "-- | --");
    s_humedad  = vspk_state_str(g_app, "humedad",  "Humedad: --");
    s_viento   = vspk_state_str(g_app, "viento",   "Viento: --");
    s_img_dia  = vspk_state_str(g_app, "img_dia",  "");
    s_img_luna = vspk_state_str(g_app, "img_luna", "");

    WeatherData d0;
    if (load_weather(&d0))
        update_ui(&d0);

    vspk_add(g_app,
        vspk_col(6,
            vspk_h1(vspk_state_span(s_ciudad)),
            vspk_p(vspk_state_span(s_fecha)),
            vspk_hr(),

            vspk_card(3,
                vspk_h2(vspk_state_span(s_temp)),
                vspk_p(vspk_state_span(s_maxmin)),
                vspk_row(2,
                    vspk_p(vspk_state_span(s_humedad)),
                    vspk_p(vspk_state_span(s_viento))
                )
            ),

            vspk_col(4,
                vspk_hr(),
                vspk_h3("Indicadores"),
                vspk_row(2,
                    vspk_card(2,
                        vspk_p("🌙 Fase Lunar"),
                        vspk_img("img_luna", "Fase Lunar")
                    ),
                    vspk_card(2,
                        vspk_p("☀ Día"),
                        vspk_img("img_dia", "Icono del Día")
                    )
                ),
                vspk_img_script()
            ),

            vspk_button("Actualizar Pronóstico", "location.reload()")
        )
    );

    vspk_run(g_app);
    vspk_free(g_app);
    return 0;
}