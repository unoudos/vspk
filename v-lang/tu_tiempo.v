// tu_tiempo.v — Pronóstico del tiempo con vspk.v
// Equivalente a tu_tiempo.spk, corriendo fuera del WebView.
//
// NOTA sobre el XML: V no trae un parser XML→objeto nativo como el
// bun.XML.parse() que usa la versión .spk. En vez de meter una dependencia
// de regex/XML solo para esto, aprovecho que la app solo usa SIEMPRE el
// primer <dia> y la primera <hora> (igual que hace update_ui en el
// original) y extraigo esos bloques con slicing de strings simple
// (all_after/all_before). Es menos general que un parser real — si algún
// día necesitas el array completo de días/horas, ahí sí conviene meter
// una lib XML de verdad.
module main

import vspk
import net.http
import x.json2 as json

#flag windows @VMODROOT/icon_res.o

const xml_url = 'http://xml.tutiempo.net/xml/3589.xml'

// ── Formateo de iconos ───────────────────────────────────────────────────

fn format_weather_icon(ico string) string {
	if ico.starts_with('http') {
		return ico
	}
	clean := ico.trim_space().replace('.svg', '').replace('.png', '')
	return 'https://v5i.tutiempo.net/wi/01/50/${clean}.png'
}

fn format_moon_icon(ico string) string {
	if ico.starts_with('http') {
		return ico
	}
	clean := ico.trim_space().replace('.svg', '').replace('.png', '')
	return 'https://v5i.tutiempo.net/wmi/01/${clean}.png'
}

// ── Extracción XML mínima (ver nota arriba) ───────────────────────────────

fn tag_content(src string, t string) string {
	open := '<${t}>'
	close := '</${t}>'
	if !src.contains(open) || !src.contains(close) {
		return ''
	}
	return src.all_after(open).all_before(close).trim_space()
}

// ── Imágenes reactivas (img_dia / img_luna) ───────────────────────────────
// Igual que en la versión .spk: el <img> arranca vacío y un script propio
// intercepta window.__set para asignar el src directo vía WebView2 una vez
// que __vspk está disponible, sin pasar por el mecanismo genérico spork.js.

fn img_tag(id string, alt string) string {
	return '<img id="${id}" alt="${vspk.html_escape(alt)}" src="" style="width:48px;height:48px;object-fit:contain;display:block;margin:8px auto;">'
}

fn img_script() string {
	return '<script>
(function() {
  function loadImg(id, url) {
    if (!url) return;
    var el = document.getElementById(id);
    if (!el || el.dataset.loaded === url) return;
    el.dataset.loaded = url;
    function tryLoad() {
      if (typeof __vspk !== "undefined") {
        el.src = url;
      } else {
        setTimeout(tryLoad, 100);
      }
    }
    tryLoad();
  }

  var _orig = window.__set;
  window.__set = function(k, v) {
    if (_orig) _orig(k, v);
    if (k === "img_dia")  loadImg("img_dia",  v);
    if (k === "img_luna") loadImg("img_luna", v);
  };

  document.addEventListener("DOMContentLoaded", function() {
    var check = setInterval(function() {
      var s = window.__state || {};
      if (s.img_dia || s.img_luna) {
        clearInterval(check);
        loadImg("img_dia",  s.img_dia);
        loadImg("img_luna", s.img_luna);
      }
    }, 100);
  });
})();
</script>'
}

// ── Carga del XML ──────────────────────────────────────────────────────────

struct WeatherData {
	ok         bool
	error      string
	localidad  string
	fecha      string
	temp_max   string
	temp_min   string
	humedad    string
	viento     string
	dir_viento string
	icono      string
	luna       string
	temp_hora  string
}

fn load_weather() WeatherData {
	resp := http.get(xml_url) or { return WeatherData{ok: false, error: err.msg()} }
	if resp.status_code != 200 {
		return WeatherData{
			ok:    false
			error: 'HTTP ${resp.status_code}'
		}
	}
	xml := resp.body

	localidad_block := tag_content(xml, 'localidad')
	dias_block := tag_content(xml, 'pronostico_dias')
	dia := tag_content(dias_block, 'dia')
	horas_block := tag_content(xml, 'pronostico_horas')
	hora := tag_content(horas_block, 'hora')

	return WeatherData{
		ok:         true
		localidad:  tag_content(localidad_block, 'nombre')
		fecha:      tag_content(dia, 'fecha_larga')
		temp_max:   tag_content(dia, 'temp_maxima')
		temp_min:   tag_content(dia, 'temp_minima')
		humedad:    tag_content(dia, 'humedad')
		viento:     tag_content(dia, 'viento')
		dir_viento: tag_content(dia, 'dir_viento')
		icono:      tag_content(dia, 'icono')
		luna:       tag_content(dia, 'ico_fase_luna')
		temp_hora:  tag_content(hora, 'temperatura')
	}
}

// ── UI reactiva ─────────────────────────────────────────────────────────

struct Ui {
mut:
	ciudad   vspk.State
	fecha    vspk.State
	temp     vspk.State
	maxmin   vspk.State
	humedad  vspk.State
	viento   vspk.State
	img_dia  vspk.State
	img_luna vspk.State
}

fn update_ui(mut ui Ui, data WeatherData) {
	if data.fecha == '' && data.temp_max == '' {
		return
	}
	temp_actual := if data.temp_hora != '' { data.temp_hora } else { 'N/A' }

	ui.ciudad.set(json.Any(data.localidad))
	ui.fecha.set(json.Any(if data.fecha != '' { data.fecha } else { '--' }))
	ui.temp.set(json.Any('Temperatura actual: ${temp_actual} °C'))
	ui.maxmin.set(json.Any('${data.temp_max} °C  |  ${data.temp_min} °C'))
	ui.humedad.set(json.Any('Humedad: ${data.humedad}%'))
	ui.viento.set(json.Any('Viento: ${data.viento} km/h - ${data.dir_viento}'))
	ui.img_dia.set(json.Any(format_weather_icon(data.icono)))
	ui.img_luna.set(json.Any(format_moon_icon(data.luna)))
}

fn fetch_weather(mut ui Ui) {
	data := load_weather()
	if !data.ok {
		ui.ciudad.set(json.Any('Error: ${data.error}'))
		return
	}
	update_ui(mut ui, data)
}

// ── main ───────────────────────────────────────────────────────────────

fn main() {
	mut app := vspk.new_app('Pronóstico del Tiempo - Málaga', 450, 560, 'light', '#0284c7')

	mut ui := Ui{
		ciudad:   app.state('ciudad', json.Any('Cargando clima...'))
		fecha:    app.state('fecha', json.Any('--'))
		temp:     app.state('temp', json.Any('--'))
		maxmin:   app.state('maxmin', json.Any('-- | --'))
		humedad:  app.state('humedad', json.Any('Humedad: --'))
		viento:   app.state('viento', json.Any('Viento: --'))
		img_dia:  app.state('img_dia', json.Any(''))
		img_luna: app.state('img_luna', json.Any(''))
	}

	// Carga inicial (antes de arrancar el servidor)
	data0 := load_weather()
	if data0.ok {
		update_ui(mut ui, data0)
	} else {
		ui.ciudad.set(json.Any('Error: ${data0.error}'))
	}

	app.add(vspk.col(vspk.h1(ui.ciudad.to_html()), vspk.p(ui.fecha.to_html()), vspk.hr(),
		vspk.card(vspk.h2(ui.temp.to_html()), vspk.p(ui.maxmin.to_html()), vspk.row(vspk.p(ui.humedad.to_html()),
		vspk.p(ui.viento.to_html()))), vspk.hr(), vspk.h3('Indicadores'),
		vspk.row(vspk.card(vspk.p('🌙 Fase Lunar'), img_tag('img_luna', 'Fase Lunar')), vspk.card(vspk.p('☀ Día'),
		img_tag('img_dia', 'Icono del Día'))), img_script(), vspk.hr(),
		vspk.button('Actualizar Pronóstico', app.on_click(fn [mut ui] () {
		fetch_weather(mut ui)
	}), 'filled', '')))

	app.run() or { eprintln('vspk error: ${err}') }
}
