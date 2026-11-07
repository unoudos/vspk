import vspk

app = vspk.App("Contador", width=400, height=300)

count = app.state("count", 0)

app.add(
    vspk.Col(
        vspk.H1(count),
        vspk.Row(
            vspk.Button("+1", on_click=lambda: count.set(count.get() + 1)),
            vspk.Button("Reset", on_click=lambda: count.set(0)),
        ),
    )
)

app.run()