package main

import (
	"fmt"
	"time"
)

func main() {
	// Inicializar la aplicación con título y dimensiones
	app := New("Monitor del Sistema Go", 900, 600, "dark", "#5c5cff")

	// Estados reactivos
	counter := app.State("counter", 0)
	statusText := app.State("status", "Sistema listo y operativo")
	progressVal := app.State("progress", 25)

	// Simular una tarea en segundo plano que actualiza el estado de forma segura
	go func() {
		for i := 25; i <= 100; i += 15 {
			time.Sleep(2 * time.Second)
			progressVal.Set(i)
			statusText.Set(fmt.Sprintf("Progreso actual: %d%%", i))
		}
		statusText.Set("¡Tarea completada con éxito!")
	}()

	// Construir la interfaz de usuario usando widgets declarativos
	app.Add(
		Card(
			H1("Panel de Control vspk"),
			P(statusText), // Se actualiza reactivamente de forma automática
			Hr(),
			Row(
				Badge("Go + Rust"),
				Badge("WebView Nativo"),
			),
		),
		Spacer(),
		Card(
			H3("Contador Interactivo"),
			H1(counter),
			Row(
				app.Button("Decrementar", counter.Dec(1), "outlined"),
				app.Button("Reiniciar", counter.SetVal("0"), "danger"),
				app.Button("Incrementar", counter.Inc(1), "filled"),
			),
		),
		Spacer(),
		Card(
			H4("Progreso de Tarea Asíncrona"),
			Progress(progressVal),
		),
	)

	// Arrancar la aplicación de escritorio
	app.Run()
}