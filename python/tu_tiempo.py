import threading
import urllib.request
import xml.etree.ElementTree as ET
import vspk

XML_URL = "http://xml.tutiempo.net/xml/3589.xml"

def format_weather_icon(ico: str) -> str:
    ico = ico.strip().removesuffix(".svg").removesuffix(".png")
    if ico.startswith("http"): return ico
    return f"https://v5i.tutiempo.net/wi/01/50/{ico}.png"

def format_moon_icon(ico: str) -> str:
    ico = ico.strip().removesuffix(".svg").removesuffix(".png")
    if ico.startswith("http"): return ico
    return f"https://v5i.tutiempo.net/wmi/01/{ico}.png"

def load_weather():
    try:
        with urllib.request.urlopen(XML_URL, timeout=10) as r:
            root = ET.parse(r).getroot()
        return (
            root.findtext("localidad/nombre") or "",
            root.findall("pronostico_dias/dia"),
            root.findall("pronostico_horas/hora"),
        )
    except Exception:
        return None, [], []

# ── App ───────────────────────────────────────────────────────────────────────

app = vspk.App("Pronóstico del Tiempo - Málaga",
               width=450, height=560,
               theme="light", primary="#0284c7")

ciudad  = app.state("ciudad",  "Cargando clima...")
fecha   = app.state("fecha",   "--")
temp    = app.state("temp",    "--")
maxmin  = app.state("maxmin",  "-- | --")
humedad = app.state("humedad", "Humedad: --")
viento  = app.state("viento",  "Viento: --")
img_dia  = app.state("img_dia",  "")
img_luna = app.state("img_luna", "")

def update_ui(ciudad_str, dias, horas):
    if not dias: return
    d = dias[0]
    temp_actual = horas[0].findtext("temperatura") or "N/A" if horas else "N/A"
    ciudad.set(ciudad_str)
    fecha.set(d.findtext("fecha_larga") or "--")
    temp.set(f"Temperatura actual: {temp_actual} °C")
    maxmin.set(f"{d.findtext('temp_maxima')} °C  |  {d.findtext('temp_minima')} °C")
    humedad.set(f"Humedad: {d.findtext('humedad')}%")
    viento.set(f"Viento: {d.findtext('viento')} km/h - {d.findtext('dir_viento')}")
    img_dia.set(format_weather_icon(d.findtext("icono") or ""))
    img_luna.set(format_moon_icon(d.findtext("ico_fase_luna") or ""))

def fetch_weather():
    c, dias, horas = load_weather()
    if c is None:
        ciudad.set("Error de conexión")
        return
    update_ui(c, dias, horas)

def on_actualizar():
    ciudad.set("Actualizando...")
    threading.Thread(target=fetch_weather, daemon=True).start()

# Carga inicial
c0, dias0, horas0 = load_weather()
if c0:
    update_ui(c0, dias0, horas0)

# ── UI ────────────────────────────────────────────────────────────────────────

app.add(
    vspk.Col(
        vspk.H1(ciudad),
        vspk.P(fecha),
        vspk.Hr(),
        vspk.Card(
            vspk.H2(temp),
            vspk.P(maxmin),
            vspk.Row(vspk.P(humedad), vspk.P(viento)),
        ),
        vspk.Hr(),
        vspk.H3("Indicadores"),
        vspk.Row(
            vspk.Card(vspk.P("🌙 Fase Lunar"), vspk.ImgState("img_luna", "Fase Lunar")),
            vspk.Card(vspk.P("☀ Día"),         vspk.ImgState("img_dia",  "Icono del Día")),
        ),
        vspk.ImgScript(),
        vspk.Hr(),
        vspk.Button("Actualizar Pronóstico", on_click=on_actualizar, variant="filled"),
    )
)

app.run()
