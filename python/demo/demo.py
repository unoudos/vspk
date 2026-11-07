import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vspk
from vspk import (Card, Col, Row, H2, H3, H4, P, Input, Checkbox, Select, Progress, Slider,
                  MenuBar, Menu, MenuItem, MenuSep)

app    = vspk.App("Demo vspk", width=520, height=720)
n      = app.state("n", 0)
pct    = app.state("pct", 0)
nombre = app.state("nombre", "")
acepto = app.state("acepto", False)
color  = app.state("color", "azul")
res    = app.state("res", "—")
vol    = app.state("vol", 30)
log    = app.state("log", "—")
tecla  = app.state("tecla", "—")
ticks  = app.state("ticks", 0)
arch   = app.state("arch", "—")
raton  = app.state("raton", "—")

lienzo = app.canvas("lienzo", 300, 150)
lienzo.color("#6750A4").rect(10, 10, 100, 60)
lienzo.color("#B3261E").circle(200, 60, 40)
lienzo.color("#000000").line_width(2).line(0, 0, 300, 150)
lienzo.font(16).text(10, 140, "Spork")
lienzo.on_mouse(lambda e: raton.set(f"{e['type']} {e['x']},{e['y']}"))
nombre.on_change(lambda v: print(f"onChange nombre={v}", file=sys.stderr, flush=True))

def enviar():
    res.set(f"nombre={nombre.get()}  acepto={'true' if acepto.get() else 'false'}  color={color.get()}")
    app.toast("Enviado", "success")

def boom():
    raise RuntimeError("prueba")

ajustes = app.window("Ajustes", 360, 240)
ajustes.add(Col(H4("Ajustes (otra ventana)"), Input(placeholder="Tu nombre (compartido)", bind=nombre), P(nombre)))

tarjeta = Card(
    H2("Demo"),
    Row(app.Button("-", on_click=lambda: n.dec(), variant="outlined"), H3(n), app.Button("+", on_click=lambda: n.inc())),
    Input(placeholder="Nombre", bind=nombre), P(nombre),
    Checkbox("Acepto", bind=acepto),
    Select([("azul", "Azul"), ("verde", "Verde"), ("rojo", "Rojo")], bind=color), P(color),
    Progress(pct), app.Button("+10%", on_click=lambda: pct.set(min(100, pct.get() + 10))),
    Slider(vol),
    app.Button("Enviar", on_click=enviar),
    app.Button("Boom", on_click=boom),
    P(res),
    H4("9. Teclado, diálogos, temporizador, ventana"),
    P(tecla),
    Row(P("ticks:"), H3(ticks)),
    Row(
        app.Button("Abrir archivo...", on_click=lambda: app.pick_file("Elige un archivo", lambda p: arch.set(f"archivo: {p}"))),
        app.Button("Cambiar título", on_click=lambda: app.set_title("Hola desde Python")),
        app.Button("Notificar", on_click=lambda: app.notify("Python", "Hecho"), variant="outlined"),
    ),
    P(arch),
    P(log),
    H4("10. Canvas"),
    lienzo,
    P(raton),
    Row(
        app.Button("Limpiar", on_click=lambda: lienzo.erase(), variant="outlined"),
        app.Button("Dibujar", on_click=lambda: lienzo.color("#00AA00").circle(150, 75, 20)),
    ),
)

# Los menús se crean después de la tarjeta (los ids de callback siguen el orden de creación).
menu = MenuBar(
    Menu("Archivo",
         MenuItem("Abrir ventana de ajustes", app.on_click(lambda: ajustes.show()), "ctrl+shift+a"),
         MenuSep(),
         MenuItem("Cerrar ajustes", app.on_click(lambda: ajustes.close()))),
    Menu("Ayuda", MenuItem("Acerca de", app.on_click(lambda: log.set("acerca de")))),
)
app.add(menu, tarjeta)

app.on_key(lambda e: tecla.set("tecla: " + e["key"]))
def cerrar():
    log.set("cerrando")
    return True
app.on_close(cerrar)
app.run_every(1000, lambda: ticks.inc())
app.run()
print("run() terminado")
