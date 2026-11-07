import sys, os, time, urllib.request, json, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
sys.path.insert(0, os.path.dirname(__file__))
import vspk

ISS_API  = "https://api.wheretheiss.at/v1/satellites/25544"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Servidor SSE ──────────────────────────────────────────────────────────────
sse_clients = []
sse_lock    = threading.Lock()

def push(data: dict):
    msg = "data: " + json.dumps(data) + "\n\n"
    with sse_lock:
        dead = []
        for c in sse_clients:
            try:
                c.wfile.write(msg.encode())
                c.wfile.flush()
            except:
                dead.append(c)
        for d in dead:
            sse_clients.remove(d)

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path == "/events":
            self.send_response(200)
            self.send_header("Content-Type",  "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with sse_lock:
                sse_clients.append(self)
            try:
                while True:
                    time.sleep(1)
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            except:
                with sse_lock:
                    if self in sse_clients:
                        sse_clients.remove(self)
        else:
            self.send_response(404)
            self.end_headers()

server = HTTPServer(("127.0.0.1", 0), Handler)
port   = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()

# Escribir puerto para que el .htv lo encuentre via asset server de vspk
port_file = os.path.join(BASE_DIR, ".iss_port")
with open(port_file, "w") as f:
    f.write(str(port))
print(f"[ISS] SSE en puerto {port}")

# ── Abrir ventana ─────────────────────────────────────────────────────────────
win = vspk.open("iss_tracker.htv")
print(f"[ISS] Ventana abierta — ID: {win.id}")

# ── Loop de datos ─────────────────────────────────────────────────────────────
def loop():
    while win.is_open():
        try:
            with urllib.request.urlopen(ISS_API, timeout=5) as r:
                d = json.loads(r.read())
            push({
                "type":       "iss",
                "lat":        d["latitude"],
                "lon":        d["longitude"],
                "alt":        d["altitude"],
                "vel":        d["velocity"],
                "visibility": d["visibility"],
            })
            print(f"[ISS] lat={d['latitude']:.2f} lon={d['longitude']:.2f} "
                  f"alt={d['altitude']:.1f}km vel={d['velocity']:.0f}km/h")
        except Exception as e:
            push({"type": "error", "msg": str(e)})
            print(f"[ISS] Error: {e}")
        time.sleep(2)

threading.Thread(target=loop, daemon=True).start()
win.wait()
server.shutdown()
try: os.remove(port_file)
except: pass
print("[ISS] Cerrado.")
