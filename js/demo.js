import {
    App, Col, Row, Card,
    H1, H2, H3, P, Hr,
    Button, Input, Select, Checkbox,
    Alert, Progress, Chip, Badge,
} from "./vspk.js"

// ── Tema oscuro con color personalizado ───────────────────────────────────────
const app = new App("Demo vspk", {
    width:   500,
    height:  700,
    theme:   "dark",
    primary: "#7c3aed",
})

// ── Estado reactivo ───────────────────────────────────────────────────────────
const count    = app.state("count",    0)
const nombre   = app.state("nombre",   "")
const plan     = app.state("plan",     "free")
const progress = app.state("progress", 30)
const activo   = app.state("activo",   true)

// ── UI ────────────────────────────────────────────────────────────────────────
app.add(
    Col(

        // ── Cabecera ──────────────────────────────────────────────────────────
        H1("Demo vspk"),
        P("Todo lo que puedes hacer ahora"),

        Hr(),

        // ── Contador con variantes de botón ───────────────────────────────────
        H2("Contador"),
        H1(count),
        Progress(progress),
        Row(
            Button("+1",     { onClick: () => count.set(count.get() + 1), variant: "filled",   size: "lg" }),
            Button("Reset",  { onClick: () => count.set(0),               variant: "outlined" }),
            Button("Borrar", { onClick: () => count.set(-1),              variant: "danger",   size: "sm" }),
        ),

        Hr(),

        // ── Input con bind bidireccional ──────────────────────────────────────
        H2("Input reactivo"),
        Input({ bind: nombre, placeholder: "Escribe tu nombre..." }),
        H3(nombre),   // se actualiza mientras escribes

        Hr(),

        // ── Select ────────────────────────────────────────────────────────────
        H2("Select"),
        Select(
            [["free", "Plan Gratuito"],
             ["pro",  "Plan Pro"],
             ["biz",  "Plan Business"]],
            { bind: plan }
        ),
        Alert(plan),

        Hr(),

        // ── Cards y Chips ─────────────────────────────────────────────────────
        H2("Cards"),
        Card(
            Row(
                H3("Spork vspk"),
                Chip("v1.0", { primary: true }),
                Chip("Beta"),
            ),
            P("GUI nativa para Python y JS. Tauri pero más simple."),
            Row(
                Button("Docs",   { variant: "text" }),
                Button("GitHub", { variant: "outlined", size: "sm" }),
            ),
        ),

        Hr(),

        // ── Alertas ───────────────────────────────────────────────────────────
        H2("Alertas"),
        Alert("Todo correcto — operación completada."),
        Alert("¡Algo salió mal!", { variant: "error" }),

        Hr(),

        // ── Checkbox ──────────────────────────────────────────────────────────
        H2("Checkbox"),
        Checkbox("Activar modo avanzado", { bind: activo }),

    )
)

await app.run()
