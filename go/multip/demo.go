package main

import "fmt"

func num(v any) float64 {
	switch x := v.(type) {
	case int:
		return float64(x)
	case float64:
		return x
	}
	return 0
}

func main() {
	app := New("Demo vspk", 520, 720)
	n := app.State("n", 0)
	nombre := app.State("nombre", "")
	acepto := app.State("acepto", false)
	color := app.State("color", "azul")
	res := app.State("res", "—")
	logS := app.State("log", "—")
	tecla := app.State("tecla", "—")
	ticks := app.State("ticks", 0)
	arch := app.State("arch", "—")
	pct := app.State("pct", 0)
	raton := app.State("raton", "—")
	lienzo := app.Canvas("lienzo", 300, 150)
	lienzo.Color("#6750A4")
	lienzo.Rect(10, 10, 100, 60)
	lienzo.Color("#B3261E")
	lienzo.Circle(200, 60, 40)
	lienzo.Color("#000000")
	lienzo.LineWidth(2)
	lienzo.Line(0, 0, 300, 150)
	lienzo.Font(16)
	lienzo.Text(10, 140, "Spork")
	lienzo.OnMouse(func(e map[string]any) { raton.Set(fmt.Sprintf("%v %v,%v", e["type"], e["x"], e["y"])) })

	ajustes := app.NewWindow("Ajustes", 360, 240)
	ajustes.Add(Col(H4("Ajustes (otra ventana)"), Input("Tu nombre (compartido)", nombre), P(nombre)))

	tarjeta := Card(
		H2("Demo"),
		Row(
			app.Button("-", app.OnClick(func() { n.Set(int(num(n.Get())) - 1) }), "outlined"),
			H3(n),
			app.Button("+", app.OnClick(func() { n.Set(int(num(n.Get())) + 1) })),
		),
		Input("Nombre", nombre), P(nombre),
		Checkbox("Acepto", acepto),
		Select([][2]string{{"azul", "Azul"}, {"verde", "Verde"}, {"rojo", "Rojo"}}, color), P(color),
		Progress(pct),
		app.Button("+10%", app.OnClick(func() { pct.Set(int(num(pct.Get())) + 10) })),
		app.Button("Reiniciar", app.OnClick(func() { pct.Set(0); logS.Set("reiniciado") }), "outlined"),
		app.Button("Enviar", app.OnClick(func() {
			res.Set(fmt.Sprintf("nombre=%v  acepto=%v  color=%v", nombre.Get(), acepto.Get(), color.Get()))
		})),
		P(res),
		H4("9. Teclado, diálogos, temporizador, ventana"),
		P(tecla),
		Row(P("ticks:"), H3(ticks)),
		Row(
			app.Button("Abrir archivo...", app.OnClick(func() {
				app.PickFile("Elige un archivo", func(p string) { arch.Set("archivo: " + p) })
			})),
			app.Button("Cambiar título", app.OnClick(func() { app.SetTitle("Hola desde Go") })),
			app.Button("Notificar", app.OnClick(func() { app.Notify("Go", "Hecho") }), "outlined"),
		),
		P(arch), P(logS),
		H4("10. Canvas"),
		lienzo,
		P(raton),
		Row(
			app.Button("Limpiar", app.OnClick(func() { lienzo.Erase() }), "outlined"),
			app.Button("Dibujar", app.OnClick(func() { lienzo.Color("#00AA00"); lienzo.Circle(150, 75, 20) })),
		),
	)

	// Los menús se crean después de la tarjeta (los ids de callback siguen el orden de creación).
	menu := MenuBar(
		Menu("Archivo",
			MenuItem("Abrir ventana de ajustes", app.OnClick(func() { ajustes.Show() }), "ctrl+shift+a"),
			MenuSep(),
			MenuItem("Cerrar ajustes", app.OnClick(func() { ajustes.Close() })),
		),
		Menu("Ayuda", MenuItem("Acerca de", app.OnClick(func() { logS.Set("acerca de") }))),
	)
	app.Add(menu, tarjeta)
	app.OnKey(func(e map[string]any) { tecla.Set(fmt.Sprintf("tecla: %v", e["key"])) })
	app.OnClose(func() bool { logS.Set("cerrando"); return true })
	app.Every(1000, func() { ticks.Set(int(num(ticks.Get())) + 1) })
	app.Run()
}
