package main

import (
	"fmt"
	"time"
)

func main() {
	app := New("Demo vspk Go", 500, 720, "dark", "#7c3aed")

	count  := app.State("count",  0)
	nombre := app.State("nombre", "")
	plan   := app.State("plan",   "free")
	activo := app.State("activo", true)
	hora   := app.State("hora",   "00:00:00")

	// Reloj — goroutine actualiza estado en segundo plano
	go func() {
		for {
			hora.Set(time.Now().Format("15:04:05"))
			time.Sleep(time.Second)
		}
	}()

	// Callback Go puro — incrementar desde el servidor
	incBtn := app.OnClick(func() {
		n := count.Get().(int) + 1
		count.Set(n)
		fmt.Printf("[go] contador → %d\n", n)
	})

	// Evento desde JS
	app.OnEvent("greet", func(payload string) {
		fmt.Printf("[go] saludo recibido: %s\n", payload)
		app.EvalJS("window.__set('nombre','¡Hola desde Go!')")
	})

	app.Add(Col(
		H1("Demo vspk — Go"),
		P("GUI nativa para Go sin CGO"),
		Hr(),

		// Reloj — goroutine → SSE → WebView
		Card(
			H3("Reloj (goroutine → SSE → WebView)"),
			H2(hora),
		),
		Hr(),

		// Contador
		H2("Contador"),
		H1(count),
		Progress(count),
		Row(
			Button("+1 JS",    JS(count.Inc(1)),     "filled", "lg"),
			Button("+1 Go",    JS(incBtn),           "outlined"),
			Button("Reset",    JS(count.SetVal("0")), "danger", "sm"),
		),
		Hr(),

		// Input reactivo
		H2("Input reactivo"),
		Input("Escribe tu nombre...", nombre),
		H3(nombre),
		Hr(),

		// Select
		H2("Select"),
		Select([][2]string{
			{"free", "Plan Gratuito"},
			{"pro",  "Plan Pro"},
			{"biz",  "Plan Business"},
		}, plan),
		Alert(plan),
		Hr(),

		// Cards
		H2("Cards"),
		Card(
			Row(H3("Spork vspk"), Chip("v1.0", true), Chip("Beta", false)),
			P("GUI nativa para Go. Tauri pero con Go."),
			Row(
				Button("Docs",   "", "text"),
				Button("GitHub", "", "outlined", "sm"),
			),
		),
		Hr(),

		// Alertas
		H2("Alertas"),
		Alert("Todo correcto — operación completada."),
		Alert("¡Algo salió mal!", "error"),
		Hr(),

		// Checkbox
		H2("Checkbox"),
		Checkbox("Activar modo avanzado", activo),
	))

	app.Run()
}