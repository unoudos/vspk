"""
vspk.py — GUI nativa para Python usando vspk (WebView) como ventana.

El programa Python abre un puente HTTP+SSE en 127.0.0.1 (puerto aleatorio), escribe un .htv temporal y
lanza vspk.exe. Mientras la ventana está abierta, run() atiende los clics (/cb/<id>), los eventos
(/event/<nombre>) y los valores de los campos enlazados, y empuja los cambios de estado por SSE.
spork.css y spork.js los sirve el propio vspk.exe (van incrustados). Todos los callbacks se ejecutan en el
hilo que llama a run(): no hace falta bloquear nada.

    import vspk
    app = vspk.App("Contador", width=400, height=300)
    n = app.state("n", 0)
    app.add(vspk.Col(vspk.H1(n), vspk.Row(
        vspk.Button("-", on_click=lambda: n.dec()), vspk.Button("+", on_click=lambda: n.inc()))))
    app.run()

Qué hay:
  · ids de callback y eventos internos con token (otra web local no puede dispararlos)
  · Button(on_click=fn) ejecuta fn en Python; Button(js="...") o js=lambda es JS puro en la página
  · app.on_key, app.on_close, app.pick_file/save_file/pick_folder, app.run_every/run_after,
    app.set_title/notify/copy_text/quit/toast/eval_js
  · app.canvas(id, w, h)  ·  MenuBar/Menu/MenuItem/MenuSep  ·  app.window(título, w, h) (ventanas extra)
"""

from __future__ import annotations
import builtins
builtins_open = builtins.open
import html as _html
import json
import os
import platform
import queue
import secrets
import socket
import subprocess
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlparse

# ── CDN de Spork UI (solo reserva: vspk.exe sirve spork.css/js por su cuenta) ─

_SPORK_CSS = "https://cdn.jsdelivr.net/gh/unoudos/spork-ui@main/spork.css"
_SPORK_JS  = "https://cdn.jsdelivr.net/gh/unoudos/spork-ui@main/spork.js"

# ── IPC ──────────────────────────────────────────────────────────────────────

_SOCK_UNIX    = "/tmp/vspk.sock"
_PIPE_WINDOWS = r"\\.\pipe\vspk"

def _is_windows() -> bool:
    return platform.system() == "Windows"

# ── Buscar ejecutable vspk ────────────────────────────────────────────────────

def _find_vspk() -> str:
    """
    Busca vspk.exe en este orden:
    1. Variable de entorno VSPK_EXE
    2. Junto al script que llama
    3. Junto a vspk.py
    4. C:\\spork y otras rutas fijas en Windows
    5. En el PATH del sistema
    """
    import shutil
    exe = "vspk.exe" if _is_windows() else "vspk"
    candidates: list = []

    env = os.environ.get("VSPK_EXE")
    if env:
        candidates.append(Path(env))

    import __main__
    if hasattr(__main__, "__file__"):
        candidates.append(Path(__main__.__file__).resolve().parent / exe)

    candidates.append(Path(__file__).resolve().parent / exe)

    if _is_windows():
        for d in [r"C:\spork", r"C:\spork_studio", r"C:\Program Files\spork"]:
            candidates.append(Path(d) / exe)

    found = shutil.which("vspk")
    if found:
        candidates.append(Path(found))

    for c in candidates:
        if c.exists():
            return str(c)

    return exe  # fallback — el SO reportará el error


def _ipc_send(msg: dict) -> Optional[dict]:
    line = json.dumps(msg) + "\n"
    try:
        if _is_windows():
            with builtins_open(_PIPE_WINDOWS, "r+b", buffering=0) as pipe:
                pipe.write(line.encode())
                resp = b""
                while not resp.endswith(b"\n"):
                    resp += pipe.read(1)
                return json.loads(resp.decode().strip())
        else:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(_SOCK_UNIX)
                s.sendall(line.encode())
                resp = b""
                while not resp.endswith(b"\n"):
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    resp += chunk
                return json.loads(resp.decode().strip())
    except Exception:
        return None

# ── Utilidades ────────────────────────────────────────────────────────────────

def _h(s: Any) -> str:
    return _html.escape("" if s is None else str(s), quote=True)

def _js(v: Any) -> str:
    """JSON para incrustar en JS dentro de HTML (sin romper </script>)."""
    return json.dumps(v, ensure_ascii=False).replace("</", "<\\/")

_CURRENT_APP: Optional["App"] = None   # la última App creada (los widgets la usan por defecto)

# ── Estado reactivo ───────────────────────────────────────────────────────────

class _JsExpr:
    """Expresión JS con soporte aritmético para compilar lambdas (js=lambda: ...)."""
    def __init__(self, js: str): self._js = js
    def _o(self, o): return o._js if isinstance(o, _JsExpr) else json.dumps(o)
    def __add__(self, o): return _JsExpr(f"({self._js}+{self._o(o)})")
    def __sub__(self, o): return _JsExpr(f"({self._js}-{self._o(o)})")
    def __mul__(self, o): return _JsExpr(f"({self._js}*{self._o(o)})")
    def __radd__(self, o): return _JsExpr(f"({json.dumps(o)}+{self._js})")
    def __rsub__(self, o): return _JsExpr(f"({json.dumps(o)}-{self._js})")
    def __repr__(self): return self._js

class _JsState:
    """Proxy de State que genera JS en lugar de ejecutar Python."""
    def __init__(self, name: str): self._name = name
    def get(self): return _JsExpr(f"window.__state.{self._name}")
    def set(self, value) -> str:
        v = value._js if isinstance(value, _JsExpr) else json.dumps(value)
        return f"window.__set('{self._name}',{v})"
    def inc(self, by=1) -> str: return self.set(self.get() + by)
    def dec(self, by=1) -> str: return self.set(self.get() - by)


class State:
    """
    Variable reactiva. Cuando cambia con .set(), todas las ventanas se actualizan sin recargar.

        count = app.state("count", 0)
        count.set(count.get() + 1)
    """

    def __init__(self, name: str, value: Any, app: "App"):
        self._name     = name
        self._value    = value
        self._app      = app
        self._watchers: list = []

    def get(self) -> Any:
        return self._value

    def set(self, value: Any) -> None:
        self._value = value
        self._app._push_state(self._name, value)

    def inc(self, by: float = 1) -> None:
        cur = self._value if isinstance(self._value, (int, float)) and not isinstance(self._value, bool) else 0
        self.set(cur + by)

    def dec(self, by: float = 1) -> None:
        self.inc(-by)

    def on_change(self, fn: Callable[[Any], None]) -> "State":
        """fn(valor) cada vez que el usuario cambia el campo enlazado a este estado."""
        self._watchers.append(fn)
        return self

    def _receive(self, value: Any) -> None:
        """Valor recibido de la página (no se reenvía a la ventana que lo escribió)."""
        self._value = value
        for w in self._watchers:
            w(value)

    # JS para usar dentro de onclick="..."
    def js_get(self) -> str: return f"window.__state[{_js(self._name)}]"
    def js_set(self, v) -> str: return f"window.__set({_js(self._name)},{_js(v)})"
    def js_inc(self, by=1) -> str: return f"window.__set({_js(self._name)},(+window.__state[{_js(self._name)}]||0)+{by})"
    def js_dec(self, by=1) -> str: return self.js_inc(-by)

    # Span reactivo — usar directamente como contenido de un widget
    def __str__(self) -> str:
        v = self._value
        txt = ("true" if v else "false") if isinstance(v, bool) else (str(v) if isinstance(v, (int, float, str)) else "")
        return f'<span data-spork-text="{_h(self._name)}">{_h(txt)}</span>'

    @property
    def name(self) -> str:
        return self._name


def _compile_callback(fn: Callable) -> str:
    """
    Compila una lambda Python → JS sustituyendo State por _JsState.
    Solo para js=lambda: ...; el resultado tiene que ser un str (lo que devuelve state.set()).
    """
    import types
    if not callable(fn):
        return ""
    try:
        fake_globals = {
            k: _JsState(v._name) if isinstance(v, State) else v
            for k, v in fn.__globals__.items()
        }
        if fn.__closure__:
            cells = []
            for cell, varname in zip(fn.__closure__, fn.__code__.co_freevars):
                try:
                    val = cell.cell_contents
                    cells.append(types.CellType(_JsState(val._name)) if isinstance(val, State) else cell)
                except ValueError:
                    cells.append(cell)
            new_fn = types.FunctionType(fn.__code__, fake_globals, fn.__name__, fn.__defaults__, tuple(cells))
        else:
            new_fn = types.FunctionType(fn.__code__, fake_globals, fn.__name__, fn.__defaults__)
        result = new_fn()
        return result if isinstance(result, str) and result else ""
    except Exception:
        return ""

def _to_js_expr(val: Any) -> str:
    """Convierte un valor Python a expresión JS para data-spork-*."""
    if isinstance(val, str):   return val
    if isinstance(val, State): return val.js_get()
    if callable(val):          return _compile_callback(val)
    return json.dumps(val)

# ── Base Widget ───────────────────────────────────────────────────────────────

class Widget:
    """Base de todos los widgets. Genera HTML compatible con spork.css."""

    tag:     str = "div"
    classes: str = ""

    def __init__(self, *children, **props):
        self._style: str = props.pop("style", "")
        self._class: str = (props.pop("cls", "") + " " + props.pop("class_", "")).strip()
        self._id:    str = props.pop("id", "")
        if_     = props.pop("if_",     None)
        style_  = props.pop("style_",  None)
        class_r = props.pop("class_r", None)
        self.children: list = list(children)
        self.props = props
        self._extra_attrs: dict[str, str] = {}
        if if_ is not None:
            js = _to_js_expr(if_)
            if js: self._extra_attrs["data-spork-if"] = js
        if style_ is not None:
            js = _to_js_expr(style_)
            if js: self._extra_attrs["data-spork-style"] = js
        if class_r is not None:
            self._extra_attrs["data-spork-class"] = json.dumps(
                {k: _to_js_expr(v) for k, v in class_r.items()}
            )

    def _render_attrs(self) -> str:
        attrs = []
        if self._id:
            attrs.append(f'id="{_h(self._id)}"')
        cls = (f"{self.classes} {self._class}").strip()
        if cls:
            attrs.append(f'class="{_h(cls)}"')
        if self._style:
            attrs.append(f'style="{_h(self._style)}"')
        for k, v in self._extra_attrs.items():
            attrs.append(f'{k}="{_h(v)}"')
        return (" " + " ".join(attrs)) if attrs else ""

    def _render_child(self, c) -> str:
        if isinstance(c, Widget):
            return c.render()
        if isinstance(c, State):
            return str(c)
        return str(c) if c is not None else ""

    def _render_children(self) -> str:
        return "\n".join(self._render_child(c) for c in self.children)

    def render(self) -> str:
        attrs = self._render_attrs()
        inner = self._render_children()
        if inner:
            return f"<{self.tag}{attrs}>\n{inner}\n</{self.tag}>"
        return f"<{self.tag}{attrs}></{self.tag}>"

    def add(self, *widgets) -> "Widget":
        self.children.extend(widgets)
        return self

    def __str__(self) -> str:
        return self.render()


class Raw(Widget):
    """HTML tal cual."""
    def __init__(self, html: str = ""):
        super().__init__()
        self._html = html
    def render(self) -> str:
        return self._html

def _bind_attr(bind: Optional[State]) -> str:
    return f' data-spork-bind="{_h(bind.name)}"' if bind is not None else ""

# ── Layout ────────────────────────────────────────────────────────────────────

class Row(Widget):
    tag = "div"; classes = "sz-row"
    def __init__(self, *children, align: str = "", padding: int = 0, **props):
        if align:   props["cls"] = (props.get("cls","") + f" sz-{align}").strip()
        if padding: props["cls"] = (props.get("cls","") + f" sz-p-{padding}").strip()
        super().__init__(*children, **props)

class Col(Widget):
    tag = "div"; classes = "sz-col sz-center"
    def __init__(self, *children, align: str = "", padding: int = 0, **props):
        if align:   props["cls"] = (props.get("cls","") + f" sz-{align}").strip()
        if padding: props["cls"] = (props.get("cls","") + f" sz-p-{padding}").strip()
        super().__init__(*children, **props)

class Grid(Widget):
    tag = "div"; classes = "sz-grid"

class Card(Widget):
    tag = "div"; classes = "sz-card"

class Container(Widget):
    tag = "div"; classes = "sz-container"

class Section(Widget):
    tag = "section"

class Header(Widget):
    tag = "header"

class Footer(Widget):
    tag = "footer"; classes = "sz-footer"

class Nav(Widget):
    tag = "nav"; classes = "sz-nav"

class Main(Widget):
    tag = "main"

class Aside(Widget):
    tag = "aside"

class Article(Widget):
    tag = "article"

class Gap(Widget):
    tag = "div"
    def __init__(self, size: str = "1rem"):
        super().__init__()
        self._style = f"height:{size}"

class Hr(Widget):
    tag = "hr"; classes = "sz-divider"
    def render(self) -> str:
        return f"<hr{self._render_attrs()}>"

class Spacer(Widget):
    tag = "div"; classes = "sz-grow"
    def __init__(self): super().__init__()

# ── Texto ─────────────────────────────────────────────────────────────────────

class H1(Widget):
    tag = "h1"; classes = "sz-h1"
    def __init__(self, text="", **props): super().__init__(text, **props)

class H2(Widget):
    tag = "h2"; classes = "sz-h2"
    def __init__(self, text="", **props): super().__init__(text, **props)

class H3(Widget):
    tag = "h3"; classes = "sz-h3"
    def __init__(self, text="", **props): super().__init__(text, **props)

class H4(Widget):
    tag = "h4"; classes = "sz-h4"
    def __init__(self, text="", **props): super().__init__(text, **props)

class P(Widget):
    tag = "p"; classes = "sz-p"
    def __init__(self, text="", **props): super().__init__(text, **props)

class Span(Widget):
    tag = "span"
    def __init__(self, text="", **props): super().__init__(text, **props)

class Label(Widget):
    tag = "label"; classes = "sz-label"
    def __init__(self, text="", **props): super().__init__(text, **props)

class Strong(Widget):
    tag = "strong"; classes = "sz-bold"
    def __init__(self, text="", **props): super().__init__(text, **props)

class Badge(Widget):
    tag = "span"; classes = "sz-badge"
    def __init__(self, text="", **props): super().__init__(text, **props)

class Text(Widget):
    tag = "span"
    def __init__(self, text="", **props): super().__init__(text, **props)

class Alert(Widget):
    tag = "div"; classes = "sz-alert"
    def __init__(self, text="", *, variant: str = "", **props):
        if variant: props["cls"] = (props.get("cls","") + f" sz-alert-{variant}").strip()
        super().__init__(text, **props)

class Progress(Widget):
    """Progress(state) — la barra se mueve sola cuando cambia el State — o Progress(40)."""
    tag = "div"; classes = "sz-progress"
    def __init__(self, value: Any = 0, max: int = 100, **props):
        super().__init__(**props)
        self._value = value
        self._max = max or 100
    def render(self) -> str:
        if isinstance(self._value, State):
            k = _js(self._value.name)
            pct = round(max(0.0, min(100.0, float(self._value.get() or 0) / self._max * 100)), 1)
            expr = '{"width":(Math.min(100,Math.max(0,(+window.__state[' + k + ']||0)/' + str(self._max) + '*100)).toFixed(1)+"%")}'
            ds = f' data-spork-style="{_h(expr)}"'
        else:
            pct = round(max(0.0, min(100.0, float(self._value or 0) / self._max * 100)), 1)
            ds = ""
        return f'<div{self._render_attrs()}><div class="sz-progress-bar" style="width:{pct}%"{ds}></div></div>'

class Chip(Widget):
    tag = "span"; classes = "sz-chip"
    def __init__(self, text="", *, primary: bool = False, **props):
        if primary: props["cls"] = (props.get("cls","") + " sz-chip-primary").strip()
        super().__init__(text, **props)

class For(Widget):
    """Lista reactiva. items=State con lista, row=función widget por item."""
    tag = "div"
    def __init__(self, items: State, row: Callable, *, var: str = "item", **props):
        super().__init__(**props)
        self._items = items
        self._row   = row
        self._var   = var
        self._fid   = f"for_{id(self)}"
    def render(self) -> str:
        try:
            sample = self._row(_JsExpr(self._var))
            tmpl = sample.render() if isinstance(sample, Widget) else str(sample)
        except Exception:
            tmpl = ""
        attrs = self._render_attrs()
        fid   = self._fid
        src   = self._items.name
        var   = self._var
        return (
            f'<div{attrs} id="{fid}" data-spork-for-src="{src}" data-spork-for-var="{var}"></div>\n'
            f'<template data-spork-for-template="{fid}">{tmpl}</template>'
        )

# ── Interacción ───────────────────────────────────────────────────────────────

class Button(Widget):
    """
    Button("Texto", on_click=fn)      → fn() se ejecuta en Python (puede usar cualquier State/API)
    Button("Texto", js="alert(1)")    → JS puro en la página (instantáneo, sin pasar por Python)
    Button("Texto", js=lambda: n.set(n.get() + 1))   → lambda compilada a JS
    """
    tag = "button"; classes = "sz-btn"

    def __init__(self, text: str = "", *,
                 on_click:  Optional[Callable] = None,
                 js:        Any  = None,
                 variant:   str  = "filled",
                 size:      str  = "",
                 full:      bool = False,
                 disabled:  bool = False,
                 _app:      Optional["App"] = None,
                 **props):
        extra = f"sz-btn-{variant}"
        if size: extra += f" sz-btn-{size}"
        if full: extra += " sz-btn-full"
        props["cls"] = (props.get("cls","") + " " + extra).strip()
        super().__init__(text, **props)
        if not disabled:
            if js is not None:
                code = js if isinstance(js, str) else _compile_callback(js)
                if code:
                    self._extra_attrs["onclick"] = code
            elif on_click is not None:
                app = _app or _CURRENT_APP
                if app is None:
                    raise RuntimeError("[vspk] crea la App antes de los widgets con on_click")
                self._extra_attrs["onclick"] = app.on_click(on_click)
        if disabled:
            self._extra_attrs["disabled"] = "disabled"
        self._extra_attrs["data-ripple"] = ""


def _payload_js(fn: Callable, expr: str, app: Optional["App"]) -> str:
    app = app or _CURRENT_APP
    if app is None:
        raise RuntimeError("[vspk] crea la App antes de los widgets con on_change")
    return app._on_payload(fn, expr)


class Input(Widget):
    tag = "input"; classes = "sz-input"

    def __init__(self, *,
                 placeholder: str = "",
                 value:       str = "",
                 type:        str = "text",
                 bind:        Optional[State] = None,
                 on_change:   Optional[Callable[[str], None]] = None,
                 _app:        Optional["App"] = None,
                 **props):
        super().__init__(**props)
        self._bind = bind
        self._value = value
        if placeholder:    self._extra_attrs["placeholder"] = placeholder
        if type != "text": self._extra_attrs["type"] = type
        if on_change and not bind:
            self._extra_attrs["oninput"] = _payload_js(on_change, "this.value", _app)

    def render(self) -> str:
        val = self._bind.get() if self._bind is not None else self._value
        v = f' value="{_h(val)}"' if val not in (None, "") else ""
        return f"<input{self._render_attrs()}{v}{_bind_attr(self._bind)}>"


class Textarea(Widget):
    tag = "textarea"; classes = "sz-textarea"

    def __init__(self, value: str = "", *,
                 placeholder: str = "",
                 rows:        int  = 4,
                 bind:        Optional[State] = None,
                 on_change:   Optional[Callable[[str], None]] = None,
                 _app:        Optional["App"] = None,
                 **props):
        super().__init__(**props)
        self._value = value
        self._bind = bind
        if placeholder: self._extra_attrs["placeholder"] = placeholder
        self._extra_attrs["rows"] = str(rows)
        if on_change and not bind:
            self._extra_attrs["oninput"] = _payload_js(on_change, "this.value", _app)

    def render(self) -> str:
        val = self._bind.get() if self._bind is not None else self._value
        return f"<textarea{self._render_attrs()}{_bind_attr(self._bind)}>{_h(val)}</textarea>"


class Slider(Widget):
    tag = "input"; classes = "sz-slider"
    def __init__(self, bind: Optional[State] = None, min: int = 0, max: int = 100, step: int = 1, **props):
        super().__init__(**props)
        self._bind, self._min, self._max, self._step = bind, min, max, step
    def render(self) -> str:
        val = self._bind.get() if self._bind is not None else self._min
        return (f'<input{self._render_attrs()} type="range" min="{self._min}" max="{self._max}" '
                f'step="{self._step}" value="{_h(val)}"{_bind_attr(self._bind)}>')


class Select(Widget):
    tag = "select"; classes = "sz-select"

    def __init__(self, options: list, *,
                 value:     str = "",
                 bind:      Optional[State] = None,
                 on_change: Optional[Callable[[str], None]] = None,
                 _app:      Optional["App"] = None,
                 **props):
        super().__init__(**props)
        self._options = options
        self._value   = value
        self._bind    = bind
        if on_change and not bind:
            self._extra_attrs["onchange"] = _payload_js(on_change, "this.value", _app)

    def render(self) -> str:
        cur = str(self._bind.get()) if self._bind is not None else str(self._value)
        opts = []
        for o in self._options:
            v, label = o if isinstance(o, (tuple, list)) else (o, o)
            sel = " selected" if str(v) == cur else ""
            opts.append(f'<option value="{_h(v)}"{sel}>{_h(label)}</option>')
        return f"<select{self._render_attrs()}{_bind_attr(self._bind)}>" + "".join(opts) + "</select>"


class Checkbox(Widget):
    """Interruptor (sz-switch, la clase real de spork.css)."""
    tag = "label"; classes = ""

    def __init__(self, label: str = "", *,
                 checked:   bool = False,
                 bind:      Optional[State] = None,
                 on_change: Optional[Callable[[bool], None]] = None,
                 _app:      Optional["App"] = None,
                 **props):
        super().__init__(**props)
        self._label     = label
        self._checked   = checked
        self._bind      = bind
        self._onchange  = ""
        if on_change and not bind:
            self._onchange = f' onchange="{_h(_payload_js(on_change, "this.checked", _app))}"'

    def render(self) -> str:
        on = bool(self._bind.get()) if self._bind is not None else self._checked
        return ('<label class="sz-switch">'
                f'<input type="checkbox"{" checked" if on else ""}{_bind_attr(self._bind)}{self._onchange}>'
                '<span class="sz-switch-track"><span class="sz-switch-thumb"></span></span>'
                f'<span class="sz-switch-label">{_h(self._label)}</span>'
                '</label>')

# ── Media ─────────────────────────────────────────────────────────────────────

class Img(Widget):
    tag = "img"; classes = "sz-img"
    def __init__(self, src: str, alt: str = "", **props):
        super().__init__(**props)
        self._extra_attrs["src"] = src
        self._extra_attrs["alt"] = alt
    def render(self) -> str:
        return f"<img{self._render_attrs()}>"

class ImgState(Widget):
    """Imagen cuyo src se actualiza via state reactivo (el id del <img> es el nombre del state)."""
    tag = "img"
    def __init__(self, state_key: str, alt: str = "", **props):
        super().__init__(**props)
        self._state_key = state_key
        self._extra_attrs["id"]    = state_key
        self._extra_attrs["alt"]   = alt
        self._extra_attrs["src"]   = ""
        self._extra_attrs["style"] = "width:48px;height:48px;object-fit:contain;display:block;margin:8px auto"
    def render(self) -> str:
        return f"<img{self._render_attrs()}>"

class ImgScript(Widget):
    """Script que actualiza el src de ImgState cuando cambia el estado."""
    tag = "div"
    def render(self) -> str:
        return """<script>
(function() {
    var _orig = window.__set;
    window.__set = function(k, v) {
        if (_orig) _orig(k, v);
        var el = document.getElementById(k);
        if (el && el.tagName === 'IMG' && v) { el.src = v; el.dataset.loaded = v; }
    };
    var s = window.__state || {};
    for (var k in s) {
        var el = document.getElementById(k);
        if (el && el.tagName === 'IMG' && s[k]) el.src = s[k];
    }
})();
</script>"""

class Video(Widget):
    tag = "video"; classes = "sz-video"
    def __init__(self, src: str, *, controls: bool = True, **props):
        super().__init__(**props)
        self._extra_attrs["src"] = src
        if controls: self._extra_attrs["controls"] = "controls"

class Audio(Widget):
    tag = "audio"; classes = "sz-audio"
    def __init__(self, src: str, *, controls: bool = True, **props):
        super().__init__(**props)
        self._extra_attrs["src"] = src
        if controls: self._extra_attrs["controls"] = "controls"

# ── Listas ────────────────────────────────────────────────────────────────────

class Ul(Widget):
    tag = "ul"; classes = "sz-ul"

class Ol(Widget):
    tag = "ol"; classes = "sz-ol"

class Li(Widget):
    tag = "li"; classes = "sz-li"
    def __init__(self, text="", **props): super().__init__(text, **props)

class Link(Widget):
    tag = "a"
    def __init__(self, text="", href="#", **props):
        super().__init__(text, **props)
        self._extra_attrs["href"] = href

# ── Canvas ────────────────────────────────────────────────────────────────────
#
#   cv = app.canvas("lienzo", 400, 300)
#   cv.color("#6750A4").rect(10, 10, 100, 60); cv.circle(200, 60, 40); cv.line(0, 0, 400, 300)
#   cv.text(10, 280, "hola"); cv.erase(); cv.on_mouse(lambda e: ...)   # e: type down|up|move|click, x, y, button

class Canvas(Widget):
    tag = "canvas"
    def __init__(self, app: "App", cid: str, w: int, h: int):
        super().__init__()
        self._app, self.id, self.w, self.h = app, cid, w, h
    def render(self) -> str:
        return (f'<canvas id="{_h(self.id)}" width="{self.w}" height="{self.h}" style="width:{self.w}px;max-width:100%;'
                'height:auto;border:1px solid rgba(128,128,128,.4);border-radius:8px;touch-action:none"></canvas>')
    def _op(self, op, *args):
        self._app._cv(self.id, op, list(args)); return self
    def color(self, c):               return self._op("color", c)
    def line_width(self, n):          return self._op("lw", n)
    def font(self, size):             return self._op("font", size)
    def line(self, x1, y1, x2, y2):   return self._op("line", x1, y1, x2, y2)
    def rect(self, x, y, w, h):       return self._op("rect", x, y, w, h)
    def frame(self, x, y, w, h):      return self._op("frame", x, y, w, h)
    def circle(self, x, y, r):        return self._op("circle", x, y, r)
    def ring(self, x, y, r):          return self._op("ring", x, y, r)
    def text(self, x, y, s):          return self._op("text", x, y, s)
    def poly(self, points):           return self._op("poly", [list(p) for p in points])
    def erase(self):                  return self._op("clear")
    def draw(self, js):               return self._op("draw", js)   # JS crudo con (ctx, canvas) en el ámbito
    def on_mouse(self, fn):
        self._app._cv_mouse(self.id, fn); return self

# ── Menús (barra de menú HTML con atajos de teclado) ─────────────────────────
#
#   app.add(MenuBar(
#       Menu("Archivo", MenuItem("Abrir...", app.on_click(abrir), "ctrl+o"), MenuSep(),
#                       MenuItem("Salir", app.on_click(app.quit))),
#       Menu("Ayuda", MenuItem("Acerca de", app.on_click(acerca)))), resto...)
#   Atajos: "ctrl+o", "ctrl+shift+s", "alt+x", "f5"... (orden: ctrl, shift, alt, tecla).

_MENU_A = '<style>.sz-menubar{position:fixed;top:0;left:0;right:0;z-index:1000;display:flex;gap:2px;padding:3px 6px;background:var(--sz-surface,#fff);color:var(--sz-on-surface,#1d1b20);border-bottom:1px solid rgba(128,128,128,.3);font-size:14px}.sz-menubar-space{height:38px;width:100%;flex:none}.sz-menu{position:relative}.sz-menu-title{background:none;border:0;padding:6px 10px;border-radius:6px;color:inherit;font:inherit;cursor:pointer}.sz-menu-title:hover,.sz-menu.sz-open>.sz-menu-title{background:rgba(128,128,128,.18)}.sz-menu-list{display:none;position:absolute;top:100%;left:0;min-width:210px;padding:4px;background:var(--sz-surface,#fff);color:inherit;border:1px solid rgba(128,128,128,.35);border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.2)}.sz-menu.sz-open>.sz-menu-list{display:block}.sz-menu-item{display:flex;justify-content:space-between;gap:24px;width:100%;background:none;border:0;padding:6px 10px;border-radius:6px;color:inherit;font:inherit;cursor:pointer;text-align:left}.sz-menu-item:hover{background:rgba(128,128,128,.18)}.sz-menu-item kbd{opacity:.6;font:inherit;font-size:12px}.sz-menu-sep{height:1px;margin:4px 6px;background:rgba(128,128,128,.3)}.sz-native .sz-menubar,.sz-native .sz-menubar-space{display:none!important}</style><div class="sz-menubar">'
_MENU_B = '</div><div class="sz-menubar-space"></div><script>(function(){if(window.__menu)return;window.__menu=1;var bar=document.querySelector(\'.sz-menubar\');function menus(){return bar.querySelectorAll(\':scope > .sz-menu\')}window.__vspk_menu_click=function(id){var p=id.split(\'.\');var m=menus()[+p[0]];if(m)m.querySelector(\'.sz-menu-list\').children[+p[1]].click()};window.__vspk_menu_ok=function(){document.documentElement.classList.add(\'sz-native\')};if(bar&&window.ipc&&window.__vspk_native_menu_ok){var ms=[];Array.prototype.forEach.call(menus(),function(m,mi){var items=[];Array.prototype.forEach.call(m.querySelector(\'.sz-menu-list\').children,function(c,ii){if(c.classList.contains(\'sz-menu-sep\'))items.push({sep:true});else items.push({id:mi+\'.\'+ii,label:(c.querySelector(\'span\')||c).textContent,accel:c.getAttribute(\'data-accel\')||\'\'})});ms.push({label:m.querySelector(\'.sz-menu-title\').textContent,items:items})});window.ipc.postMessage(JSON.stringify({cmd:\'setMenu\',menu:ms}))}function closeAll(except){document.querySelectorAll(\'.sz-menu.sz-open\').forEach(function(m){if(m!==except)m.classList.remove(\'sz-open\')})}document.addEventListener(\'click\',function(e){var t=e.target.closest?e.target.closest(\'.sz-menu-title\'):null;closeAll(t?t.parentNode:null);if(t)t.parentNode.classList.toggle(\'sz-open\');var it=e.target.closest?e.target.closest(\'.sz-menu-item\'):null;if(it)closeAll(null)});document.addEventListener(\'mouseover\',function(e){var t=e.target.closest?e.target.closest(\'.sz-menu-title\'):null;var o=document.querySelector(\'.sz-menu.sz-open\');if(t&&o&&o!==t.parentNode){closeAll(t.parentNode);t.parentNode.classList.add(\'sz-open\')}});document.addEventListener(\'keydown\',function(e){if(e.key===\'Escape\'){closeAll(null);return}if(document.documentElement.classList.contains(\'sz-native\')&&!/Win/.test(navigator.platform))return;var k=(e.ctrlKey?\'ctrl+\':\'\')+(e.shiftKey?\'shift+\':\'\')+(e.altKey?\'alt+\':\'\')+e.key.toLowerCase();var items=document.querySelectorAll(\'.sz-menu-item[data-accel]\');for(var i=0;i<items.length;i++){var a=items[i].getAttribute(\'data-accel\');if(a&&a.toLowerCase()===k){e.preventDefault();items[i].click();return}}})})();</script>'

def MenuItem(label: str, js: str = "", shortcut: str = "") -> Widget:
    click = js.replace('"', "&quot;")
    kbd = f"<kbd>{_h(shortcut)}</kbd>" if shortcut else ""
    return Raw(f'<button type="button" class="sz-menu-item" onclick="{click}" data-accel="{_h(shortcut)}"><span>{_h(label)}</span>{kbd}</button>')

def MenuSep() -> Widget:
    return Raw('<div class="sz-menu-sep"></div>')

def Menu(title: str, *items) -> Widget:
    inner = "".join(i.render() if isinstance(i, Widget) else str(i) for i in items)
    return Raw(f'<div class="sz-menu"><button type="button" class="sz-menu-title">{_h(title)}</button><div class="sz-menu-list">{inner}</div></div>')

def MenuBar(*menus) -> Widget:
    inner = "".join(m.render() if isinstance(m, Widget) else str(m) for m in menus)
    return Raw(_MENU_A + inner + _MENU_B)

# ── Ventanas adicionales ─────────────────────────────────────────────────────
#
#   aj = app.window("Ajustes", 360, 240)
#   aj.add(Col(H4("Ajustes"), Input(bind=nombre)))    # los states se comparten entre ventanas
#   aj.show()   aj.close()   aj.on_close(lambda: True)   aj.set_title("...")   aj.eval_js("...")

# ── Tabla, árbol, lista (se hidratan en la página; ver vspk_ui.js incrustado en vspk.exe) ──

_vt_n = 0
def _vt_id(prefix: str) -> str:
    global _vt_n
    _vt_n += 1
    return f"{prefix}{_vt_n}"


class Table(Widget):
    """
    Table(["Nombre", "Edad"], [["Ana", 31], ["Luis", 28]], on_select=fn, on_dblclick=fn, on_sort=fn)
      · clic en la cabecera ordena (▲/▼, numérico si son números); ``sortable=False`` lo desactiva
      · on_select(d) → d = {"index", "row", "indexes", "rows"} (index = posición original en rows)
      · multi=True permite Ctrl/Shift; height="240px" activa scroll; header=False oculta la cabecera
      · columnas: "texto" o {"label": "Edad", "align": "right", "width": 80}
      · cambiar datos desde Python: app.table_set(t.id, rows[, cols])
    """
    classes = "vspk-table"
    def __init__(self, cols: list, rows: list, *,
                 on_select:   Optional[Callable[[dict], None]] = None,
                 on_dblclick: Optional[Callable[[dict], None]] = None,
                 on_sort:     Optional[Callable[[dict], None]] = None,
                 sortable: bool = True, multi: bool = False, striped: bool = True,
                 header: bool = True, height: Any = None, selected: int = -1,
                 _app: Optional["App"] = None, **props):
        if not props.get("id"): props["id"] = _vt_id("vt")
        super().__init__(**props)
        self.id = self._id
        cfg = {"cols": cols, "rows": rows, "sortable": sortable, "multi": multi,
               "striped": striped, "header": header, "selected": selected}
        if height is not None: cfg["height"] = height
        self._extra_attrs["data-vt"] = json.dumps(cfg, ensure_ascii=False)
        if on_select:   self._extra_attrs["data-on-select"]   = _payload_js(on_select,   "p", _app)
        if on_dblclick: self._extra_attrs["data-on-dblclick"] = _payload_js(on_dblclick, "p", _app)
        if on_sort:     self._extra_attrs["data-on-sort"]     = _payload_js(on_sort,     "p", _app)


def Listbox(items: list, *, on_select=None, on_dblclick=None, height: Any = None, _app=None, **props) -> Table:
    """Lista de una columna sin cabecera. on_select(d) → d["row"][0] es el elemento elegido."""
    return Table([""], [[x] for x in items], header=False, sortable=False, striped=False,
                 on_select=on_select, on_dblclick=on_dblclick, height=height, _app=_app, **props)


class Tree(Widget):
    """
    Tree([{"label": "src", "open": True, "children": [{"label": "main.rs", "id": 7}]}], on_select=fn)
      · on_select(d) → d = {"path": [0, 0], "label": "main.rs", "id": 7}
      · cambiar nodos: app.tree_set(t.id, nodes)
    """
    classes = "vspk-tree"
    def __init__(self, nodes: list, *,
                 on_select:   Optional[Callable[[dict], None]] = None,
                 on_dblclick: Optional[Callable[[dict], None]] = None,
                 height: Any = None, _app: Optional["App"] = None, **props):
        if not props.get("id"): props["id"] = _vt_id("vtree")
        super().__init__(**props)
        self.id = self._id
        cfg = {"nodes": nodes}
        self._extra_attrs["data-vt"] = json.dumps(cfg, ensure_ascii=False)
        if on_select:   self._extra_attrs["data-on-select"]   = _payload_js(on_select,   "p", _app)
        if on_dblclick: self._extra_attrs["data-on-dblclick"] = _payload_js(on_dblclick, "p", _app)
        if height is not None:
            h = height if isinstance(height, str) else f"{height}px"
            self._style = (self._style + f";max-height:{h}").strip(";")


def ColorPicker(*, value: str = "#6750a4", bind: Optional[State] = None, on_change=None, _app=None, **props) -> Input:
    """Selector de color nativo (<input type=color>). on_change(str) recibe '#rrggbb'."""
    return Input(type="color", value=value, bind=bind, on_change=on_change, _app=_app, **props)


def DatePicker(*, value: str = "", bind: Optional[State] = None, on_change=None, time: bool = False, _app=None, **props) -> Input:
    """Selector de fecha (<input type=date>) o fecha y hora con time=True. on_change(str) recibe 'AAAA-MM-DD'."""
    return Input(type="datetime-local" if time else "date", value=value, bind=bind, on_change=on_change, _app=_app, **props)



class ChildWindow:
    def __init__(self, app: "App", wid: str, title: str, width: int, height: int):
        self._app, self.id, self.title, self.width, self.height = app, wid, title, width, height
        self.widgets: list = []
        self.proc: Optional[subprocess.Popen] = None
        self.htv: str = ""
        self.want = False
        self.close_on = False
        self.close_js = ""

    def add(self, *widgets) -> "ChildWindow":
        self.widgets.extend(widgets); return self
    def show(self) -> "ChildWindow":
        self._app._win_show(self); return self
    def close(self) -> None:
        self._app._win_eval(self, "__vspk.close()")
    def set_title(self, t: str) -> None:
        self._app._win_eval(self, f"__vspk.setTitle({_js(t)})")
    def eval_js(self, js: str) -> None:
        self._app._win_eval(self, js)
    def on_close(self, fn: Callable[[], Any]) -> "ChildWindow":
        self._app._win_on_close(self, fn); return self
    def is_open(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

# ── App ───────────────────────────────────────────────────────────────────────

_PAGE_JS = 'window.__state = %STATE%;\nwindow.__win = %WIN%;\nwindow.__set = function(name, value) {\n  window.__state[name] = value;\n  document.querySelectorAll(\'[data-spork-text="\' + name + \'"]\').forEach(function(el) { el.textContent = value; });\n  document.querySelectorAll(\'[data-spork-bind="\' + name + \'"]\').forEach(function(el) {\n    if (el.type === \'checkbox\') el.checked = !!value;\n    else if (el.value != value) el.value = value;\n  });\n  var ev = function(code) { return new Function(\'return (\' + code + \')\')(); };\n  document.querySelectorAll(\'[data-spork-style]\').forEach(function(el) { try { Object.assign(el.style, ev(el.dataset.sporkStyle)); } catch(_) {} });\n  document.querySelectorAll(\'[data-spork-if]\').forEach(function(el) { try { el.style.display = ev(el.dataset.sporkIf) ? \'\' : \'none\'; } catch(_) {} });\n  document.querySelectorAll(\'[data-spork-class]\').forEach(function(el) { try { var c = ev(el.dataset.sporkClass); if (typeof c === \'string\') el.className = (el.dataset.sporkBase || (el.dataset.sporkBase = el.className)) + \' \' + c; } catch(_) {} });\n};\n// Valor que el usuario escribe/elige → a PHP (State::get() lo ve) y a los demás widgets enlazados.\nwindow.__sync = function(n, v) {\n  try { fetch(\'http://127.0.0.1:%PORT%/event/%VEV%\', {method: \'POST\', mode: \'no-cors\', headers: {\'Content-Type\': \'text/plain\'}, body: JSON.stringify({n: n, v: v, w: window.__win})}); } catch(_) {}\n};\n(function() {\n  function onUser(e) {\n    var el = e.target && e.target.closest ? e.target.closest(\'[data-spork-bind]\') : null;\n    if (!el) return;\n    var v = el.type === \'checkbox\' ? el.checked : (el.type === \'range\' || el.type === \'number\') ? Number(el.value) : el.value;\n    var n = el.getAttribute(\'data-spork-bind\');\n    window.__set(n, v);\n    window.__sync(n, v);\n  }\n  document.addEventListener(\'input\', onUser);\n  document.addEventListener(\'change\', onUser);\n})();\ndocument.addEventListener(\'click\', function(e) {      // Tabs\n  var b = e.target.closest ? e.target.closest(\'[data-ttarget]\') : null;\n  if (!b) return;\n  var g = b.dataset.ttarget, i = +b.dataset.tidx;\n  document.querySelectorAll(\'[data-tpanel]\').forEach(function(p) { if (p.dataset.tpanel === g) p.classList.toggle(\'sz-active\', +p.dataset.tidx === i); });\n  document.querySelectorAll(\'[data-ttarget]\').forEach(function(x) { if (x.dataset.ttarget === g) x.classList.toggle(\'sz-active\', +x.dataset.tidx === i); });\n});\nwindow.__toast = function(msg, v, ms) {\n  var c = document.getElementById(\'__vspk_toasts\');\n  if (!c) { c = document.createElement(\'div\'); c.className = \'sz-toast-container\'; c.id = \'__vspk_toasts\'; document.body.appendChild(c); }\n  var t = document.createElement(\'div\'); t.className = \'sz-toast\' + (v ? \' sz-toast-\' + v : \'\'); t.textContent = msg; c.appendChild(t);\n  setTimeout(function() { t.style.opacity = \'0\'; t.style.transition = \'opacity .3s\'; setTimeout(function() { t.remove(); }, 300); }, ms || 3000);\n};\nwindow.__vspk_cmd = function(cmd, a, b) {\n  try {\n    if (cmd === \'close\' || cmd === \'fullscreen\') window.ipc && window.ipc.postMessage(JSON.stringify({cmd: cmd === \'close\' ? \'close\' : \'toggleFullscreen\'}));\n    else if (cmd === \'setTitle\' && window.__vspk_api) window.__vspk_api.setTitle(a);\n    else if (cmd === \'setTitle\' && typeof __vspk !== \'undefined\') __vspk.setTitle(a);\n    else if (cmd === \'notify\' && typeof __vspk !== \'undefined\') __vspk.notify(a, b);\n  } catch(err) { console.error(err); }\n};\nwindow.__cv = function(id, op, a) {\n  var c = document.getElementById(id); if (!c) return;\n  var x = c.getContext(\'2d\');\n  if (op === \'clear\') { x.clearRect(0, 0, c.width, c.height); }\n  else if (op === \'color\') { x.fillStyle = a[0]; x.strokeStyle = a[0]; }\n  else if (op === \'lw\') { x.lineWidth = a[0]; }\n  else if (op === \'font\') { x.font = a[0] + \'px sans-serif\'; }\n  else if (op === \'line\') { x.beginPath(); x.moveTo(a[0], a[1]); x.lineTo(a[2], a[3]); x.stroke(); }\n  else if (op === \'rect\') { x.fillRect(a[0], a[1], a[2], a[3]); }\n  else if (op === \'frame\') { x.strokeRect(a[0], a[1], a[2], a[3]); }\n  else if (op === \'circle\') { x.beginPath(); x.arc(a[0], a[1], a[2], 0, 6.283185307); x.fill(); }\n  else if (op === \'ring\') { x.beginPath(); x.arc(a[0], a[1], a[2], 0, 6.283185307); x.stroke(); }\n  else if (op === \'text\') { x.fillText(a[2], a[0], a[1]); }\n  else if (op === \'poly\') { var p = a[0]; x.beginPath(); x.moveTo(p[0][0], p[0][1]); for (var i = 1; i < p.length; i++) x.lineTo(p[i][0], p[i][1]); x.closePath(); x.fill(); }\n  else if (op === \'draw\') { new Function(\'ctx\', \'canvas\', a[0])(x, c); }\n};\nObject.keys(window.__state).forEach(function(k) { window.__set(k, window.__state[k]); });\n(function connectSSE() {\n  var es = new EventSource(\'http://127.0.0.1:%PORT%/events\');\n  es.addEventListener(\'state\', function(e) { var d = JSON.parse(e.data); if (d.src && d.src === window.__win) return; window.__set(d.name, d.value); });\n  [%EVALEV%, \'all\'].forEach(function(n) { es.addEventListener(n, function(e) { try { (0, eval)(JSON.parse(e.data)); } catch(err) { console.error(err); } }); });\n  es.onerror = function() { es.close(); setTimeout(connectSSE, 1000); };\n})();'


class App:
    """
    Punto de entrada. Crea la ventana, define el estado reactivo y corre la aplicación.

        app = vspk.App("Mi App", width=800, height=600)
        nombre = app.state("nombre", "")
        saludo = app.state("saludo", "Hola!")
        app.add(vspk.Col(
            vspk.H1(saludo),
            vspk.Input(bind=nombre, placeholder="Tu nombre"),
            vspk.Button("Saludar", on_click=lambda: saludo.set(f"Hola, {nombre.get()}!")),
        ))
        app.run()
    """

    def __init__(self,
                 title:      str  = "App",
                 *,
                 width:      int  = 1024,
                 height:     int  = 768,
                 theme:      str  = "light",
                 primary:    str  = "#6750A4",
                 bg:         str  = "",
                 surface:    str  = "",
                 font:       str  = "",
                 devtools:   bool = False,
                 debug_html: bool = False,
                 vspk_exe:   str  = None):
        global _CURRENT_APP
        self.title      = title
        self.width      = width
        self.height     = height
        self.theme      = theme
        self.primary    = primary
        self.bg         = bg
        self.surface    = surface
        self.font       = font
        self.devtools   = devtools
        self.debug_html = debug_html
        self.vspk_exe   = vspk_exe if vspk_exe is not None else _find_vspk()
        self._root:     Col  = Col()
        self._states:   dict = {}
        self._sse_clients: list = []                 # una queue por conexión /events
        self._sse_lock       = threading.Lock()
        self._token          = secrets.token_hex(8)  # ids de callback/eventos no adivinables desde otra web
        self._cb_registry: dict[str, Callable] = {}
        self._cb_count:    int = 0
        self._events:      dict[str, Callable] = {}      # eventos internos (con token)
        self._event_handlers: dict[str, list[Callable]] = {}   # on_event público (/event/<nombre>)
        self._q: "queue.Queue" = queue.Queue()
        self._timers: list = []
        self._key_on = False
        self._close_on = False
        self._running = False
        self._quit = False
        self._cv_ids: list = []
        self._cv_logs: dict = {}
        self._cv_mouse_js = ""
        self._wins: list = []
        # El puerto se conoce ya, antes de construir los widgets.
        self._server = self._make_server()
        self._port: int = self._server.server_address[1]
        _CURRENT_APP = self

    # ── Estado ────────────────────────────────────────────────────────────────

    def state(self, name: str, initial: Any) -> State:
        s = self._states.get(name)
        if s is None:
            s = State(name, initial, self)
            self._states[name] = s
        return s

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _ev(self, name: str) -> str:
        return f"__{name}_{self._token}"

    def _post_js(self, name: str, body_expr: str) -> str:
        return (f"fetch('http://127.0.0.1:{self._port}/event/{name}',{{method:'POST',mode:'no-cors',"
                f"headers:{{'Content-Type':'text/plain'}},body:{body_expr}}})")

    def on_click(self, fn: Callable) -> str:
        """Registra fn (se ejecuta en Python) y devuelve el JS para dispararla desde un onclick."""
        self._cb_count += 1
        cid = f"cb_{self._token}_{self._cb_count}"
        self._cb_registry[cid] = fn
        return f"fetch('http://127.0.0.1:{self._port}/cb/{cid}',{{mode:'no-cors'}})"

    def Button(self, text: str = "", **kw) -> Button:
        kw.setdefault("_app", self)
        return Button(text, **kw)

    def _on_payload(self, fn: Callable, expr: str) -> str:
        """JS que envía expr (JSON) a fn(valor) — para on_change de Input/Select/Checkbox."""
        self._cb_count += 1
        name = self._ev(f"p{self._cb_count}")
        self._events[name] = fn
        return self._post_js(name, f"JSON.stringify({expr})")

    def on_event(self, event: str, handler: Callable[[Any], None]) -> None:
        """
        Handler para eventos enviados desde la página:
            fetch('/event/mi_evento', {method:'POST', body: JSON.stringify({dato: 42})})
        (la URL completa lleva el puerto: usa window.__vspk_port o la que ves en la página).
        También acepta eventos via IPC (window.ipc.postMessage) cuando vspk los reenvía al socket.
        """
        self._event_handlers.setdefault(event, []).append(handler)
        if not hasattr(self, "_ipc_thread") or not self._ipc_thread.is_alive():
            self._ipc_thread = threading.Thread(target=self._listen_ipc, daemon=True)
            self._ipc_thread.start()

    # ── SSE ───────────────────────────────────────────────────────────────────

    def _push_sse(self, event: str, data: Any) -> None:
        msg = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        with self._sse_lock:
            for q in self._sse_clients:
                q.put(msg)

    def _push_state(self, name: str, value: Any) -> None:
        self._push_sse("state", {"name": name, "value": value})

    def eval_js(self, js: str) -> None:
        """Ejecuta JS en la ventana principal."""
        self._push_sse("eval", js)

    # ── Utilidades de ventana ─────────────────────────────────────────────────

    def toast(self, msg: str, variant: str = "", ms: int = 3000) -> None:
        self.eval_js(f"window.__toast({_js(msg)},{_js(variant)},{int(ms)})")

    def set_title(self, title: str) -> None:
        self.eval_js(f"__vspk.setTitle({_js(title)})")

    def notify(self, title: str, body: str = "") -> None:
        self.eval_js(f"__vspk.notify({_js(title)},{_js(body)})")

    def copy_text(self, text: str) -> None:
        self.eval_js(f"__vspk.clipboard.write({_js(text)})")

    def quit(self) -> None:
        self._quit = True

    def on_key(self, fn: Callable[[dict], None]) -> "App":
        """fn recibe {key, code, ctrl, shift, alt, meta}. Llamar antes de run()."""
        self._key_on = True
        self._events[self._ev("k")] = fn
        return self

    def on_close(self, fn: Callable[[], Any]) -> "App":
        """fn() devuelve False para cancelar el cierre de la ventana. Llamar antes de run()."""
        self._close_on = True
        def _h_close(_data):
            try:
                r = fn()
            except Exception as e:
                print(f"[vspk] error en on_close: {e}")
                r = True
            self.eval_js("__vspk.cancelClose()" if r is False else "__vspk.confirmClose()")
        self._events[self._ev("c")] = _h_close
        return self

    def _dialog(self, kind: str, title: str, fn: Callable[[Optional[str]], None]) -> None:
        self._cb_count += 1
        name = self._ev(f"d{self._cb_count}")
        self._events[name] = lambda d: fn(d.get("path") if isinstance(d, dict) else None)
        self.eval_js(f"__vspk.dialog({{kind:{_js(kind)},title:{_js(title)}}}).then(function(p){{"
                     + self._post_js(name, "JSON.stringify({path:p})") + "})")

    def pick_file(self, title: str, fn):   self._dialog("open", title, fn)
    def save_file(self, title: str, fn):   self._dialog("save", title, fn)
    def pick_folder(self, title: str, fn): self._dialog("folder", title, fn)

    # ── Diálogos modales (mensaje / confirmación / pedir texto) ──────────────

    def _modal(self, js_call: str, conv: Callable, fn: Optional[Callable]) -> None:
        self._cb_count += 1
        name = self._ev(f"m{self._cb_count}")
        self._events[name] = lambda d: fn(conv(d.get("v") if isinstance(d, dict) else None)) if fn else None
        self.eval_js(f"Promise.resolve({js_call}).then(function(v){{" + self._post_js(name, "JSON.stringify({v:v})") + "})")

    def message(self, text: str, fn: Optional[Callable[[], None]] = None) -> None:
        """Diálogo modal con un botón Aceptar. fn() se llama al cerrarlo."""
        self._modal(f"alert({_js(text)})", lambda v: None, (lambda _: fn()) if fn else None)

    def confirm(self, text: str, fn: Callable[[bool], None]) -> None:
        """Modal Aceptar/Cancelar. fn(True|False)."""
        self._modal(f"confirm({_js(text)})", lambda v: bool(v), fn)

    def prompt(self, text: str, fn: Callable[[Optional[str]], None], default: str = "") -> None:
        """Modal que pide un texto. fn(texto) o fn(None) si se cancela."""
        self._modal(f"prompt({_js(text)},{_js(default)})", lambda v: v if isinstance(v, str) else None, fn)

    # ── Tabla / árbol ────────────────────────────────────────────────────────

    def table_set(self, tid: str, rows: list, cols: Optional[list] = None, win: Optional[ChildWindow] = None) -> None:
        """Sustituye las filas (y opcionalmente las columnas) de una Table. win = ventana extra donde vive."""
        js = f"window.__vspk_table_set({_js(tid)},{_js(cols)},{_js(rows)})"
        (win or self).eval_js(js)

    def table_select(self, tid: str, index: int, win: Optional[ChildWindow] = None) -> None:
        (win or self).eval_js(f"window.__vspk_table_select({_js(tid)},{int(index)})")

    def table_sort(self, tid: str, col: int, desc: bool = False, win: Optional[ChildWindow] = None) -> None:
        (win or self).eval_js(f"window.__vspk_table_sort({_js(tid)},{int(col)},{-1 if desc else 1})")

    def tree_set(self, tid: str, nodes: list, win: Optional[ChildWindow] = None) -> None:
        (win or self).eval_js(f"window.__vspk_tree_set({_js(tid)},{_js(nodes)})")

    def run_after(self, ms: int, fn: Callable) -> "App":
        """Ejecuta fn una vez dentro de ms milisegundos (mientras run() esté activo)."""
        self._timers.append({"at": time.monotonic() + ms / 1000, "every": None, "fn": fn})
        return self

    def run_every(self, ms: int, fn: Callable) -> "App":
        """Ejecuta fn cada ms milisegundos. Devuelve False desde fn para cancelarlo."""
        self._timers.append({"at": time.monotonic() + ms / 1000, "every": ms / 1000, "fn": fn})
        return self

    after = run_after
    every = run_every

    # ── Canvas ────────────────────────────────────────────────────────────────

    def canvas(self, cid: str, w: int, h: int) -> Canvas:
        self._cv_ids.append(cid)
        self._cv_logs[cid] = ""
        return Canvas(self, cid, w, h)

    def _cv(self, cid: str, op: str, args: list) -> None:
        js = f"__cv({_js(cid)},{_js(op)},{_js(args)})"
        if op == "clear":
            self._cv_logs[cid] = ""
        self._cv_logs[cid] = self._cv_logs.get(cid, "") + js + ";"
        if self._running:
            self._push_sse("all", js)

    def _cv_mouse(self, cid: str, fn: Callable) -> None:
        self._cb_count += 1
        name = self._ev(f"m{self._cb_count}")
        self._events[name] = fn
        js = ("(function(){var c=document.getElementById(" + _js(cid) + ");if(!c)return;function p(t,e){"
              "if(t==='move'){var n=Date.now();if(n-(c.__lm||0)<30)return;c.__lm=n;}var r=c.getBoundingClientRect();"
              + self._post_js(name, "JSON.stringify({type:t,x:Math.round((e.clientX-r.left)*c.width/r.width),"
                                    "y:Math.round((e.clientY-r.top)*c.height/r.height),button:e.button})")
              + "}['down','up','move','click'].forEach(function(t){c.addEventListener(t==='down'?'mousedown':"
                "t==='up'?'mouseup':t==='move'?'mousemove':'click',function(e){p(t,e)})})})();")
        self._cv_mouse_js += js
        if self._running:
            self._push_sse("all", js)

    # ── Ventanas adicionales ──────────────────────────────────────────────────

    def window(self, title: str, width: int = 480, height: int = 360) -> ChildWindow:
        w = ChildWindow(self, f"w{len(self._wins) + 1}", title, width, height)
        self._wins.append(w)
        return w

    new_window = window

    def _win_eval(self, w: ChildWindow, js: str) -> None:
        self._push_sse(f"eval_{w.id}", js)

    def _win_show(self, w: ChildWindow) -> None:
        if self._running:
            self._win_open(w)
        else:
            w.want = True

    def _win_on_close(self, w: ChildWindow, fn: Callable) -> None:
        ev = self._ev("c" + w.id)
        w.close_on = True
        w.close_js = "window.addEventListener('vspk:closeRequested',function(){" + self._post_js(ev, "'{}'") + "});"
        def _h_close(_d):
            try:
                r = fn()
            except Exception as e:
                print(f"[vspk] error en on_close: {e}")
                r = True
            self._win_eval(w, "__vspk.cancelClose()" if r is False else "__vspk.confirmClose()")
        self._events[ev] = _h_close

    def _win_open(self, w: ChildWindow) -> None:
        if w.is_open():
            return
        if w.htv:
            try: os.unlink(w.htv)
            except OSError: pass
        body = "\n".join(x.render() if isinstance(x, Widget) else str(x) for x in w.widgets)
        page = self._build_page(w.title, body, f"eval_{w.id}", False, w.close_js)
        _ic = self._find_icon()
        head = f"title: {w.title}\nwidth: {w.width}\nheight: {w.height}\ndevtools: true\n" + (f"icon: {_ic}\n" if _ic else "") + ("on_close: confirm\n" if w.close_on else "")
        w.htv = self._write_htv(head + "\n" + page)
        w.proc = self._spawn(w.htv)

    # ── Widgets acumulados ────────────────────────────────────────────────────

    def add(self, *widgets) -> "App":
        self._root.add(*widgets)
        return self

    # ── HTML ──────────────────────────────────────────────────────────────────

    def _build_html(self) -> str:
        return self._build_page(self.title, self._root.render(), "eval", True, "")

    def _build_page(self, title: str, body: str, eval_ev: str, is_main: bool, child_close_js: str) -> str:
        state_js = _js({name: s.get() for name, s in self._states.items()}) if self._states else "{}"
        js = (_PAGE_JS.replace("%STATE%", state_js).replace("%PORT%", str(self._port))
              .replace("%VEV%", self._ev("v")).replace("%WIN%", _js(eval_ev)).replace("%EVALEV%", _js(eval_ev)))
        key_js = ""
        if is_main and self._key_on:
            key_js = ('document.addEventListener("keydown",function(e){' + self._post_js(self._ev("k"),
                      "JSON.stringify({key:e.key,code:e.code,ctrl:e.ctrlKey,shift:e.shiftKey,alt:e.altKey,meta:e.metaKey})") + "});")
        close_js = child_close_js
        if is_main and self._close_on:
            close_js += 'window.addEventListener("vspk:closeRequested",function(){' + self._post_js(self._ev("c"), '"{}"') + "});"
        js += "\n" + key_js + close_js + "".join(self._cv_logs.get(i, "") for i in self._cv_ids) + self._cv_mouse_js

        css_vars = f"  --sz-primary: {self.primary};"
        if self.bg:      css_vars += f"\n  --sz-bg: {self.bg};"
        if self.surface: css_vars += f"\n  --sz-surface: {self.surface};"
        if self.font:    css_vars += f"\n  --sz-font: {self.font}, system-ui, sans-serif;"
        theme = "dark" if self.theme == "dark" else "light"
        return f"""<!DOCTYPE html>
<html data-theme="{theme}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_h(title)}</title>
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="spork.css" onerror="this.onerror=null;this.href='{_SPORK_CSS}'">
  <style>:root {{
{css_vars}
}}</style>
</head>
<body class="sz-body">

<div id="__app" class="sz-page">
{body}
</div>

<script>
{js}
</script>
<script src="spork.js" onerror="var s=document.createElement('script');s.src='{_SPORK_JS}';document.body.appendChild(s)"></script>
</body>
</html>"""

    # ── Servidor HTTP (puente) ────────────────────────────────────────────────

    def _make_server(self) -> ThreadingHTTPServer:
        app_ref = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"
            def log_message(self, *args): pass
            def log_error(self, *args):   pass

            def _reply(self, code: int, body: bytes = b""):
                self.send_response(code)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "*")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.end_headers()
                if body:
                    self.wfile.write(body)
                self.close_connection = True

            def do_OPTIONS(self):
                self._reply(204)

            def do_POST(self):
                path = urlparse(self.path).path
                length = int(self.headers.get("Content-Length", 0) or 0)
                body = self.rfile.read(length).decode("utf-8", errors="replace") if length else ""
                if path.startswith("/event/"):
                    app_ref._q.put(("event", path[7:], body))
                    self._reply(200, b"ok")
                else:
                    self._reply(404)

            def do_GET(self):
                path = urlparse(self.path).path
                if path == "/events":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "keep-alive")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    q: "queue.Queue" = queue.Queue()
                    with app_ref._sse_lock:
                        app_ref._sse_clients.append(q)
                    try:
                        self.wfile.write(b": conectado\n\n")
                        self.wfile.flush()
                        while True:
                            try:
                                msg = q.get(timeout=15)
                            except queue.Empty:
                                msg = ": ping\n\n"
                            if msg is None:
                                break
                            self.wfile.write(msg.encode("utf-8"))
                            self.wfile.flush()
                    except Exception:
                        pass
                    finally:
                        with app_ref._sse_lock:
                            if q in app_ref._sse_clients:
                                app_ref._sse_clients.remove(q)
                        self.close_connection = True
                elif path.startswith("/cb/"):
                    app_ref._q.put(("cb", path[4:], ""))
                    self._reply(200, b"ok")
                elif path == "/favicon.ico":
                    self._reply(204)
                else:
                    self._reply(404)

        class _QuietServer(ThreadingHTTPServer):
            daemon_threads = True
            def handle_error(self, request, client_address):
                pass  # WebView cierra conexiones — es normal

        return _QuietServer(("127.0.0.1", 0), Handler)

    # ── Despacho (hilo de run()) ──────────────────────────────────────────────

    def _dispatch(self, item) -> None:
        kind, name, body = item
        try:
            if kind == "cb":
                fn = self._cb_registry.get(name)      # id sin token válido → no existe → no hace nada
                if fn:
                    fn()
                return
            try:
                data = json.loads(body) if body else None
            except json.JSONDecodeError:
                data = body
            if name == self._ev("v"):
                if isinstance(data, dict) and str(data.get("n")) in self._states:
                    n = str(data["n"])
                    self._states[n]._receive(data.get("v"))
                    if self._wins:   # se reenvía a las demás ventanas (la de origen ignora su eco)
                        self._push_sse("state", {"name": n, "value": data.get("v"), "src": str(data.get("w") or "")})
                return
            fn = self._events.get(name)
            if fn:
                fn(data)
                return
            for h in self._event_handlers.get(name, []):
                h(data)
        except Exception as e:
            import traceback
            print(f"[vspk] error en callback: {e}")
            traceback.print_exc()

    def _run_timers(self) -> None:
        now = time.monotonic()
        for t in list(self._timers):
            if t["at"] > now:
                continue
            try:
                r = t["fn"]()
            except Exception as e:
                print(f"[vspk] error en temporizador: {e}")
                r = False
            if t["every"] is None or r is False:
                self._timers.remove(t)
            else:
                t["at"] = now + t["every"]

    # ── IPC — eventos desde JS via window.ipc.postMessage ────────────────────

    def _listen_ipc(self) -> None:
        while True:
            try:
                if _is_windows():
                    self._listen_ipc_windows()
                else:
                    self._listen_ipc_unix()
            except Exception:
                time.sleep(0.5)

    def _listen_ipc_unix(self) -> None:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(_SOCK_UNIX)
            reg = json.dumps({"cmd": "register", "info": {
                "id": 0, "title": "_py_listener", "x": 0, "y": 0,
                "w": 0, "h": 0, "file": ""
            }}) + "\n"
            s.sendall(reg.encode())
            buf = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    self._dispatch_ipc(line.decode().strip())

    def _listen_ipc_windows(self) -> None:
        reg  = (json.dumps({"cmd": "register", "info": {
            "id": 0, "title": "_py_listener", "x": 0, "y": 0,
            "w": 0, "h": 0, "file": ""
        }}) + "\n").encode()
        poll = (json.dumps({"cmd": "poll"}) + "\n").encode()
        while True:
            try:
                with builtins_open(_PIPE_WINDOWS, "r+b", buffering=0) as pipe:
                    pipe.write(reg)
                    resp = b""
                    while b"\n" not in resp:
                        chunk = pipe.read(65536)
                        if not chunk: break
                        resp += chunk
                    while True:
                        pipe.write(poll)
                        buf = b""
                        while b"\n" not in buf:
                            chunk = pipe.read(65536)
                            if not chunk: raise ConnectionError("pipe closed")
                            buf += chunk
                        for raw in buf.split(b"\n"):
                            txt = raw.decode(errors="ignore").strip()
                            if txt: self._dispatch_ipc(txt)
                        time.sleep(0.05)
            except Exception:
                time.sleep(0.1)

    def _dispatch_ipc(self, line: str) -> None:
        if not line:
            return
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            return
        if not msg.get("__vspk_emit"):
            return
        event   = msg.get("event", "")
        payload = msg.get("payload")
        for fn in self._event_handlers.get(event, []):
            try:
                fn(payload)
            except Exception as e:
                print(f"[vspk] IPC handler '{event}' error: {e}")

    # ── run() ─────────────────────────────────────────────────────────────────

    def _write_htv(self, content: str) -> str:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".htv", prefix="vspk_", delete=False, encoding="utf-8") as f:
            f.write(content)
            return f.name

    def _spawn(self, htv_path: str) -> subprocess.Popen:
        kw: dict = {}
        if _is_windows():
            kw["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
        return subprocess.Popen([self.vspk_exe, htv_path], **kw)

    def _find_icon(self) -> str:
        import inspect
        try:
            caller_file = inspect.stack()[-1].filename
            caller_dir  = os.path.dirname(os.path.abspath(caller_file))
            base        = os.path.splitext(os.path.basename(caller_file))[0]
        except Exception:
            return ""
        for candidate in [base + ".ico", base + ".png", "icon.ico", "icon.png", "favicon.ico", "favicon.png"]:
            p = os.path.join(caller_dir, candidate)
            if os.path.isfile(p):
                return p
        # Sin icono propio: el del rayito (vspk_default.ico), buscado hacia arriba
        d = os.environ.get("VSPK_DEFAULT_ICON", "")
        if d and os.path.isfile(d):
            return d
        for start in (caller_dir, os.path.dirname(os.path.abspath(__file__))):
            cur = start
            for _ in range(10):
                p = os.path.join(cur, "vspk_default.ico")
                if os.path.isfile(p):
                    return p
                nxt = os.path.dirname(cur)
                if nxt == cur:
                    break
                cur = nxt
        return ""

    def run(self) -> None:
        """Arranca el puente HTTP, abre vspk con un .htv temporal y atiende eventos hasta que se cierra."""
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        html = self._build_html()
        if self.debug_html:
            print(html)
        icon = self._find_icon()
        head = (f"title: {self.title}\nwidth: {self.width}\nheight: {self.height}\n"
                + ("devtools: true\n" if self.devtools else "")
                + (f"icon: {icon}\n" if icon else "")
                + ("on_close: confirm\n" if self._close_on else ""))
        htv_path = self._write_htv(head + "\n" + html)
        proc = None
        try:
            proc = self._spawn(htv_path)
            self._running = True
            for w in self._wins:
                if w.want:
                    self._win_open(w)
            while proc.poll() is None and not self._quit:
                try:
                    self._dispatch(self._q.get(timeout=0.015))
                    while True:
                        self._dispatch(self._q.get_nowait())
                except queue.Empty:
                    pass
                self._run_timers()
            if self._quit and proc.poll() is None:
                proc.terminate()
        finally:
            self._running = False
            # Al cerrar la principal se cierran las demás.
            for w in self._wins:
                if w.is_open():
                    self._win_eval(w, "__vspk.close()")
            if self._wins:
                time.sleep(0.3)
            for w in self._wins:
                if w.proc is not None and w.proc.poll() is None:
                    w.proc.terminate()
                if w.htv:
                    try: os.unlink(w.htv)
                    except OSError: pass
            with self._sse_lock:
                for q in self._sse_clients:
                    q.put(None)
            try: os.unlink(htv_path)
            except OSError: pass
            self._server.shutdown()
            self._server.server_close()



# ── Window — handle de ventana abierta con vspk.open() ───────────────────────

class Window:
    """
    Handle de una ventana nativa abierta con vspk.open().

    Ejemplo:
        win = vspk.open("mi_app.htv")
        win.send({"evento": "dato", "payload": 42})
        win.wait()
    """

    def __init__(self, *, id: int, process: subprocess.Popen):
        self._id      = id
        self._process = process
        self._event_handlers: dict[str, list[Callable]] = {}
        self._ipc_thread: Optional[threading.Thread] = None

    @property
    def id(self) -> int:
        return self._id

    def is_open(self) -> bool:
        return self._process.poll() is None

    def wait(self) -> None:
        self._process.wait()

    def close(self) -> None:
        _ipc_send({"cmd": "unregister", "id": self._id})

    def send(self, payload: Any) -> bool:
        result = _ipc_send({"cmd": "send", "to": self._id, "payload": payload})
        return bool(result and result.get("ok"))

    def focus(self) -> bool:
        result = _ipc_send({"cmd": "focus", "id": self._id})
        return bool(result and result.get("ok"))

    def move(self, x: int, y: int) -> bool:
        result = _ipc_send({"cmd": "move", "id": self._id, "x": x, "y": y})
        return bool(result and result.get("ok"))

    def resize(self, w: int, h: int) -> bool:
        result = _ipc_send({"cmd": "resize", "id": self._id, "w": w, "h": h})
        return bool(result and result.get("ok"))

    def snap(self, pos: str) -> bool:
        result = _ipc_send({"cmd": "snap", "id": self._id, "pos": pos})
        return bool(result and result.get("ok"))

    def on_event(self, event: str, handler: Callable[[Any], None]) -> None:
        self._event_handlers.setdefault(event, []).append(handler)
        if not self._ipc_thread or not self._ipc_thread.is_alive():
            self._ipc_thread = threading.Thread(
                target=self._listen_ipc, daemon=True
            )
            self._ipc_thread.start()

    def _listen_ipc(self) -> None:
        while self.is_open():
            try:
                if _is_windows():
                    self._listen_ipc_windows()
                else:
                    self._listen_ipc_unix()
            except Exception:
                time.sleep(0.5)

    def _listen_ipc_unix(self) -> None:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(_SOCK_UNIX)
            reg = json.dumps({"cmd": "register", "info": {
                "id": self._id or 1, "title": "_py_listener",
                "x": 0, "y": 0, "w": 0, "h": 0, "file": ""
            }}) + "\n"
            s.sendall(reg.encode())
            buf = b""
            while self.is_open():
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    self._dispatch_ipc(line.decode().strip())

    def _listen_ipc_windows(self) -> None:
        reg  = (json.dumps({"cmd": "register", "info": {
            "id": self._id or 1, "title": "_py_listener",
            "x": 0, "y": 0, "w": 0, "h": 0, "file": ""
        }}) + "\n").encode()
        poll = (json.dumps({"cmd": "poll"}) + "\n").encode()
        while self.is_open():
            try:
                with builtins_open(_PIPE_WINDOWS, "r+b", buffering=0) as pipe:
                    pipe.write(reg)
                    resp = b""
                    while b"\n" not in resp:
                        chunk = pipe.read(65536)
                        if not chunk: break
                        resp += chunk
                    while self.is_open():
                        pipe.write(poll)
                        buf = b""
                        while b"\n" not in buf:
                            chunk = pipe.read(65536)
                            if not chunk: raise ConnectionError("pipe closed")
                            buf += chunk
                        for raw in buf.split(b"\n"):
                            txt = raw.decode(errors="ignore").strip()
                            if txt: self._dispatch_ipc(txt)
                        time.sleep(0.05)
            except Exception:
                time.sleep(0.1)

    def _dispatch_ipc(self, line: str) -> None:
        if not line:
            return
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            return
        if not msg.get("__vspk_emit"):
            return
        event   = msg.get("event", "")
        payload = msg.get("payload")
        for fn in self._event_handlers.get(event, []):
            try:
                fn(payload)
            except Exception as e:
                print(f"[vspk] Window handler '{event}' error: {e}")

    def __repr__(self):
        status = "abierta" if self.is_open() else "cerrada"
        return f"<Window id={self._id} {status}>"


# ── open() — abrir un archivo .htv directamente ──────────────────────────────

def open(
    file: str,
    *,
    title:        Optional[str]   = None,
    width:        Optional[int]   = None,
    height:       Optional[int]   = None,
    vspk_exe:     Optional[str]   = None,
    wait_timeout: float           = 5.0,
) -> Window:
    """
    Abre un archivo .htv en una ventana nativa vspk.

    Ejemplo:
        win = vspk.open("mi_app.htv")
        win.send({"dato": 42})
        win.wait()
    """
    if vspk_exe is None: vspk_exe = _find_vspk()
    file_path = Path(file)
    if not file_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file}")

    if title or width or height:
        config = {"file": str(file_path.resolve())}
        if title:  config["title"]  = title
        if width:  config["width"]  = width
        if height: config["height"] = height
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(config, tmp)
            cfg_path = tmp.name
        cmd = [vspk_exe, "--config", cfg_path]
    else:
        cmd = [vspk_exe, str(file_path)]

    kwargs: dict = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if _is_windows():
        kwargs["creationflags"] = 0x08000000
    process = subprocess.Popen(cmd, **kwargs)

    # Esperar a que el socket IPC esté disponible
    deadline = time.monotonic() + wait_timeout
    while time.monotonic() < deadline:
        result = _ipc_send({"cmd": "list"})
        if result is not None:
            break
        time.sleep(0.05)

    win_id = 0
    result = _ipc_send({"cmd": "list"})
    if result and result.get("windows"):
        win_id = max(w["id"] for w in result["windows"])

    return Window(id=win_id, process=process)


def list_windows() -> list:
    result = _ipc_send({"cmd": "list"})
    if result and result.get("ok"):
        return result.get("windows", [])
    return []


def broadcast(payload: Any) -> bool:
    result = _ipc_send({"cmd": "broadcast", "payload": payload})
    return bool(result and result.get("ok"))
