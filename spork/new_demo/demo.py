# Generado por Spork → target Python

import sys
import os
import json
import math
import random
import time
import re


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
            return f"""<{_spk_i(t)}{_spk_i(cls_attr)}{_spk_i(attrs_str)}></{_spk_i(t)}>"""
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
        attrs["oninput"] = f"""window.__set('{_spk_i(bind.name)}',this.value);window.__sync('{_spk_i(bind.name)}',this.value)"""
    return tag("input", "sz-input", attrs)

def Textarea(placeholder = "", rows = 4, bind = None):
    attrs = _SpkHash({"rows": f"""{_spk_i(rows)}"""})
    if placeholder != "":
        attrs["placeholder"] = placeholder
    if bind != None:
        attrs["data-spork-bind"] = bind.name
        attrs["oninput"] = f"""window.__set('{_spk_i(bind.name)}',this.value);window.__sync('{_spk_i(bind.name)}',this.value)"""
    return tag("textarea", "sz-textarea", attrs)

def Checkbox(label_text, bind = None):
    attrs = _SpkHash({"type": "checkbox"})
    if bind != None:
        attrs["data-spork-checked"] = bind.name
        attrs["onchange"] = f"""window.__set('{_spk_i(bind.name)}',this.checked);window.__sync('{_spk_i(bind.name)}',this.checked)"""
    chk = tag("input", "", attrs)
    track = "<span class=\"sz-switch-track\"><span class=\"sz-switch-thumb\"></span></span>"
    lbl = f"""<span class=\"sz-switch-label\">{_spk_i(label_text)}</span>"""
    return tag("label", "sz-switch", _SpkHash({}), chk, track, lbl)

def Select(options, bind = None):
    def _closureL1(pair):
        val = pair[0]
        lbl = pair[1]
        return f"""<option value=\"{_spk_i(html_escape(val))}\">{_spk_i(html_escape(lbl))}</option>"""
    opts = ("\n").join(str(x) for x in list(map(_closureL1, options)))
    attrs = _SpkHash({})
    if bind != None:
        attrs["data-spork-bind"] = bind.name
        attrs["onchange"] = f"""window.__set('{_spk_i(bind.name)}',this.value);window.__sync('{_spk_i(bind.name)}',this.value)"""
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
    id = f"""cb_{_spk_i(_token)}_{_spk_i(_cb_count)}"""
    _callbacks[id] = fn_cb
    return f"""fetch('http://127.0.0.1:{_spk_i(_port)}/cb/{_spk_i(id)}',{{mode:'no-cors'}})"""

def on_event(name, fn_cb):
    _events[name] = fn_cb

def _ev(name):
    return f"""__{_spk_i(name)}_{_spk_i(_token)}"""

def _post_js(name, body_expr):
    return f"""fetch('http://127.0.0.1:{_spk_i(_port)}/event/{_spk_i(name)}',{{method:'POST',mode:'no-cors',headers:{{'Content-Type':'text/plain'}},body:{_spk_i(body_expr)}}})"""

def on_key(fn_cb):
    global _key_on
    _key_on = True
    return on_event(_ev("k"), fn_cb)

def _safe_true(f):
    try:
        return _call0(f)
    except Exception as e:
        return True

def _call0(f):
    h = _SpkHash({"f": f})
    return h["f"]()

def _call1(f, a):
    h = _SpkHash({"f": f})
    return h["f"](a)

def on_close(fn_cb):
    global _close_on
    _close_on = True
    def _closureL1(d):
        r = _safe_true(fn_cb)
        if r == False:
            eval_js("__vspk.cancelClose()")
        if r != False:
            return eval_js("__vspk.confirmClose()")
    return on_event(_ev("c"), _closureL1)

def _dialog(kind, title, fn_cb):
    global _cb_count
    _cb_count = _cb_count + 1
    name = _ev(f"""d{_spk_i(_cb_count)}""")
    on_event(name, lambda d: _call1(fn_cb, d["path"]))
    return eval_js(f"""__vspk.dialog({{kind:'{_spk_i(kind)}',title:{_spk_i(json.dumps(title))}}}).then(function(p){{{_spk_i(_post_js(name, "JSON.stringify({path:p})"))}}})""")

def pick_file(title, fn_cb):
    return _dialog("open", title, fn_cb)

def save_file(title, fn_cb):
    return _dialog("save", title, fn_cb)

def pick_folder(title, fn_cb):
    return _dialog("folder", title, fn_cb)

def _timer(js_fn, ms, fn_cb):
    global _cb_count
    _cb_count = _cb_count + 1
    name = _ev(f"""t{_spk_i(_cb_count)}""")
    on_event(name, lambda d: _call0(fn_cb))
    js = f"""{_spk_i(js_fn)}(function(){{{_spk_i(_post_js(name, "'{}'"))}}},{_spk_i(ms)})"""
    _timers.append(f"""{_spk_i(js)}""")
    if _running:
        eval_js(js)
    return True

def run_every(ms, fn_cb):
    return _timer("setInterval", ms, fn_cb)

def run_after(ms, fn_cb):
    return _timer("setTimeout", ms, fn_cb)

def set_title(t):
    return eval_js(f"""__vspk.setTitle({_spk_i(json.dumps(t))})""")

def notify(title, body = ""):
    return eval_js(f"""__vspk.notify({_spk_i(json.dumps(title))},{_spk_i(json.dumps(body))})""")

def copy_text(text):
    return eval_js(f"""__vspk.clipboard.write({_spk_i(json.dumps(text))})""")

def quit():
    return eval_js("__vspk.close()")

def _cv_do(id, op, args):
    js = f"""__cv({_spk_i(json.dumps(id))},{_spk_i(json.dumps(op))},{_spk_i(json.dumps(args))})"""
    if op == "clear":
        _cv_logs[id] = ""
    _cv_logs[id] = f"""{_spk_i(_cv_logs[id])}{_spk_i(js)};"""
    if _running:
        eval_js(js)
    return True

def _cv_on_mouse(id, fn_cb):
    global _cb_count, _cv_mouse_js
    _cb_count = _cb_count + 1
    name = _ev(f"""m{_spk_i(_cb_count)}""")
    on_event(name, fn_cb)
    js = f"""(function(){{var c=document.getElementById('{_spk_i(id)}');function p(t,e){{if(t==='move'){{var n=Date.now();if(n-(c.__lm||0)<30)return;c.__lm=n;}}var r=c.getBoundingClientRect();{_spk_i(_post_js(name, "JSON.stringify({type:t,x:Math.round((e.clientX-r.left)*c.width/r.width),y:Math.round((e.clientY-r.top)*c.height/r.height),button:e.button})"))}}}['down','up','move','click'].forEach(function(t){{c.addEventListener(t==='down'?'mousedown':t==='up'?'mouseup':t==='move'?'mousemove':'click',function(e){{p(t,e)}})}})}})();"""
    _cv_mouse_js = _cv_mouse_js + js
    if _running:
        eval_js(js)
    return True

def canvas(id, w, h):
    _cv_logs[id] = ""
    _cv_ids.append(id)
    def to_html():
        return f"""<canvas id=\"{_spk_i(id)}\" width=\"{_spk_i(w)}\" height=\"{_spk_i(h)}\" style=\"width:{_spk_i(w)}px;max-width:100%;height:auto;border:1px solid rgba(128,128,128,.4);border-radius:8px;touch-action:none\"></canvas>"""
    def _color(c):
        return _cv_do(id, "color", [c])
    def _line_width(n):
        return _cv_do(id, "lw", [n])
    def _font(size):
        return _cv_do(id, "font", [size])
    def _line(x1, y1, x2, y2):
        return _cv_do(id, "line", [x1, y1, x2, y2])
    def _rect(x, y, rw, rh):
        return _cv_do(id, "rect", [x, y, rw, rh])
    def _frame(x, y, rw, rh):
        return _cv_do(id, "frame", [x, y, rw, rh])
    def _circle(x, y, r):
        return _cv_do(id, "circle", [x, y, r])
    def _ring(x, y, r):
        return _cv_do(id, "ring", [x, y, r])
    def _text(x, y, s):
        return _cv_do(id, "text", [x, y, s])
    def _poly(points):
        return _cv_do(id, "poly", [points])
    def _clear():
        return _cv_do(id, "clear", [])
    def _draw(js):
        return _cv_do(id, "draw", [js])
    def _on_mouse(fn_cb):
        return _cv_on_mouse(id, fn_cb)
    return _SpkHash({"to_html": to_html, "color": _color, "line_width": _line_width, "font": _font, "line": _line, "rect": _rect, "frame": _frame, "circle": _circle, "ring": _ring, "text": _text, "poly": _poly, "erase": _clear, "draw": _draw, "on_mouse": _on_mouse, "__str__": lambda : to_html()})

def add(*ws):
    for w in ws:
        _widgets.append(f"""{_spk_i(w)}""")

def eval_js(js):
    return _push_sse("eval", js)

def _build_html():
    state_json = json.dumps(_states)
    body_html = ("\n").join(str(x) for x in _widgets)
    key_js = (f"""document.addEventListener('keydown',function(e){{{_spk_i(_post_js(_ev("k"), "JSON.stringify({key:e.key,code:e.code,ctrl:e.ctrlKey,shift:e.shiftKey,alt:e.altKey,meta:e.metaKey})"))}}});""" if _key_on else "")
    close_js = (f"""window.addEventListener('vspk:closeRequested',function(){{{_spk_i(_post_js(_ev("c"), "'{}'"))}}});""" if _close_on else "")
    timers_js = (";").join(str(x) for x in _timers) + ";"
    cv_js = f"""{_spk_i(("").join(str(x) for x in list(map(lambda i: _cv_logs[i], _cv_ids))))}{_spk_i(_cv_mouse_js)}"""
    accent_style = (f"""<style>:root{{--sz-accent:{_spk_i(_accent)};}} .sz-btn-filled{{background:{_spk_i(_accent)};border-color:{_spk_i(_accent)};}}</style>""" if _accent != "" else "")
    return f"""<!DOCTYPE html>\n<html data-theme=\"{_spk_i(_theme)}\">\n<head>\n  <meta charset=\"UTF-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n  <title>{_spk_i(html_escape(_title))}</title>\n  <link rel=\"icon\" href=\"data:,\">\n  <link rel=\"stylesheet\" href=\"{_spk_i(SPORK_CSS)}\" onerror=\"this.onerror=null;this.href='{_spk_i(SPORK_CSS_CDN)}'\">\n  {_spk_i(accent_style)}\n</head>\n<body class=\"sz-body\">\n\n<div id=\"__app\" class=\"sz-page\">\n{_spk_i(body_html)}\n</div>\n\n<script>\nwindow.__state = {_spk_i(state_json)};\n\nwindow.__set = function(name, value) {{\n  window.__state[name] = value;\n  document.querySelectorAll('[data-spork-text=\"' + name + '\"]').forEach(function(el) {{\n    el.textContent = value;\n  }});\n  document.querySelectorAll('[data-spork-bind=\"' + name + '\"]').forEach(function(el) {{\n    if (el.type === 'checkbox') el.checked = value;\n    else el.value = value;\n  }});\n  document.querySelectorAll('[data-spork-style]').forEach(function(el) {{\n    try {{ Object.assign(el.style, new Function('return (' + el.dataset.sporkStyle + ')')()) }} catch(_){{}}\n  }});\n  document.querySelectorAll('[data-spork-if]').forEach(function(el) {{\n    try {{ el.style.display = new Function('return !!(' + el.dataset.sporkIf + ')')() ? '' : 'none' }} catch(_){{}}\n  }});\n  document.querySelectorAll('[data-spork-checked=\"' + name + '\"]').forEach(function(el) {{\n    el.checked = !!value;\n  }});\n}};\n\n// Envía a Spork el valor que el usuario escribe/elige, para que state.get() lo vea\n// (los widgets enlazados solo actualizaban la página). POST simple (text/plain, no-cors).\nwindow.__sync = function(n, v) {{\n  try {{\n    fetch('http://127.0.0.1:{_spk_i(_port)}/event/{_spk_i(_ev("v"))}', {{method: 'POST', mode: 'no-cors', headers: {{'Content-Type': 'text/plain'}}, body: JSON.stringify({{n: n, v: v}})}});\n  }} catch(_) {{}}\n}};\n\nwindow.__cv = function(id, op, a) {{\n  var c = document.getElementById(id); if (!c) return;\n  var x = c.getContext('2d');\n  if (op === 'clear') {{ x.clearRect(0, 0, c.width, c.height); }}\n  else if (op === 'color') {{ x.fillStyle = a[0]; x.strokeStyle = a[0]; }}\n  else if (op === 'lw') {{ x.lineWidth = a[0]; }}\n  else if (op === 'font') {{ x.font = a[0] + 'px sans-serif'; }}\n  else if (op === 'line') {{ x.beginPath(); x.moveTo(a[0], a[1]); x.lineTo(a[2], a[3]); x.stroke(); }}\n  else if (op === 'rect') {{ x.fillRect(a[0], a[1], a[2], a[3]); }}\n  else if (op === 'frame') {{ x.strokeRect(a[0], a[1], a[2], a[3]); }}\n  else if (op === 'circle') {{ x.beginPath(); x.arc(a[0], a[1], a[2], 0, 6.283185307); x.fill(); }}\n  else if (op === 'ring') {{ x.beginPath(); x.arc(a[0], a[1], a[2], 0, 6.283185307); x.stroke(); }}\n  else if (op === 'text') {{ x.fillText(a[2], a[0], a[1]); }}\n  else if (op === 'poly') {{ var p = a[0]; x.beginPath(); x.moveTo(p[0][0], p[0][1]); for (var i = 1; i < p.length; i++) x.lineTo(p[i][0], p[i][1]); x.closePath(); x.fill(); }}\n  else if (op === 'draw') {{ new Function('ctx', 'canvas', a[0])(x, c); }}\n}};\nObject.keys(window.__state).forEach(function(k) {{ window.__set(k, window.__state[k]); }});\n{_spk_i(key_js)}\n{_spk_i(close_js)}\n{_spk_i(timers_js)}\n{_spk_i(cv_js)}\n\n(function connectSSE() {{\n  var es = new EventSource('http://127.0.0.1:{_spk_i(_port)}/events');\n  es.addEventListener('state', function(e) {{\n    var d = JSON.parse(e.data);\n    window.__set(d.name, d.value);\n  }});\n  es.addEventListener('eval', function(e) {{\n    try {{ eval(JSON.parse(e.data)); }} catch(err) {{ console.error(err); }}\n  }});\n  es.onerror = function() {{\n    es.close();\n    setTimeout(connectSSE, 1000);\n  }};\n}})();\n</script>\n<script src=\"{_spk_i(SPORK_JS)}\" onerror=\"var s=document.createElement('script');s.src='{_spk_i(SPORK_JS_CDN)}';document.body.appendChild(s)\"></script>\n</body>\n</html>"""

def App(title, width = 1024, height = 768, theme = "light", accent = ""):
    global _title, _width, _height, _theme, _accent, _port, _token
    _title = title
    _width = width
    _height = height
    _theme = theme
    _accent = accent
    _port = math.floor(random.random() * 10000) + 20000
    _token = str(int(random.random() * 1000000000)) + str(int(random.random() * 1000000000)) + str(int(random.random() * 1000000000))
    return _SpkHash({"state": state, "canvas": canvas, "add": add, "on_click": on_click, "on_event": on_event, "eval_js": eval_js, "run": run, "on_key": on_key, "on_close": on_close, "pick_file": pick_file, "save_file": save_file, "pick_folder": pick_folder, "run_every": run_every, "run_after": run_after, "set_title": set_title, "notify": notify, "copy_text": copy_text, "quit": quit})

def run():
    global _running
    _vspk_exe = find_vspk()
    vspk_bridge_start(_port)
    html = _build_html()
    icon_dirs = [_spk_path_dir(_spk_import.meta.dir), _spk_import.meta.dir]
    icon_names = ["icon.ico", "icon.png", "favicon.ico", "favicon.png"]
    icon_path = ""
    for dir in icon_dirs:
        for name in icon_names:
            if icon_path == "":
                candidate = _spk_path_join(dir, name)
                if f_exists_q(candidate):
                    icon_path = candidate
    icon_line = (f"""icon: {_spk_i(icon_path)}\n""" if icon_path != "" else "")
    close_line = ("on_close: confirm\n" if _close_on else "")
    htv_content = f"""title: {_spk_i(_title)}\nwidth: {_spk_i(_width)}\nheight: {_spk_i(_height)}\ndevtools: true\n{_spk_i(icon_line)}{_spk_i(close_line)}\n{_spk_i(html)}"""
    htv_path = temp_file("vspk_", ".htv")
    _spk_f_write(htv_path, htv_content)
    proc = spawn([_vspk_exe, htv_path])
    _running = True
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
                    data = _spk_try(lambda: json.loads(msg.body), lambda: None)
                    is_value = msg.name == _ev("v")
                    if is_value and data != None:
                        key = str(data["n"])
                        _states[key] = data["v"]
                    if not is_value and _spk_has(_events, msg.name):
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
_token = ""
_key_on = False
_close_on = False
_running = False
_timers = []
_cv_ids = []
_cv_logs = _SpkHash({})
_cv_mouse_js = ""


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
    res = _spk_m(gui, 'state', "res", "—")
    tecla = _spk_m(gui, 'state', "tecla", "—")
    ticks = _spk_m(gui, 'state', "ticks", 0)
    arch = _spk_m(gui, 'state', "arch", "—")
    raton = _spk_m(gui, 'state', "raton", "—")
    lienzo = _spk_m(gui, 'canvas', "lienzo", 300, 150)
    lienzo.color("#6750A4")
    lienzo.rect(10, 10, 100, 60)
    lienzo.color("#B3261E")
    lienzo.circle(200, 60, 40)
    lienzo.color("#000000")
    lienzo.line_width(2)
    lienzo.line(0, 0, 300, 150)
    lienzo.font(16)
    lienzo.text(10, 140, "Spork")
    lienzo.on_mouse(lambda e: raton.set(f"""{_spk_i(e["type"])} {_spk_i(e["x"])},{_spk_i(e["y"])}"""))
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
        lienzo.color("#00AA00")
        return lienzo.circle(150, 75, 20)
    def _closure14():
        lienzo.color("#00AA00")
        return lienzo.circle(150, 75, 20)
    def _closure15():
        n.dec()
        return log.set("n bajó")
    def _closure16():
        n.dec()
        return log.set("n bajó")
    def _closure17():
        n.inc()
        return log.set("n subió")
    def _closure18():
        n.inc()
        return log.set("n subió")
    def _closure19():
        if pct.get() < 100:
            pct.set(pct.get() + 10)
        return log.set(f"""progreso {_spk_i(pct.get())}""")
    def _closure20():
        if pct.get() < 100:
            pct.set(pct.get() + 10)
        return log.set(f"""progreso {_spk_i(pct.get())}""")
    def _closure21():
        pct.set(0)
        return log.set("reiniciado")
    def _closure22():
        pct.set(0)
        return log.set("reiniciado")
    def _closure23():
        _spk_m(gui, 'eval_js', "document.body.style.background = '#fff3cd'")
        return log.set("fondo teñido desde Spork")
    def _closure24():
        _spk_m(gui, 'eval_js', "document.body.style.background = '#fff3cd'")
        return log.set("fondo teñido desde Spork")
    def _closure25():
        _spk_m(gui, 'eval_js', "document.body.style.background = ''")
        return log.set("fondo restaurado")
    def _closure26():
        _spk_m(gui, 'eval_js', "document.body.style.background = ''")
        return log.set("fondo restaurado")
    def _closure27():
        lienzo.color("#00AA00")
        return lienzo.circle(150, 75, 20)
    def _closure28():
        lienzo.color("#00AA00")
        return lienzo.circle(150, 75, 20)
    _spk_m(gui, 'add', Card(H2("Demo vspk"), H4("1. Contador en Spork (cada clic va al puente)"), Row(Button("-", _spk_m(gui, 'on_click', _closure16), "outlined"), H3(n), Button("+", _spk_m(gui, 'on_click', _closure18))), Hr(), H4("2. Contador solo JS (sin puente, debe ser instantáneo)"), Row(Button("-", m.js_dec(), "outlined"), H3(m), Button("+", m.js_inc())), Hr(), H4("3. Input enlazado"), Input("Escribe tu nombre", nombre), P(nombre), Hr(), H4("4. Checkbox y Select"), Checkbox("Acepto las condiciones", acepto), Select([["azul", "Azul"], ["verde", "Verde"], ["rojo", "Rojo"]], color), P(color), Hr(), H4("5. Progreso (Spork actualiza la barra)"), Progress(pct), Row(Button("+10%", _spk_m(gui, 'on_click', _closure20)), Button("Reiniciar", _spk_m(gui, 'on_click', _closure22), "outlined")), Hr(), H4("6. Variantes y alertas"), Row(Chip("normal"), Chip("primario", True), Badge("badge")), Alert("Todo correcto", "success"), Alert("Cuidado", "warning"), Row(Button("Texto", "", "text"), Button("Peligro", "", "danger"), Button("Pequeño", "", "filled", "sm")), Hr(), H4("7. eval_js desde Spork"), Row(Button("Teñir fondo", _spk_m(gui, 'on_click', _closure24)), Button("Quitar", _spk_m(gui, 'on_click', _closure26), "outlined")), P(log), Hr(), H4("8. Spork lee los campos de arriba (3 y 4)"), Button("Enviar", _spk_m(gui, 'on_click', lambda : res.set(f"""nombre={_spk_i(nombre.get())}  acepto={_spk_i(acepto.get())}  color={_spk_i(color.get())}"""))), P(res), Hr(), H4("9. Teclado, diálogos, temporizador, ventana"), P(tecla), Row(P("ticks:"), H3(ticks)), Row(Button("Abrir archivo...", _spk_m(gui, 'on_click', lambda : _spk_m(gui, 'pick_file', "Elige un archivo", lambda p: arch.set(f"""archivo: {_spk_i(p)}""")))), Button("Cambiar título", _spk_m(gui, 'on_click', lambda : _spk_m(gui, 'set_title', "Hola desde Spork"))), Button("Notificar", _spk_m(gui, 'on_click', lambda : _spk_m(gui, 'notify', "Spork", "Hecho")), "outlined")), P(arch), Hr(), H4("10. Canvas"), lienzo, P(raton), Row(Button("Limpiar", _spk_m(gui, 'on_click', lambda : lienzo.erase()), "outlined"), Button("Dibujar", _spk_m(gui, 'on_click', _closure28)))))
    _spk_m(gui, 'on_key', lambda e: tecla.set(f"""tecla: {_spk_i(e["key"])}"""))
    _spk_m(gui, 'on_close', lambda : log.set("cerrando"))
    _spk_m(gui, 'run_every', 1000, lambda : ticks.inc())
    _spk_m(gui, 'run')
