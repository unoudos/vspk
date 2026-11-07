package main

import (
	"encoding/xml"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"time"
)

type WeatherData struct {
	City           string `xml:"localidad>nombre"`
	PronosticoDias struct {
		Dias []DiaDatos `xml:"dia"`
	} `xml:"pronostico_dias"`
	PronosticoHoras struct {
		Horas []HoraDatos `xml:"hora"`
	} `xml:"pronostico_horas"`
}

type DiaDatos struct {
	Fecha       string `xml:"fecha"`
	FechaLarga  string `xml:"fecha_larga"`
	TempMaxima  string `xml:"temp_maxima"`
	TempMinima  string `xml:"temp_minima"`
	Icono       string `xml:"icono"`
	Texto       string `xml:"texto"`
	Humedad     string `xml:"humedad"`
	Viento      string `xml:"viento"`
	DirViento   string `xml:"dir_viento"`
	IcoFaseLuna string `xml:"ico_fase_luna"`
}

type HoraDatos struct {
	Temperatura string `xml:"temperatura"`
	Icono       string `xml:"icono"`
}

var client = &http.Client{Timeout: time.Second * 10}

func formatWeatherIconURL(ico string) string {
	ico = strings.TrimSpace(ico)
	if ico == "" { return "" }
	ico = strings.TrimSuffix(strings.TrimSuffix(ico, ".svg"), ".png")
	if strings.HasPrefix(ico, "http") { return ico }
	return fmt.Sprintf("https://v5i.tutiempo.net/wi/01/50/%s.png", ico)
}

func formatMoonIconURL(ico string) string {
	ico = strings.TrimSpace(ico)
	if ico == "" { return "" }
	ico = strings.TrimSuffix(strings.TrimSuffix(ico, ".svg"), ".png")
	if strings.HasPrefix(ico, "http") { return ico }
	return fmt.Sprintf("https://v5i.tutiempo.net/wmi/01/%s.png", ico)
}

// Img — imagen simple con id
func Img(id string, alt string) Widget {
	return Raw(fmt.Sprintf(
		`<img id="%s" alt="%s" src="" style="width:48px;height:48px;object-fit:contain;display:block;margin:8px auto;">`,
		id, alt,
	))
}

// ImgScript — igual que crypto.php: espera __vspk y carga imagenes via fetch nativo
func ImgScript() Widget {
	return Raw(`<script>
(function() {
	function loadImg(id, url) {
		if (!url) return;
		var el = document.getElementById(id);
		if (!el || el.dataset.loaded === url) return;
		el.dataset.loaded = url;
		// Igual que crypto.php usa __vspk.fetch() — proxy nativo sin CORS
		function tryLoad() {
			if (typeof __vspk !== 'undefined') {
				el.src = url; // WebView2 es Chromium, carga directa
			} else {
				setTimeout(tryLoad, 100);
			}
		}
		tryLoad();
	}

	// Interceptar window.__set para detectar cambios en img_dia / img_luna
	var _orig = window.__set;
	window.__set = function(k, v) {
		if (_orig) _orig(k, v);
		if (k === 'img_dia')  loadImg('img_dia',  v);
		if (k === 'img_luna') loadImg('img_luna', v);
	};

	// Cargar al conectar SSE (DOM listo)
	document.addEventListener('DOMContentLoaded', function() {
		var check = setInterval(function() {
			var s = window.__state || {};
			if (s.img_dia || s.img_luna) {
				clearInterval(check);
				loadImg('img_dia',  s.img_dia);
				loadImg('img_luna', s.img_luna);
			}
		}, 100);
	});
})();
</script>`)
}

func main() {
	app := New("Pronostico del Tiempo - Malaga", 450, 560, "white", "#0284c7")

	ciudad  := app.State("ciudad",  "Cargando clima...")
	fecha   := app.State("fecha",   "--")
	temp    := app.State("temp",    "--")
	maxMin  := app.State("maxmin",  "-- | --")
	humedad := app.State("humedad", "Humedad: --")
	viento  := app.State("viento",  "Viento: --")
	imgDia  := app.State("img_dia",  "")
	imgLuna := app.State("img_luna", "")

	updateUI := func(data *WeatherData) {
		if len(data.PronosticoDias.Dias) == 0 { return }
		primerDia  := data.PronosticoDias.Dias[0]
		tempActual := "N/A"
		if len(data.PronosticoHoras.Horas) > 0 {
			tempActual = data.PronosticoHoras.Horas[0].Temperatura
		}
		ciudad.Set(data.City)
		fecha.Set(primerDia.FechaLarga)
		temp.Set(fmt.Sprintf("Temperatura actual: %s C", tempActual))
		maxMin.Set(fmt.Sprintf("%s C | %s C", primerDia.TempMaxima, primerDia.TempMinima))
		humedad.Set(fmt.Sprintf("Humedad: %s%%", primerDia.Humedad))
		viento.Set(fmt.Sprintf("Viento: %s km/h - %s", primerDia.Viento, primerDia.DirViento))
		imgDia.Set(formatWeatherIconURL(primerDia.Icono))
		imgLuna.Set(formatMoonIconURL(primerDia.IcoFaseLuna))
	}

	data, _ := loadWeatherData()
	if data != nil { updateUI(data) }

	btnActualizar := app.OnClick(func() {
		ciudad.Set("Actualizando...")
		data2, err := loadWeatherData()
		if err != nil { ciudad.Set("Error de conexion"); return }
		updateUI(data2)
	})

	app.Add(Col(
		H1(ciudad),
		P(fecha),
		Hr(),
		Card(
			H2(temp),
			P(maxMin),
			Row(P(humedad), P(viento)),
		),
		Hr(),
		H3("Indicadores"),
		Row(
			Card(P("Fase Lunar"), Img("img_luna", "Fase Lunar")),
			Card(P("Dia"),        Img("img_dia",  "Icono del Dia")),
		),
		ImgScript(),
		Hr(),
		Button("Actualizar Pronostico", JS(btnActualizar), "filled"),
	))

	app.Run()
}

func loadWeatherData() (*WeatherData, error) {
	resp, err := client.Get("http://xml.tutiempo.net/xml/3589.xml")
	if err != nil { return nil, fmt.Errorf("error: %v", err) }
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return nil, errors.New("respuesta no valida")
	}
	var data WeatherData
	if err := xml.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, fmt.Errorf("error XML: %v", err)
	}
	return &data, nil
}
