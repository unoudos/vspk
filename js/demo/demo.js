import { App, Card, Col, Row, H2, H3, H4, P, Input, Checkbox, Select, Progress, Slider, MenuBar, Menu, MenuItem, MenuSep, Button } from "./vspk.js"

const app    = new App("Demo vspk", { width: 520, height: 720 })
const n      = app.state("n", 0)
const pct    = app.state("pct", 0)
const nombre = app.state("nombre", "")
const acepto = app.state("acepto", false)
const color  = app.state("color", "azul")
const res    = app.state("res", "—")
const vol    = app.state("vol", 30)
const log    = app.state("log", "—")
const tecla  = app.state("tecla", "—")
const ticks  = app.state("ticks", 0)
const arch   = app.state("arch", "—")
const raton  = app.state("raton", "—")

const lienzo = app.canvas("lienzo", 300, 150)
lienzo.color("#6750A4").rect(10, 10, 100, 60)
lienzo.color("#B3261E").circle(200, 60, 40)
lienzo.color("#000000").lineWidth(2).line(0, 0, 300, 150)
lienzo.font(16).text(10, 140, "Spork")
lienzo.onMouse(e => raton.set(`${e.type} ${e.x},${e.y}`))
nombre.onChange(v => console.error(`onChange nombre=${v}`))

const enviar = () => {
    res.set(`nombre=${nombre.get()}  acepto=${acepto.get() ? "true" : "false"}  color=${color.get()}`)
    app.toast("Enviado", "success")
}

const ajustes = app.window("Ajustes", 360, 240)
ajustes.add(Col(H4("Ajustes (otra ventana)"), Input({ placeholder: "Tu nombre (compartido)", bind: nombre }), P(nombre)))

const tarjeta = Card(
    H2("Demo"),
    Row(Button("-", { onClick: () => n.dec(), variant: "outlined" }), H3(n), Button("+", { onClick: () => n.inc() })),
    Input({ placeholder: "Nombre", bind: nombre }), P(nombre),
    Checkbox("Acepto", { bind: acepto }),
    Select([["azul", "Azul"], ["verde", "Verde"], ["rojo", "Rojo"]], { bind: color }), P(color),
    Progress(pct), Button("+10%", { onClick: () => pct.set(Math.min(100, pct.get() + 10)) }),
    Slider({ bind: vol }),
    Button("Enviar", { onClick: enviar }),
    Button("Boom", { onClick: () => { throw new Error("prueba") } }),
    P(res),
    H4("9. Teclado, diálogos, temporizador, ventana"),
    P(tecla),
    Row(P("ticks:"), H3(ticks)),
    Row(
        Button("Abrir archivo...", { onClick: () => app.pickFile("Elige un archivo", p => arch.set(`archivo: ${p}`)) }),
        Button("Cambiar título", { onClick: () => app.setTitle("Hola desde Bun") }),
        Button("Notificar", { onClick: () => app.notify("Bun", "Hecho"), variant: "outlined" }),
    ),
    P(arch),
    P(log),
    H4("10. Canvas"),
    lienzo,
    P(raton),
    Row(
        Button("Limpiar", { onClick: () => lienzo.erase(), variant: "outlined" }),
        Button("Dibujar", { onClick: () => lienzo.color("#00AA00").circle(150, 75, 20) }),
    ),
)

// Los menús van al final: los ids de callback siguen el orden de creación.
const menu = MenuBar(
    Menu("Archivo",
        MenuItem("Abrir ventana de ajustes", app.onClick(() => ajustes.show()), "ctrl+shift+a"),
        MenuSep(),
        MenuItem("Cerrar ajustes", app.onClick(() => ajustes.close()))),
    Menu("Ayuda", MenuItem("Acerca de", app.onClick(() => log.set("acerca de")))),
)
app.add(menu, tarjeta)

app.onKey(e => tecla.set("tecla: " + e.key))
app.onClose(() => { log.set("cerrando"); return true })
app.runEvery(1000, () => ticks.inc())
await app.run()
console.log("run() terminado")
