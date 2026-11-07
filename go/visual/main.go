package main

import (
	"encoding/json"
	"fmt"
	"time"
)

func main() {
	// Inicializar la app con dimensiones de panel de control y tema oscuro con acento violeta/neón
	app := New("CyberDeck Studio", 1000, 680, "dark", "#7c3aed")

	// Estados reactivos para la UI (eliminado 'activeTab' si no se usaba, o lo puedes usar en un componente)
	searchQuery   := app.State("search", "")
	selectedMode  := app.State("mode", "turbo")
	cpuUsage      := app.State("cpu", 42)
	ramUsage      := app.State("ram", 68)
	terminalLog   := app.State("log", "[INFO] Sistema inicializado correctamente...\n[INFO] Esperando conexiones en puerto 8080...")
	notifications := app.State("notif_enabled", true)

	// Simulación de métricas en tiempo real desde Go (Goroutine)
	go func() {
		tick := 0
		for {
			time.Sleep(2 * time.Second)
			tick++
			
			// Variaciones simuladas de CPU y RAM
			simCpu := 30 + (tick * 7) % 45
			simRam := 60 + (tick * 3) % 25
			
			cpuUsage.Set(simCpu)
			ramUsage.Set(simRam)

			if tick%3 == 0 {
				terminalLog.Set(fmt.Sprintf("[INFO] Sincronización de paquetes OK (Ciclo %d)\n%s", tick, terminalLog.Get().(string)))
			}
		}
	}()

	// Manejador de eventos personalizado recibido desde JavaScript (corregido 'parseErr')
	app.OnEvent("action_click", func(payload string) {
		var data map[string]string
		if parseErr := json.Unmarshal([]byte(payload), &data); parseErr == nil {
			terminalLog.Set(fmt.Sprintf("[ACTION] Ejecutada orden: %s\n%s", data["name"], terminalLog.Get().(string)))
		}
	})

	// Construcción de la interfaz llamativa
	app.Add(
		// Barra superior / Cabecera con título y badges de estado
		Row(
			H2("⚡ CyberDeck OS"),
			Spacer(),
			Badge("v2.1-stable"),
			Badge("Go Backend"),
		),
		Hr(),

		// Sección de Estadísticas en Grid (Tarjetas de Rendimiento)
		Grid(
			Card(
				H4("Carga de CPU"),
				H2(cpuUsage),
				Progress(cpuUsage),
			),
			Card(
				H4("Memoria RAM"),
				H2(ramUsage),
				Progress(ramUsage),
			),
		),
		Spacer(),

		// Sección interactiva con Controles y Formularios
		Card(
			H3("Panel de Configuración Rápida"),
			P("Filtra y ajusta los parámetros del sistema en tiempo real:"),
			Spacer(),
			Row(
				Input("Escribe para buscar...", searchQuery),
				Select([][2]string{
					{"turbo", "Modo Turbo (Max Performance)"},
					{"eco", "Modo Eco (Ahorro energético)"},
					{"silent", "Modo Silencioso"},
				}, selectedMode),
			),
			Spacer(),
			Row(
				Checkbox("Activar notificaciones flotantes", notifications, true),
				Spacer(),
				// Botón que ejecuta JavaScript y comunica con Go mediante un evento personalizado
				app.Button("Ejecutar Diagnóstico", JS("fetch('/event/action_click?data=' + encodeURIComponent(JSON.stringify({name: 'Diagnóstico'})))"), "filled"),
			),
		),
		Spacer(),

		// Terminal de registros incrustada estilo retro-moderno
		Card(
			H4("Registro de Actividad (Live Stream)"),
			Spacer(),
			// Usamos Textarea de solo lectura simulando una consola
			Textarea("", 5, terminalLog),
		),
	)

	// Arrancar la aplicación nativa
	app.Run()
}