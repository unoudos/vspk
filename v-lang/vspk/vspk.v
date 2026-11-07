// vspk.v — GUI nativa para V usando vspk (WebView) como ventana.
//
// El programa abre un puente HTTP+SSE en 127.0.0.1 (puerto aleatorio), escribe un .htv temporal y lanza
// vspk(.exe). Mientras la ventana está abierta, run() atiende los clics (/cb/<id>), los eventos
// (/event/<nombre>) y los valores de los campos enlazados, y empuja los cambios de estado por SSE.
// spork.css y spork.js los sirve el propio vspk (van incrustados).
//
// Estructura:   demo.v  +  vspk/vspk.v        (o instálalo en ~/.vmodules/vspk/)
//
//   import vspk
//
//   fn main() {
//       app := vspk.new_app('Contador', width: 400, height: 300)
//       n := app.state('n', 0)
//       app.add(vspk.col(
//           vspk.h1(n.ref()),
//           vspk.row(app.button('-', fn [n] () { n.dec(1) }), app.button('+', fn [n] () { n.inc(1) })),
//       ))
//       app.run() or { eprintln(err) }
//   }
//
// Qué hay:
//   · ids de callback y eventos internos con token (otra web local no puede dispararlos)
//   · app.button(texto, fn () {...}) ejecuta el cierre en V; app.button_js(texto, 'js') es JS puro en la página
//   · todos los callbacks (clics, teclas, temporizadores...) se ejecutan serializados (un solo candado)
//   · app.on_key, app.on_close, app.pick_file/save_file/pick_folder, app.run_every/run_after,
//     app.set_title/notify/copy_text/quit/toast/eval_js
//   · app.canvas(id, w, h)  ·  menubar/menu/menu_item/menu_sep  ·  app.window(título, w, h) (ventanas extra)
//
// Los métodos usan receptores `&T`: no hace falta declarar `mut` en tus variables ni en las capturas
// (fn [n] () { n.inc(1) }).
module vspk

import os
import net
import sync
import time
import crypto.rand as crand

const css_cdn = 'https://cdn.jsdelivr.net/gh/unoudos/spork-ui@main/spork.css'
const js_cdn = 'https://cdn.jsdelivr.net/gh/unoudos/spork-ui@main/spork.js'
const menu_a = '<style>.sz-menubar{position:fixed;top:0;left:0;right:0;z-index:1000;display:flex;gap:2px;padding:3px 6px;background:var(--sz-surface,#fff);color:var(--sz-on-surface,#1d1b20);border-bottom:1px solid rgba(128,128,128,.3);font-size:14px}.sz-menubar-space{height:38px;width:100%;flex:none}.sz-menu{position:relative}.sz-menu-title{background:none;border:0;padding:6px 10px;border-radius:6px;color:inherit;font:inherit;cursor:pointer}.sz-menu-title:hover,.sz-menu.sz-open>.sz-menu-title{background:rgba(128,128,128,.18)}.sz-menu-list{display:none;position:absolute;top:100%;left:0;min-width:210px;padding:4px;background:var(--sz-surface,#fff);color:inherit;border:1px solid rgba(128,128,128,.35);border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.2)}.sz-menu.sz-open>.sz-menu-list{display:block}.sz-menu-item{display:flex;justify-content:space-between;gap:24px;width:100%;background:none;border:0;padding:6px 10px;border-radius:6px;color:inherit;font:inherit;cursor:pointer;text-align:left}.sz-menu-item:hover{background:rgba(128,128,128,.18)}.sz-menu-item kbd{opacity:.6;font:inherit;font-size:12px}.sz-menu-sep{height:1px;margin:4px 6px;background:rgba(128,128,128,.3)}.sz-native .sz-menubar,.sz-native .sz-menubar-space{display:none!important}</style><div class="sz-menubar">'
const menu_b = '</div><div class="sz-menubar-space"></div><script>(function(){if(window.__menu)return;window.__menu=1;var bar=document.querySelector(\'.sz-menubar\');function menus(){return bar.querySelectorAll(\':scope > .sz-menu\')}window.__vspk_menu_click=function(id){var p=id.split(\'.\');var m=menus()[+p[0]];if(m)m.querySelector(\'.sz-menu-list\').children[+p[1]].click()};window.__vspk_menu_ok=function(){document.documentElement.classList.add(\'sz-native\')};if(bar&&window.ipc&&window.__vspk_native_menu_ok){var ms=[];Array.prototype.forEach.call(menus(),function(m,mi){var items=[];Array.prototype.forEach.call(m.querySelector(\'.sz-menu-list\').children,function(c,ii){if(c.classList.contains(\'sz-menu-sep\'))items.push({sep:true});else items.push({id:mi+\'.\'+ii,label:(c.querySelector(\'span\')||c).textContent,accel:c.getAttribute(\'data-accel\')||\'\'})});ms.push({label:m.querySelector(\'.sz-menu-title\').textContent,items:items})});window.ipc.postMessage(JSON.stringify({cmd:\'setMenu\',menu:ms}))}function closeAll(except){document.querySelectorAll(\'.sz-menu.sz-open\').forEach(function(m){if(m!==except)m.classList.remove(\'sz-open\')})}document.addEventListener(\'click\',function(e){var t=e.target.closest?e.target.closest(\'.sz-menu-title\'):null;closeAll(t?t.parentNode:null);if(t)t.parentNode.classList.toggle(\'sz-open\');var it=e.target.closest?e.target.closest(\'.sz-menu-item\'):null;if(it)closeAll(null)});document.addEventListener(\'mouseover\',function(e){var t=e.target.closest?e.target.closest(\'.sz-menu-title\'):null;var o=document.querySelector(\'.sz-menu.sz-open\');if(t&&o&&o!==t.parentNode){closeAll(t.parentNode);t.parentNode.classList.add(\'sz-open\')}});document.addEventListener(\'keydown\',function(e){if(e.key===\'Escape\'){closeAll(null);return}if(document.documentElement.classList.contains(\'sz-native\')&&!/Win/.test(navigator.platform))return;var k=(e.ctrlKey?\'ctrl+\':\'\')+(e.shiftKey?\'shift+\':\'\')+(e.altKey?\'alt+\':\'\')+e.key.toLowerCase();var items=document.querySelectorAll(\'.sz-menu-item[data-accel]\');for(var i=0;i<items.length;i++){var a=items[i].getAttribute(\'data-accel\');if(a&&a.toLowerCase()===k){e.preventDefault();items[i].click();return}}})})();</script>'
const page_js = [
	'window.__state = %STATE%;',
	'window.__win = %WIN%;',
	'window.__set = function(name, value) {',
	'  window.__state[name] = value;',
	'  document.querySelectorAll(\'[data-spork-text="\' + name + \'"]\').forEach(function(el) { el.textContent = value; });',
	'  document.querySelectorAll(\'[data-spork-bind="\' + name + \'"]\').forEach(function(el) {',
	"    if (el.type === 'checkbox') el.checked = !!value;",
	'    else if (el.value != value) el.value = value;',
	'  });',
	"  var ev = function(code) { return new Function('return (' + code + ')')(); };",
	"  document.querySelectorAll('[data-spork-style]').forEach(function(el) { try { Object.assign(el.style, ev(el.dataset.sporkStyle)); } catch(_) {} });",
	"  document.querySelectorAll('[data-spork-if]').forEach(function(el) { try { el.style.display = ev(el.dataset.sporkIf) ? '' : 'none'; } catch(_) {} });",
	"  document.querySelectorAll('[data-spork-class]').forEach(function(el) { try { var c = ev(el.dataset.sporkClass); if (typeof c === 'string') el.className = (el.dataset.sporkBase || (el.dataset.sporkBase = el.className)) + ' ' + c; } catch(_) {} });",
	'};',
	'// Valor que el usuario escribe/elige → a PHP (State::get() lo ve) y a los demás widgets enlazados.',
	'window.__sync = function(n, v) {',
	"  try { fetch('http://127.0.0.1:%PORT%/event/%VEV%', {method: 'POST', mode: 'no-cors', headers: {'Content-Type': 'text/plain'}, body: JSON.stringify({n: n, v: v, w: window.__win})}); } catch(_) {}",
	'};',
	'(function() {',
	'  function onUser(e) {',
	"    var el = e.target && e.target.closest ? e.target.closest('[data-spork-bind]') : null;",
	'    if (!el) return;',
	"    var v = el.type === 'checkbox' ? el.checked : (el.type === 'range' || el.type === 'number') ? Number(el.value) : el.value;",
	"    var n = el.getAttribute('data-spork-bind');",
	'    window.__set(n, v);',
	'    window.__sync(n, v);',
	'  }',
	"  document.addEventListener('input', onUser);",
	"  document.addEventListener('change', onUser);",
	'})();',
	"document.addEventListener('click', function(e) {      // Tabs",
	"  var b = e.target.closest ? e.target.closest('[data-ttarget]') : null;",
	'  if (!b) return;',
	'  var g = b.dataset.ttarget, i = +b.dataset.tidx;',
	"  document.querySelectorAll('[data-tpanel]').forEach(function(p) { if (p.dataset.tpanel === g) p.classList.toggle('sz-active', +p.dataset.tidx === i); });",
	"  document.querySelectorAll('[data-ttarget]').forEach(function(x) { if (x.dataset.ttarget === g) x.classList.toggle('sz-active', +x.dataset.tidx === i); });",
	'});',
	'window.__toast = function(msg, v, ms) {',
	"  var c = document.getElementById('__vspk_toasts');",
	"  if (!c) { c = document.createElement('div'); c.className = 'sz-toast-container'; c.id = '__vspk_toasts'; document.body.appendChild(c); }",
	"  var t = document.createElement('div'); t.className = 'sz-toast' + (v ? ' sz-toast-' + v : ''); t.textContent = msg; c.appendChild(t);",
	"  setTimeout(function() { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; setTimeout(function() { t.remove(); }, 300); }, ms || 3000);",
	'};',
	'window.__vspk_cmd = function(cmd, a, b) {',
	'  try {',
	"    if (cmd === 'close' || cmd === 'fullscreen') window.ipc && window.ipc.postMessage(JSON.stringify({cmd: cmd === 'close' ? 'close' : 'toggleFullscreen'}));",
	"    else if (cmd === 'setTitle' && window.__vspk_api) window.__vspk_api.setTitle(a);",
	"    else if (cmd === 'setTitle' && typeof __vspk !== 'undefined') __vspk.setTitle(a);",
	"    else if (cmd === 'notify' && typeof __vspk !== 'undefined') __vspk.notify(a, b);",
	'  } catch(err) { console.error(err); }',
	'};',
	'window.__cv = function(id, op, a) {',
	'  var c = document.getElementById(id); if (!c) return;',
	"  var x = c.getContext('2d');",
	"  if (op === 'clear') { x.clearRect(0, 0, c.width, c.height); }",
	"  else if (op === 'color') { x.fillStyle = a[0]; x.strokeStyle = a[0]; }",
	"  else if (op === 'lw') { x.lineWidth = a[0]; }",
	"  else if (op === 'font') { x.font = a[0] + 'px sans-serif'; }",
	"  else if (op === 'line') { x.beginPath(); x.moveTo(a[0], a[1]); x.lineTo(a[2], a[3]); x.stroke(); }",
	"  else if (op === 'rect') { x.fillRect(a[0], a[1], a[2], a[3]); }",
	"  else if (op === 'frame') { x.strokeRect(a[0], a[1], a[2], a[3]); }",
	"  else if (op === 'circle') { x.beginPath(); x.arc(a[0], a[1], a[2], 0, 6.283185307); x.fill(); }",
	"  else if (op === 'ring') { x.beginPath(); x.arc(a[0], a[1], a[2], 0, 6.283185307); x.stroke(); }",
	"  else if (op === 'text') { x.fillText(a[2], a[0], a[1]); }",
	"  else if (op === 'poly') { var p = a[0]; x.beginPath(); x.moveTo(p[0][0], p[0][1]); for (var i = 1; i < p.length; i++) x.lineTo(p[i][0], p[i][1]); x.closePath(); x.fill(); }",
	"  else if (op === 'draw') { new Function('ctx', 'canvas', a[0])(x, c); }",
	'};',
	'Object.keys(window.__state).forEach(function(k) { window.__set(k, window.__state[k]); });',
	'(function connectSSE() {',
	"  var es = new EventSource('http://127.0.0.1:%PORT%/events');",
	"  es.addEventListener('state', function(e) { var d = JSON.parse(e.data); if (d.src && d.src === window.__win) return; window.__set(d.name, d.value); });",
	"  [%EVALEV%, 'all'].forEach(function(n) { es.addEventListener(n, function(e) { try { (0, eval)(JSON.parse(e.data)); } catch(err) { console.error(err); } }); });",
	'  es.onerror = function() { es.close(); setTimeout(connectSSE, 1000); };',
	'})();',
].join('\n')

// ── JSON mínimo (objetos planos que genera la propia página) ─────────────────

// Literal de cadena JSON/JS, seguro dentro de <script> y de atributos HTML.
pub fn js_str(s string) string {
	mut b := []u8{cap: s.len + 2}
	b << `"`
	for c in s.bytes() {
		match c {
			`"` {
				b << '\\"'.bytes()
			}
			`\\` {
				b << '\\\\'.bytes()
			}
			`\n` {
				b << '\\n'.bytes()
			}
			`\r` {
				b << '\\r'.bytes()
			}
			`\t` {
				b << '\\t'.bytes()
			}
			`<` {
				b << '\\u003c'.bytes()
			}
			`>` {
				b << '\\u003e'.bytes()
			}
			`&` {
				b << '\\u0026'.bytes()
			}
			else {
				if c < 0x20 {
					b << '\\u00${c:02x}'.bytes()
				} else {
					b << c
				}
			}
		}
	}
	b << `"`
	return b.bytestr()
}

fn jskip(s string, i int) int {
	mut j := i
	for j < s.len && (s[j] == ` ` || s[j] == `\t` || s[j] == `\n` || s[j] == `\r`) {
		j++
	}
	return j
}

// i apunta a la comilla de apertura; devuelve la posición tras la de cierre
fn jend_str(s string, i int) int {
	mut j := i + 1
	for j < s.len && s[j] != `"` {
		if s[j] == `\\` && j + 1 < s.len {
			j++
		}
		j++
	}
	return if j < s.len { j + 1 } else { j }
}

fn jvalue_end(s string, i int) int {
	mut j := jskip(s, i)
	if j >= s.len {
		return j
	}
	if s[j] == `"` {
		return jend_str(s, j)
	}
	if s[j] == `{` || s[j] == `[` {
		mut d := 0
		for j < s.len {
			if s[j] == `"` {
				j = jend_str(s, j)
				continue
			}
			if s[j] == `{` || s[j] == `[` {
				d++
			}
			if s[j] == `}` || s[j] == `]` {
				d--
				if d == 0 {
					return j + 1
				}
			}
			j++
		}
		return j
	}
	for j < s.len && s[j] != `,` && s[j] != `}` && s[j] != `]` && s[j] != ` ` && s[j] != `\n` {
		j++
	}
	return j
}

// Posición del valor de `key` en el objeto (nivel 1) o -1.
fn jfind(s string, key string) int {
	mut i := jskip(s, 0)
	if i >= s.len || s[i] != `{` {
		return -1
	}
	i++
	for {
		i = jskip(s, i)
		for i < s.len && s[i] == `,` {
			i = jskip(s, i + 1)
		}
		if i >= s.len || s[i] != `"` {
			return -1
		}
		ke := jend_str(s, i)
		k := s[i + 1..ke - 1]
		i = jskip(s, ke)
		if i >= s.len || s[i] != `:` {
			return -1
		}
		i = jskip(s, i + 1)
		if k == key {
			return i
		}
		i = jvalue_end(s, i)
		if i >= s.len {
			return -1
		}
	}
	return -1
}

fn hexval(c u8) int {
	return if c >= `0` && c <= `9` {
		int(c - `0`)
	} else {
		int((c | 0x20) - `a`) + 10
	}
}

fn is_hex(c u8) bool {
	return (c >= `0` && c <= `9`) || ((c | 0x20) >= `a` && (c | 0x20) <= `f`)
}

// Cadena JSON en s[i] → desescapada.
fn junq(s string, i int) string {
	mut b := []u8{}
	mut j := i + 1
	for j < s.len && s[j] != `"` {
		if s[j] != `\\` {
			b << s[j]
			j++
			continue
		}
		j++
		if j >= s.len {
			break
		}
		match s[j] {
			`n` {
				b << `\n`
			}
			`r` {
				b << `\r`
			}
			`t` {
				b << `\t`
			}
			`b` {
				b << 8
			}
			`f` {
				b << 12
			}
			`u` {
				mut cp := 0
				mut k := 1
				for k <= 4 && j + k < s.len && is_hex(s[j + k]) {
					cp = cp * 16 + hexval(s[j + k])
					k++
				}
				j += 4
				if cp >= 0xD800 && cp < 0xDC00 && j + 6 < s.len && s[j + 1] == `\\`
					&& s[j + 2] == `u` {
					mut lo := 0
					for q in 3 .. 7 {
						lo = lo * 16 + hexval(s[j + q])
					}
					cp = 0x10000 + int(u32(cp - 0xD800) << 10) + (lo - 0xDC00)
					j += 6
				}
				b << rune(cp).str().bytes()
			}
			else {
				b << s[j]
			}
		}

		j++
	}
	return b.bytestr()
}

// Campo de texto de un objeto JSON; ok=false si no existe o no es una cadena.
fn jstr(json string, key string) (string, bool) {
	i := jfind(json, key)
	if i < 0 || json[i] != `"` {
		return '', false
	}
	return junq(json, i), true
}

fn jnum(json string, key string) f64 {
	i := jfind(json, key)
	if i < 0 || json[i] == `"` {
		return 0
	}
	return json[i..jvalue_end(json, i)].f64()
}

fn jbool(json string, key string) bool {
	i := jfind(json, key)
	return i >= 0 && json[i..].starts_with('true')
}

// ── HTML ─────────────────────────────────────────────────────────────────────

pub fn html_escape(s string) string {
	return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'",
		'&#39;')
}

fn group(tag string, cls string, kids []string) string {
	return '<${tag} class="${cls}">\n${kids.join('\n')}\n</${tag}>'
}

fn text_tag(tag string, cls string, html string) string {
	return '<${tag} class="${cls}">\n${html}\n</${tag}>'
}

pub fn row(kids ...string) string {
	return group('div', 'sz-row', kids)
}

pub fn col(kids ...string) string {
	return group('div', 'sz-col sz-center', kids)
}

pub fn card(kids ...string) string {
	return group('div', 'sz-card', kids)
}

pub fn grid(kids ...string) string {
	return group('div', 'sz-grid', kids)
}

pub fn nav(kids ...string) string {
	return group('nav', 'sz-nav', kids)
}

pub fn hr() string {
	return '<hr class="sz-divider">'
}

pub fn spacer() string {
	return '<div class="sz-grow"></div>'
}

// El texto es HTML: usa state.ref() para un valor reactivo, o text(s) para un literal escapado.
pub fn h1(c string) string {
	return text_tag('h1', 'sz-h1', c)
}

pub fn h2(c string) string {
	return text_tag('h2', 'sz-h2', c)
}

pub fn h3(c string) string {
	return text_tag('h3', 'sz-h3', c)
}

pub fn h4(c string) string {
	return text_tag('h4', 'sz-h4', c)
}

pub fn p(c string) string {
	return text_tag('p', 'sz-p', c)
}

pub fn label(c string) string {
	return text_tag('label', 'sz-label', c)
}

pub fn badge(c string) string {
	return text_tag('span', 'sz-badge', c)
}

pub fn chip(c string, primary bool) string {
	return text_tag('span', if primary { 'sz-chip sz-chip-primary' } else { 'sz-chip' }, c)
}

pub fn alert(c string, variant string) string {
	return text_tag('div', if variant != '' { 'sz-alert sz-alert-${variant}' } else { 'sz-alert' },
		c)
}

// Texto literal (se escapa) para meterlo dentro de h1..p
pub fn text(s string) string {
	return html_escape(s)
}

// HTML propio tal cual
pub fn raw(html string) string {
	return html
}

pub fn img(src string, alt string) string {
	return '<img class="sz-img" src="${html_escape(src)}" alt="${html_escape(alt)}">'
}

fn button_html(text string, variant string, size string, full bool, disabled bool, onclick string) string {
	mut cls := 'sz-btn sz-btn-${if variant == '' { 'filled' } else { variant }}'
	if size != '' {
		cls += ' sz-btn-${size}'
	}
	if full {
		cls += ' sz-btn-full'
	}
	oc := if !disabled && onclick != '' { ' onclick="${html_escape(onclick)}"' } else { '' }
	dis := if disabled { ' disabled="disabled"' } else { '' }
	return '<button class="${cls}"${oc}${dis} data-ripple="">${text}</button>'
}

@[params]
pub struct BtnOpts {
pub:
	variant  string = 'filled' // filled, outlined, text...
	size     string
	full     bool
	disabled bool
}

// Botón con JS puro en la página (instantáneo, sin pasar por V).
pub fn button_js(text string, js string, o BtnOpts) string {
	return button_html(text, o.variant, o.size, o.full, o.disabled, js)
}

// ── Estado ───────────────────────────────────────────────────────────────────

pub type Val = bool | f64 | int | string

fn val_json(v Val) string {
	return match v {
		string { js_str(v) }
		int { v.str() }
		bool { v.str() }
		f64 { num_str(v) }
	}
}

fn num_str(f f64) string {
	if f == f64(i64(f)) {
		return i64(f).str()
	}
	return f.str()
}

fn val_text(v Val) string {
	return match v {
		string { v }
		int { v.str() }
		bool { v.str() }
		f64 { num_str(v) }
	}
}

@[heap]
pub struct State {
pub:
	name string
mut:
	app    &App = unsafe { nil }
	val    Val
	change fn (string) = fn (_ string) {}
}

pub fn (s &State) get() Val {
	return s.val
}

pub fn (s &State) text() string {
	return val_text(s.val)
}

pub fn (s &State) as_f64() f64 {
	return match s.val {
		string {
			s.val.f64()
		}
		int {
			f64(s.val)
		}
		bool {
			if s.val {
				1.0
			} else {
				0.0
			}
		}
		f64 {
			s.val
		}
	}
}

pub fn (s &State) as_int() int {
	return int(s.as_f64())
}

pub fn (s &State) as_bool() bool {
	return match s.val {
		string { s.val == 'true' || s.val == '1' }
		int { s.val != 0 }
		bool { s.val }
		f64 { s.val != 0 }
	}
}

pub fn (s &State) set(v Val) {
	mut me := unsafe { s }
	me.val = v
	me.push(unsafe { nil })
}

pub fn (s &State) inc(by f64) {
	if s.val is int && by == f64(int(by)) {
		s.set(Val(s.as_int() + int(by)))
	} else {
		s.set(Val(s.as_f64() + by))
	}
}

pub fn (s &State) dec(by f64) {
	s.inc(-by)
}

// fn(valor) cada vez que el usuario cambia el campo enlazado a este estado
pub fn (s &State) on_change(f fn (string)) {
	mut me := unsafe { s }
	me.change = f
}

// Span reactivo: úsalo como contenido de h1..p
pub fn (s &State) ref() string {
	return '<span data-spork-text="${html_escape(s.name)}">${html_escape(s.text())}</span>'
}

fn (s &State) push(src &string) {
	if !s.app.running {
		return
	}
	mut d := '{"name":${js_str(s.name)},"value":${val_json(s.val)}'
	if !isnil(src) {
		d += ',"src":${js_str(*src)}'
	}
	d += '}'
	s.app.sse('state', d)
}

// ── Widgets con estado ───────────────────────────────────────────────────────

fn bind_attr(b &State) string {
	return if isnil(b) { '' } else { ' data-spork-bind="${html_escape(b.name)}"' }
}

pub fn input(bind &State, placeholder string) string {
	ph := if placeholder != '' { ' placeholder="${html_escape(placeholder)}"' } else { '' }
	v := if !isnil(bind) && bind.text() != '' { ' value="${html_escape(bind.text())}"' } else { '' }
	return '<input class="sz-input"${ph}${v}${bind_attr(bind)}>'
}

pub fn textarea(bind &State, placeholder string, rows int) string {
	ph := if placeholder != '' { ' placeholder="${html_escape(placeholder)}"' } else { '' }
	v := if !isnil(bind) { html_escape(bind.text()) } else { '' }
	return '<textarea class="sz-textarea"${ph} rows="${if rows > 0 {
		rows
	} else {
		4
	}}"${bind_attr(bind)}>${v}</textarea>'
}

pub fn slider(bind &State, min f64, max f64, step f64) string {
	v := if !isnil(bind) { html_escape(bind.text()) } else { num_str(min) }
	return '<input class="sz-slider" type="range" min="${num_str(min)}" max="${num_str(max)}" step="${num_str(step)}" value="${v}"${bind_attr(bind)}>'
}

// options: [valor, etiqueta] ...
pub fn select_input(bind &State, options [][2]string) string {
	cur := if !isnil(bind) { bind.text() } else { '' }
	mut opts := ''
	for o in options {
		sel := if o[0] == cur { ' selected' } else { '' }
		opts += '<option value="${html_escape(o[0])}"${sel}>${html_escape(o[1])}</option>'
	}
	return '<select class="sz-select"${bind_attr(bind)}>${opts}</select>'
}

// Interruptor (sz-switch) enlazado a un estado booleano
pub fn checkbox(label_text string, bind &State) string {
	on := if !isnil(bind) && bind.as_bool() { ' checked' } else { '' }
	return '<label class="sz-switch"><input type="checkbox"${on}${bind_attr(bind)}><span class="sz-switch-track"><span class="sz-switch-thumb"></span></span><span class="sz-switch-label">${html_escape(label_text)}</span></label>'
}

// Barra de progreso que se mueve sola cuando cambia el estado (valor / max).
pub fn progress(st &State, max_ f64) string {
	m := if max_ > 0 { max_ } else { 100.0 }
	mut pct := st.as_f64() / m * 100
	if pct < 0 {
		pct = 0
	}
	if pct > 100 {
		pct = 100
	}
	sty := '{"width":(Math.min(100,Math.max(0,(+window.__state[${js_str(st.name)}]||0)/${num_str(m)}*100)).toFixed(1)+"%")}'
	return '<div class="sz-progress"><div class="sz-progress-bar" style="width:${pct:.1f}%" data-spork-style="${html_escape(sty)}"></div></div>'
}

// ── Menús (barra de menú HTML con atajos de teclado) ─────────────────────────
//   app.add(vspk.menubar(
//       vspk.menu('Archivo', vspk.menu_item('Abrir...', app.on_click(abrir), 'ctrl+o'), vspk.menu_sep(),
//                            vspk.menu_item('Salir', app.on_click(salir), '')),
//       vspk.menu('Ayuda', vspk.menu_item('Acerca de', app.on_click(acerca), ''))), resto...)
//   Atajos: 'ctrl+o', 'ctrl+shift+s', 'alt+x', 'f5'... (orden: ctrl, shift, alt, tecla).

pub fn menu_item(label_text string, onclick_js string, shortcut string) string {
	kbd := if shortcut != '' { '<kbd>${html_escape(shortcut)}</kbd>' } else { '' }
	return '<button type="button" class="sz-menu-item" onclick="${html_escape(onclick_js)}" data-accel="${html_escape(shortcut)}"><span>${html_escape(label_text)}</span>${kbd}</button>'
}

pub fn menu_sep() string {
	return '<div class="sz-menu-sep"></div>'
}

pub fn menu(title string, items ...string) string {
	return '<div class="sz-menu"><button type="button" class="sz-menu-title">${html_escape(title)}</button><div class="sz-menu-list">${items.join('')}</div></div>'
}

pub fn menubar(menus ...string) string {
	return menu_a + menus.join('') + menu_b
}

// ── Tipos de eventos ─────────────────────────────────────────────────────────

pub struct KeyEvent {
pub:
	key   string
	code  string
	ctrl  bool
	shift bool
	alt   bool
	meta  bool
}

pub struct MouseEvent {
pub:
	typ    string // down, up, move, click
	x      int
	y      int
	button int
}

// ── App ──────────────────────────────────────────────────────────────────────

@[heap]
struct Client {
mut:
	conn  &net.TcpConn = unsafe { nil }
	alive bool
}

@[heap]
struct Timer {
mut:
	ms        int
	once      bool
	cancelled bool
	next      i64
	f         fn () bool = fn () bool {
		return false
	}
}

@[params]
pub struct AppConfig {
pub:
	width    int    = 1024
	height   int    = 768
	theme    string = 'light'
	primary  string = '#6750A4'
	bg       string
	surface  string
	font     string
	devtools bool
	exe      string
}

@[heap]
pub struct App {
mut:
	title    string
	cfg      AppConfig
	token    string
	port     int
	listener &net.TcpListener = unsafe { nil }
	root     []string
	states   []&State
	cbs      map[string]fn ()
	evs      map[string]fn (string)
	timers   []&Timer
	clients  []&Client
	cvs      []&Canvas
	cvmouse  string
	wins     []&Window
	counter  int
	htvn     int
	key_on   bool
	close_on bool
	running  bool
	quitting bool
	stopping bool
	nthr     int
	proc     &os.Process = unsafe { nil }
	umu      &sync.Mutex = sync.new_mutex()
	smu      &sync.Mutex = sync.new_mutex()
	tmu      &sync.Mutex = sync.new_mutex()
}

pub fn new_app(title string, cfg AppConfig) &App {
	mut a := &App{
		title: title
		cfg:   cfg
		token: crand.read(8) or { time.now().unix_micro().str().bytes() }.hex()
	}
	mut l := net.listen_tcp(.ip, '127.0.0.1:0') or {
		eprintln('[vspk] no se pudo abrir el puerto local: ${err}')
		exit(1)
	}
	a.port = (l.addr() or { panic(err) }).port() or { panic(err) }
	a.listener = l
	a.thr_inc()
	spawn a.accept_loop() // el puerto se conoce ya, antes de construir los widgets
	return a
}

// Añade widgets a la página (en orden).
pub fn (a &App) add(ws ...string) {
	mut me := unsafe { a }
	me.root << ws
}

pub fn (a &App) state(name string, initial Val) &State {
	for s in a.states {
		if s.name == name {
			return s
		}
	}
	mut me := unsafe { a }
	st := &State{
		name: name
		app:  a
		val:  initial
	}
	me.states << st
	return st
}

fn (a &App) ev(name string) string {
	return '__${name}_${a.token}'
}

fn (a &App) next_id() int {
	mut me := unsafe { a }
	me.counter++
	return me.counter
}

fn (a &App) post_js(name string, body_expr string) string {
	return "fetch('http://127.0.0.1:${a.port}/event/${name}',{method:'POST',mode:'no-cors',headers:{'Content-Type':'text/plain'},body:${body_expr}})"
}

fn (a &App) add_ev(name string, f fn (string)) {
	mut me := unsafe { a }
	me.evs[name] = f
}

// Registra f (se ejecuta en V) y devuelve el JS para dispararla desde un onclick.
pub fn (a &App) on_click(f fn ()) string {
	mut me := unsafe { a }
	id := 'cb_${a.token}_${a.next_id()}'
	me.cbs[id] = f
	return "fetch('http://127.0.0.1:${a.port}/cb/${id}',{mode:'no-cors'})"
}

// Botón cuyo clic ejecuta f en V.
pub fn (a &App) button(text string, f fn (), o BtnOpts) string {
	return button_html(text, o.variant, o.size, o.full, o.disabled, a.on_click(f))
}

// Handler para eventos enviados desde la página:
// fetch('http://127.0.0.1:PUERTO/event/nombre', {method:'POST', body: JSON.stringify(dato)})
pub fn (a &App) on_event(name string, f fn (string)) {
	a.add_ev(name, f)
}

// ── SSE ──────────────────────────────────────────────────────────────────────

fn (a &App) sse(event string, data string) {
	msg := 'event: ${event}\ndata: ${data}\n\n'
	mut me := unsafe { a }
	a.smu.lock()
	for mut c in me.clients {
		if c.alive {
			c.conn.write_string(msg) or { c.alive = false }
		}
	}
	a.smu.unlock()
}

// Ejecuta JS en la ventana principal.
pub fn (a &App) eval_js(code string) {
	a.sse('eval', js_str(code))
}

// ── Utilidades de ventana ────────────────────────────────────────────────────

pub fn (a &App) toast(msg string, variant string) {
	a.eval_js('window.__toast(${js_str(msg)},${js_str(variant)},3000)')
}

pub fn (a &App) set_title(t string) {
	a.eval_js('__vspk.setTitle(${js_str(t)})')
}

pub fn (a &App) notify(title string, body string) {
	a.eval_js('__vspk.notify(${js_str(title)},${js_str(body)})')
}

pub fn (a &App) copy_text(text string) {
	a.eval_js('__vspk.clipboard.write(${js_str(text)})')
}

pub fn (a &App) quit() {
	mut me := unsafe { a }
	me.quitting = true
	if !isnil(me.proc) {
		me.proc.signal_kill()
	}
}

fn close_result(ok bool) string {
	return if ok { '__vspk.confirmClose()' } else { '__vspk.cancelClose()' }
}

// f recibe la tecla pulsada. Llamar antes de run().
pub fn (a &App) on_key(f fn (KeyEvent)) {
	mut me := unsafe { a }
	me.key_on = true
	a.add_ev(a.ev('k'), fn [f] (body string) {
		k, _ := jstr(body, 'key')
		c, _ := jstr(body, 'code')
		f(KeyEvent{
			key:   k
			code:  c
			ctrl:  jbool(body, 'ctrl')
			shift: jbool(body, 'shift')
			alt:   jbool(body, 'alt')
			meta:  jbool(body, 'meta')
		})
	})
}

// f devuelve false para cancelar el cierre de la ventana. Llamar antes de run().
pub fn (a &App) on_close(f fn () bool) {
	mut me := unsafe { a }
	me.close_on = true
	a.add_ev(a.ev('c'), fn [a, f] (_ string) {
		a.eval_js(close_result(f()))
	})
}

fn (a &App) dialog(kind string, title string, f fn (string)) {
	name := a.ev('d${a.next_id()}')
	a.add_ev(name, fn [f] (body string) {
		path, _ := jstr(body, 'path')
		f(path) // '' si se cancela
	})
	a.eval_js('__vspk.dialog({kind:${js_str(kind)},title:${js_str(title)}}).then(function(p){${a.post_js(name,
		'JSON.stringify({path:p})')}})')
}

pub fn (a &App) pick_file(title string, f fn (string)) {
	a.dialog('open', title, f)
}

pub fn (a &App) save_file(title string, f fn (string)) {
	a.dialog('save', title, f)
}

pub fn (a &App) pick_folder(title string, f fn (string)) {
	a.dialog('folder', title, f)
}

// ── Diálogos modales (mensaje / confirmación / pedir texto) ──────────────────

fn (a &App) modal(call string, f fn (string)) {
	name := a.ev('m${a.next_id()}')
	a.add_ev(name, f)
	a.eval_js('Promise.resolve(${call}).then(function(v){${a.post_js(name, 'JSON.stringify({v:v})')}})')
}

// Diálogo modal con un botón Aceptar. f se llama al cerrarlo.
pub fn (a &App) message(text string, f fn ()) {
	a.modal('alert(${js_str(text)})', fn [f] (_ string) {
		f()
	})
}

// Modal Aceptar/Cancelar. f(true|false).
pub fn (a &App) confirm(text string, f fn (bool)) {
	a.modal('confirm(${js_str(text)})', fn [f] (body string) {
		f(jbool(body, 'v'))
	})
}

// Modal que pide un texto. f(texto, true), o f('', false) si se cancela.
pub fn (a &App) prompt(text string, default_value string, f fn (string, bool)) {
	a.modal('prompt(${js_str(text)},${js_str(default_value)})', fn [f] (body string) {
		v, ok := jstr(body, 'v')
		f(v, ok)
	})
}

// ── Tabla, árbol, lista (se hidratan en la página; ver vspk_ui.js incrustado en vspk.exe) ──
//
//   app.add(app.table(['Nombre', 'Edad'], [['Ana', '31'], ['Luis', '28']], id: 'tabla', on_select: fn (e vspk.TableEvent) { println(e.row) }))
//   app.table_set('tabla', filas)       // cambiar datos (id obligatorio)
//   Clic en la cabecera ordena (numérico si las celdas son números). multi: true permite Ctrl/Shift.

pub struct TableEvent {
pub:
	index   int      // posición original de la fila elegida
	row     []string // celdas de esa fila
	indexes []int    // todas las seleccionadas (multi)
}

pub struct SortEvent {
pub:
	col int // -1 si se quitó el orden
	dir int // 1 asc, -1 desc, 0 sin orden
}

pub struct TreeEvent {
pub:
	path  []int
	label string
	id    string
}

@[params]
pub struct TableOpts {
pub:
	id          string
	sortable    bool = true
	multi       bool
	striped     bool = true
	header      bool = true
	height      string
	on_select   fn (TableEvent) = unsafe { nil }
	on_dblclick fn (TableEvent) = unsafe { nil }
	on_sort     fn (SortEvent)  = unsafe { nil }
}

@[params]
pub struct TreeOpts {
pub:
	id          string
	height      string
	on_select   fn (TreeEvent) = unsafe { nil }
	on_dblclick fn (TreeEvent) = unsafe { nil }
}

// Elementos (como texto) de un array JSON de nivel 1: [1,"a"] → ['1','a'].
fn jarray_items(json string, key string) []string {
	mut out := []string{}
	i := jfind(json, key)
	if i < 0 || json[i] != `[` {
		return out
	}
	mut j := jskip(json, i + 1)
	for j < json.len && json[j] != `]` {
		e := jvalue_end(json, j)
		if json[j] == `"` {
			out << junq(json, j)
		} else {
			out << json[j..e]
		}
		j = jskip(json, e)
		if j < json.len && json[j] == `,` {
			j = jskip(json, j + 1)
		}
	}
	return out
}

fn table_event(body string) TableEvent {
	return TableEvent{
		index:   int(jnum(body, 'index'))
		row:     jarray_items(body, 'row')
		indexes: jarray_items(body, 'indexes').map(it.int())
	}
}

fn tree_event(body string) TreeEvent {
	id_i := jfind(body, 'id')
	mut id := ''
	if id_i >= 0 && body[id_i] != `n` {
		id = if body[id_i] == `"` { junq(body, id_i) } else { body[id_i..jvalue_end(body, id_i)] }
	}
	lb, _ := jstr(body, 'label')
	return TreeEvent{
		path:  jarray_items(body, 'path').map(it.int())
		label: lb
		id:    id
	}
}

fn (a &App) vt_attr(attr string, f fn (string)) string {
	name := a.ev('v${a.next_id()}')
	a.add_ev(name, f)
	return ' ${attr}="${html_escape(a.post_js(name, 'JSON.stringify(p)'))}"'
}

fn (a &App) vt_html(cls string, prefix string, id string, cfg string, extra string, style string) string {
	el_id := if id != '' { id } else { '${prefix}${a.next_id()}' }
	st := if style != '' { ' style="${html_escape(style)}"' } else { '' }
	return '<div id="${html_escape(el_id)}" class="${cls}" data-vt="${html_escape(cfg)}"${st}${extra}></div>'
}

fn json_str_array(items []string) string {
	return '[' + items.map(js_str(it)).join(',') + ']'
}

fn (a &App) table_cfg(cols []string, rows [][]string, o TableOpts, show_header bool) string {
	rs := rows.map(json_str_array(it)).join(',')
	mut cfg := '{"cols":${json_str_array(cols)},"rows":[${rs}],"sortable":${o.sortable},"multi":${o.multi},"striped":${o.striped},"header":${show_header},"selected":-1'
	if o.height != '' {
		cfg += ',"height":${js_str(o.height)}'
	}
	return cfg + '}'
}

fn (a &App) table_events(o TableOpts) string {
	mut ex := ''
	if o.on_select != unsafe { nil } {
		f := o.on_select
		ex += a.vt_attr('data-on-select', fn [f] (b string) {
			f(table_event(b))
		})
	}
	if o.on_dblclick != unsafe { nil } {
		f := o.on_dblclick
		ex += a.vt_attr('data-on-dblclick', fn [f] (b string) {
			f(table_event(b))
		})
	}
	if o.on_sort != unsafe { nil } {
		f := o.on_sort
		ex += a.vt_attr('data-on-sort', fn [f] (b string) {
			f(SortEvent{
				col: int(jnum(b, 'col'))
				dir: int(jnum(b, 'dir'))
			})
		})
	}
	return ex
}

// Tabla con orden por columna y selección. Las celdas son texto.
pub fn (a &App) table(cols []string, rows [][]string, o TableOpts) string {
	return a.vt_html('vspk-table', 'vt', o.id, a.table_cfg(cols, rows, o, o.header),
		a.table_events(o), '')
}

// Lista de una columna sin cabecera. on_select: e.row[0] es el elemento.
pub fn (a &App) listbox(items []string, o TableOpts) string {
	rows := items.map([it])
	mut oo := TableOpts{
		...o
		sortable: false
		striped:  false
	}
	return a.vt_html('vspk-table', 'vt', o.id, a.table_cfg([''], rows, oo, false),
		a.table_events(oo), '')
}

// Nodo de árbol (para tree()).
pub struct TreeNode {
pub:
	label    string
	id       string
	open     bool
	children []TreeNode
}

fn tree_json(nodes []TreeNode) string {
	return '[' + nodes.map(fn (n TreeNode) string {
		mut s := '{"label":${js_str(n.label)}'
		if n.id != '' {
			s += ',"id":${js_str(n.id)}'
		}
		if n.open {
			s += ',"open":true'
		}
		if n.children.len > 0 {
			s += ',"children":${tree_json(n.children)}'
		}
		return s + '}'
	}).join(',') + ']'
}

// Árbol. on_select: e.path (índices), e.label, e.id.
pub fn (a &App) tree(nodes []TreeNode, o TreeOpts) string {
	mut ex := ''
	if o.on_select != unsafe { nil } {
		f := o.on_select
		ex += a.vt_attr('data-on-select', fn [f] (b string) {
			f(tree_event(b))
		})
	}
	if o.on_dblclick != unsafe { nil } {
		f := o.on_dblclick
		ex += a.vt_attr('data-on-dblclick', fn [f] (b string) {
			f(tree_event(b))
		})
	}
	st := if o.height != '' { 'max-height:${o.height}' } else { '' }
	return a.vt_html('vspk-tree', 'vtree', o.id, '{"nodes":${tree_json(nodes)}}', ex, st)
}

pub fn table_set_js(id string, rows [][]string) string {
	rs := rows.map(json_str_array(it)).join(',')
	return 'window.__vspk_table_set(${js_str(id)},null,[${rs}])'
}

// Cambia las filas de una tabla. Si vive en una ventana extra: w.eval_js(vspk.table_set_js(id, filas)).
pub fn (a &App) table_set(id string, rows [][]string) {
	a.eval_js(table_set_js(id, rows))
}

pub fn (a &App) table_select(id string, index int) {
	a.eval_js('window.__vspk_table_select(${js_str(id)},${index})')
}

pub fn (a &App) table_sort(id string, col int, desc bool) {
	a.eval_js('window.__vspk_table_sort(${js_str(id)},${col},${if desc { -1 } else { 1 }})')
}

pub fn (a &App) tree_set(id string, nodes []TreeNode) {
	a.eval_js('window.__vspk_tree_set(${js_str(id)},${tree_json(nodes)})')
}

// Selector de color / fecha enlazados a un State.
pub fn color_picker(bind &State) string {
	return '<input type="color" class="sz-input"${bind_attr(bind)}>'
}

pub fn date_picker(bind &State, with_time bool) string {
	return '<input type="${if with_time {
		'datetime-local'
	} else {
		'date'
	}}" class="sz-input"${bind_attr(bind)}>'
}

// Temporizadores (activos mientras run() esté en marcha). f devuelve false para cancelar.
pub fn (a &App) run_every(ms int, f fn () bool) {
	mut me := unsafe { a }
	me.timers << &Timer{
		ms:   ms
		f:    f
		next: if a.running { time.ticks() + ms } else { -1 }
	}
}

pub fn (a &App) run_after(ms int, f fn ()) {
	mut me := unsafe { a }
	me.timers << &Timer{
		ms:   ms
		once: true
		f:    fn [f] () bool {
			f()
			return false
		}
		next: if a.running { time.ticks() + ms } else { -1 }
	}
}

// ── Canvas ───────────────────────────────────────────────────────────────────
//   cv := app.canvas('lienzo', 400, 300)
//   cv.color('#6750A4').rect(10, 10, 100, 60).circle(200, 60, 40)
//   app.add(cv.html())      cv.erase()      cv.on_mouse(fn (e vspk.MouseEvent) {...})

@[heap]
pub struct Canvas {
	id string
	w  int
	h  int
mut:
	app &App = unsafe { nil }
	log string
}

pub fn (a &App) canvas(id string, w int, h int) &Canvas {
	mut me := unsafe { a }
	c := &Canvas{
		id:  id
		w:   w
		h:   h
		app: a
	}
	me.cvs << c
	return c
}

pub fn (c &Canvas) html() string {
	return '<canvas id="${html_escape(c.id)}" width="${c.w}" height="${c.h}" style="width:${c.w}px;max-width:100%;height:auto;border:1px solid rgba(128,128,128,.4);border-radius:8px;touch-action:none"></canvas>'
}

fn (c &Canvas) op(name string, args string) &Canvas {
	mut me := unsafe { c }
	code := '__cv(${js_str(c.id)},${js_str(name)},${args})'
	if name == 'clear' {
		me.log = ''
	}
	me.log += code + ';'
	if c.app.running {
		c.app.sse('all', js_str(code))
	}
	return c
}

fn (c &Canvas) opn(name string, v []f64) &Canvas {
	return c.op(name, '[' + v.map(num_str(it)).join(',') + ']')
}

pub fn (c &Canvas) color(col string) &Canvas {
	return c.op('color', '[${js_str(col)}]')
}

pub fn (c &Canvas) line_width(w f64) &Canvas {
	return c.opn('lw', [w])
}

pub fn (c &Canvas) font(size f64) &Canvas {
	return c.opn('font', [size])
}

pub fn (c &Canvas) line(x1 f64, y1 f64, x2 f64, y2 f64) &Canvas {
	return c.opn('line', [x1, y1, x2, y2])
}

pub fn (c &Canvas) rect(x f64, y f64, w f64, h f64) &Canvas {
	return c.opn('rect', [x, y, w, h])
}

pub fn (c &Canvas) frame(x f64, y f64, w f64, h f64) &Canvas {
	return c.opn('frame', [x, y, w, h])
}

pub fn (c &Canvas) circle(x f64, y f64, r f64) &Canvas {
	return c.opn('circle', [x, y, r])
}

pub fn (c &Canvas) ring(x f64, y f64, r f64) &Canvas {
	return c.opn('ring', [x, y, r])
}

pub fn (c &Canvas) text(x f64, y f64, s string) &Canvas {
	return c.op('text', '[${num_str(x)},${num_str(y)},${js_str(s)}]')
}

pub fn (c &Canvas) poly(points [][2]f64) &Canvas {
	return c.op('poly', '[[' + points.map('[${num_str(it[0])},${num_str(it[1])}]').join(',') + ']]')
}

pub fn (c &Canvas) erase() &Canvas {
	return c.op('clear', '[]')
}

// JS crudo con (ctx, canvas) en el ámbito
pub fn (c &Canvas) draw(code string) &Canvas {
	return c.op('draw', '[${js_str(code)}]')
}

pub fn (c &Canvas) on_mouse(f fn (MouseEvent)) &Canvas {
	a := c.app
	name := a.ev('m${a.next_id()}')
	a.add_ev(name, fn [f] (body string) {
		t, _ := jstr(body, 'type')
		f(MouseEvent{
			typ:    t
			x:      int(jnum(body, 'x'))
			y:      int(jnum(body, 'y'))
			button: int(jnum(body, 'button'))
		})
	})
	post := a.post_js(name,
		'JSON.stringify({type:t,x:Math.round((e.clientX-r.left)*c.width/r.width),y:Math.round((e.clientY-r.top)*c.height/r.height),button:e.button})')
	code := "(function(){var c=document.getElementById(${js_str(c.id)});if(!c)return;function p(t,e){if(t==='move'){var n=Date.now();if(n-(c.__lm||0)<30)return;c.__lm=n;}var r=c.getBoundingClientRect();${post}}['down','up','move','click'].forEach(function(t){c.addEventListener(t==='down'?'mousedown':t==='up'?'mouseup':t==='move'?'mousemove':'click',function(e){p(t,e)})})})();"
	mut me := unsafe { a }
	me.cvmouse += code
	if a.running {
		a.sse('all', js_str(code))
	}
	return c
}

// ── Ventanas adicionales ─────────────────────────────────────────────────────
//   aj := app.window('Ajustes', 360, 240)
//   aj.add(vspk.col(vspk.h4('Ajustes'), vspk.input(nombre, 'Nombre')))   // los estados se comparten
//   aj.show()   aj.close()   aj.on_close(fn () bool { return true })   aj.set_title('...')   aj.eval_js('...')

@[heap]
pub struct Window {
	id     string
	width  int
	height int
mut:
	app      &App = unsafe { nil }
	title    string
	body     []string
	proc     &os.Process = unsafe { nil }
	htv      string
	want     bool
	close_on bool
	close_js string
}

pub fn (a &App) window(title string, w int, h int) &Window {
	mut me := unsafe { a }
	win := &Window{
		id:     'w${a.wins.len + 1}'
		width:  if w > 0 { w } else { 480 }
		height: if h > 0 { h } else { 360 }
		app:    a
		title:  title
	}
	me.wins << win
	return win
}

pub fn (w &Window) add(ws ...string) {
	mut me := unsafe { w }
	me.body << ws
}

pub fn (w &Window) is_open() bool {
	return alive(w.proc)
}

pub fn (w &Window) eval_js(code string) {
	w.app.sse('eval_${w.id}', js_str(code))
}

pub fn (w &Window) close() {
	w.eval_js('__vspk.close()')
}

pub fn (w &Window) set_title(t string) {
	w.eval_js('__vspk.setTitle(${js_str(t)})')
}

// f devuelve false para cancelar el cierre de la ventana.
pub fn (w &Window) on_close(f fn () bool) {
	mut me := unsafe { w }
	a := w.app
	name := a.ev('c${w.id}')
	me.close_on = true
	me.close_js = "window.addEventListener('vspk:closeRequested',function(){${a.post_js(name,
		"'{}'")}});"
	a.add_ev(name, fn [w, f] (_ string) {
		w.eval_js(close_result(f()))
	})
}

pub fn (w &Window) show() {
	if w.app.running {
		w.open()
	} else {
		mut me := unsafe { w }
		me.want = true
	}
}

fn (w &Window) open() {
	if w.is_open() {
		return
	}
	mut me := unsafe { w }
	a := w.app
	if me.htv != '' {
		os.rm(me.htv) or {}
	}
	page := a.build_page(w.title, w.body.join('\n'), 'eval_${w.id}', false, w.close_js)
	ic := a.find_icon()
	ic_line := if ic != '' { 'icon: ' + ic + '\n' } else { '' }
	head := 'title: ${w.title}\nwidth: ${w.width}\nheight: ${w.height}\ndevtools: true\n${ic_line}${if w.close_on {
		'on_close: confirm\n'
	} else {
		''
	}}'
	me.htv = a.write_htv(head, page) or { return }
	me.proc = a.spawn_vspk(me.htv) or { return }
}

// ── Página ───────────────────────────────────────────────────────────────────

fn (a &App) build_page(title string, body string, evalev string, is_main bool, child_close string) string {
	mut st := '{'
	for i, s in a.states {
		if i > 0 {
			st += ','
		}
		st += '${js_str(s.name)}:${val_json(s.val)}'
	}
	st += '}'
	mut code := page_js.replace('%PORT%', a.port.str()).replace('%VEV%', a.ev('v')).replace('%WIN%',
		js_str(evalev)).replace('%EVALEV%', js_str(evalev))
	code =
		code.replace('%STATE%', st) // el último: el contenido del usuario no se vuelve a sustituir
	mut tail := '\n'
	if is_main && a.key_on {
		tail += 'document.addEventListener("keydown",function(e){' +
			a.post_js(a.ev('k'), 'JSON.stringify({key:e.key,code:e.code,ctrl:e.ctrlKey,shift:e.shiftKey,alt:e.altKey,meta:e.metaKey})') +
			'});'
	}
	tail += child_close
	if is_main && a.close_on {
		tail += 'window.addEventListener("vspk:closeRequested",function(){' +
			a.post_js(a.ev('c'), '"{}"') + '});'
	}
	for c in a.cvs {
		tail += c.log
	}
	tail += a.cvmouse
	mut vars := '  --sz-primary: ${a.cfg.primary};'
	if a.cfg.bg != '' {
		vars += '\n  --sz-bg: ${a.cfg.bg};'
	}
	if a.cfg.surface != '' {
		vars += '\n  --sz-surface: ${a.cfg.surface};'
	}
	if a.cfg.font != '' {
		vars += '\n  --sz-font: ${a.cfg.font}, system-ui, sans-serif;'
	}
	theme := if a.cfg.theme == 'dark' { 'dark' } else { 'light' }
	return '<!DOCTYPE html>
<html data-theme="${theme}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${html_escape(title)}</title>
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="spork.css" onerror="this.onerror=null;this.href=\'${css_cdn}\'">
  <style>:root {
${vars}
}</style>
</head>
<body class="sz-body">

<div id="__app" class="sz-page">
${body}
</div>

<script>
${code}${tail}
</script>
<script src="spork.js" onerror="var s=document.createElement(\'script\');s.src=\'${js_cdn}\';document.body.appendChild(s)"></script>
</body>
</html>'
}

fn (a &App) write_htv(head string, html string) !string {
	mut me := unsafe { a }
	me.htvn++
	path := os.join_path(os.temp_dir(), 'vspk_${a.token}_${a.htvn}.htv')
	os.write_file(path, head + '\n' + html)!
	return path
}

fn (a &App) find_exe() string {
	if a.cfg.exe != '' {
		return a.cfg.exe
	}
	exe := if os.user_os() == 'windows' { 'vspk.exe' } else { 'vspk' }
	env := os.getenv('VSPK_EXE')
	if env != '' {
		return env
	}
	beside := os.join_path(os.dir(os.executable()), exe)
	if os.exists(beside) {
		return beside
	}
	if os.exists(exe) {
		return os.join_path(os.getwd(), exe)
	}
	if os.user_os() == 'windows' {
		for d in ['C:\\spork', 'C:\\spork_studio'] {
			if os.exists(os.join_path(d, exe)) {
				return os.join_path(d, exe)
			}
		}
	}
	return os.find_abs_path_of_executable(exe) or { exe }
}

fn (a &App) spawn_vspk(htv string) !&os.Process {
	mut pr := os.new_process(a.find_exe())
	pr.set_args([htv])
	pr.run()
	if pr.status == .aborted {
		return error('no se pudo lanzar ${a.find_exe()}')
	}
	return pr
}

fn (a &App) find_icon() string {
	for d in [os.getwd(), os.dir(os.executable())] {
		for n in ['icon.ico', 'icon.png', 'favicon.ico', 'favicon.png'] {
			f := os.join_path(d, n)
			if os.exists(f) {
				return f
			}
		}
	}
	return ''
}

// ── Servidor HTTP (puente) ───────────────────────────────────────────────────

const cors = 'Access-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET, POST, OPTIONS\r\nAccess-Control-Allow-Headers: *\r\n'

fn alive(p &os.Process) bool {
	if isnil(p) {
		return false
	}
	mut q := unsafe { p }
	return q.is_alive()
}

fn (a &App) thr_inc() {
	a.tmu.lock()
	mut me := unsafe { a }
	me.nthr++
	a.tmu.unlock()
}

fn (a &App) thr_dec() {
	a.tmu.lock()
	mut me := unsafe { a }
	me.nthr--
	a.tmu.unlock()
}

fn (a &App) accept_loop() {
	for !a.stopping {
		mut l := unsafe { a.listener }
		mut c := l.accept() or {
			if a.stopping {
				break
			}
			time.sleep(5 * time.millisecond)
			continue
		}
		a.thr_inc()
		spawn a.handle_conn(mut c)
	}
	a.thr_dec()
}

fn reply(mut conn net.TcpConn, status string, body string) {
	conn.write_string('HTTP/1.1 ${status}\r\n${cors}Content-Type: text/plain\r\nContent-Length: ${body.len}\r\nConnection: close\r\n\r\n${body}') or {}
}

fn (a &App) handle_conn(mut conn net.TcpConn) {
	conn.set_read_timeout(5 * time.second)
	mut data := []u8{}
	mut buf := []u8{len: 4096}
	mut hend := -1
	mut need := 0
	for {
		if hend < 0 && data.len > 0 {
			s := data.bytestr()
			i := s.index('\r\n\r\n') or { -1 }
			if i >= 0 {
				hend = i + 4
				low := s[..i].to_lower()
				cl := low.index('content-length:') or { -1 }
				mut n := 0
				if cl >= 0 {
					rest := low[cl + 15..]
					line := rest.all_before('\r\n')
					n = line.trim_space().int()
				}
				need = hend + n
				if need > 4 * 1024 * 1024 {
					conn.close() or {}
					a.thr_dec()
					return
				}
			}
		}
		if hend >= 0 && data.len >= need {
			break
		}
		n := conn.read(mut buf) or { 0 }
		if n <= 0 || data.len > 4 * 1024 * 1024 {
			conn.close() or {}
			a.thr_dec()
			return
		}
		data << buf[..n]
	}
	req := data.bytestr()
	first := req.all_before('\r\n').split(' ')
	method := if first.len > 0 { first[0] } else { '' }
	mut path := if first.len > 1 { first[1] } else { '' }
	if path.contains('?') {
		path = path.all_before('?')
	}
	path = percent_decode(path)
	body := req[hend..]
	mut closed := false
	if method == 'OPTIONS' {
		reply(mut conn, '204 No Content', '')
	} else if path == '/events' {
		a.serve_sse(mut conn)
	} else if path == '/favicon.ico' {
		reply(mut conn, '204 No Content', '')
	} else if path.starts_with('/cb/') {
		reply(mut conn, '200 OK', 'ok')
		conn.close() or {}
		closed = true
		a.dispatch_cb(path[4..])
	} else if path.starts_with('/event/') && method == 'POST' {
		reply(mut conn, '200 OK', 'ok')
		conn.close() or {}
		closed = true
		a.dispatch_ev(path[7..], body)
	} else {
		reply(mut conn, '404 Not Found', 'not found')
	}
	if !closed {
		conn.close() or {}
	}
	a.thr_dec()
}

fn percent_decode(s string) string {
	if !s.contains('%') {
		return s
	}
	mut b := []u8{}
	mut i := 0
	for i < s.len {
		if s[i] == `%` && i + 2 < s.len + 0 && is_hex(s[i + 1]) && is_hex(s[i + 2]) {
			b << u8(hexval(s[i + 1]) * 16 + hexval(s[i + 2]))
			i += 3
		} else {
			b << s[i]
			i++
		}
	}
	return b.bytestr()
}

fn (a &App) serve_sse(mut conn net.TcpConn) {
	hdr := 'HTTP/1.1 200 OK\r\n${cors}Content-Type: text/event-stream\r\nCache-Control: no-cache\r\nConnection: close\r\n\r\n: conectado\n\n'
	conn.write_string(hdr) or { return }
	mut me := unsafe { a }
	mut c := &Client{
		conn:  conn
		alive: true
	}
	a.smu.lock()
	me.clients << c
	a.smu.unlock()
	mut last := time.ticks()
	for c.alive && !a.stopping {
		time.sleep(100 * time.millisecond)
		if time.ticks() - last > 15000 {
			last = time.ticks()
			a.smu.lock()
			if c.alive {
				conn.write_string(': ping\n\n') or { c.alive = false }
			}
			a.smu.unlock()
		}
	}
	a.smu.lock()
	me.clients = me.clients.filter(it != c)
	a.smu.unlock()
}

fn (a &App) dispatch_cb(id string) {
	a.umu.lock()
	if f := a.cbs[id] { // id sin token válido → no existe → no hace nada
		f()
	}
	a.umu.unlock()
}

fn (a &App) dispatch_ev(name string, body string) {
	a.umu.lock()
	defer {
		a.umu.unlock()
	}
	if f := a.evs[name] {
		f(body)
		return
	}
	if name != a.ev('v') {
		return
	}
	// valor de un campo enlazado: {n, v, w}
	n, ok := jstr(body, 'n')
	if !ok {
		return
	}
	w, _ := jstr(body, 'w')
	vi := jfind(body, 'v')
	if vi < 0 {
		return
	}
	for s in a.states {
		if s.name != n {
			continue
		}
		mut st := unsafe { s }
		if body[vi] == `"` {
			st.val = Val(junq(body, vi))
		} else if body[vi..].starts_with('true') {
			st.val = Val(true)
		} else if body[vi..].starts_with('false') {
			st.val = Val(false)
		} else {
			f := body[vi..jvalue_end(body, vi)].f64()
			st.val = if f == f64(int(f)) { Val(int(f)) } else { Val(f) }
		}
		if a.wins.len > 0 {
			st.push(&w)
		}
		st.change(st.text())
		return
	}
}

// ── run() ────────────────────────────────────────────────────────────────────

// Abre vspk con un .htv temporal y atiende eventos hasta que se cierra la ventana.
pub fn (a &App) run() ! {
	mut me := unsafe { a }
	html := a.build_page(a.title, a.root.join('\n'), 'eval', true, '')
	icon := a.find_icon()
	mut head := 'title: ${a.title}\nwidth: ${a.cfg.width}\nheight: ${a.cfg.height}\n'
	if a.cfg.devtools {
		head += 'devtools: true\n'
	}
	if icon != '' {
		head += 'icon: ${icon}\n'
	}
	if a.close_on {
		head += 'on_close: confirm\n'
	}
	htv := a.write_htv(head, html)!
	me.proc = a.spawn_vspk(htv) or {
		os.rm(htv) or {}
		return err
	}
	a.umu.lock()
	me.running = true
	for w in a.wins {
		if w.want {
			w.open()
		}
	}
	t0 := time.ticks()
	for mut t in me.timers {
		if t.next < 0 {
			t.next = t0 + t.ms
		}
	}
	a.umu.unlock()

	for !a.quitting && alive(a.proc) {
		now := time.ticks()
		a.umu.lock()
		mut i := 0
		for i < me.timers.len {
			mut t := me.timers[i]
			if !t.cancelled && t.next >= 0 && now >= t.next {
				keep := t.f() // f puede añadir temporizadores
				if t.once || !keep {
					t.cancelled = true
				} else {
					t.next = time.ticks() + t.ms
				}
			}
			i++
		}
		a.umu.unlock()
		time.sleep(10 * time.millisecond)
	}

	a.umu.lock()
	me.running = false
	a.umu.unlock()
	// Al cerrar la principal se cierran las demás.
	for w in a.wins {
		if w.is_open() {
			w.eval_js('__vspk.close()')
		}
	}
	if a.wins.len > 0 {
		time.sleep(300 * time.millisecond)
	}
	for w in a.wins {
		if !isnil(w.proc) {
			mut pr := unsafe { w.proc }
			if alive(pr) {
				pr.signal_kill()
			}
			pr.wait()
			pr.close()
		}
		if w.htv != '' {
			os.rm(w.htv) or {}
		}
	}
	if alive(a.proc) {
		mut pr := me.proc
		pr.signal_kill()
	}
	mut pr := me.proc
	pr.wait()
	pr.close()
	os.rm(htv) or {}
	// apaga el puente
	me.stopping = true
	a.smu.lock()
	for mut c in me.clients {
		c.alive = false
	}
	a.smu.unlock()
	mut l := me.listener
	l.close() or {}
	for _ in 0 .. 40 {
		a.tmu.lock()
		n := a.nthr
		a.tmu.unlock()
		if n <= 0 {
			break
		}
		time.sleep(50 * time.millisecond)
	}
}
