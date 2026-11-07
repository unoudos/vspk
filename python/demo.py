import vspk

app = vspk.App("Demo vspk", width=500, height=700, theme="white", primary="#7c3aed")

count    = app.state("count",    0)
nombre   = app.state("nombre",   "")
plan     = app.state("plan",     "free")
activo   = app.state("activo",   True)

app.add(
    vspk.Col(
        vspk.H1("Demo vspk"),
        vspk.P("Todo lo que puedes hacer ahora"),
        vspk.Hr(),

        vspk.H2("Contador"),
        vspk.H1(count),
        vspk.Progress(count),   # barra reactiva ligada a count
        vspk.Row(
            vspk.Button("+1",    on_click=lambda: count.set(count.get() + 1), variant="filled",   size="lg"),
            vspk.Button("Reset", on_click=lambda: count.set(0),               variant="outlined"),
            vspk.Button("-1",    on_click=lambda: count.set(count.get() - 1), variant="danger",   size="sm"),
        ),
        vspk.Hr(),

        vspk.H2("Input reactivo"),
        vspk.Input(bind=nombre, placeholder="Escribe tu nombre..."),
        vspk.H3(nombre),
        vspk.Hr(),

        vspk.H2("Select"),
        vspk.Select(
            [("free","Plan Gratuito"), ("pro","Plan Pro"), ("biz","Plan Business")],
            bind=plan,
        ),
        vspk.Alert(plan),
        vspk.Hr(),

        vspk.H2("Cards"),
        vspk.Card(
            vspk.Row(
                vspk.H3("Spork vspk"),
                vspk.Chip("v1.0", primary=True),
                vspk.Chip("Beta"),
            ),
            vspk.P("GUI nativa para Python. Tauri pero con Python."),
            vspk.Row(
                vspk.Button("Docs",   variant="text"),
                vspk.Button("GitHub", variant="outlined", size="sm"),
            ),
        ),
        vspk.Hr(),

        vspk.H2("Alertas"),
        vspk.Alert("Todo correcto — operación completada."),
        vspk.Alert("¡Algo salió mal!", variant="error"),
        vspk.Hr(),

        vspk.H2("Checkbox"),
        vspk.Checkbox("Activar modo avanzado", bind=activo),
    )
)

app.run()
