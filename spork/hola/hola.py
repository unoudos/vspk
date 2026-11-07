# Generado por Spork → target Python

import sys
import os
import json
import math
import random
import time


def _spk_flat(arr):
    return [x for sub in arr for x in sub]

def _spk_chunk(arr, n):
    return [arr[i:i + n] for i in range(0, len(arr), n)]

def _spk_rotate(arr, n):
    if not arr: return arr
    n = n % len(arr)
    return arr[n:] + arr[:n]

def _spk_uniq(arr):
    seen, out = set(), []
    for x in arr:
        k = x if isinstance(x, (int, float, str, bool)) else id(x)
        if k not in seen:
            seen.add(k)
            out.append(x)
    return out

def _spk_mat_new(rows, cols, fill=0):
    return [[fill]*cols for _ in range(rows)]

def _spk_mat_rows(m): return len(m)
def _spk_mat_cols(m): return len(m[0]) if m else 0
def _spk_mat_get(m, r, c): return m[r][c]
def _spk_mat_set(m, r, c, v): m[r][c] = v

def _spk_mat_add(a, b):
    return [[a[r][c]+b[r][c] for c in range(len(a[0]))] for r in range(len(a))]

def _spk_mat_sub(a, b):
    return [[a[r][c]-b[r][c] for c in range(len(a[0]))] for r in range(len(a))]

def _spk_mat_mul(a, b):
    R, K, C = len(a), len(b), len(b[0])
    return [[sum(a[r][k]*b[k][c] for k in range(K)) for c in range(C)] for r in range(R)]

def _spk_mat_scale(m, s):
    return [[m[r][c]*s for c in range(len(m[0]))] for r in range(len(m))]

def _spk_mat_t(m):
    return [[m[r][c] for r in range(len(m))] for c in range(len(m[0]))]

def _spk_mat_eye(n):
    return [[1 if r==c else 0 for c in range(n)] for r in range(n)]

def _spk_mat_trace(m):
    return sum(m[i][i] for i in range(min(len(m), len(m[0]))))

def _spk_mat_print(m):
    for row in m: print('	'.join(str(x) for x in row))

def _spk_mat_eq(a, b):
    if len(a)!=len(b) or len(a[0])!=len(b[0]): return False
    return all(a[r][c]==b[r][c] for r in range(len(a)) for c in range(len(a[0])))

def _spk_cpow(z, n): return z**n

def _spk_conj(z): return z.conjugate()

def _spk_phase(z):
    import cmath as _cm; return _cm.phase(z)

def _spk_magnitude(z): return abs(z)

def _spk_fmt_c(z):
    r = int(z.real) if z.real == int(z.real) else z.real
    i = int(z.imag) if z.imag == int(z.imag) else z.imag
    if i >= 0: return f"{r} + {i}i"
    return f"{r} - {abs(i)}i"

def _spk_upcase_first(s):
    return s[0].upper() + s[1:] if s else s

def _spk_lcm(a, b):
    import math as _m
    return abs(a * b) // _m.gcd(a, b) if a and b else 0

def _spk_sign(x):
    return (x > 0) - (x < 0)

def _spk_cbrt(x):
    r = x ** (1/3) if x >= 0 else -((-x) ** (1/3))
    ri = int(round(r))
    return ri if ri ** 3 == x else r

def _spk_sqrt(x):
    r = x ** 0.5
    return int(r) if r == int(r) else r

def _spk_pow(base, exp):
    r = base ** exp
    return int(r) if isinstance(r, float) and r == int(r) else r

def _spk_clamp(val, lo, hi):
    return max(lo, min(hi, val))

def _spk_is_prime(n):
    if n < 2: return False
    if n == 2: return True
    if n % 2 == 0: return False
    for i in range(3, int(n**0.5)+1, 2):
        if n % i == 0: return False
    return True

class _SpkHash(dict):
    def __getattr__(self, key):
        try: return self[key]
        except KeyError: raise AttributeError(key)
    def __setattr__(self, key, val): self[key] = val

class _SpkList(list):
    def __repr__(self):
        if not self: return '[]'
        return '[ ' + ', '.join(repr(x) for x in self) + ' ]'
    def __str__(self):
        return self.__repr__()

def _spk_hour():
    import time as _t; return _t.localtime().tm_hour

def _spk_minute():
    import time as _t; return _t.localtime().tm_min

def _spk_second():
    import time as _t; return _t.localtime().tm_sec

def _spk_year():
    import time as _t; return _t.localtime().tm_year

def _spk_month():
    import time as _t; return _t.localtime().tm_mon

def _spk_day():
    import time as _t; return _t.localtime().tm_mday

def _spk_any_q(arr, pred):
    return any(pred(x) for x in arr)

def _spk_all_q(arr, pred):
    return all(pred(x) for x in arr)

def _spk_zip(*arrays):
    return [list(row) for row in zip(*arrays)]

def _spk_group_by(arr, fn):
    result = {}
    for x in arr:
        k = fn(x)
        if k not in result: result[k] = []
        result[k].append(x)
    return result

def _spk_partition(arr, fn):
    yes, no = [], []
    for x in arr:
        (yes if fn(x) else no).append(x)
    return [yes, no]

def _spk_tally(arr):
    result = {}
    for x in arr:
        result[x] = result.get(x, 0) + 1
    return result

def _spk_count_by(arr, fn):
    result = {}
    for x in arr:
        k = fn(x)
        k = str(k).lower() if isinstance(k, bool) else k
        result[k] = result.get(k, 0) + 1
    return result

def _spk_flat_map_deep(arr, fn):
    result = []
    def _go(x):
        v = fn(x)
        if isinstance(v, list):
            for item in v: _go(item)
        else: result.append(v)
    for x in arr: _go(x)
    return result

def _spk_flatten_deep(arr):
    result = []
    def _go(x):
        if isinstance(x, list):
            for item in x: _go(item)
        else: result.append(x)
    for x in arr: _go(x)
    return result

def _spk_tap(val, fn):
    fn(val)
    return val

def _spk_shuffle_copy(arr):
    import random as _r
    a = list(arr)
    _r.shuffle(a)
    return a

def _spk_to_csv(rows):
    if not rows: return ''
    import io as _io_mod, csv as _csv_mod
    buf = _io_mod.StringIO()
    w = _csv_mod.DictWriter(buf, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().rstrip('\n')

def _spk_from_csv(s):
    if not s: return []
    import io as _io_mod, csv as _csv_mod
    buf = _io_mod.StringIO(s)
    return list(_csv_mod.DictReader(buf))

# ── bitwise ──────────────────────────────────────────────────────────
def _spk_bit_and(a, b): return a & b
def _spk_bit_or(a, b):  return a | b
def _spk_bit_xor(a, b): return a ^ b
def _spk_bit_not(a):    return ~a
def _spk_shl(a, b):     return a << b
def _spk_shr(a, b):     return a >> b

# ── numeric predicates ───────────────────────────────────────────────
def _spk_is_nan_q(x):    return x != x
def _spk_is_inf_q(x):    return math.isinf(x)
def _spk_is_finite_q(x): return math.isfinite(x)
def _spk_is_nil(x):      return x is None

# ── array extras ─────────────────────────────────────────────────────
def _spk_size(arr): return sum(1 for x in arr if x is not None)
def _spk_index(arr, val):
    try: return arr.index(val)
    except ValueError: return -1
def _spk_sorted(*args):
    if len(args) == 1 and hasattr(args[0], '__iter__') and not isinstance(args[0], str):
        return sorted(args[0])
    return sorted(args)
def _spk_array(it):
    if hasattr(it, '__iter__') and not isinstance(it, str):
        return _SpkList(it)
    return _SpkList([it])

# ── hash utils ───────────────────────────────────────────────────────
def _spk_pick(h, *keys): return {k: h[k] for k in keys if k in h}
def _spk_omit(h, *keys): return {k: v for k, v in h.items() if k not in keys}
def _spk_assoc(h, k, v): return {**h, k: v}
def _spk_dissoc(h, *keys): return {k2: v for k2, v in h.items() if k2 not in keys}
def _spk_merge_b(a, b): return {**a, **b}
def _spk_rename_key(h, old, new_k):
    result = dict(h)
    if old in result: result[new_k] = result.pop(old)
    return result
def _spk_deep_get(h, path):
    parts = path.split('.')
    cur = h
    for p in parts:
        if not isinstance(cur, dict): return None
        cur = cur.get(p)
    return cur
def _spk_deep_set(h, path, val):
    import copy as _cp
    result = _cp.deepcopy(h)
    parts = path.split('.')
    cur = result
    for p in parts[:-1]: cur = cur.setdefault(p, {})
    cur[parts[-1]] = val
    return result
def _spk_from_json_ht(s): return json.loads(s)

# ── string extras ────────────────────────────────────────────────────
def _spk_center(s, n, fill=' '): return s.center(n, fill)
def _spk_count_substr(s, sub): return s.count(sub)
def _spk_word_wrap(s, width):
    words = s.split()
    lines, line = [], []
    for w in words:
        if line and len(' '.join(line + [w])) > width:
            lines.append(' '.join(line)); line = [w]
        else: line.append(w)
    if line: lines.append(' '.join(line))
    return '\n'.join(lines)
def _spk_format(tmpl, *args): return tmpl.format(*args)

# ── higher-order / closures ──────────────────────────────────────────
def _spk_call(fn, *args): return fn(*args)
def _spk_invoke(fn, *args): return fn(*args)
def _spk_partial(fn, *args):
    import functools as _ft; return _ft.partial(fn, *args)
def _spk_compose(*fns):
    def _c(x):
        for f in reversed(fns): x = f(x)
        return x
    return _c
def _spk_pipe_fn(*fns):
    def _p(x):
        for f in fns: x = f(x)
        return x
    return _p
def _spk_each_with_index(arr, fn):
    for i, x in enumerate(arr): fn(x, i)
def _spk_each_slice(arr, n, fn):
    for i in range(0, len(arr), n): fn(arr[i:i+n])
def _spk_group_by_key(arr, key):
    result = {}
    for x in arr: result.setdefault(x[key], []).append(x)
    return result
def _spk_reduce_compat(arr, fn, init=None):
    import functools as _ft
    return _ft.reduce(fn, arr) if init is None else _ft.reduce(fn, arr, init)

# ── range ────────────────────────────────────────────────────────────
def _spk_range(a, b, step=None):
    if step is not None: return range(a, b, step)
    if a <= b: return range(a, b + 1)
    return range(a, b - 1, -1)

# ── debug ────────────────────────────────────────────────────────────
import sys as _sys
def _spk_debug(*args):   print(*args, file=_sys.stderr)
def _spk_verbose(*args): print(*args, file=_sys.stderr)

# ── filesystem ───────────────────────────────────────────────────────
import os as _os, shutil as _shu
def _spk_mkdir(p):      _os.makedirs(p, exist_ok=True)
def _spk_deltree(p):    _shu.rmtree(p, ignore_errors=True)
def _spk_f_write(p, s): open(p, 'w', encoding='utf-8').write(s)
def _spk_f_read(p):     return open(p, encoding='utf-8').read()
def _spk_f_append(p, s):open(p, 'a', encoding='utf-8').write(s)
def _spk_f_copy(src, dst): _shu.copy2(src, dst)
def _spk_f_move(src, dst): _shu.move(src, dst)
def _spk_f_rename(p, new_name):
    _os.rename(p, _os.path.join(_os.path.dirname(p), new_name))
def _spk_f_delete(p):   _os.remove(p)
def _spk_file_exists_q(p): return _os.path.isfile(p)
def _spk_dir_exists_q(p):  return _os.path.isdir(p)
def _spk_dir_list(p):
    return [e for e in _os.listdir(p) if _os.path.isdir(_os.path.join(p, e))]
def _spk_dir_list_files(p):
    return [e for e in _os.listdir(p) if _os.path.isfile(_os.path.join(p, e))]
def _spk_dir_move_q(src, dst): _shu.move(src, dst)

# ── path utils ───────────────────────────────────────────────────────
def _spk_path_join(*parts): return _os.path.join(*parts)
def _spk_path_dir(p):  return _os.path.dirname(p)
def _spk_path_base(p): return _os.path.basename(p)
def _spk_path_ext(p):  return _os.path.splitext(p)[1]
def _spk_path_stem(p): return _os.path.splitext(_os.path.basename(p))[0]
def _spk_path_abs(p):  return _os.path.abspath(p)
def _spk_path_relative(p, base='.'): return _os.path.relpath(p, base)

# ── vspk prelude: http_get / xml_tag / xml_section ──────────────
import urllib.request as _urllib_req
import re as _re

def http_get(url):
    req = _urllib_req.Request(str(url), headers={"User-Agent": "Mozilla/5.0"})
    with _urllib_req.urlopen(req, timeout=10) as r:
        return r.read().decode('utf-8', errors='replace')

def xml_tag(text, tag):
    if not text: return 'N/A'
    m = _re.search(r'<' + tag + r'(?:s[^>]*)?>([^<]*)</' + tag + r'>', text)
    return m.group(1).strip() if m else 'N/A'

def xml_section(text, tag):
    if not text: return ''
    m = _re.search(r'<' + tag + r'(?:s[^>]*)?>(.+?)</' + tag + r'>', text, _re.DOTALL)
    return m.group(0) if m else ''

# ── vspk Python bridge — GUI real via vspk.exe / HTTP+SSE ─────────
import threading as _vspk_threading
import subprocess as _vspk_subprocess
import tempfile as _vspk_tempfile
import json as _vspk_json
import queue as _vspk_queue
import random as _vspk_random
import sys as _vspk_sys

_SPORK_CSS = "spork.css"
_SPORK_JS  = "spork.js"
_SPORK_CSS_CDN = "https://cdn.jsdelivr.net/gh/unoudos/spork-ui@main/spork.css"
_SPORK_JS_CDN  = "https://cdn.jsdelivr.net/gh/unoudos/spork-ui@main/spork.js"

def _vr(x):
    if x is None: return ''
    if hasattr(x, 'to_html'): return x.to_html()
    return str(x)

def html_escape(s):
    return str(s).replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

class _VspkState:
    def __init__(self, key, default):
        self._key    = key
        self._val    = default
        self._app    = None
    def set(self, val):
        self._val = val
        if self._app: self._app._push_state(self._key, val)
    def get(self):        return self._val
    def to_html(self):    return f'<span data-spork-text="{self._key}"></span>'
    def __str__(self):    return self.to_html()

class _VspkApp:
    def __init__(self, title, width=1024, height=768, theme='light', accent=''):
        self._title      = title
        self._width      = int(width)
        self._height     = int(height)
        self._theme      = theme
        self._accent     = accent
        self._port       = _vspk_random.randint(20000, 30000)
        self._states     = {}
        self._children   = []
        self._callbacks  = {}
        self._cb_count   = 0
        self._sse_queues = []
        self._cb_queue   = _vspk_queue.Queue()

    def state(self, key, default=None):
        s = _VspkState(key, default)
        s._app = self
        self._states[key] = s
        return s

    def add(self, *children):
        self._children.extend(children)

    def on_click(self, fn=None):
        if fn is None: return self
        self._cb_count += 1
        cb_id = f"cb_{self._cb_count}"
        self._callbacks[cb_id] = fn
        return f"fetch('/cb/{cb_id}')"

    def _push_state(self, name, value):
        msg = f"event: state\ndata: {_vspk_json.dumps({'name': name, 'value': value})}\n\n"
        for q in list(self._sse_queues):
            try: q.put_nowait(msg)
            except: pass

    def _build_html(self):
        state_json = _vspk_json.dumps({k: s._val for k, s in self._states.items()})
        body_html  = '\n'.join(str(c) for c in self._children if c is not None)
        accent_css = f'<style>:root{{--sz-accent:{self._accent};}}.sz-btn-filled{{background:{self._accent};border-color:{self._accent};}}</style>' if self._accent else ''
        port = self._port
        return f"""<!DOCTYPE html>
<html data-theme="{self._theme}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{html_escape(self._title)}</title>
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="{_SPORK_CSS}" onerror="this.onerror=null;this.href='{_SPORK_CSS_CDN}'">
  {accent_css}
</head>
<body class="sz-body">
<div id="__app" class="sz-page">
{body_html}
</div>
<script>
window.__state={state_json};
window.__set=function(n,v){{
  window.__state[n]=v;
  document.querySelectorAll('[data-spork-text="'+n+'"]').forEach(function(e){{e.textContent=v;}});
  document.querySelectorAll('[data-spork-bind="'+n+'"]').forEach(function(e){{
    if(e.type==='checkbox')e.checked=v;else e.value=v;
  }});
  document.querySelectorAll('[data-spork-checked="'+n+'"]').forEach(function(e){{e.checked=!!v;}});
}};
window.__vspk = true;
Object.keys(window.__state).forEach(function(k){{window.__set(k,window.__state[k]);}});
(function sse(){{
  var es=new EventSource('http://localhost:{port}/events');
  es.addEventListener('state',function(e){{var d=JSON.parse(e.data);window.__set(d.name,d.value);}});
  es.addEventListener('eval',function(e){{try{{eval(JSON.parse(e.data));}}catch(err){{}}}});
  es.onerror=function(){{es.close();setTimeout(sse,1000);}};
}})();
</script>
<script src="{_SPORK_JS}" onerror="var s=document.createElement('script');s.src='{_SPORK_JS_CDN}';document.body.appendChild(s)"></script>
</body>
</html>"""

    def _start_server(self):
        import http.server as _hs
        app = self
        class _H(_hs.BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_OPTIONS(self):
                self.send_response(204)
                self.send_header('Access-Control-Allow-Origin','*')
                self.end_headers()
            def do_GET(self):
                if self.path == '/events':
                    self.send_response(200)
                    self.send_header('Content-Type','text/event-stream')
                    self.send_header('Cache-Control','no-cache')
                    self.send_header('Access-Control-Allow-Origin','*')
                    self.end_headers()
                    q = _vspk_queue.Queue()
                    app._sse_queues.append(q)
                    try:
                        while True:
                            try:
                                msg = q.get(timeout=25)
                                self.wfile.write(msg.encode()); self.wfile.flush()
                            except _vspk_queue.Empty:
                                self.wfile.write(b': ping\n\n'); self.wfile.flush()
                    except Exception: pass
                    finally:
                        try: app._sse_queues.remove(q)
                        except: pass
                elif self.path.startswith('/cb/'):
                    cb_id = self.path[4:]
                    app._cb_queue.put(cb_id)
                    self.send_response(200)
                    self.send_header('Content-Type','text/plain')
                    self.send_header('Access-Control-Allow-Origin','*')
                    self.end_headers()
                    self.wfile.write(b'ok')
                elif self.path == '/favicon.ico':
                    self.send_response(204)
                    self.send_header('Access-Control-Allow-Origin','*')
                    self.end_headers()
                else:
                    self.send_response(404); self.end_headers()
        # ThreadingHTTPServer: con HTTPServer (un solo hilo) la conexión SSE de /events
        # bloqueaba el servidor entero y los /cb/ (clics) nunca se atendían.
        srv = _hs.ThreadingHTTPServer(('localhost', app._port), _H)
        srv.daemon_threads = True
        _vspk_threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv

    def _find_vspk(self):
        exe = 'vspk.exe' if _vspk_sys.platform == 'win32' else 'vspk'
        cwd = _os.getcwd()
        for d in [_os.path.dirname(cwd), cwd]:
            c = _os.path.join(d, exe)
            if _os.path.exists(c): return c
        return exe

    def _find_icon(self):
        # Solo la carpeta propia (cwd y la del script); sin icono -> el del rayito (vspk_default.ico)
        cwd = _os.getcwd()
        try:
            sd = _os.path.dirname(_os.path.abspath(sys.argv[0]))
        except Exception:
            sd = cwd
        names = ['icon.ico', 'icon.png', 'favicon.ico', 'favicon.png']
        for d in (cwd, sd):
            for name in names:
                p = _os.path.join(d, name)
                if _os.path.exists(p): return p
        d = _os.environ.get('VSPK_DEFAULT_ICON', '')
        if d and _os.path.exists(d): return d
        for start in (sd, cwd):
            cur = start
            for _ in range(10):
                p = _os.path.join(cur, 'vspk_default.ico')
                if _os.path.exists(p): return p
                nxt = _os.path.dirname(cur)
                if nxt == cur: break
                cur = nxt
        return ''

    def run(self):
        srv = self._start_server()
        html = self._build_html()
        fd, htv = _vspk_tempfile.mkstemp(prefix='vspk_', suffix='.htv')
        _os.close(fd)
        icon_path = self._find_icon()
        icon_line = f'icon: {icon_path}\n' if icon_path else ''
        with open(htv, 'w', encoding='utf-8') as f:
            f.write(f"title: {self._title}\nwidth: {self._width}\nheight: {self._height}\ndevtools: true\n{icon_line}\n{html}")
        vspk_exe = self._find_vspk()
        try:
            proc = _vspk_subprocess.Popen([vspk_exe, htv])
            while proc.poll() is None:
                try:
                    cb_id = self._cb_queue.get(timeout=0.015)
                    if cb_id in self._callbacks:
                        try: self._callbacks[cb_id]()
                        except: pass
                except _vspk_queue.Empty: pass
        except FileNotFoundError:
            print(f"[vspk] No se encontró '{vspk_exe}' — mostrando datos en consola:")
            for k, s in self._states.items():
                v = s.get()
                if v: print(f"  {k}: {v}")
        finally:
            try: _os.unlink(htv)
            except: pass
            try: srv.shutdown()
            except: pass

def App(title, *a, **kw):
    w = a[0] if len(a) > 0 else kw.get('width',  1024)
    h = a[1] if len(a) > 1 else kw.get('height', 768)
    t = a[2] if len(a) > 2 else kw.get('theme',  'light')
    ac= a[3] if len(a) > 3 else kw.get('accent', '')
    return _VspkApp(title, w, h, t, ac)

_builtin_set = set
def set(obj, val=None):
    if isinstance(obj, _VspkState): obj.set(val)
    elif val is None: return _builtin_set(obj)
def state(app, key, default=None):   return app.state(key, default)
def add(app, *children):             app.add(*children)
def on_click(app, fn=None):          return app.on_click(fn)
def run(app):                        app.run()

# Widgets — devuelven HTML real
def Col(*kids):  return f'<div class="sz-col sz-center">{"".join(str(c) for c in kids if c is not None)}</div>'
def Row(*kids):  return f'<div class="sz-row">{"".join(str(c) for c in kids if c is not None)}</div>'
def Card(*kids): return f'<div class="sz-card">{"".join(str(c) for c in kids if c is not None)}</div>'
def H1(x):  return f'<h1 class="sz-h1">{x}</h1>'
def H2(x):  return f'<h2 class="sz-h2">{x}</h2>'
def H3(x):  return f'<h3 class="sz-h3">{x}</h3>'
def P(x):   return f'<p class="sz-p">{x}</p>'
def Hr():   return '<hr class="sz-divider">'
def Button(label, handler=None, style='filled', size=''):
    css = f"sz-btn sz-btn-{style}" + (f" sz-btn-{size}" if size else '')
    oc  = f' onclick="{html_escape(handler)}"' if isinstance(handler, str) else ''
    return f'<button class="{css}" data-ripple{oc}>{label}</button>'
def Img(id, alt=''):
    return f'<img id="{id}" alt="{alt}" src="" style="width:48px;height:48px;object-fit:contain;display:block;margin:8px auto;">'
def ImgScript(): return ''


# ── cwd / script dir ────────────────────────────────────────────────
def _spk_cd(p):  _os.chdir(p)
def _spk_pwd():  return _os.getcwd()
def _spk_script_dir():
    try:
        import inspect as _ins
        f = _ins.stack()[-1].filename
        return _os.path.dirname(_os.path.abspath(f)) if f != '<string>' else _os.getcwd()
    except Exception:
        return _os.getcwd()


if __name__ == "__main__":
    gui = App("Hola Mundo", 400, 300)
    msg = state(gui, "msg", "Pulsa el boton")
    add(gui, Card(H1("Hola Mundo"), P(msg), Button("Saludar", on_click(gui, lambda : set(msg, "Hola desde Spork!")))))
    run(gui)
