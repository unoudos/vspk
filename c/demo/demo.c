/* Demo vspk.h — gcc demo.c -o demo -lpthread */
#include "vspk.h"

static VspkApp *app;
static VspkState *n, *pct, *nombre, *acepto, *color, *res, *vol, *lg, *tecla, *ticks, *arch, *raton;
static VspkCanvas *lienzo;
static VspkWin *ajustes;

static void c_menos(void *u)   { (void)u; vspk_dec(n, 1); }
static void c_mas(void *u)     { (void)u; vspk_inc(n, 1); }
static void c_pct(void *u)     { (void)u; double v = vspk_get_num(pct) + 10; vspk_set_num(pct, v > 100 ? 100 : v); }
static void c_enviar(void *u)  {
    char t[512]; (void)u;
    snprintf(t, sizeof t, "nombre=%s  acepto=%s  color=%s", vspk_get_str(nombre), vspk_get_bool(acepto) ? "true" : "false", vspk_get_str(color));
    vspk_set_str(res, t);
    vspk_toast(app, "Enviado", "success", 3000);
}
static void got_file(const char *p, void *u) { char t[600]; (void)u; snprintf(t, sizeof t, "archivo: %s", p ? p : "(cancelado)"); vspk_set_str(arch, t); }
static void c_abrir(void *u)   { (void)u; vspk_pick_file(app, "Elige un archivo", got_file, NULL); }
static void c_titulo(void *u)  { (void)u; vspk_set_title(app, "Hola desde C"); }
static void c_notif(void *u)   { (void)u; vspk_notify(app, "C", "Hecho"); }
static void c_limpiar(void *u) { (void)u; vspk_cv_erase(lienzo); }
static void c_dibujar(void *u) { (void)u; vspk_cv_color(lienzo, "#00AA00"); vspk_cv_circle(lienzo, 150, 75, 20); }
static void m_abrir(void *u)   { (void)u; vspk_win_show(ajustes); }
static void m_cerrar(void *u)  { (void)u; vspk_win_close(ajustes); }
static void m_acerca(void *u)  { (void)u; vspk_set_str(lg, "acerca de"); }
static void on_mouse(const char *t, int x, int y, int b, void *u) { char s[64]; (void)b; (void)u; snprintf(s, sizeof s, "%s %d,%d", t, x, y); vspk_set_str(raton, s); }
static void on_name(const char *v, void *u) { (void)u; fprintf(stderr, "onChange nombre=%s\n", v); }
static void on_key(const char *k, const char *j, void *u) { char s[96]; (void)j; (void)u; snprintf(s, sizeof s, "tecla: %s", k); vspk_set_str(tecla, s); }
static int on_close(void *u) { (void)u; vspk_set_str(lg, "cerrando"); return 1; }
static int on_tick(void *u)  { (void)u; vspk_inc(ticks, 1); return 1; }

int main(void) {
    app    = vspk_app("Demo vspk", 520, 720);
    n      = vspk_state_int(app, "n", 0);
    pct    = vspk_state_int(app, "pct", 0);
    nombre = vspk_state_str(app, "nombre", "");
    acepto = vspk_state_bool(app, "acepto", 0);
    color  = vspk_state_str(app, "color", "azul");
    res    = vspk_state_str(app, "res", "—");
    vol    = vspk_state_int(app, "vol", 30);
    lg     = vspk_state_str(app, "log", "—");
    tecla  = vspk_state_str(app, "tecla", "—");
    ticks  = vspk_state_int(app, "ticks", 0);
    arch   = vspk_state_str(app, "arch", "—");
    raton  = vspk_state_str(app, "raton", "—");

    lienzo = vspk_canvas(app, "lienzo", 300, 150);
    vspk_cv_color(lienzo, "#6750A4"); vspk_cv_rect(lienzo, 10, 10, 100, 60);
    vspk_cv_color(lienzo, "#B3261E"); vspk_cv_circle(lienzo, 200, 60, 40);
    vspk_cv_color(lienzo, "#000000"); vspk_cv_line_width(lienzo, 2); vspk_cv_line(lienzo, 0, 0, 300, 150);
    vspk_cv_font(lienzo, 16); vspk_cv_text(lienzo, 10, 140, "Spork");
    vspk_cv_on_mouse(app, lienzo, on_mouse, NULL);
    vspk_on_change(nombre, on_name, NULL);

    ajustes = vspk_window(app, "Ajustes", 360, 240);
    vspk_win_add(ajustes, vspk_col(vspk_h4("Ajustes (otra ventana)"), vspk_input(nombre, "Tu nombre (compartido)"), vspk_p(vspk_ref(nombre))));

    const char *tarjeta = vspk_card(
        vspk_h2("Demo"),
        vspk_row(vspk_button_v(app, "-", "outlined", c_menos, NULL), vspk_h3(vspk_ref(n)), vspk_button(app, "+", c_mas, NULL)),
        vspk_input(nombre, "Nombre"), vspk_p(vspk_ref(nombre)),
        vspk_checkbox("Acepto", acepto),
        vspk_select(color, "azul", "Azul", "verde", "Verde", "rojo", "Rojo"), vspk_p(vspk_ref(color)),
        vspk_progress(pct, 100), vspk_button(app, "+10%", c_pct, NULL),
        vspk_slider(vol, 0, 100, 1),
        vspk_button(app, "Enviar", c_enviar, NULL),
        vspk_p(vspk_ref(res)),
        vspk_h4("9. Teclado, diálogos, temporizador, ventana"),
        vspk_p(vspk_ref(tecla)),
        vspk_row(vspk_p("ticks:"), vspk_h3(vspk_ref(ticks))),
        vspk_row(vspk_button(app, "Abrir archivo...", c_abrir, NULL), vspk_button(app, "Cambiar título", c_titulo, NULL), vspk_button_v(app, "Notificar", "outlined", c_notif, NULL)),
        vspk_p(vspk_ref(arch)),
        vspk_p(vspk_ref(lg)),
        vspk_h4("10. Canvas"),
        vspk_canvas_html(lienzo),
        vspk_p(vspk_ref(raton)),
        vspk_row(vspk_button_v(app, "Limpiar", "outlined", c_limpiar, NULL), vspk_button(app, "Dibujar", c_dibujar, NULL))
    );

    /* Los menús se crean después de la tarjeta (los ids de callback siguen el orden de creación). */
    const char *menu = vspk_menubar(
        vspk_menu("Archivo",
                  vspk_menu_item("Abrir ventana de ajustes", vspk_on_click(app, m_abrir, NULL), "ctrl+shift+a"),
                  vspk_menu_sep(),
                  vspk_menu_item("Cerrar ajustes", vspk_on_click(app, m_cerrar, NULL), "")),
        vspk_menu("Ayuda", vspk_menu_item("Acerca de", vspk_on_click(app, m_acerca, NULL), "")));
    vspk_add(app, menu, tarjeta);

    vspk_on_key(app, on_key, NULL);
    vspk_on_close(app, on_close, NULL);
    vspk_run_every(app, 1000, on_tick, NULL);
    vspk_run(app);
    puts("run() terminado");
    vspk_free(app);
    return 0;
}
