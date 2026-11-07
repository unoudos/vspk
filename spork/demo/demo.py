# Generado por Spork → target Python

import sys
import os
import json
import math
import random
import time


# ── lib: vspk.spk ──────────────────────────────────────────
# Generado por Spork → target Python

import sys
import os
import json
import math
import random
import time


class _SpkHash(dict):
    def __getattribute__(self, key):
        if key[:2] != '__' and dict.__contains__(self, key): return dict.__getitem__(self, key)
        return dict.__getattribute__(self, key)
    def __getattr__(self, key):
        try: return self[key]
        except KeyError: raise AttributeError(key)
    def __setattr__(self, key, val): self[key] = val

# ── filesystem ───────────────────────────────────────────────────────
import os as _os, shutil as _shu

def _spk_f_write(p, s): open(p, 'w', encoding='utf-8').write(s)

def _spk_f_delete(p):   _os.remove(p)

# ── path utils ───────────────────────────────────────────────────────
def _spk_path_join(*parts): return _os.path.join(*parts)

def _spk_path_dir(p):  return _os.path.dirname(p)

# ── vspk: primitivas del runtime que usa vspk.spk compilado ─────────
import sys as _vsys, shutil as _vshutil, subprocess as _vsub, tempfile as _vtmp

import threading as _vthr, queue as _vq, json as _vjson

from http.server import ThreadingHTTPServer as _VSrv, BaseHTTPRequestHandler as _VHandler

def _spk_try(f, g):
    try: return f()
    except Exception: return g()

def _spk_has(o, k): return k in o

def _spk_i(x): return 'true' if x is True else ('false' if x is False else x)

def _spk_has_m(o, m): return (m in o) if isinstance(o, dict) else hasattr(o, m)

def _spk_m(o, m, *a):
    if _spk_has_m(o, m): return getattr(o, m)(*a)
    return globals()[m](o, *a)

def type_of(x):
    if x is None: return "nil"
    if isinstance(x, bool): return "bool"
    if isinstance(x, int): return "int"
    if isinstance(x, float): return "float"
    if isinstance(x, str): return "string"
    if isinstance(x, (list, tuple)): return "array"
    if isinstance(x, dict): return "hash"
    if callable(x): return "function"
    return "object"

def platform(): return _vsys.platform

def env(k, d=""): return _os.environ.get(k, d)

def f_exists_q(p): return _os.path.exists(p)

def which(x): return _vshutil.which(x) or ""

def temp_file(prefix="", suffix=""):
    fd, p = _vtmp.mkstemp(prefix=prefix, suffix=suffix)
    _os.close(fd)
    return p

class _SpkProc:
    def __init__(self, p): self._p = p
    def exited(self): return self._p.poll() is not None

def spawn(cmd): return _SpkProc(_vsub.Popen(list(cmd)))

_vb_msgs = _vq.Queue()

_vb_sse = []

def vspk_bridge_start(port):
    class _H(_VHandler):
        protocol_version = 'HTTP/1.0'
        def log_message(self, *a): pass
        def _head(self, code, ctype='text/plain'):
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', '*')
            self.end_headers()
        def do_OPTIONS(self):
            self._head(204)
        def do_POST(self):
            if self.path.startswith('/event/'):
                n = int(self.headers.get('Content-Length') or 0)
                body = self.rfile.read(n).decode('utf-8', errors='replace') if n else ''
                _vb_msgs.put(_SpkHash({"kind": "event", "name": self.path[7:].split('?')[0], "body": body}))
                self._head(200)
                self.wfile.write(b'ok')
            else:
                self._head(404)
        def do_GET(self):
            if self.path == '/events':
                self._head(200, 'text/event-stream')
                self.wfile.write(b': ' + b' ' * 2048 + b'\n\n')
                self.wfile.flush()
                q = _vq.Queue()
                _vb_sse.append(q)
                try:
                    while True:
                        try:
                            msg = q.get(timeout=15)
                            self.wfile.write(msg.encode('utf-8')); self.wfile.flush()
                        except _vq.Empty:
                            self.wfile.write(b': ping\n\n'); self.wfile.flush()
                except Exception:
                    pass
                finally:
                    try: _vb_sse.remove(q)
                    except ValueError: pass
            elif self.path.startswith('/cb/'):
                _vb_msgs.put(_SpkHash({"kind": "cb", "id": self.path[4:].split('?')[0]}))
                self._head(200)
                self.wfile.write(b'ok')
            elif self.path == '/favicon.ico':
                self._head(204)
            else:
                self._head(404)
    srv = _VSrv(('127.0.0.1', port), _H)
    srv.daemon_threads = True
    _vthr.Thread(target=srv.serve_forever, daemon=True).start()
    return srv

def vspk_bridge_push_sse(msg):
    for q in list(_vb_sse):
        try: q.put_nowait(msg)
        except Exception: pass

def vspk_bridge_poll():
    try: return _vb_msgs.get_nowait()
    except _vq.Empty: return None

def _spk_script_dir():
    try:
        import inspect as _ins
        f = _ins.stack()[-1].filename
        return _os.path.dirname(_os.path.abspath(f)) if f != '<string>' else _os.getcwd()
    except Exception:
        return _os.getcwd()

_spk_import = _SpkHash({"meta": _SpkHash({"dir": _spk_script_dir(), "main": True})})


def find_vspk():
    exe = ("vspk.exe" if platform() == "win32" else "vspk")
    from_env = env("VSPK_EXE")
    if from_env != "" and f_exists_q(from_env):
        return from_env
    beside_script = _spk_path_join(_spk_path_dir(_spk_import.meta.dir), exe)
    if f_exists_q(beside_script):
        return beside_script
    beside_lib = _spk_path_join(_spk_import.meta.dir, exe)
    if f_exists_q(beside_lib):
        return beside_lib
    in_path = which(exe)
    if in_path != "":
        return in_path
    return exe

def html_escape(s):
    return str.replace(str.replace(str.replace(str.replace(s, "&", "&amp;"), "<", "&lt;"), ">", "&gt;"), "\"", "&quot;")

def tag(t, css_class, attrs, *kids):
    cls_attr = (f""" class=\"{_spk_i(css_class)}\"""" if css_class != "" else "")
    def _closureL1(kv):
        k = kv[0]
        v = kv[1]
        if k == "onclick" or k == "oninput" or k == "onchange":
            return f""" {_spk_i(k)}=\"{_spk_i(str.replace(v, "\"", "&quot;"))}\""""
        else:
            return f""" {_spk_i(k)}=\"{_spk_i(html_escape(v))}\""""
    attrs_str = ("").join(str(x) for x in list(map(_closureL1, list(attrs.items()))))
    inner = ("\n").join(str(x) for x in list(map(lambda c: (_spk_m(c, 'to_html') if (type_of(c) == "hash" or type_of(c) == "object") and c.to_html else f"""{_spk_i(c)}"""), kids)))
    _spk_void = t == "input" or t == "hr" or t == "br"
    if _spk_void:
        return f"""<{_spk_i(t)}{_spk_i(cls_attr)}{_spk_i(attrs_str)}>"""
    else:
        if inner == "":
            return f"""<{_spk_i(t)}{_spk_i(cls_attr)}{_spk_i(attrs_str)}></ {_spk_i(t)}>"""
        else:
            return f"""<{_spk_i(t)}{_spk_i(cls_attr)}{_spk_i(attrs_str)}>\n{_spk_i(inner)}\n</{_spk_i(t)}>"""

def Row(*kids):
    return tag("div", "sz-row", _SpkHash({}), *kids)

def Col(*kids):
    return tag("div", "sz-col sz-center", _SpkHash({}), *kids)

def Card(*kids):
    return tag("div", "sz-card", _SpkHash({}), *kids)

def Grid(*kids):
    return tag("div", "sz-grid", _SpkHash({}), *kids)

def Hr():
    return "<hr class=\"sz-divider\">"

def Spacer():
    return "<div class=\"sz-grow\"></div>"

def H1(c):
    return tag("h1", "sz-h1", _SpkHash({}), c)

def H2(c):
    return tag("h2", "sz-h2", _SpkHash({}), c)

def H3(c):
    return tag("h3", "sz-h3", _SpkHash({}), c)

def H4(c):
    return tag("h4", "sz-h4", _SpkHash({}), c)

def P(c):
    return tag("p", "sz-p", _SpkHash({}), c)

def Label(c):
    return tag("label", "sz-label", _SpkHash({}), c)

def Badge(c):
    return tag("span", "sz-badge", _SpkHash({}), c)

def Chip(text, primary = False):
    css_class = ("sz-chip sz-chip-primary" if primary else "sz-chip")
    return tag("span", css_class, _SpkHash({}), text)

def Alert(c, variant = ""):
    css_class = (f"""sz-alert sz-alert-{_spk_i(variant)}""" if variant != "" else "sz-alert")
    return tag("div", css_class, _SpkHash({}), c)

def Button(text, js = "", variant = "filled", size = ""):
    css_class = f"""sz-btn sz-btn-{_spk_i(variant)}{_spk_i((f""" sz-btn-{_spk_i(size)}""" if size != "" else ""))}"""
    attrs = (_SpkHash({"data-ripple": "", "onclick": js}) if js != "" else _SpkHash({"data-ripple": ""}))
    return tag("button", css_class, attrs, text)

def Input(placeholder = "", bind = None):
    attrs = _SpkHash({"type": "text"})
    if placeholder != "":
        attrs["placeholder"] = placeholder
    if bind != None:
        attrs["data-spork-bind"] = bind.name
        attrs["oninput"] = f"""window.__set('{_spk_i(bind.name)}',this.value)"""
    return tag("input", "sz-input", attrs)

def Textarea(placeholder = "", rows = 4, bind = None):
    attrs = _SpkHash({"rows": f"""{_spk_i(rows)}"""})
    if placeholder != "":
        attrs["placeholder"] = placeholder
    if bind != None:
        attrs["data-spork-bind"] = bind.name
        attrs["oninput"] = f"""window.__set('{_spk_i(bind.name)}',this.value)"""
    return tag("textarea", "sz-textarea", attrs)

def Checkbox(label_text, bind = None):
    attrs = _SpkHash({"type": "checkbox"})
    if bind != None:
        attrs["data-spork-checked"] = bind.name
        attrs["onchange"] = f"""window.__set('{_spk_i(bind.name)}',this.checked)"""
    chk = tag("input", "sz-checkbox-input", attrs)
    return tag("label", "sz-checkbox", _SpkHash({}), chk, " ", label_text)

def Select(options, bind = None):
    def _closureL1(pair):
        val = pair[0]
        lbl = pair[1]
        return f"""<option value=\"{_spk_i(html_escape(val))}\">{_spk_i(html_escape(lbl))}</option>"""
    opts = ("\n").join(str(x) for x in list(map(_closureL1, options)))
    attrs = _SpkHash({})
    if bind != None:
        attrs["data-spork-bind"] = bind.name
        attrs["onchange"] = f"""window.__set('{_spk_i(bind.name)}',this.value)"""
    return f"""<select class=\"sz-select\"{_spk_i(("").join(str(x) for x in list(map(lambda kv: f""" {_spk_i(kv[0])}=\"{_spk_i(kv[1])}\"""", list(attrs.items())))))}>\n{_spk_i(opts)}\n</select>"""

def Progress(state):
    style_expr = html_escape(f"""{{\"width\": window.__state.{_spk_i(state.name)} + \"%\"}}""")
    return f"""<div class=\"sz-progress\"><div class=\"sz-progress-bar\" data-spork-style=\"{_spk_i(style_expr)}\"></div></div>"""

def Avatar(src, alt = ""):
    return f"""<img class=\"sz-avatar\" src=\"{_spk_i(html_escape(src))}\" alt=\"{_spk_i(html_escape(alt))}\">"""

def Divider():
    return "<hr class=\"sz-divider\">"

def _push_sse(event, data):
    return vspk_bridge_push_sse(f"""event: {_spk_i(event)}\ndata: {_spk_i(json.dumps(data))}\n\n""")

def _push_state(name, value):
    _states[name] = value
    return _push_sse("state", _SpkHash({"name": name, "value": value}))

def state(name, initial):
    _states[name] = initial
    def to_html():
        return f"""<span data-spork-text=\"{_spk_i(name)}\"></span>"""
    def js_get():
        return f"""window.__state.{_spk_i(name)}"""
    def js_set(val):
        return f"""window.__set('{_spk_i(name)}',{_spk_i(json.dumps(val))})"""
    def js_inc(by = 1):
        return f"""window.__set('{_spk_i(name)}',window.__state.{_spk_i(name)}+{_spk_i(by)})"""
    def js_dec(by = 1):
        return f"""window.__set('{_spk_i(name)}',window.__state.{_spk_i(name)}-{_spk_i(by)})"""
    def get():
        return _states[name]
    def set(val):
        return _push_state(name, val)
    def inc(by = 1):
        return set(get() + by)
    def dec(by = 1):
        return set(get() - by)
    return _SpkHash({"name": name, "to_html": to_html, "js_get": js_get, "js_set": js_set, "js_inc": js_inc, "js_dec": js_dec, "get": get, "set": set, "inc": inc, "dec": dec, "__str__": lambda : to_html()})

def on_click(fn_cb):
    global _cb_count
    _cb_count = _cb_count + 1
    id = f"""cb_{_spk_i(_cb_count)}"""
    _callbacks[id] = fn_cb
    return f"""fetch('http://127.0.0.1:{_spk_i(_port)}/cb/{_spk_i(id)}',{{mode:'no-cors'}})"""

def on_event(name, fn_cb):
    _events[name] = fn_cb

def add(*ws):
    for w in ws:
        _widgets.append(f"""{_spk_i(w)}""")

def eval_js(js):
    return _push_sse("eval", js)

def _build_html():
    state_json = json.dumps(_states)
    body_html = ("\n").join(str(x) for x in _widgets)
    accent_style = (f"""<style>:root{{--sz-accent:{_spk_i(_accent)};}} .sz-btn-filled{{background:{_spk_i(_accent)};border-color:{_spk_i(_accent)};}}</style>""" if _accent != "" else "")
    return f"""<!DOCTYPE html>\n<html data-theme=\"{_spk_i(_theme)}\">\n<head>\n  <meta charset=\"UTF-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n  <title>{_spk_i(html_escape(_title))}</title>\n  <link rel=\"icon\" href=\"data:,\">\n  <link rel=\"stylesheet\" href=\"{_spk_i(SPORK_CSS)}\" onerror=\"this.onerror=null;this.href='{_spk_i(SPORK_CSS_CDN)}'\">\n  {_spk_i(accent_style)}\n  <script>window.__vspk=true;</script>\n</head>\n<body class=\"sz-body\">\n\n<div id=\"__app\" class=\"sz-page\">\n{_spk_i(body_html)}\n</div>\n\n<script>\nwindow.__state = {_spk_i(state_json)};\nwindow.__vspk   = true;\n\nwindow.__set = function(name, value) {{\n  window.__state[name] = value;\n  document.querySelectorAll('[data-spork-text=\"' + name + '\"]').forEach(function(el) {{\n    el.textContent = value;\n  }});\n  document.querySelectorAll('[data-spork-bind=\"' + name + '\"]').forEach(function(el) {{\n    if (el.type === 'checkbox') el.checked = value;\n    else el.value = value;\n  }});\n  document.querySelectorAll('[data-spork-style]').forEach(function(el) {{\n    try {{ Object.assign(el.style, new Function('return (' + el.dataset.sporkStyle + ')')()) }} catch(_){{}}\n  }});\n  document.querySelectorAll('[data-spork-if]').forEach(function(el) {{\n    try {{ el.style.display = new Function('return !!(' + el.dataset.sporkIf + ')')() ? '' : 'none' }} catch(_){{}}\n  }});\n  document.querySelectorAll('[data-spork-checked=\"' + name + '\"]').forEach(function(el) {{\n    el.checked = !!value;\n  }});\n}};\n\nObject.keys(window.__state).forEach(function(k) {{ window.__set(k, window.__state[k]); }});\n\n(function connectSSE() {{\n  var es = new EventSource('http://127.0.0.1:{_spk_i(_port)}/events');\n  es.addEventListener('state', function(e) {{\n    var d = JSON.parse(e.data);\n    window.__set(d.name, d.value);\n  }});\n  es.addEventListener('eval', function(e) {{\n    try {{ eval(JSON.parse(e.data)); }} catch(err) {{ console.error(err); }}\n  }});\n  es.onerror = function() {{\n    es.close();\n    setTimeout(connectSSE, 1000);\n  }};\n}})();\n</script>\n<script src=\"{_spk_i(SPORK_JS)}\" onerror=\"var s=document.createElement('script');s.src='{_spk_i(SPORK_JS_CDN)}';document.body.appendChild(s)\"></script>\n</body>\n</html>"""

def App(title, width = 1024, height = 768, theme = "light", accent = ""):
    global _title, _width, _height, _theme, _accent, _port
    _title = title
    _width = width
    _height = height
    _theme = theme
    _accent = accent
    _port = math.floor(random.random() * 10000) + 20000
    return _SpkHash({"state": state, "add": add, "on_click": on_click, "on_event": on_event, "eval_js": eval_js, "run": run})

def run():
    _vspk_exe = find_vspk()
    vspk_bridge_start(_port)
    html = _build_html()
    icon_names = ["icon.ico", "icon.png", "favicon.ico", "favicon.png"]
    icon_path = ""
    for name in icon_names:
        if icon_path == "":
            candidate = _spk_path_join(_spk_import.meta.dir, name)
            if f_exists_q(candidate):
                icon_path = candidate
    if icon_path == "":
        from_env = env("VSPK_DEFAULT_ICON")
        if from_env != "" and f_exists_q(from_env):
            icon_path = from_env
    if icon_path == "":
        dir = _spk_import.meta.dir
        for i in [0, 1, 2, 3, 4, 5, 6, 7]:
            if icon_path == "":
                candidate = _spk_path_join(dir, "vspk_default.ico")
                if f_exists_q(candidate):
                    icon_path = candidate
                nd = _spk_path_dir(dir)
                dir = nd if nd != dir else ""
    icon_line = (f"""icon: {_spk_i(icon_path)}\n""" if icon_path != "" else "")
    htv_content = f"""title: {_spk_i(_title)}\nwidth: {_spk_i(_width)}\nheight: {_spk_i(_height)}\ndevtools: true\n{_spk_i(icon_line)}\n{_spk_i(html)}"""
    htv_path = temp_file("vspk_", ".htv")
    _spk_f_write(htv_path, htv_content)
    proc = spawn([_vspk_exe, htv_path])
    while not proc.exited():
        msg = vspk_bridge_poll()
        if msg != None:
            if msg.kind == "cb":
                if _spk_has(_callbacks, msg.id):
                    try:
                        _callbacks[msg.id]()
                    except Exception as e:
                        pass
            else:
                if msg.kind == "event":
                    if _spk_has(_events, msg.name):
                        data = _spk_try(lambda: json.loads(msg.body), lambda: None)
                        try:
                            _events[msg.name](data)
                        except Exception as e:
                            pass
        (lambda __ms: __import__("time").sleep(__ms / 1000))(15)
    return _spk_f_delete(htv_path)

SPORK_CSS = "spork.css"
SPORK_JS = "spork.js"
SPORK_CSS_CDN = "https://cdn.jsdelivr.net/gh/unoudos/spork-ui@main/spork.css"
SPORK_JS_CDN = "https://cdn.jsdelivr.net/gh/unoudos/spork-ui@main/spork.js"
_states = _SpkHash({})
_widgets = []
_callbacks = _SpkHash({})
_events = _SpkHash({})
_cb_count = 0
_port = 0
_title = ""
_width = 1024
_height = 768
_theme = "light"
_accent = ""


def _spk_i(x): return 'true' if x is True else ('false' if x is False else x)

def _spk_has_m(o, m): return (m in o) if isinstance(o, dict) else hasattr(o, m)

def _spk_m(o, m, *a):
    if _spk_has_m(o, m): return getattr(o, m)(*a)
    return globals()[m](o, *a)


if __name__ == "__main__":
    gui = App("Demo vspk", 520, 720)
    n = _spk_m(gui, 'state', "n", 0)
    m = _spk_m(gui, 'state', "m", 0)
    pct = _spk_m(gui, 'state', "pct", 0)
    nombre = _spk_m(gui, 'state', "nombre", "")
    acepto = _spk_m(gui, 'state', "acepto", False)
    color = _spk_m(gui, 'state', "color", "azul")
    log = _spk_m(gui, 'state', "log", "—")
    def _closure1():
        n.dec()
        return log.set("n bajó")
    def _closure2():
        n.dec()
        return log.set("n bajó")
    def _closure3():
        n.inc()
        return log.set("n subió")
    def _closure4():
        n.inc()
        return log.set("n subió")
    def _closure5():
        if pct.get() < 100:
            pct.set(pct.get() + 10)
        return log.set(f"""progreso {_spk_i(pct.get())}""")
    def _closure6():
        if pct.get() < 100:
            pct.set(pct.get() + 10)
        return log.set(f"""progreso {_spk_i(pct.get())}""")
    def _closure7():
        pct.set(0)
        return log.set("reiniciado")
    def _closure8():
        pct.set(0)
        return log.set("reiniciado")
    def _closure9():
        _spk_m(gui, 'eval_js', "document.body.style.background = '#fff3cd'")
        return log.set("fondo teñido desde Spork")
    def _closure10():
        _spk_m(gui, 'eval_js', "document.body.style.background = '#fff3cd'")
        return log.set("fondo teñido desde Spork")
    def _closure11():
        _spk_m(gui, 'eval_js', "document.body.style.background = ''")
        return log.set("fondo restaurado")
    def _closure12():
        _spk_m(gui, 'eval_js', "document.body.style.background = ''")
        return log.set("fondo restaurado")
    def _closure13():
        n.dec()
        return log.set("n bajó")
    def _closure14():
        n.dec()
        return log.set("n bajó")
    def _closure15():
        n.inc()
        return log.set("n subió")
    def _closure16():
        n.inc()
        return log.set("n subió")
    def _closure17():
        if pct.get() < 100:
            pct.set(pct.get() + 10)
        return log.set(f"""progreso {_spk_i(pct.get())}""")
    def _closure18():
        if pct.get() < 100:
            pct.set(pct.get() + 10)
        return log.set(f"""progreso {_spk_i(pct.get())}""")
    def _closure19():
        pct.set(0)
        return log.set("reiniciado")
    def _closure20():
        pct.set(0)
        return log.set("reiniciado")
    def _closure21():
        _spk_m(gui, 'eval_js', "document.body.style.background = '#fff3cd'")
        return log.set("fondo teñido desde Spork")
    def _closure22():
        _spk_m(gui, 'eval_js', "document.body.style.background = '#fff3cd'")
        return log.set("fondo teñido desde Spork")
    def _closure23():
        _spk_m(gui, 'eval_js', "document.body.style.background = ''")
        return log.set("fondo restaurado")
    def _closure24():
        _spk_m(gui, 'eval_js', "document.body.style.background = ''")
        return log.set("fondo restaurado")
    _spk_m(gui, 'add', Card(H2("Demo vspk"), H4("1. Contador en Spork (cada clic va al puente)"), Row(Button("-", _spk_m(gui, 'on_click', _closure14), "outlined"), H3(n), Button("+", _spk_m(gui, 'on_click', _closure16))), Hr(), H4("2. Contador solo JS (sin puente, debe ser instantáneo)"), Row(Button("-", m.js_dec(), "outlined"), H3(m), Button("+", m.js_inc())), Hr(), H4("3. Input enlazado"), Input("Escribe tu nombre", nombre), P(nombre), Hr(), H4("4. Checkbox y Select"), Checkbox("Acepto las condiciones", acepto), Select([["azul", "Azul"], ["verde", "Verde"], ["rojo", "Rojo"]], color), P(color), Hr(), H4("5. Progreso (Spork actualiza la barra)"), Progress(pct), Row(Button("+10%", _spk_m(gui, 'on_click', _closure18)), Button("Reiniciar", _spk_m(gui, 'on_click', _closure20), "outlined")), Hr(), H4("6. Variantes y alertas"), Row(Chip("normal"), Chip("primario", True), Badge("badge")), Alert("Todo correcto", "success"), Alert("Cuidado", "warning"), Row(Button("Texto", "", "text"), Button("Peligro", "", "danger"), Button("Pequeño", "", "filled", "sm")), Hr(), H4("7. eval_js desde Spork"), Row(Button("Teñir fondo", _spk_m(gui, 'on_click', _closure22)), Button("Quitar", _spk_m(gui, 'on_click', _closure24), "outlined")), P(log)))
    _spk_m(gui, 'run')
