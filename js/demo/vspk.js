/**
 * vspk.js — GUI nativa para Bun usando vspk (WebView) como ventana.
 *
 * El programa abre un puente HTTP+SSE en 127.0.0.1 (puerto aleatorio), escribe un .htv temporal y lanza
 * vspk.exe. Mientras la ventana está abierta, run() atiende los clics (/cb/<id>), los eventos
 * (/event/<nombre>) y los valores de los campos enlazados, y empuja los cambios de estado por SSE.
 * spork.css y spork.js los sirve el propio vspk.exe (van incrustados).
 *
 *   import { App, Col, Row, H1, Button } from "./vspk.js"
 *   const app = new App("Contador", { width: 400, height: 300 })
 *   const n = app.state("n", 0)
 *   app.add(Col(H1(n), Row(Button("-", { onClick: () => n.dec() }), Button("+", { onClick: () => n.inc() }))))
 *   await app.run()
 *
 * Qué hay:
 *   · ids de callback y eventos internos con token (otra web local no puede dispararlos)
 *   · Button(texto, { onClick: fn }) ejecuta fn en Bun; Button(texto, { js: "..." }) es JS puro en la página
 *   · app.onKey, app.onClose, app.pickFile/saveFile/pickFolder, app.runEvery/runAfter,
 *     app.setTitle/notify/copyText/quit/toast/evalJs
 *   · app.canvas(id, w, h)  ·  MenuBar/Menu/MenuItem/MenuSep  ·  app.window(título, w, h) (ventanas extra)
 */

import net  from "net"
import os   from "os"
import path from "path"
import { spawn } from "bun"

const IS_WINDOWS = process.platform === "win32"
const PIPE       = IS_WINDOWS ? "\\\\.\\pipe\\vspk" : "/tmp/vspk.sock"

// ── IPC (con vspk.exe) ────────────────────────────────────────────────────────

function ipcSend(msg) {
    return new Promise((resolve) => {
        const sock = net.createConnection({ path: PIPE })
        let buf = ""
        sock.on("data", (chunk) => {
            buf += chunk.toString()
            if (buf.includes("\n")) {
                try { resolve(JSON.parse(buf.trim())) } catch { resolve(null) }
                sock.destroy()
            }
        })
        sock.on("error", () => resolve(null))
        sock.on("connect", () => {
            sock.write(JSON.stringify(msg) + "\n")
        })
    })
}

async function waitForSocket(timeout = 5000) {
    const deadline = Date.now() + timeout
    while (Date.now() < deadline) {
        const r = await ipcSend({ cmd: "list" })
        if (r !== null) return true
        await Bun.sleep(50)
    }
    return false
}

// ── Utilidades ────────────────────────────────────────────────────────────────

const esc = (s) => String(s ?? "")
    .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;")
// JSON para incrustar en JS dentro de HTML (sin romper </script>)
const js = (v) => JSON.stringify(v).replaceAll("</", "<\\/")

let _currentApp = null   // la última App creada (los widgets la usan por defecto)

// ── Estado reactivo ───────────────────────────────────────────────────────────

export class State {
    #name; #value; #app; #watchers = []
    constructor(name, value, app) {
        this.#name  = name
        this.#value = value
        this.#app   = app
    }
    get name()  { return this.#name }
    get()       { return this.#value }
    set(value)  {
        this.#value = value
        this.#app._pushState(this.#name, value)
    }
    inc(by = 1) { this.set((typeof this.#value === "number" ? this.#value : 0) + by) }
    dec(by = 1) { this.inc(-by) }
    /** fn(valor) cada vez que el usuario cambia el campo enlazado a este estado */
    onChange(fn) { this.#watchers.push(fn); return this }
    _receive(value) { this.#value = value; for (const w of this.#watchers) w(value) }

    // JS para usar dentro de onclick="..."
    jsGet()      { return `window.__state[${js(this.#name)}]` }
    jsSet(v)     { return `window.__set(${js(this.#name)},${js(v)})` }
    jsInc(by = 1) { return `window.__set(${js(this.#name)},(+window.__state[${js(this.#name)}]||0)+${by})` }
    jsDec(by = 1) { return this.jsInc(-by) }

    // Span reactivo — se usa directamente como contenido de un widget
    toString() {
        const v = this.#value
        const txt = typeof v === "boolean" ? String(v) : (["number", "string"].includes(typeof v) ? String(v) : "")
        return `<span data-spork-text="${esc(this.#name)}">${esc(txt)}</span>`
    }
}

function toJsExpr(val) {
    if (typeof val === "string") return val
    if (val instanceof State)    return val.jsGet()
    return JSON.stringify(val)
}

// ── Widgets ───────────────────────────────────────────────────────────────────

export class Widget {
    constructor(children = [], props = {}) {
        this._children = children.flat()
        this._cls      = [props.cls, props.class_].filter(Boolean).join(" ")
        this._style    = props.style || ""
        this._id       = props.id    || ""
        this._extra    = {}
        if (props.if_    != null) this._extra["data-spork-if"]    = toJsExpr(props.if_)
        if (props.style_ != null) this._extra["data-spork-style"] = toJsExpr(props.style_)
        if (props.class_r != null) this._extra["data-spork-class"] = JSON.stringify(
            Object.fromEntries(Object.entries(props.class_r).map(([k, v]) => [k, toJsExpr(v)]))
        )
    }
    get tag()     { return "div" }
    get classes() { return "" }

    _attrs() {
        const parts = []
        if (this._id) parts.push(`id="${esc(this._id)}"`)
        const cls = [this.classes, this._cls].filter(Boolean).join(" ")
        if (cls) parts.push(`class="${esc(cls)}"`)
        if (this._style) parts.push(`style="${esc(this._style)}"`)
        for (const [k, v] of Object.entries(this._extra)) parts.push(`${k}="${esc(v)}"`)
        return parts.length ? " " + parts.join(" ") : ""
    }

    _renderChild(c) {
        if (c instanceof Widget) return c.render()
        if (c instanceof State)  return c.toString()
        return c != null ? String(c) : ""
    }

    render() {
        const attrs = this._attrs()
        const inner = this._children.map(c => this._renderChild(c)).join("\n")
        return inner
            ? `<${this.tag}${attrs}>\n${inner}\n</${this.tag}>`
            : `<${this.tag}${attrs}></${this.tag}>`
    }

    add(...widgets) { this._children.push(...widgets); return this }
    toString() { return this.render() }
}

class Raw extends Widget {
    constructor(html) { super(); this._html = html }
    render() { return this._html }
}
export const RawHtml = (html) => new Raw(html)

const makeWidget = (tag, cls) => class extends Widget {
    get tag()     { return tag }
    get classes() { return cls }
}
const W = {
    row:  makeWidget("div", "sz-row"),    col:  makeWidget("div", "sz-col sz-center"),
    card: makeWidget("div", "sz-card"),   grid: makeWidget("div", "sz-grid"),
    nav:  makeWidget("nav", "sz-nav"),
    h1: makeWidget("h1", "sz-h1"), h2: makeWidget("h2", "sz-h2"), h3: makeWidget("h3", "sz-h3"), h4: makeWidget("h4", "sz-h4"),
    p: makeWidget("p", "sz-p"), label: makeWidget("label", "sz-label"), badge: makeWidget("span", "sz-badge"),
    chip: makeWidget("span", "sz-chip"), alert: makeWidget("div", "sz-alert"), spacer: makeWidget("div", "sz-grow"),
}

// Layout
export const Row  = (...children) => new W.row([...children])
export const Col  = (...children) => new W.col([...children])
export const Card = (...children) => new W.card([...children])
export const Grid = (...children) => new W.grid([...children])
export const Nav  = (...children) => new W.nav([...children])
export class Hr extends Widget { get tag() { return "hr" } get classes() { return "sz-divider" } render() { return `<hr${this._attrs()}>` } }
export const Spacer = () => new W.spacer([])

// Texto
export const H1    = (text, p = {}) => new W.h1([text], p)
export const H2    = (text, p = {}) => new W.h2([text], p)
export const H3    = (text, p = {}) => new W.h3([text], p)
export const H4    = (text, p = {}) => new W.h4([text], p)
export const P     = (text, p = {}) => new W.p([text], p)
export const Label = (text, p = {}) => new W.label([text], p)
export const Badge = (text, p = {}) => new W.badge([text], p)
export const Chip  = (text, { primary = false, ...p } = {}) => {
    if (primary) p.cls = ((p.cls || "") + " sz-chip-primary").trim()
    return new W.chip([text], p)
}
export const Alert = (text, { variant = "", ...p } = {}) => {
    if (variant) p.cls = ((p.cls || "") + ` sz-alert-${variant}`).trim()
    return new W.alert([text], p)
}

const bindAttr = (bind) => bind ? ` data-spork-bind="${esc(bind.name)}"` : ""

function appOf(app) {
    const a = app || _currentApp
    if (!a) throw new Error("[vspk] crea la App antes de los widgets con onClick/onChange")
    return a
}

/**
 * Button(texto, { onClick: fn })   → fn() se ejecuta en Bun (puede usar cualquier State/API)
 * Button(texto, { js: "alert(1)" }) → JS puro en la página (instantáneo, sin pasar por Bun)
 */
export const Button = (text, { onClick, js: jsCode, variant = "filled", size = "", full = false, disabled = false, app, ...p } = {}) => {
    let cls = `sz-btn-${variant}`
    if (size) cls += ` sz-btn-${size}`
    if (full) cls += " sz-btn-full"
    p.cls = ((p.cls || "") + " " + cls).trim()
    const w = new (makeWidget("button", "sz-btn"))([text], p)
    if (!disabled) {
        if (typeof jsCode === "string") w._extra["onclick"] = jsCode
        else if (onClick) w._extra["onclick"] = appOf(app).onClick(onClick)
    }
    if (disabled) w._extra["disabled"] = "disabled"
    w._extra["data-ripple"] = ""
    return w
}

export const Input = ({ bind = null, placeholder = "", type = "text", value = "", onChange, app, ...p } = {}) => {
    const w = new (makeWidget("input", "sz-input"))([], p)
    if (placeholder) w._extra["placeholder"] = placeholder
    if (type !== "text") w._extra["type"] = type
    if (onChange && !bind) w._extra["oninput"] = appOf(app)._onPayload(onChange, "this.value")
    w.render = () => {
        const val = bind ? bind.get() : value
        return `<input${w._attrs()}${val !== "" && val != null ? ` value="${esc(val)}"` : ""}${bindAttr(bind)}>`
    }
    return w
}

// ── Tabla, árbol, lista (se hidratan en la página; ver vspk_ui.js incrustado en vspk.exe) ──
let _vtN = 0
const _vtId = (p) => `${p}${++_vtN}`

/**
 * Table(["Nombre","Edad"], [["Ana",31],["Luis",28]], { onSelect, onDblclick, onSort, sortable, multi, striped, header, height, selected })
 *   onSelect(d) → d = { index, row, indexes, rows } (index = posición original en rows). Clic en la cabecera ordena.
 *   Cambiar datos: app.tableSet(t.id, rows[, cols])
 */
export const Table = (cols, rows, { onSelect, onDblclick, onSort, sortable = true, multi = false, striped = true, header = true, height, selected = -1, app, ...p } = {}) => {
    if (!p.id) p.id = _vtId("vt")
    const w = new (makeWidget("div", "vspk-table"))([], p)
    w.id = p.id
    const cfg = { cols, rows, sortable, multi, striped, header, selected }
    if (height != null) cfg.height = height
    w._extra["data-vt"] = JSON.stringify(cfg)
    if (onSelect)   w._extra["data-on-select"]   = appOf(app)._onPayload(onSelect, "p")
    if (onDblclick) w._extra["data-on-dblclick"] = appOf(app)._onPayload(onDblclick, "p")
    if (onSort)     w._extra["data-on-sort"]     = appOf(app)._onPayload(onSort, "p")
    return w
}

/** Lista de una columna sin cabecera. onSelect(d) → d.row[0] es el elemento elegido. */
export const Listbox = (items, { onSelect, onDblclick, height, app, ...p } = {}) =>
    Table([""], items.map(x => [x]), { header: false, sortable: false, striped: false, onSelect, onDblclick, height, app, ...p })

/**
 * Tree([{label:"src", open:true, children:[{label:"main.rs", id:7}]}], { onSelect, onDblclick, height })
 *   onSelect(d) → d = { path:[0,0], label, id }. Cambiar nodos: app.treeSet(t.id, nodes)
 */
export const Tree = (nodes, { onSelect, onDblclick, height, app, ...p } = {}) => {
    if (!p.id) p.id = _vtId("vtree")
    if (height != null) p.style = ((p.style || "") + `;max-height:${typeof height === "number" ? height + "px" : height}`).replace(/^;/, "")
    const w = new (makeWidget("div", "vspk-tree"))([], p)
    w.id = p.id
    w._extra["data-vt"] = JSON.stringify({ nodes })
    if (onSelect)   w._extra["data-on-select"]   = appOf(app)._onPayload(onSelect, "p")
    if (onDblclick) w._extra["data-on-dblclick"] = appOf(app)._onPayload(onDblclick, "p")
    return w
}

/** Selector de color nativo. onChange(str) recibe '#rrggbb'. */
export const ColorPicker = ({ value = "#6750a4", ...o } = {}) => Input({ type: "color", value, ...o })
/** Selector de fecha (o fecha y hora con time:true). onChange(str) recibe 'AAAA-MM-DD'. */
export const DatePicker = ({ value = "", time = false, ...o } = {}) => Input({ type: time ? "datetime-local" : "date", value, ...o })


export const Textarea = ({ bind = null, placeholder = "", rows = 4, value = "", onChange, app, ...p } = {}) => {
    const w = new (makeWidget("textarea", "sz-textarea"))([], p)
    if (placeholder) w._extra["placeholder"] = placeholder
    w._extra["rows"] = String(rows)
    if (onChange && !bind) w._extra["oninput"] = appOf(app)._onPayload(onChange, "this.value")
    w.render = () => `<textarea${w._attrs()}${bindAttr(bind)}>${esc(bind ? bind.get() : value)}</textarea>`
    return w
}

export const Slider = ({ bind = null, min = 0, max = 100, step = 1, ...p } = {}) => {
    const w = new (makeWidget("input", "sz-slider"))([], p)
    w.render = () => `<input${w._attrs()} type="range" min="${min}" max="${max}" step="${step}" value="${esc(bind ? bind.get() : min)}"${bindAttr(bind)}>`
    return w
}

export const Select = (options, { bind = null, value = "", onChange, app, ...p } = {}) => {
    const w = new (makeWidget("select", "sz-select"))([], p)
    if (onChange && !bind) w._extra["onchange"] = appOf(app)._onPayload(onChange, "this.value")
    w.render = () => {
        const cur = String(bind ? bind.get() : value)
        const opts = options.map(o => {
            const [v, label] = Array.isArray(o) ? o : [o, o]
            return `<option value="${esc(v)}"${String(v) === cur ? " selected" : ""}>${esc(label)}</option>`
        }).join("")
        return `<select${w._attrs()}${bindAttr(bind)}>${opts}</select>`
    }
    return w
}

/** Interruptor (sz-switch, la clase real de spork.css) */
export const Checkbox = (label, { bind = null, checked = false, onChange, app, ...p } = {}) => {
    const w = new (makeWidget("label", ""))([], p)
    const onch = (onChange && !bind) ? ` onchange="${esc(appOf(app)._onPayload(onChange, "this.checked"))}"` : ""
    w.render = () => {
        const on = bind ? !!bind.get() : checked
        return `<label class="sz-switch"><input type="checkbox"${on ? " checked" : ""}${bindAttr(bind)}${onch}>`
             + `<span class="sz-switch-track"><span class="sz-switch-thumb"></span></span>`
             + `<span class="sz-switch-label">${esc(label)}</span></label>`
    }
    return w
}

export const Img = (src, alt = "", p = {}) => {
    const w = new (makeWidget("img", "sz-img"))([], p)
    w._extra["src"] = src; w._extra["alt"] = alt
    w.render = () => `<img${w._attrs()}>`
    return w
}

/** Progress(state) — la barra se mueve sola cuando cambia el State — o Progress(40) */
export const Progress = (value, max = 100, p = {}) => {
    const w = new (makeWidget("div", "sz-progress"))([], p)
    max = max || 100
    w.render = () => {
        const isState = value instanceof State
        const pct = Math.round(Math.max(0, Math.min(100, (Number(isState ? value.get() : value) || 0) / max * 100)) * 10) / 10
        const ds = isState
            ? ` data-spork-style="${esc(`{"width":(Math.min(100,Math.max(0,(+window.__state[${js(value.name)}]||0)/${max}*100)).toFixed(1)+"%")}`)}"`
            : ""
        return `<div${w._attrs()}><div class="sz-progress-bar" style="width:${pct}%"${ds}></div></div>`
    }
    return w
}

// ── Canvas ────────────────────────────────────────────────────────────────────
//
//   const cv = app.canvas("lienzo", 400, 300)
//   cv.color("#6750A4").rect(10, 10, 100, 60); cv.circle(200, 60, 40); cv.line(0, 0, 400, 300)
//   cv.text(10, 280, "hola"); cv.erase(); cv.onMouse(e => ...)   // e: type down|up|move|click, x, y, button

class Canvas extends Widget {
    constructor(app, id, w, h) { super(); this._app = app; this.id = id; this.w = w; this.h = h }
    render() {
        return `<canvas id="${esc(this.id)}" width="${this.w}" height="${this.h}" style="width:${this.w}px;max-width:100%;height:auto;border:1px solid rgba(128,128,128,.4);border-radius:8px;touch-action:none"></canvas>`
    }
    _op(op, ...args) { this._app._cv(this.id, op, args); return this }
    color(c)              { return this._op("color", c) }
    lineWidth(n)          { return this._op("lw", n) }
    font(size)            { return this._op("font", size) }
    line(x1, y1, x2, y2)  { return this._op("line", x1, y1, x2, y2) }
    rect(x, y, w, h)      { return this._op("rect", x, y, w, h) }
    frame(x, y, w, h)     { return this._op("frame", x, y, w, h) }
    circle(x, y, r)       { return this._op("circle", x, y, r) }
    ring(x, y, r)         { return this._op("ring", x, y, r) }
    text(x, y, s)         { return this._op("text", x, y, s) }
    poly(points)          { return this._op("poly", points.map(p => [...p])) }
    erase()               { return this._op("clear") }
    draw(code)            { return this._op("draw", code) }   // JS crudo con (ctx, canvas) en el ámbito
    onMouse(fn)           { this._app._cvMouse(this.id, fn); return this }
}

// ── Menús (barra de menú HTML con atajos de teclado) ─────────────────────────
//
//   app.add(MenuBar(
//     Menu("Archivo", MenuItem("Abrir...", app.onClick(abrir), "ctrl+o"), MenuSep(),
//                     MenuItem("Salir", app.onClick(() => app.quit()))),
//     Menu("Ayuda", MenuItem("Acerca de", app.onClick(acerca)))), ...resto)
//   Atajos: "ctrl+o", "ctrl+shift+s", "alt+x", "f5"... (orden: ctrl, shift, alt, tecla).

const MENU_A = "<style>.sz-menubar{position:fixed;top:0;left:0;right:0;z-index:1000;display:flex;gap:2px;padding:3px 6px;background:var(--sz-surface,#fff);color:var(--sz-on-surface,#1d1b20);border-bottom:1px solid rgba(128,128,128,.3);font-size:14px}.sz-menubar-space{height:38px;width:100%;flex:none}.sz-menu{position:relative}.sz-menu-title{background:none;border:0;padding:6px 10px;border-radius:6px;color:inherit;font:inherit;cursor:pointer}.sz-menu-title:hover,.sz-menu.sz-open>.sz-menu-title{background:rgba(128,128,128,.18)}.sz-menu-list{display:none;position:absolute;top:100%;left:0;min-width:210px;padding:4px;background:var(--sz-surface,#fff);color:inherit;border:1px solid rgba(128,128,128,.35);border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.2)}.sz-menu.sz-open>.sz-menu-list{display:block}.sz-menu-item{display:flex;justify-content:space-between;gap:24px;width:100%;background:none;border:0;padding:6px 10px;border-radius:6px;color:inherit;font:inherit;cursor:pointer;text-align:left}.sz-menu-item:hover{background:rgba(128,128,128,.18)}.sz-menu-item kbd{opacity:.6;font:inherit;font-size:12px}.sz-menu-sep{height:1px;margin:4px 6px;background:rgba(128,128,128,.3)}.sz-native .sz-menubar,.sz-native .sz-menubar-space{display:none!important}</style><div class=\"sz-menubar\">"
const MENU_B = "</div><div class=\"sz-menubar-space\"></div><script>(function(){if(window.__menu)return;window.__menu=1;var bar=document.querySelector('.sz-menubar');function menus(){return bar.querySelectorAll(':scope > .sz-menu')}window.__vspk_menu_click=function(id){var p=id.split('.');var m=menus()[+p[0]];if(m)m.querySelector('.sz-menu-list').children[+p[1]].click()};window.__vspk_menu_ok=function(){document.documentElement.classList.add('sz-native')};if(bar&&window.ipc&&window.__vspk_native_menu_ok){var ms=[];Array.prototype.forEach.call(menus(),function(m,mi){var items=[];Array.prototype.forEach.call(m.querySelector('.sz-menu-list').children,function(c,ii){if(c.classList.contains('sz-menu-sep'))items.push({sep:true});else items.push({id:mi+'.'+ii,label:(c.querySelector('span')||c).textContent,accel:c.getAttribute('data-accel')||''})});ms.push({label:m.querySelector('.sz-menu-title').textContent,items:items})});window.ipc.postMessage(JSON.stringify({cmd:'setMenu',menu:ms}))}function closeAll(except){document.querySelectorAll('.sz-menu.sz-open').forEach(function(m){if(m!==except)m.classList.remove('sz-open')})}document.addEventListener('click',function(e){var t=e.target.closest?e.target.closest('.sz-menu-title'):null;closeAll(t?t.parentNode:null);if(t)t.parentNode.classList.toggle('sz-open');var it=e.target.closest?e.target.closest('.sz-menu-item'):null;if(it)closeAll(null)});document.addEventListener('mouseover',function(e){var t=e.target.closest?e.target.closest('.sz-menu-title'):null;var o=document.querySelector('.sz-menu.sz-open');if(t&&o&&o!==t.parentNode){closeAll(t.parentNode);t.parentNode.classList.add('sz-open')}});document.addEventListener('keydown',function(e){if(e.key==='Escape'){closeAll(null);return}if(document.documentElement.classList.contains('sz-native')&&!/Win/.test(navigator.platform))return;var k=(e.ctrlKey?'ctrl+':'')+(e.shiftKey?'shift+':'')+(e.altKey?'alt+':'')+e.key.toLowerCase();var items=document.querySelectorAll('.sz-menu-item[data-accel]');for(var i=0;i<items.length;i++){var a=items[i].getAttribute('data-accel');if(a&&a.toLowerCase()===k){e.preventDefault();items[i].click();return}}})})();</script>"

export const MenuItem = (label, onclick = "", shortcut = "") =>
    new Raw(`<button type="button" class="sz-menu-item" onclick="${String(onclick).replaceAll('"', "&quot;")}" data-accel="${esc(shortcut)}"><span>${esc(label)}</span>${shortcut ? `<kbd>${esc(shortcut)}</kbd>` : ""}</button>`)
export const MenuSep = () => new Raw(`<div class="sz-menu-sep"></div>`)
export const Menu = (title, ...items) =>
    new Raw(`<div class="sz-menu"><button type="button" class="sz-menu-title">${esc(title)}</button><div class="sz-menu-list">${items.map(i => i instanceof Widget ? i.render() : String(i)).join("")}</div></div>`)
export const MenuBar = (...menus) =>
    new Raw(MENU_A + menus.map(m => m instanceof Widget ? m.render() : String(m)).join("") + MENU_B)

// ── Ventanas adicionales ─────────────────────────────────────────────────────
//
//   const aj = app.window("Ajustes", 360, 240)
//   aj.add(Col(H4("Ajustes"), Input({ bind: nombre })))   // los states se comparten entre ventanas
//   aj.show()   aj.close()   aj.onClose(() => true)   aj.setTitle("...")   aj.evalJs("...")

class ChildWindow {
    constructor(app, id, title, width, height) {
        this._app = app; this.id = id; this.title = title; this.width = width; this.height = height
        this.widgets = []; this.proc = null; this.htv = ""; this.want = false; this.closeOn = false; this.closeJs = ""
    }
    add(...ws)       { this.widgets.push(...ws); return this }
    show()           { this._app._winShow(this); return this }
    close()          { this._app._winEval(this, "__vspk.close()") }
    setTitle(t)      { this._app._winEval(this, `__vspk.setTitle(${js(t)})`) }
    evalJs(code)     { this._app._winEval(this, code) }
    onClose(fn)      { this._app._winOnClose(this, fn); return this }
    isOpen()         { return this.proc !== null && this.proc.exitCode === null }
}

// ── App ───────────────────────────────────────────────────────────────────────

const PAGE_JS = "window.__state = %STATE%;\nwindow.__win = %WIN%;\nwindow.__set = function(name, value) {\n  window.__state[name] = value;\n  document.querySelectorAll('[data-spork-text=\"' + name + '\"]').forEach(function(el) { el.textContent = value; });\n  document.querySelectorAll('[data-spork-bind=\"' + name + '\"]').forEach(function(el) {\n    if (el.type === 'checkbox') el.checked = !!value;\n    else if (el.value != value) el.value = value;\n  });\n  var ev = function(code) { return new Function('return (' + code + ')')(); };\n  document.querySelectorAll('[data-spork-style]').forEach(function(el) { try { Object.assign(el.style, ev(el.dataset.sporkStyle)); } catch(_) {} });\n  document.querySelectorAll('[data-spork-if]').forEach(function(el) { try { el.style.display = ev(el.dataset.sporkIf) ? '' : 'none'; } catch(_) {} });\n  document.querySelectorAll('[data-spork-class]').forEach(function(el) { try { var c = ev(el.dataset.sporkClass); if (typeof c === 'string') el.className = (el.dataset.sporkBase || (el.dataset.sporkBase = el.className)) + ' ' + c; } catch(_) {} });\n};\n// Valor que el usuario escribe/elige \u2192 a PHP (State::get() lo ve) y a los dem\u00e1s widgets enlazados.\nwindow.__sync = function(n, v) {\n  try { fetch('http://127.0.0.1:%PORT%/event/%VEV%', {method: 'POST', mode: 'no-cors', headers: {'Content-Type': 'text/plain'}, body: JSON.stringify({n: n, v: v, w: window.__win})}); } catch(_) {}\n};\n(function() {\n  function onUser(e) {\n    var el = e.target && e.target.closest ? e.target.closest('[data-spork-bind]') : null;\n    if (!el) return;\n    var v = el.type === 'checkbox' ? el.checked : (el.type === 'range' || el.type === 'number') ? Number(el.value) : el.value;\n    var n = el.getAttribute('data-spork-bind');\n    window.__set(n, v);\n    window.__sync(n, v);\n  }\n  document.addEventListener('input', onUser);\n  document.addEventListener('change', onUser);\n})();\ndocument.addEventListener('click', function(e) {      // Tabs\n  var b = e.target.closest ? e.target.closest('[data-ttarget]') : null;\n  if (!b) return;\n  var g = b.dataset.ttarget, i = +b.dataset.tidx;\n  document.querySelectorAll('[data-tpanel]').forEach(function(p) { if (p.dataset.tpanel === g) p.classList.toggle('sz-active', +p.dataset.tidx === i); });\n  document.querySelectorAll('[data-ttarget]').forEach(function(x) { if (x.dataset.ttarget === g) x.classList.toggle('sz-active', +x.dataset.tidx === i); });\n});\nwindow.__toast = function(msg, v, ms) {\n  var c = document.getElementById('__vspk_toasts');\n  if (!c) { c = document.createElement('div'); c.className = 'sz-toast-container'; c.id = '__vspk_toasts'; document.body.appendChild(c); }\n  var t = document.createElement('div'); t.className = 'sz-toast' + (v ? ' sz-toast-' + v : ''); t.textContent = msg; c.appendChild(t);\n  setTimeout(function() { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; setTimeout(function() { t.remove(); }, 300); }, ms || 3000);\n};\nwindow.__vspk_cmd = function(cmd, a, b) {\n  try {\n    if (cmd === 'close' || cmd === 'fullscreen') window.ipc && window.ipc.postMessage(JSON.stringify({cmd: cmd === 'close' ? 'close' : 'toggleFullscreen'}));\n    else if (cmd === 'setTitle' && window.__vspk_api) window.__vspk_api.setTitle(a);\n    else if (cmd === 'setTitle' && typeof __vspk !== 'undefined') __vspk.setTitle(a);\n    else if (cmd === 'notify' && typeof __vspk !== 'undefined') __vspk.notify(a, b);\n  } catch(err) { console.error(err); }\n};\nwindow.__cv = function(id, op, a) {\n  var c = document.getElementById(id); if (!c) return;\n  var x = c.getContext('2d');\n  if (op === 'clear') { x.clearRect(0, 0, c.width, c.height); }\n  else if (op === 'color') { x.fillStyle = a[0]; x.strokeStyle = a[0]; }\n  else if (op === 'lw') { x.lineWidth = a[0]; }\n  else if (op === 'font') { x.font = a[0] + 'px sans-serif'; }\n  else if (op === 'line') { x.beginPath(); x.moveTo(a[0], a[1]); x.lineTo(a[2], a[3]); x.stroke(); }\n  else if (op === 'rect') { x.fillRect(a[0], a[1], a[2], a[3]); }\n  else if (op === 'frame') { x.strokeRect(a[0], a[1], a[2], a[3]); }\n  else if (op === 'circle') { x.beginPath(); x.arc(a[0], a[1], a[2], 0, 6.283185307); x.fill(); }\n  else if (op === 'ring') { x.beginPath(); x.arc(a[0], a[1], a[2], 0, 6.283185307); x.stroke(); }\n  else if (op === 'text') { x.fillText(a[2], a[0], a[1]); }\n  else if (op === 'poly') { var p = a[0]; x.beginPath(); x.moveTo(p[0][0], p[0][1]); for (var i = 1; i < p.length; i++) x.lineTo(p[i][0], p[i][1]); x.closePath(); x.fill(); }\n  else if (op === 'draw') { new Function('ctx', 'canvas', a[0])(x, c); }\n};\nObject.keys(window.__state).forEach(function(k) { window.__set(k, window.__state[k]); });\n(function connectSSE() {\n  var es = new EventSource('http://127.0.0.1:%PORT%/events');\n  es.addEventListener('state', function(e) { var d = JSON.parse(e.data); if (d.src && d.src === window.__win) return; window.__set(d.name, d.value); });\n  [%EVALEV%, 'all'].forEach(function(n) { es.addEventListener(n, function(e) { try { (0, eval)(JSON.parse(e.data)); } catch(err) { console.error(err); } }); });\n  es.onerror = function() { es.close(); setTimeout(connectSSE, 1000); };\n})();"
const SPORK_CSS_CDN = "https://cdn.jsdelivr.net/gh/unoudos/spork-ui@main/spork.css"
const SPORK_JS_CDN  = "https://cdn.jsdelivr.net/gh/unoudos/spork-ui@main/spork.js"

export class App {
    constructor(title = "App", {
        width    = 1024,
        height   = 768,
        theme    = "light",
        primary  = "#6750A4",
        bg       = "",
        surface  = "",
        font     = "",
        devtools = false,
        vspkExe  = null,
    } = {}) {
        this.title = title; this.width = width; this.height = height; this.theme = theme; this.primary = primary
        this.bg = bg; this.surface = surface; this.font = font; this.devtools = devtools; this.vspkExe = vspkExe
        this._root = Col()
        this._states = {}
        this._token = crypto.randomUUID().replaceAll("-", "").slice(0, 16)   // ids no adivinables desde otra web
        this._cbs = new Map(); this._cbCount = 0
        this._events = new Map()             // eventos internos (con token)
        this._eventHandlers = new Map()      // onEvent público (/event/<nombre>)
        this._clients = new Set()            // controladores SSE
        this._timers = []; this._timerIds = []
        this._keyOn = false; this._closeOn = false; this._running = false; this._quit = false
        this._cvIds = []; this._cvLogs = {}; this._cvMouseJs = ""
        this._wins = []
        this._proc = null
        this._server = this._makeServer()    // el puerto se conoce ya, antes de construir los widgets
        this._port = this._server.port
        _currentApp = this
    }

    // ── Estado ────────────────────────────────────────────────────────────────
    state(name, initial) {
        return this._states[name] ??= new State(name, initial, this)
    }

    // ── Callbacks ─────────────────────────────────────────────────────────────
    _ev(name) { return `__${name}_${this._token}` }
    _postJs(name, bodyExpr) {
        return `fetch('http://127.0.0.1:${this._port}/event/${name}',{method:'POST',mode:'no-cors',headers:{'Content-Type':'text/plain'},body:${bodyExpr}})`
    }
    /** Registra fn (se ejecuta en Bun) y devuelve el JS para dispararla desde un onclick. */
    onClick(fn) {
        const id = `cb_${this._token}_${++this._cbCount}`
        this._cbs.set(id, fn)
        return `fetch('http://127.0.0.1:${this._port}/cb/${id}',{mode:'no-cors'})`
    }
    Button(text, opts = {}) { return Button(text, { app: this, ...opts }) }
    _onPayload(fn, expr) {
        const name = this._ev(`p${++this._cbCount}`)
        this._events.set(name, fn)
        return this._postJs(name, `JSON.stringify(${expr})`)
    }
    /** Handler para eventos enviados desde la página: fetch('http://127.0.0.1:PUERTO/event/nombre', {method:'POST', body: JSON.stringify(dato)}) */
    onEvent(event, handler) {
        if (!this._eventHandlers.has(event)) this._eventHandlers.set(event, [])
        this._eventHandlers.get(event).push(handler)
        return this
    }

    // ── SSE ───────────────────────────────────────────────────────────────────
    _pushSse(event, data) {
        const msg = new TextEncoder().encode(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`)
        for (const c of this._clients) { try { c.enqueue(msg) } catch { this._clients.delete(c) } }
    }
    _pushState(name, value) { this._pushSse("state", { name, value }) }
    /** Ejecuta JS en la ventana principal. */
    evalJs(code) { this._pushSse("eval", code) }

    // ── Utilidades de ventana ─────────────────────────────────────────────────
    toast(msg, variant = "", ms = 3000) { this.evalJs(`window.__toast(${js(msg)},${js(variant)},${ms})`) }
    setTitle(t)           { this.evalJs(`__vspk.setTitle(${js(t)})`) }
    notify(title, body = "") { this.evalJs(`__vspk.notify(${js(title)},${js(body)})`) }
    copyText(text)        { this.evalJs(`__vspk.clipboard.write(${js(text)})`) }
    quit()                { this._quit = true; try { this._proc?.kill() } catch {} }

    /** fn recibe {key, code, ctrl, shift, alt, meta}. Llamar antes de run(). */
    onKey(fn) { this._keyOn = true; this._events.set(this._ev("k"), fn); return this }
    /** fn() devuelve false para cancelar el cierre de la ventana. Llamar antes de run(). */
    onClose(fn) {
        this._closeOn = true
        this._events.set(this._ev("c"), async () => {
            let r = true
            try { r = await fn() } catch (e) { console.error("[vspk] error en onClose:", e) }
            this.evalJs(r === false ? "__vspk.cancelClose()" : "__vspk.confirmClose()")
        })
        return this
    }

    _dialog(kind, title, fn) {
        const name = this._ev(`d${++this._cbCount}`)
        this._events.set(name, (d) => fn(d && typeof d === "object" ? (d.path ?? null) : null))
        this.evalJs(`__vspk.dialog({kind:${js(kind)},title:${js(title)}}).then(function(p){${this._postJs(name, "JSON.stringify({path:p})")}})`)
    }
    pickFile(title, fn)   { this._dialog("open", title, fn) }
    saveFile(title, fn)   { this._dialog("save", title, fn) }
    pickFolder(title, fn) { this._dialog("folder", title, fn) }

    // ── Diálogos modales (mensaje / confirmación / pedir texto) ──
    _modal(call, conv, fn) {
        const name = this._ev(`m${++this._cbCount}`)
        this._events.set(name, (d) => { if (fn) fn(conv(d && typeof d === "object" ? d.v : null)) })
        this.evalJs(`Promise.resolve(${call}).then(function(v){${this._postJs(name, "JSON.stringify({v:v})")}})`)
    }
    /** Diálogo modal con un botón Aceptar. fn() al cerrarlo. */
    message(text, fn)  { this._modal(`alert(${js(text)})`, () => null, fn ? () => fn() : null) }
    /** Modal Aceptar/Cancelar. fn(true|false). */
    confirm(text, fn)  { this._modal(`confirm(${js(text)})`, (v) => !!v, fn) }
    /** Modal que pide un texto. fn(texto) o fn(null) si se cancela. */
    prompt(text, fn, def = "") { this._modal(`prompt(${js(text)},${js(def)})`, (v) => typeof v === "string" ? v : null, fn) }

    // ── Tabla / árbol (win = ventana extra donde vive el widget) ──
    tableSet(id, rows, cols = null, win = null)  { (win ?? this).evalJs(`window.__vspk_table_set(${js(id)},${js(cols)},${js(rows)})`) }
    tableSelect(id, index, win = null)           { (win ?? this).evalJs(`window.__vspk_table_select(${js(id)},${index | 0})`) }
    tableSort(id, col, desc = false, win = null) { (win ?? this).evalJs(`window.__vspk_table_sort(${js(id)},${col | 0},${desc ? -1 : 1})`) }
    treeSet(id, nodes, win = null)               { (win ?? this).evalJs(`window.__vspk_tree_set(${js(id)},${js(nodes)})`) }

    /** Ejecuta fn una vez dentro de ms milisegundos (mientras run() esté activo). */
    runAfter(ms, fn) { this._timers.push({ ms, once: true, fn }); if (this._running) this._startTimer(this._timers.at(-1)); return this }
    /** Ejecuta fn cada ms milisegundos. Devuelve false desde fn para cancelarlo. */
    runEvery(ms, fn) { this._timers.push({ ms, once: false, fn }); if (this._running) this._startTimer(this._timers.at(-1)); return this }
    _startTimer(t) {
        const tick = async () => {
            let r
            try { r = await t.fn() } catch (e) { console.error("[vspk] error en temporizador:", e); r = false }
            if (t.once || r === false) t.cancel()
        }
        if (t.once) { const id = setTimeout(tick, t.ms); t.cancel = () => clearTimeout(id) }
        else        { const id = setInterval(tick, t.ms); t.cancel = () => clearInterval(id) }
        this._timerIds.push(t)
    }

    // ── Canvas ────────────────────────────────────────────────────────────────
    canvas(id, w, h) {
        this._cvIds.push(id); this._cvLogs[id] = ""
        return new Canvas(this, id, w, h)
    }
    _cv(id, op, args) {
        const code = `__cv(${js(id)},${js(op)},${js(args)})`
        if (op === "clear") this._cvLogs[id] = ""
        this._cvLogs[id] = (this._cvLogs[id] ?? "") + code + ";"
        if (this._running) this._pushSse("all", code)
    }
    _cvMouse(id, fn) {
        const name = this._ev(`m${++this._cbCount}`)
        this._events.set(name, fn)
        const code = `(function(){var c=document.getElementById(${js(id)});if(!c)return;function p(t,e){if(t==='move'){var n=Date.now();if(n-(c.__lm||0)<30)return;c.__lm=n;}var r=c.getBoundingClientRect();`
            + this._postJs(name, "JSON.stringify({type:t,x:Math.round((e.clientX-r.left)*c.width/r.width),y:Math.round((e.clientY-r.top)*c.height/r.height),button:e.button})")
            + `}['down','up','move','click'].forEach(function(t){c.addEventListener(t==='down'?'mousedown':t==='up'?'mouseup':t==='move'?'mousemove':'click',function(e){p(t,e)})})})();`
        this._cvMouseJs += code
        if (this._running) this._pushSse("all", code)
    }

    // ── Ventanas adicionales ──────────────────────────────────────────────────
    window(title, width = 480, height = 360) {
        const w = new ChildWindow(this, `w${this._wins.length + 1}`, title, width, height)
        this._wins.push(w)
        return w
    }
    _winEval(w, code) { this._pushSse(`eval_${w.id}`, code) }
    _winShow(w) { if (this._running) this._winOpen(w); else w.want = true }
    _winOnClose(w, fn) {
        const ev = this._ev("c" + w.id)
        w.closeOn = true
        w.closeJs = `window.addEventListener('vspk:closeRequested',function(){${this._postJs(ev, "'{}'")}});`
        this._events.set(ev, async () => {
            let r = true
            try { r = await fn() } catch (e) { console.error("[vspk] error en onClose:", e) }
            this._winEval(w, r === false ? "__vspk.cancelClose()" : "__vspk.confirmClose()")
        })
    }
    async _winOpen(w) {
        if (w.isOpen()) return
        if (w.htv) { try { await Bun.file(w.htv).delete?.() } catch {} }
        const body = w.widgets.map(x => x instanceof Widget ? x.render() : String(x)).join("\n")
        const page = this._buildPage(w.title, body, `eval_${w.id}`, false, w.closeJs)
        const icon = await this._findIcon()
        const head = `title: ${w.title}\nwidth: ${w.width}\nheight: ${w.height}\ndevtools: true\n${icon ? `icon: ${icon}\n` : ""}${w.closeOn ? "on_close: confirm\n" : ""}`
        w.htv = await this._writeHtv(head + "\n" + page)
        w.proc = this._spawn(w.htv)
    }

    add(...widgets) { this._root.add(...widgets); return this }

    // ── HTML ──────────────────────────────────────────────────────────────────
    _buildHtml() { return this._buildPage(this.title, this._root.render(), "eval", true, "") }

    _buildPage(title, body, evalEv, isMain, childCloseJs) {
        const stateJs = js(Object.fromEntries(Object.entries(this._states).map(([k, s]) => [k, s.get()])))
        let code = PAGE_JS.replaceAll("%STATE%", stateJs).replaceAll("%PORT%", String(this._port))
            .replaceAll("%VEV%", this._ev("v")).replaceAll("%WIN%", js(evalEv)).replaceAll("%EVALEV%", js(evalEv))
        const keyJs = (isMain && this._keyOn)
            ? 'document.addEventListener("keydown",function(e){' + this._postJs(this._ev("k"),
                "JSON.stringify({key:e.key,code:e.code,ctrl:e.ctrlKey,shift:e.shiftKey,alt:e.altKey,meta:e.metaKey})") + "});"
            : ""
        let closeJs = childCloseJs
        if (isMain && this._closeOn)
            closeJs += 'window.addEventListener("vspk:closeRequested",function(){' + this._postJs(this._ev("c"), '"{}"') + "});"
        code += "\n" + keyJs + closeJs + this._cvIds.map(i => this._cvLogs[i] ?? "").join("") + this._cvMouseJs

        let cssVars = `  --sz-primary: ${this.primary};`
        if (this.bg)      cssVars += `\n  --sz-bg: ${this.bg};`
        if (this.surface) cssVars += `\n  --sz-surface: ${this.surface};`
        if (this.font)    cssVars += `\n  --sz-font: ${this.font}, system-ui, sans-serif;`
        const theme = this.theme === "dark" ? "dark" : "light"
        return `<!DOCTYPE html>
<html data-theme="${theme}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${esc(title)}</title>
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="spork.css" onerror="this.onerror=null;this.href='${SPORK_CSS_CDN}'">
  <style>:root {
${cssVars}
}</style>
</head>
<body class="sz-body">

<div id="__app" class="sz-page">
${body}
</div>

<script>
${code}
</script>
<script src="spork.js" onerror="var s=document.createElement('script');s.src='${SPORK_JS_CDN}';document.body.appendChild(s)"></script>
</body>
</html>`
    }

    // ── Servidor HTTP (puente) ────────────────────────────────────────────────
    _makeServer() {
        const app = this
        const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, OPTIONS", "Access-Control-Allow-Headers": "*" }
        return Bun.serve({
            port: 0,
            hostname: "127.0.0.1",
            idleTimeout: 0,   // Bun cierra por defecto las conexiones inactivas a los 10 s: el SSE se cortaría
            async fetch(req) {
                const u = new URL(req.url)
                if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS })
                if (u.pathname === "/events") {
                    let ctrl
                    const stream = new ReadableStream({
                        start(c) {
                            ctrl = c; app._clients.add(c)
                            const enc = new TextEncoder()
                            c.enqueue(enc.encode(": conectado\n\n"))
                            c.__hb = setInterval(() => { try { c.enqueue(enc.encode(": ping\n\n")) } catch { clearInterval(c.__hb) } }, 15000)
                        },
                        cancel() { clearInterval(ctrl.__hb); app._clients.delete(ctrl) },
                    })
                    return new Response(stream, { headers: { ...CORS, "Content-Type": "text/event-stream", "Cache-Control": "no-cache", "Connection": "keep-alive" } })
                }
                if (u.pathname === "/favicon.ico") return new Response(null, { status: 204, headers: CORS })
                const cb = u.pathname.match(/^\/cb\/(.+)$/)
                if (cb) { app._dispatch("cb", decodeURIComponent(cb[1]), ""); return new Response("ok", { headers: CORS }) }
                const ev = u.pathname.match(/^\/event\/(.+)$/)
                if (ev && req.method === "POST") {
                    app._dispatch("event", decodeURIComponent(ev[1]), await req.text())
                    return new Response("ok", { headers: CORS })
                }
                return new Response("not found", { status: 404, headers: CORS })
            },
        })
    }

    // ── Despacho ──────────────────────────────────────────────────────────────
    async _dispatch(kind, name, body) {
        try {
            if (kind === "cb") {
                const fn = this._cbs.get(name)    // id sin token válido → no existe → no hace nada
                if (fn) await fn()
                return
            }
            let data = null
            try { data = body ? JSON.parse(body) : null } catch { data = body }
            if (name === this._ev("v")) {
                if (data && typeof data === "object" && String(data.n) in this._states) {
                    const n = String(data.n)
                    this._states[n]._receive(data.v)
                    if (this._wins.length) this._pushSse("state", { name: n, value: data.v, src: String(data.w ?? "") })
                }
                return
            }
            const fn = this._events.get(name)
            if (fn) { await fn(data); return }
            for (const h of this._eventHandlers.get(name) ?? []) await h(data)
        } catch (e) {
            console.error("[vspk] error en callback:", e)
        }
    }

    // ── run() ─────────────────────────────────────────────────────────────────
    async _writeHtv(content) {
        const p = path.join(os.tmpdir(), `vspk_${Math.random().toString(36).slice(2)}.htv`)
        await Bun.write(p, content)
        return p
    }
    _spawn(htv) {
        return spawn({ cmd: [this.vspkExe ?? this._exe, htv], stdout: "inherit", stderr: "inherit", windowsHide: true })
    }
    async _findIcon() {
        const dirs = [path.dirname(Bun.main), import.meta.dir]
        for (const d of dirs) for (const n of ["icon.ico", "icon.png", "favicon.ico", "favicon.png"]) {
            const p = path.join(d, n)
            if (await Bun.file(p).exists()) return p
        }
        return ""
    }

    /** Abre vspk con un .htv temporal y atiende eventos hasta que se cierra la ventana. */
    async run() {
        this._exe = this.vspkExe ?? (await findVspk())
        const html = this._buildHtml()
        const icon = await this._findIcon()
        const head = `title: ${this.title}\nwidth: ${this.width}\nheight: ${this.height}\n`
            + (this.devtools ? "devtools: true\n" : "") + (icon ? `icon: ${icon}\n` : "") + (this._closeOn ? "on_close: confirm\n" : "")
        const htv = await this._writeHtv(head + "\n" + html)
        try {
            this._proc = this._spawn(htv)
            this._running = true
            for (const w of this._wins) if (w.want) await this._winOpen(w)
            for (const t of this._timers) this._startTimer(t)
            await this._proc.exited
        } finally {
            this._running = false
            for (const t of this._timerIds) { try { t.cancel() } catch {} }
            // Al cerrar la principal se cierran las demás.
            for (const w of this._wins) if (w.isOpen()) this._winEval(w, "__vspk.close()")
            if (this._wins.length) await Bun.sleep(300)
            for (const w of this._wins) {
                if (w.proc && w.proc.exitCode === null) { try { w.proc.kill() } catch {} }
                if (w.htv) { try { (await import("node:fs")).unlinkSync(w.htv) } catch {} }
            }
            for (const c of this._clients) { try { clearInterval(c.__hb); c.close() } catch {} }
            this._clients.clear()
            try { (await import("node:fs")).unlinkSync(htv) } catch {}
            this._server.stop(true)
        }
    }
}

async function findVspk() {
    const exe = IS_WINDOWS ? "vspk.exe" : "vspk"
    const candidates = [
        process.env.VSPK_EXE,
        path.join(path.dirname(Bun.main), exe),
        path.join(import.meta.dir, exe),
        ...(IS_WINDOWS ? [`C:\\spork\\${exe}`, `C:\\spork_studio\\${exe}`] : []),
    ].filter(Boolean)
    for (const c of candidates) {
        if (await Bun.file(c).exists()) return c
    }
    // En el PATH
    for (const d of (process.env.PATH ?? "").split(path.delimiter)) {
        const p = path.join(d, exe)
        if (d && await Bun.file(p).exists()) return p
    }
    return exe
}

// ── Ventanas vspk por IPC ─────────────────────────────────────────────────────

export class Window {
    #id
    #process
    #handlers = {}
    #listening = false

    constructor(id, process) {
        this.#id      = id
        this.#process = process
    }

    get id() { return this.#id }

    send(payload) {
        return ipcSend({ cmd: "send", to: this.#id, payload })
    }

    broadcast(payload) {
        return ipcSend({ cmd: "broadcast", payload })
    }

    focus()             { return ipcSend({ cmd: "focus",  id: this.#id }) }
    move(x, y)         { return ipcSend({ cmd: "move",   id: this.#id, x, y }) }
    resize(w, h)       { return ipcSend({ cmd: "resize", id: this.#id, w, h }) }
    snap(pos)          { return ipcSend({ cmd: "snap",   id: this.#id, pos }) }
    close()            { this.#process.kill() }

    wait() { return this.#process.exited }

    isOpen() { return this.#process.exitCode === null }

    // ── Escuchar eventos desde el JS del .htv ─────────────────────────────────
    on(event, handler) {
        if (!this.#handlers[event]) this.#handlers[event] = []
        this.#handlers[event].push(handler)
        this.#startListening()
    }

    #startListening() {
        if (this.#listening) return
        this.#listening = true

        const connect = () => {
            const sock = net.createConnection({ path: PIPE })
            let buf = ""

            sock.on("connect", () => {
                console.log("[vspk] Escuchando eventos IPC")
            })

            sock.on("data", (chunk) => {
                buf += chunk.toString()
                const lines = buf.split("\n")
                buf = lines.pop()
                for (const line of lines) {
                    if (!line.trim()) continue
                    try {
                        const msg = JSON.parse(line)
                        if (msg.__vspk_emit) {
                            const handlers = this.#handlers[msg.event] ?? []
                            for (const h of handlers) {
                                try { h(msg.payload) } catch(e) {
                                    console.error(`[vspk] error en handler '${msg.event}':`, e)
                                }
                            }
                        }
                    } catch {}
                }
            })

            sock.on("error",  () => setTimeout(connect, 500))
            sock.on("close",  () => setTimeout(connect, 500))
        }

        connect()
    }

    toString() {
        return `Window(id=${this.#id}, open=${this.isOpen()})`
    }
}

// ── open() ────────────────────────────────────────────────────────────────────

export async function open(file, { title, width, height, vspkExe = "vspk" } = {}) {
    const filePath = path.resolve(file)

    let cmd = [vspkExe, filePath]

    if (title || width || height) {
        const config = { file: filePath }
        if (title)  config.title  = title
        if (width)  config.width  = width
        if (height) config.height = height
        const tmp = path.join(import.meta.dir, ".vspk_config.json")
        await Bun.write(tmp, JSON.stringify(config))
        cmd = [vspkExe, "--config", tmp]
    }

    const proc = spawn({
        cmd,
        stdout:      "ignore",
        stderr:      "ignore",
        windowsHide: true,  // no abrir ventana CMD en Windows
    })

    await waitForSocket()

    // Obtener ID de la ventana recien abierta
    const list = await ipcSend({ cmd: "list" })
    const wins = list?.windows ?? []
    const id   = wins.length ? Math.max(...wins.map(w => w.id)) : 0

    return new Window(id, proc)
}

export async function listWindows() {
    const r = await ipcSend({ cmd: "list" })
    return r?.windows ?? []
}

export async function broadcast(payload) {
    return ipcSend({ cmd: "broadcast", payload })
}

