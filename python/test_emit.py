import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import vspk

win = vspk.open("test_emit.htv")
print(f"[Python] Ventana abierta — ID: {win.id}")

@win.on("boton_a")
def on_boton_a(payload):
    print(f"[Python] boton_a: {payload}")
    win.send({"respuesta": "Recibi boton_a!"})

@win.on("boton_b")
def on_boton_b(payload):
    print(f"[Python] boton_b: {payload}")
    win.send({"respuesta": f"Recibi boton_b ts={payload.get('ts')}"})

@win.on("texto")
def on_texto(payload):
    valor = payload.get("valor", "")
    print(f"[Python] texto: '{valor}'")
    win.send({"respuesta": f"Echo: {valor.upper()}"})

print("[Python] Esperando eventos...")
win.wait()
print("[Python] Ventana cerrada.")
