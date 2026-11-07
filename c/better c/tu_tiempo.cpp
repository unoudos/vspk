/*
 * tu_tiempo.cpp — Versión ultraligera estilo Better C
 * Compilar: g++ tu_tiempo.cpp -o tu_tiempo.exe -lws2_32 -lwininet -mwindows
 */

#define VSPK_IMPLEMENTATION
#include "vspk.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>

#ifdef _WIN32
#  include <windows.h>
#  include <wininet.h>
#  pragma comment(lib, "wininet.lib")
#else
#  include <unistd.h>
#endif

struct WeatherData {
    char ciudad[128], fecha_larga[128], temp_actual[16];
    char temp_max[16], temp_min[16], humedad[16], viento[16];
    char dir_viento[32], icono[64], ico_luna[64];
};

static int http_get(const char *url, char *out, int out_size) {
#ifdef _WIN32
    HINTERNET hi = InternetOpenA("vspk/1.0", INTERNET_OPEN_TYPE_PRECONFIG, NULL, NULL, 0);
    HINTERNET hurl = InternetOpenUrlA(hi, url, NULL, 0, INTERNET_FLAG_RELOAD | INTERNET_FLAG_NO_CACHE_WRITE, 0);
    if (!hurl) { InternetCloseHandle(hi); return 0; }
    DWORD read = 0, total = 0;
    while (InternetReadFile(hurl, out + total, out_size - total - 1, &read) && read > 0) total += read;
    out[total] = '\0';
    InternetCloseHandle(hurl); InternetCloseHandle(hi);
    return (int)total;
#else
    char cmd[512], tmp[64];
    std::snprintf(tmp, sizeof(tmp), "/tmp/vspk_wx_%d.xml", (int)getpid());
    std::snprintf(cmd, sizeof(cmd), "wget -q -O '%s' '%s'", tmp, url);
    if (std::system(cmd) != 0) return 0;
    FILE *f = std::fopen(tmp, "r");
    if (!f) return 0;
    int n = (int)std::fread(out, 1, out_size - 1, f);
    out[n] = '\0'; std::fclose(f); unlink(tmp);
    return n;
#endif
}

static void xml_get(const char *src, const char *tag, char *dst, int size) {
    char open[64], close[64];
    std::snprintf(open, sizeof(open), "<%s>", tag);
    std::snprintf(close, sizeof(close), "</%s>", tag);
    const char *s = std::strstr(src, open);
    if (!s) return;
    s += std::strlen(open);
    const char *e = std::strstr(s, close);
    if (!e) return;
    int len = (int)(e - s);
    if (len >= size) len = size - 1;
    std::memcpy(dst, s, len);
    dst[len] = '\0';
}

static const char* xml_nth(const char *src, const char *tag, int n) {
    char open[64];
    std::snprintf(open, sizeof(open), "<%s>", tag);
    const char *p = src;
    for (int i = 0; i <= n; i++) {
        p = std::strstr(p, open);
        if (!p) return nullptr;
        if (i < n) p += std::strlen(open);
    }
    return p + std::strlen(open);
}

static void fmt_icon(const char *ico, const char *base_url, char *out, int size) {
    char name[64];
    std::strncpy(name, ico, sizeof(name) - 1);
    char *p;
    if ((p = std::strstr(name, ".png"))) *p = '\0';
    if ((p = std::strstr(name, ".svg"))) *p = '\0';
    if (std::strncmp(name, "http", 4) == 0)
        std::snprintf(out, size, "%s", name);
    else
        std::snprintf(out, size, "%s%s.png", base_url, name);
}

int main() {
    VspkApp *app = vspk_app("Pronóstico del Tiempo - Málaga", 450, 560);
    std::strncpy(app->primary, "#0284c7", sizeof(app->primary) - 1);

    auto s_ciudad   = vspk_state_str(app, "ciudad",   "Cargando clima...");
    auto s_fecha    = vspk_state_str(app, "fecha",    "--");
    auto s_temp     = vspk_state_str(app, "temp",     "--");
    auto s_maxmin   = vspk_state_str(app, "maxmin",   "-- | --");
    auto s_humedad  = vspk_state_str(app, "humedad",  "Humedad: --");
    auto s_viento   = vspk_state_str(app, "viento",   "Viento: --");
    auto s_img_dia  = vspk_state_str(app, "img_dia",  "");
    auto s_img_luna = vspk_state_str(app, "img_luna", "");

    // Cargar datos
    static char xml[131072];
    WeatherData d = {0};
    if (http_get("http://xml.tutiempo.net/xml/3589.xml", xml, sizeof(xml)) > 0) {
        char loc[4096] = {0};
        xml_get(xml, "localidad", loc, sizeof(loc));
        xml_get(loc, "nombre", d.ciudad, sizeof(d.ciudad));

        const char *dia1 = xml_nth(xml, "dia", 0);
        if (dia1) {
            xml_get(dia1, "fecha_larga", d.fecha_larga, sizeof(d.fecha_larga));
            xml_get(dia1, "temp_maxima", d.temp_max,    sizeof(d.temp_max));
            xml_get(dia1, "temp_minima", d.temp_min,    sizeof(d.temp_min));
            xml_get(dia1, "humedad",     d.humedad,     sizeof(d.humedad));
            xml_get(dia1, "viento",      d.viento,      sizeof(d.viento));
            xml_get(dia1, "dir_viento",  d.dir_viento,  sizeof(d.dir_viento));
            xml_get(dia1, "icono",       d.icono,       sizeof(d.icono));
            xml_get(dia1, "ico_fase_luna", d.ico_luna,  sizeof(d.ico_luna));
        }

        const char *hora1 = xml_nth(xml, "hora", 0);
        if (hora1) xml_get(hora1, "temperatura", d.temp_actual, sizeof(d.temp_actual));
        else std::strcpy(d.temp_actual, "N/A");
    }

    // Actualizar estados
    vspk_state_set_str(app, s_ciudad, d.ciudad);
    vspk_state_set_str(app, s_fecha,  d.fecha_larga);

    char buf[256];
    std::snprintf(buf, sizeof(buf), "Temperatura actual: %s °C", d.temp_actual);
    vspk_state_set_str(app, s_temp, buf);

    std::snprintf(buf, sizeof(buf), "%s °C  |  %s °C", d.temp_max, d.temp_min);
    vspk_state_set_str(app, s_maxmin, buf);

    std::snprintf(buf, sizeof(buf), "Humedad: %s%%", d.humedad);
    vspk_state_set_str(app, s_humedad, buf);

    std::snprintf(buf, sizeof(buf), "Viento: %s km/h - %s", d.viento, d.dir_viento);
    vspk_state_set_str(app, s_viento, buf);

    char url[256];
    fmt_icon(d.icono, "https://v5i.tutiempo.net/wi/01/50/", url, sizeof(url));
    vspk_state_set_str(app, s_img_dia, url);

    fmt_icon(d.ico_luna, "https://v5i.tutiempo.net/wmi/01/", url, sizeof(url));
    vspk_state_set_str(app, s_img_luna, url);

    // Layout UI
    vspk_add(app,
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
                    vspk_card(2, vspk_p("🌙 Fase Lunar"), vspk_img("img_luna", "Fase Lunar")),
                    vspk_card(2, vspk_p("☀ Día"), vspk_img("img_dia", "Icono del Día"))
                ),
                vspk_img_script()
            ),
            vspk_button("Actualizar Pronóstico", "location.reload()")
        )
    );

    vspk_run(app);
    vspk_free(app);
    return 0;
}