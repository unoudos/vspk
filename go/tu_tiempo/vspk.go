// vspk.go — GUI nativa para Go usando vspk como WebView
//
// Uso:
//   app := vspk.New("Mi App", 800, 600)
//   count := app.State("count", 0)
//
//   app.Add(vspk.Col(
//       vspk.H1(count),
//       vspk.Row(
//           app.Button("+1",    vspk.JS(count.Inc(1))),
//           app.Button("Reset", vspk.JS(count.Set("0"))),
//       ),
//   ))
//   app.Run()

package main

import (
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"
)

// ── Log a fichero ─────────────────────────────────────────────────────────────
var (
	vlogOnce sync.Once
	vlogF    *os.File
)

func vlogFile() *os.File {
	vlogOnce.Do(func() {
		dir := "."
		if bin, err := os.Executable(); err == nil {
			dir = filepath.Dir(bin)
		}
		f, err := os.OpenFile(filepath.Join(dir, "vspk_debug.log"),
			os.O_CREATE|os.O_WRONLY|os.O_TRUNC, 0644)
		if err == nil {
			vlogF = f
		}
	})
	return vlogF
}

func vlogf(format string, args ...any) {
	line := fmt.Sprintf("[%s] ", time.Now().Format("15:04:05")) + fmt.Sprintf(format, args...)
	if f := vlogFile(); f != nil {
		fmt.Fprint(f, line)
		f.Sync()
	}
	fmt.Fprint(os.Stderr, line)
}

// ── Buscar vspk executable ────────────────────────────────────────────────────

func findVspk() string {
	exe := "vspk"
	if runtime.GOOS == "windows" {
		exe = "vspk.exe"
	}

	self := ""
	if bin, err := os.Executable(); err == nil {
		if abs, err := filepath.Abs(bin); err == nil {
			self = filepath.Clean(abs)
		}
	}
	safe := func(p string) string {
		if p == "" {
			return ""
		}
		if self != "" {
			if abs, err := filepath.Abs(p); err == nil && filepath.Clean(abs) == self {
				return ""
			}
		}
		if _, err := os.Stat(p); err != nil {
			return ""
		}
		return p
	}

	if env := os.Getenv("VSPK_EXE"); env != "" {
		if p := safe(env); p != "" {
			return p
		}
	}
	if bin, err := os.Executable(); err == nil {
		if p := safe(filepath.Join(filepath.Dir(bin), exe)); p != "" {
			return p
		}
	}
	if p, err := exec.LookPath(exe); err == nil {
		if p := safe(p); p != "" {
			return p
		}
	}
	if runtime.GOOS == "windows" {
		for _, c := range []string{
			`C:\spork\vspk.exe`,
			`C:\spork_studio\vspk.exe`,
			`C:\00\vspk\spkgui\target\release\vspk.exe`,
		} {
			if p := safe(c); p != "" {
				return p
			}
		}
	}
	return exe
}

// ── Estado reactivo ───────────────────────────────────────────────────────────

type State struct {
	name  string
	value any
	app   *App
	vmu   sync.RWMutex
}

func (s *State) Name() string { return s.name }
func (s *State) Get() any {
	s.vmu.RLock()
	defer s.vmu.RUnlock()
	return s.value
}

func (s *State) Set(value any) {
	s.vmu.Lock()
	s.value = value
	s.vmu.Unlock()
	s.app.pushState(s.name, value)
}

// setSilent guarda el valor SIN reenviarlo a la página (valor escrito/elegido por el usuario).
func (s *State) setSilent(value any) {
	s.vmu.Lock()
	s.value = value
	s.vmu.Unlock()
}

func (s *State) SetAsync(value any) { go s.Set(value) }

func (s *State) Get_js() string { return "window.__state." + s.name }
func (s *State) Set_js(expr string) string {
	return fmt.Sprintf("window.__set('%s',%s)", s.name, expr)
}
func (s *State) Inc(by float64) string {
	if by >= 0 {
		return fmt.Sprintf("window.__set('%s',window.__state.%s+%v)", s.name, s.name, by)
	}
	return fmt.Sprintf("window.__set('%s',window.__state.%s%v)", s.name, s.name, by)
}
func (s *State) Dec(by float64) string { return s.Inc(-by) }
func (s *State) SetVal(expr string) string {
	return fmt.Sprintf("window.__set('%s',%s)", s.name, expr)
}

func (s *State) String() string {
	return fmt.Sprintf(`<span data-spork-text="%s"></span>`, s.name)
}

// ── Widgets ───────────────────────────────────────────────────────────────────

type Widget interface {
	Render() string
}

type Raw string

func (r Raw) Render() string { return string(r) }

func JS(s string) string { return s }

func renderChild(c any) string {
	switch v := c.(type) {
	case Widget:
		return v.Render()
	case *State:
		return v.String()
	case string:
		return v
	case fmt.Stringer:
		return v.String()
	default:
		return fmt.Sprintf("%v", v)
	}
}

func renderChildren(children []any) string {
	parts := make([]string, len(children))
	for i, c := range children {
		parts[i] = renderChild(c)
	}
	return strings.Join(parts, "\n")
}

type tag struct {
	t        string
	cls      string
	children []any
	attrs    map[string]string
}

func (w *tag) Render() string {
	parts := []string{}
	if w.cls != "" {
		parts = append(parts, fmt.Sprintf(`class="%s"`, w.cls))
	}
	for k, v := range w.attrs {
		if k == "onclick" || k == "oninput" || k == "onchange" {
			v = strings.ReplaceAll(v, `"`, "&quot;")
		} else {
			v = htmlEscape(v)
		}
		parts = append(parts, fmt.Sprintf(`%s="%s"`, k, v))
	}
	attrStr := ""
	if len(parts) > 0 {
		attrStr = " " + strings.Join(parts, " ")
	}
	inner := renderChildren(w.children)
	if w.t == "input" || w.t == "hr" {
		return fmt.Sprintf("<%s%s>", w.t, attrStr)
	}
	if inner == "" {
		return fmt.Sprintf("<%s%s></%s>", w.t, attrStr, w.t)
	}
	return fmt.Sprintf("<%s%s>\n%s\n</%s>", w.t, attrStr, inner, w.t)
}

func htmlEscape(s string) string {
	s = strings.ReplaceAll(s, "&", "&amp;")
	s = strings.ReplaceAll(s, "<", "&lt;")
	s = strings.ReplaceAll(s, ">", "&gt;")
	s = strings.ReplaceAll(s, `"`, "&quot;")
	return s
}

func newTag(t, cls string, children ...any) *tag {
	return &tag{t: t, cls: cls, children: children}
}

// Layout
func Row(children ...any) Widget  { return newTag("div", "sz-row", children...) }
func Col(children ...any) Widget  { return newTag("div", "sz-col sz-center", children...) }
func Card(children ...any) Widget { return newTag("div", "sz-card", children...) }
func Grid(children ...any) Widget { return newTag("div", "sz-grid", children...) }
func Hr() Widget                  { return Raw(`<hr class="sz-divider">`) }
func Spacer() Widget              { return Raw(`<div class="sz-grow"></div>`) }

// Texto
func H1(content any) Widget    { return newTag("h1", "sz-h1", content) }
func H2(content any) Widget    { return newTag("h2", "sz-h2", content) }
func H3(content any) Widget    { return newTag("h3", "sz-h3", content) }
func H4(content any) Widget    { return newTag("h4", "sz-h4", content) }
func P(content any) Widget     { return newTag("p", "sz-p", content) }
func Label(content any) Widget { return newTag("label", "sz-label", content) }
func Badge(content any) Widget { return newTag("span", "sz-badge", content) }

func Chip(text string, primary bool) Widget {
	cls := "sz-chip"
	if primary {
		cls += " sz-chip-primary"
	}
	return newTag("span", cls, text)
}

func Alert(content any, variant ...string) Widget {
	cls := "sz-alert"
	if len(variant) > 0 && variant[0] != "" {
		cls += " sz-alert-" + variant[0]
	}
	return newTag("div", cls, content)
}

func Progress(s *State) Widget {
	style := fmt.Sprintf(`{"width": window.__state.%s + "%%"}`, s.Name())
	return Raw(fmt.Sprintf(
		`<div class="sz-progress"><div class="sz-progress-bar" data-spork-style="%s"></div></div>`,
		htmlEscape(style),
	))
}

func Button(text, js string, opts ...string) Widget {
	variant := "filled"
	size := ""
	if len(opts) > 0 && opts[0] != "" {
		variant = opts[0]
	}
	if len(opts) > 1 && opts[1] != "" {
		size = opts[1]
	}
	cls := "sz-btn sz-btn-" + variant
	if size != "" {
		cls += " sz-btn-" + size
	}
	w := newTag("button", cls, text)
	w.attrs = map[string]string{"data-ripple": ""}
	if js != "" {
		w.attrs["onclick"] = js
	}
	return w
}

func Input(placeholder string, bind *State) Widget {
	w := &tag{t: "input", cls: "sz-input", attrs: map[string]string{}}
	if placeholder != "" {
		w.attrs["placeholder"] = placeholder
	}
	if bind != nil {
		w.attrs["data-spork-bind"] = bind.Name()
		w.attrs["oninput"] = fmt.Sprintf("window.__set('%s',this.value);window.__sync('%s',this.value)", bind.Name(), bind.Name())
	}
	return w
}

func Textarea(placeholder string, rows int, bind *State) Widget {
	w := &tag{t: "textarea", cls: "sz-textarea", attrs: map[string]string{
		"rows": fmt.Sprintf("%d", rows),
	}}
	if placeholder != "" {
		w.attrs["placeholder"] = placeholder
	}
	if bind != nil {
		w.attrs["data-spork-bind"] = bind.Name()
		w.attrs["oninput"] = fmt.Sprintf("window.__set('%s',this.value);window.__sync('%s',this.value)", bind.Name(), bind.Name())
	}
	return w
}

func Select(options [][2]string, bind *State) Widget {
	opts := make([]string, len(options))
	for i, o := range options {
		opts[i] = fmt.Sprintf(`  <option value="%s">%s</option>`, htmlEscape(o[0]), htmlEscape(o[1]))
	}
	onchange := ""
	dataAttr := ""
	if bind != nil {
		onchange = fmt.Sprintf(` onchange="window.__set('%s',this.value);window.__sync('%s',this.value)"`, bind.Name(), bind.Name())
		dataAttr = fmt.Sprintf(` data-spork-bind="%s"`, bind.Name())
	}
	return Raw(fmt.Sprintf(
		`<select class="sz-select"%s%s>`+"\n%s\n</select>",
		dataAttr, onchange, strings.Join(opts, "\n"),
	))
}

func Checkbox(label string, bind *State, checked ...bool) Widget {
	isChecked := len(checked) > 0 && checked[0]
	checkedAttr := ""
	if isChecked {
		checkedAttr = " checked"
	}
	bindAttr := ""
	if bind != nil {
		bindAttr = fmt.Sprintf(` data-spork-bind="%s" onchange="window.__set('%s',this.checked);window.__sync('%s',this.checked)"`, bind.Name(), bind.Name(), bind.Name())
	}
	return Raw(fmt.Sprintf(
		`<label class="sz-switch">`+
			`<input type="checkbox"%s%s>`+
			`<span class="sz-switch-track"><span class="sz-switch-thumb"></span></span>`+
			`<span class="sz-switch-label">%s</span>`+
			`</label>`,
		checkedAttr, bindAttr, htmlEscape(label),
	))
}

// ── App ───────────────────────────────────────────────────────────────────────

type App struct {
	title    string
	width    int
	height   int
	theme    string
	primary  string
	devtools bool

	states  map[string]*State
	root    []Widget
	vspkExe string

	mu      sync.Mutex
	clients []chan string

	callbacks map[string]func()
	handlers  map[string]func(string)

	token   string
	ln      net.Listener
	port    int
	cbCount int
	vtCount int
	keyOn   bool
	closeOn bool
	running bool
	timers  []func() // arrancan cuando la ventana está abierta

	cvOrder   []string          // ids de canvas, en orden de creación
	cvLogs    map[string]string // JS de dibujo por canvas (se reproduce al cargar la página)
	cvMouseJs string
	stop      chan struct{}

	wins []*Win
}

func New(title string, width, height int, opts ...string) *App {
	theme := "light"
	primary := "#6750A4"
	if len(opts) > 0 && opts[0] != "" {
		theme = opts[0]
	}
	if len(opts) > 1 && opts[1] != "" {
		primary = opts[1]
	}
	// El puerto del bridge y el token se conocen ya, antes de construir los widgets.
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		panic("vspk: no se pudo abrir puerto: " + err.Error())
	}
	tb := make([]byte, 8)
	rand.Read(tb)
	return &App{
		ln:      ln,
		port:    ln.Addr().(*net.TCPAddr).Port,
		token:   hex.EncodeToString(tb),
		stop:    make(chan struct{}),
		title:   title,
		width:   width,
		height:  height,
		theme:   theme,
		primary: primary,
		states:  map[string]*State{},
		vspkExe: findVspk(),
	}
}

func (a *App) WithDevtools() *App { a.devtools = true; return a }

func (a *App) State(name string, initial any) *State {
	s := &State{name: name, value: initial, app: a}
	a.states[name] = s
	return s
}

func (a *App) Add(widgets ...Widget) *App {
	a.root = append(a.root, widgets...)
	return a
}

func (a *App) Button(text, js string, opts ...string) Widget {
	return Button(text, js, opts...)
}

func Image(bind *State, alt ...string) Widget {
	attrsMap := fmt.Sprintf(`{"src": "window.__state.%s"}`, bind.Name())
	altText := ""
	if len(alt) > 0 {
		altText = alt[0]
	}
	return Raw(fmt.Sprintf(
		`<img class="sz-img" alt="%s" data-spork-attrs="%s">`,
		htmlEscape(altText),
		htmlEscape(attrsMap),
	))
}

func (a *App) broadcast(m map[string]any) {
	data, _ := json.Marshal(m)
	msg := "data: " + string(data) + "\n\n"
	a.mu.Lock()
	defer a.mu.Unlock()
	for _, ch := range a.clients {
		select {
		case ch <- msg:
		default:
		}
	}
}

func (a *App) pushState(name string, value any) {
	a.broadcast(map[string]any{"type": "state", "key": name, "value": value, "src": ""})
}

// EvalJS ejecuta JS en la ventana principal.
func (a *App) EvalJS(js string) { a.evalTo("main", js) }

// evalTo: to = "main", el id de una ventana hija ("w1"...) o "all" (todas las ventanas).
func (a *App) evalTo(to, js string) {
	a.broadcast(map[string]any{"type": "eval", "value": js, "to": to})
}

func (a *App) addSSEClient(ch chan string) {
	a.mu.Lock()
	a.clients = append(a.clients, ch)
	a.mu.Unlock()
}

func (a *App) removeSSEClient(ch chan string) {
	a.mu.Lock()
	defer a.mu.Unlock()
	for i, c := range a.clients {
		if c == ch {
			a.clients = append(a.clients[:i], a.clients[i+1:]...)
			return
		}
	}
}

// ── HTML ──────────────────────────────────────────────────────────────────────

func (a *App) buildHTML() string {
	return a.buildPage(a.title, nil, "main", true, "")
}

// buildPage arma la página de una ventana: la principal (win = "main") o una hija ("w1"...).
func (a *App) buildPage(title string, widgets []Widget, win string, isMain bool, childCloseJs string) string {
	inits := []string{}
	for name, s := range a.states {
		v, _ := json.Marshal(s.Get())
		inits = append(inits, fmt.Sprintf("window.__set(%q, %s);", name, v))
	}
	stateInit := strings.Join(inits, "\n  ")

	src := a.root
	if !isMain {
		src = widgets
	}
	parts := make([]string, len(src))
	for i, w := range src {
		parts[i] = w.Render()
	}
	body := strings.Join(parts, "\n")

	darkCls := ""
	if a.theme == "dark" {
		darkCls = "sz-dark"
	}

	keyJs, closeJs := "", ""
	if isMain && a.keyOn {
		keyJs = `document.addEventListener("keydown",function(e){` + a.postJS(a.ev("k"),
			`JSON.stringify({key:e.key,code:e.code,ctrl:e.ctrlKey,shift:e.shiftKey,alt:e.altKey,meta:e.metaKey})`) + `});`
	}
	if isMain && a.closeOn {
		closeJs = `window.addEventListener("vspk:closeRequested",function(){` + a.postJS(a.ev("c"), `"{}"`) + `});`
	}
	closeJs += childCloseJs
	return fmt.Sprintf(`<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>%s</title>
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="spork.css">
  <style>
  :root { --sz-primary: %s; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  #app { display: flex; flex-direction: column; align-items: center;
         padding: 2rem; min-height: 100vh; }
  </style>
</head>
<body class="%s">
  <div id="app" class="sz-page">
%s
  </div>
  <script>
  window.__state = {};
  window.__set = function(k, v) {
    window.__state[k] = v;
    document.querySelectorAll('[data-spork-text]').forEach(function(el) {
      var key = el.getAttribute('data-spork-text').replace('window.__state.', '');
      if (key === k) el.textContent = String(v == null ? '' : v);
    });
    document.querySelectorAll('[data-spork-bind="' + k + '"]').forEach(function(el) {
      if (el.type === 'checkbox') el.checked = !!v; else el.value = (v == null ? '' : v);
    });
    document.querySelectorAll('[data-spork-style]').forEach(function(el) {
      var expr = el.getAttribute('data-spork-style');
      if (expr.indexOf('window.__state.' + k) !== -1) {
        try { var ss=Function('return ('+expr+')')(); for(var p in ss) el.style[p]=String(ss[p]); } catch(e) {}
      }
    });
    document.querySelectorAll('[data-spork-if]').forEach(function(el) {
      var expr = el.getAttribute('data-spork-if');
      if (expr.indexOf('window.__state.' + k) !== -1) {
        try { el.style.display = Function('return !!('+expr+')')() ? '' : 'none'; } catch(e) {}
      }
    });
  };
  // Envía a Go el valor que el usuario escribe/elige, para que State.Get() lo vea.
  window.__sync = function(k, v) {
    try { fetch('http://127.0.0.1:%d/event/%s', {method: 'POST', mode: 'no-cors', headers: {'Content-Type': 'text/plain'}, body: JSON.stringify({n: k, v: v, w: window.__win})}); } catch(_) {}
  };
  %s
  document.querySelectorAll('[data-spork-style]').forEach(function(el) {
    try { var ss=Function('return ('+el.getAttribute('data-spork-style')+')')(); for(var p in ss) el.style[p]=String(ss[p]); } catch(e) {}
  });
  var __es = new EventSource('http://127.0.0.1:%d/events');
  __es.onmessage = function(e) {
    try {
      var m = JSON.parse(e.data);
      if (m.type === 'state') { if (m.src && m.src === window.__win) return; window.__set(m.key, m.value); }
      else if (m.type === 'eval') { if (m.to === 'all' || m.to === window.__win) eval(m.value); }
    } catch(_) {}
  };
  </script>
  <script src="spork.js"></script>
  <script>if(window.Spork)Spork.init(window.__state);</script>
</body>
</html>`, htmlEscape(title), a.primary, darkCls, body, a.port, a.ev("v"), "window.__win = "+jsonStr(win)+";\n  "+stateInit+"\n  "+keyJs+closeJs+a.cvScript(), a.port)
}

// ── Servidor HTTP ─────────────────────────────────────────────────────────────

func (a *App) startServer(html string) (int, *http.Server) {
	mux := http.NewServeMux()

	mux.HandleFunc("/favicon.ico", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	})

	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" && r.URL.Path != "/index.html" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		io.WriteString(w, html)
	})

	mux.HandleFunc("/events", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/event-stream")
		w.Header().Set("Cache-Control", "no-cache")
		w.Header().Set("X-Accel-Buffering", "no")
		w.Header().Set("Access-Control-Allow-Origin", "*")

		ch := make(chan string, 32)
		a.addSSEClient(ch)
		defer a.removeSSEClient(ch)

		flusher, ok := w.(http.Flusher)
		ctx := r.Context()
		fmt.Fprint(w, ": conectado\n\n")
		if ok {
			flusher.Flush()
		}
		for {
			select {
			case <-ctx.Done():
				return
			case msg := <-ch:
				fmt.Fprint(w, msg)
				if ok {
					flusher.Flush()
				}
			case <-time.After(1 * time.Second):
				fmt.Fprint(w, ": ping\n\n")
				if ok {
					flusher.Flush()
				}
			}
		}
	})

	mux.HandleFunc("/proxy", func(w http.ResponseWriter, r *http.Request) {
		target := r.URL.Query().Get("url")
		if target == "" {
			http.Error(w, "missing url", http.StatusBadRequest)
			return
		}
		decoded, err := url.QueryUnescape(target)
		if err != nil {
			decoded = target
		}

		client := &http.Client{Timeout: 15 * time.Second}
		resp, err := client.Get(decoded)
		if err != nil {
			http.Error(w, "proxy error: "+err.Error(), http.StatusBadGateway)
			return
		}
		defer resp.Body.Close()

		ct := resp.Header.Get("Content-Type")
		if ct == "" {
			ct = "application/octet-stream"
		}
		w.Header().Set("Content-Type", ct)
		w.Header().Set("Access-Control-Allow-Origin", "*")
		io.Copy(w, resp.Body)
	})

	mux.HandleFunc("/cb/", func(w http.ResponseWriter, r *http.Request) {
		id := strings.TrimPrefix(r.URL.Path, "/cb/")
		a.mu.Lock()
		fn, ok := a.callbacks[id]
		a.mu.Unlock()
		if ok && fn != nil {
			go fn()
		}
		w.WriteHeader(http.StatusNoContent)
	})

	mux.HandleFunc("/event/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		if r.Method == http.MethodOptions {
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST")
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
			w.WriteHeader(http.StatusNoContent)
			return
		}
		name := strings.TrimPrefix(r.URL.Path, "/event/")
		if name == a.ev("v") && r.Method == http.MethodPost {
			// valor de un widget enlazado: {"n": nombre, "v": valor} -> State (sin reenviar a la página)
			body, _ := io.ReadAll(r.Body)
			var msg struct {
				N string `json:"n"`
				V any    `json:"v"`
				W string `json:"w"`
			}
			if json.Unmarshal(body, &msg) == nil {
				a.mu.Lock()
				s, ok := a.states[msg.N]
				nwins := len(a.wins)
				a.mu.Unlock()
				if ok {
					s.setSilent(msg.V)
					if nwins > 0 {
						// se reenvía a las demás ventanas (la de origen ignora su propio eco)
						a.broadcast(map[string]any{"type": "state", "key": msg.N, "value": msg.V, "src": msg.W})
					}
				}
			}
			w.WriteHeader(http.StatusNoContent)
			return
		}
		var payload string
		if r.Method == http.MethodPost {
			body, err := io.ReadAll(r.Body)
			if err == nil {
				payload = string(body)
			}
		} else {
			payload = r.URL.Query().Get("data")
		}
		a.mu.Lock()
		fn, ok := a.handlers[name]
		a.mu.Unlock()
		if ok && fn != nil {
			go fn(payload)
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		io.WriteString(w, `{"ok":true}`)
	})

	mux.HandleFunc("/state/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		name := strings.TrimPrefix(r.URL.Path, "/state/")
		val := r.URL.Query().Get("v")
		a.mu.Lock()
		if s, ok := a.states[name]; ok {
			s.setSilent(val)
			data, _ := json.Marshal(map[string]any{"type": "state", "key": name, "value": val})
			msg := "data: " + string(data) + "\n\n"
			for _, ch := range a.clients {
				select {
				case ch <- msg:
				default:
				}
			}
		}
		a.mu.Unlock()
		w.WriteHeader(http.StatusNoContent)
	})

	srv := &http.Server{Handler: mux}
	go srv.Serve(a.ln)
	return a.port, srv
}

// ── Callbacks y handlers ──────────────────────────────────────────────────────

func (a *App) initMaps() {
	if a.callbacks == nil {
		a.callbacks = map[string]func(){}
	}
	if a.handlers == nil {
		a.handlers = map[string]func(string){}
	}
}

func (a *App) OnClick(fn func()) string {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.initMaps()
	a.cbCount++
	id := fmt.Sprintf("cb_%s_%d", a.token, a.cbCount)
	a.callbacks[id] = fn
	return fmt.Sprintf("fetch('http://127.0.0.1:%d/cb/%s',{mode:'no-cors'})", a.port, id)
}

func (a *App) OnEvent(name string, fn func(payload string)) {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.initMaps()
	a.handlers[name] = fn
}

// ── Run ───────────────────────────────────────────────────────────────────────

func (a *App) Run() {
	a.mu.Lock()
	a.initMaps()
	a.mu.Unlock()

	html := a.buildHTML()
	_, srv := a.startServer(html)
	defer srv.Close()

	// .htv: cabecera + línea en blanco + HTML. vspk.exe sirve spork.css/js y inyecta window.__vspk.
	htv := filepath.Join(os.TempDir(), fmt.Sprintf("vspk_%d_%s.htv", os.Getpid(), a.token[:6]))
	head := fmt.Sprintf("title: %s\nwidth: %d\nheight: %d\ndevtools: %v\n", a.title, a.width, a.height, a.devtools)
	if ic := findIcon(); ic != "" {
		head += "icon: " + ic + "\n"
	}
	if a.closeOn {
		head += "on_close: confirm\n"
	}
	if err := os.WriteFile(htv, []byte(head+"\n"+html), 0o600); err != nil {
		vlogf("no se pudo escribir %s: %v\n", htv, err)
		return
	}
	defer os.Remove(htv)

	vlogf("lanzando: %s %s\n", a.vspkExe, htv)
	cmd := exec.Command(a.vspkExe, htv)
	cmd.Stdout = os.Stdout
	if f := vlogFile(); f != nil {
		cmd.Stderr = f // (no asignar un *os.File nil: dejaría un io.Writer no nulo con puntero nulo)
	}
	if err := cmd.Start(); err != nil {
		vlogf("no se encontró %s: %v\n", a.vspkExe, err)
		return
	}

	a.mu.Lock()
	a.running = true
	timers := a.timers
	wins := append([]*Win(nil), a.wins...)
	a.mu.Unlock()
	for _, t := range timers {
		go t()
	}
	for _, w := range wins {
		if w.want {
			a.winOpen(w)
		}
	}

	err := cmd.Wait()
	close(a.stop)
	// Al cerrar la principal se cierran las demás.
	for _, w := range wins {
		if w.IsOpen() {
			a.evalTo(w.id, "__vspk.close()")
		}
	}
	if len(wins) > 0 {
		time.Sleep(300 * time.Millisecond)
	}
	for _, w := range wins {
		w.mu.Lock()
		if w.cmd != nil && w.cmd.Process != nil && w.open {
			w.cmd.Process.Kill()
		}
		htv := w.htv
		w.mu.Unlock()
		if htv != "" {
			os.Remove(htv)
		}
	}
	if err != nil {
		vlogf("ventana cerrada (%v) — exit code: %v\n", err, cmd.ProcessState.ExitCode())
	} else {
		vlogf("ventana cerrada limpiamente\n")
	}
}

// ── API nueva: teclado, cierre, diálogos, temporizadores, ventana ────────────

func (a *App) ev(name string) string { return "__" + name + "_" + a.token }

func (a *App) postJS(name, bodyExpr string) string {
	return fmt.Sprintf("fetch('http://127.0.0.1:%d/event/%s',{method:'POST',mode:'no-cors',headers:{'Content-Type':'text/plain'},body:%s})", a.port, name, bodyExpr)
}

func (a *App) handle(name string, fn func(string)) {
	a.mu.Lock()
	a.initMaps()
	a.handlers[name] = fn
	a.mu.Unlock()
}

// OnKey: fn recibe {key, code, ctrl, shift, alt, meta}. Llamar antes de Run().
func (a *App) OnKey(fn func(e map[string]any)) {
	a.keyOn = true
	a.handle(a.ev("k"), func(p string) {
		var m map[string]any
		if json.Unmarshal([]byte(p), &m) == nil {
			fn(m)
		}
	})
}

// OnClose: fn devuelve false para cancelar el cierre. Llamar antes de Run().
func (a *App) OnClose(fn func() bool) {
	a.closeOn = true
	a.handle(a.ev("c"), func(string) {
		if fn() {
			a.EvalJS("__vspk.confirmClose()")
		} else {
			a.EvalJS("__vspk.cancelClose()")
		}
	})
}

func (a *App) dialog(kind, title string, fn func(path string)) {
	a.mu.Lock()
	a.cbCount++
	name := a.ev(fmt.Sprintf("d%d", a.cbCount))
	a.mu.Unlock()
	a.handle(name, func(p string) {
		var m struct {
			Path *string `json:"path"`
		}
		if json.Unmarshal([]byte(p), &m) == nil && m.Path != nil {
			fn(*m.Path)
		} else {
			fn("")
		}
	})
	a.EvalJS(fmt.Sprintf("__vspk.dialog({kind:%s,title:%s}).then(function(p){%s})",
		jsonStr(kind), jsonStr(title), a.postJS(name, "JSON.stringify({path:p})")))
}

// Diálogos nativos; fn recibe la ruta elegida ("" si se cancela).
func (a *App) PickFile(title string, fn func(path string))   { a.dialog("open", title, fn) }
func (a *App) SaveFile(title string, fn func(path string))   { a.dialog("save", title, fn) }
func (a *App) PickFolder(title string, fn func(path string)) { a.dialog("folder", title, fn) }

// ── Diálogos modales (mensaje / confirmación / pedir texto) ──────────────────

func (a *App) modal(call string, fn func(v any)) {
	a.mu.Lock()
	a.cbCount++
	name := a.ev(fmt.Sprintf("m%d", a.cbCount))
	a.mu.Unlock()
	a.handle(name, func(p string) {
		var m struct {
			V any `json:"v"`
		}
		_ = json.Unmarshal([]byte(p), &m)
		if fn != nil {
			fn(m.V)
		}
	})
	a.EvalJS(fmt.Sprintf("Promise.resolve(%s).then(function(v){%s})", call, a.postJS(name, "JSON.stringify({v:v})")))
}

// Message: diálogo modal con un botón Aceptar. fn (puede ser nil) se llama al cerrarlo.
func (a *App) Message(text string, fn func()) {
	a.modal("alert("+jsonStr(text)+")", func(any) {
		if fn != nil {
			fn()
		}
	})
}

// Confirm: modal Aceptar/Cancelar. fn(true|false).
func (a *App) Confirm(text string, fn func(ok bool)) {
	a.modal("confirm("+jsonStr(text)+")", func(v any) { b, _ := v.(bool); fn(b) })
}

// Prompt: modal que pide un texto. fn(texto, true) o fn("", false) si se cancela.
func (a *App) Prompt(text, def string, fn func(value string, ok bool)) {
	a.modal("prompt("+jsonStr(text)+","+jsonStr(def)+")", func(v any) { s, ok := v.(string); fn(s, ok) })
}

// ── Tabla, árbol, lista (se hidratan en la página; ver vspk_ui.js incrustado en vspk.exe) ──

// TableOpts: opciones de Table/Listbox/Tree. Los callbacks reciben el JSON del evento como map.
//
//	OnSelect: d["index"] (posición original), d["row"], d["indexes"], d["rows"]   (Tree: d["path"], d["label"], d["id"])
//	ID hace falta si luego vas a cambiar los datos con TableSet/TreeSet.
type TableOpts struct {
	ID                                string
	OnSelect, OnDblclick, OnSort      func(d map[string]any)
	NoSort, Multi, NoHeader, NoStripe bool
	Height                            string // p. ej. "240px": activa el scroll
}

// TreeNode: nodo de Tree.
type TreeNode struct {
	Label    string     `json:"label"`
	ID       any        `json:"id,omitempty"`
	Open     bool       `json:"open,omitempty"`
	Children []TreeNode `json:"children,omitempty"`
}

func (a *App) vtWidget(cls, prefix string, cfg map[string]any, o TableOpts) Widget {
	a.mu.Lock()
	a.vtCount++
	id := o.ID
	if id == "" {
		id = fmt.Sprintf("%s%d", prefix, a.vtCount)
	}
	a.mu.Unlock()
	b, _ := json.Marshal(cfg)
	w := &tag{t: "div", cls: cls, attrs: map[string]string{"id": id, "data-vt": string(b)}}
	if o.Height != "" && cls == "vspk-tree" {
		w.attrs["style"] = "max-height:" + o.Height
	}
	for attr, cb := range map[string]func(map[string]any){"data-on-select": o.OnSelect, "data-on-dblclick": o.OnDblclick, "data-on-sort": o.OnSort} {
		if cb == nil {
			continue
		}
		cb := cb
		a.mu.Lock()
		a.cbCount++
		name := a.ev(fmt.Sprintf("v%d", a.cbCount))
		a.mu.Unlock()
		a.handle(name, func(p string) {
			var m map[string]any
			if json.Unmarshal([]byte(p), &m) == nil {
				cb(m)
			}
		})
		w.attrs[attr] = a.postJS(name, "JSON.stringify(p)")
	}
	return w
}

// Table: tabla con orden por columna (clic en la cabecera) y selección.
//
//	app.Table([]string{"Nombre", "Edad"}, [][]any{{"Ana", 31}, {"Luis", 28}}, vspk.TableOpts{ID: "t", OnSelect: func(d map[string]any) { ... }})
func (a *App) Table(cols []string, rows [][]any, o TableOpts) Widget {
	cfg := map[string]any{"cols": cols, "rows": rows, "sortable": !o.NoSort, "multi": o.Multi, "striped": !o.NoStripe, "header": !o.NoHeader, "selected": -1}
	if o.Height != "" {
		cfg["height"] = o.Height
	}
	return a.vtWidget("vspk-table", "vt", cfg, o)
}

// Listbox: lista de una columna sin cabecera. OnSelect: d["row"].([]any)[0] es el elemento.
func (a *App) Listbox(items []string, o TableOpts) Widget {
	rows := make([][]any, len(items))
	for i, it := range items {
		rows[i] = []any{it}
	}
	cfg := map[string]any{"cols": []string{""}, "rows": rows, "sortable": false, "multi": false, "striped": false, "header": false, "selected": -1}
	if o.Height != "" {
		cfg["height"] = o.Height
	}
	return a.vtWidget("vspk-table", "vt", cfg, o)
}

// Tree: árbol de nodos. OnSelect: d["path"], d["label"], d["id"].
func (a *App) Tree(nodes []TreeNode, o TableOpts) Widget {
	return a.vtWidget("vspk-tree", "vtree", map[string]any{"nodes": nodes}, o)
}

func (a *App) TableSet(id string, rows [][]any, cols []string) {
	a.EvalJS(tableSetJS(id, rows, cols))
}
func tableSetJS(id string, rows [][]any, cols []string) string {
	rb, _ := json.Marshal(rows)
	cb, _ := json.Marshal(cols) // nil → null
	return "window.__vspk_table_set(" + jsonStr(id) + "," + string(cb) + "," + string(rb) + ")"
}
func (a *App) TableSelect(id string, index int) {
	a.EvalJS(fmt.Sprintf("window.__vspk_table_select(%s,%d)", jsonStr(id), index))
}
func (a *App) TableSort(id string, col int, desc bool) {
	d := 1
	if desc {
		d = -1
	}
	a.EvalJS(fmt.Sprintf("window.__vspk_table_sort(%s,%d,%d)", jsonStr(id), col, d))
}
func (a *App) TreeSet(id string, nodes []TreeNode) {
	nb, _ := json.Marshal(nodes)
	a.EvalJS("window.__vspk_tree_set(" + jsonStr(id) + "," + string(nb) + ")")
}

// Lo mismo en una ventana extra.
func (w *Win) TableSet(id string, rows [][]any, cols []string) { w.EvalJS(tableSetJS(id, rows, cols)) }
func (w *Win) TreeSet(id string, nodes []TreeNode) {
	nb, _ := json.Marshal(nodes)
	w.EvalJS("window.__vspk_tree_set(" + jsonStr(id) + "," + string(nb) + ")")
}

// ColorPicker / DatePicker enlazados a un State.
func ColorPicker(bind *State) Widget {
	w := Input("", bind).(*tag)
	w.attrs["type"] = "color"
	return w
}
func DatePicker(bind *State, withTime ...bool) Widget {
	w := Input("", bind).(*tag)
	w.attrs["type"] = "date"
	if len(withTime) > 0 && withTime[0] {
		w.attrs["type"] = "datetime-local"
	}
	return w
}

// Every ejecuta fn cada ms milisegundos mientras la ventana esté abierta.
func (a *App) Every(ms int, fn func()) {
	t := func() {
		tk := time.NewTicker(time.Duration(ms) * time.Millisecond)
		defer tk.Stop()
		for {
			select {
			case <-a.stop:
				return
			case <-tk.C:
				fn()
			}
		}
	}
	a.mu.Lock()
	a.timers = append(a.timers, t)
	run := a.running
	a.mu.Unlock()
	if run {
		go t()
	}
}

// After ejecuta fn una vez dentro de ms milisegundos.
func (a *App) After(ms int, fn func()) {
	t := func() {
		select {
		case <-a.stop:
		case <-time.After(time.Duration(ms) * time.Millisecond):
			fn()
		}
	}
	a.mu.Lock()
	a.timers = append(a.timers, t)
	run := a.running
	a.mu.Unlock()
	if run {
		go t()
	}
}

func (a *App) Notify(title, body string) {
	a.EvalJS(fmt.Sprintf("__vspk.notify(%s,%s)", jsonStr(title), jsonStr(body)))
}

func (a *App) SetTitle(title string) { a.EvalJS(fmt.Sprintf("__vspk.setTitle(%s)", jsonStr(title))) }
func (a *App) CopyText(text string) {
	a.EvalJS(fmt.Sprintf("__vspk.clipboard.write(%s)", jsonStr(text)))
}
func (a *App) Quit() { a.EvalJS("__vspk.close()") }

func jsonStr(s string) string {
	b, _ := json.Marshal(s)
	return string(b)
}

// ── Canvas ────────────────────────────────────────────────────────────────────
//
//	cv := app.Canvas("lienzo", 400, 300)
//	cv.Color("#6750A4"); cv.Rect(10, 10, 100, 60); cv.Circle(200, 60, 40); cv.Line(0, 0, 400, 300)
//	cv.Text(10, 280, "hola"); cv.Erase()
//	cv.OnMouse(func(e map[string]any) { ... }) // e["type"] = down|up|move|click, e["x"], e["y"], e["button"]

type Canvas struct {
	app  *App
	id   string
	w, h int
}

const cvJS = `window.__cv = function(id, op, a) {
  var c = document.getElementById(id); if (!c) return;
  var x = c.getContext('2d');
  if (op === 'clear') { x.clearRect(0, 0, c.width, c.height); }
  else if (op === 'color') { x.fillStyle = a[0]; x.strokeStyle = a[0]; }
  else if (op === 'lw') { x.lineWidth = a[0]; }
  else if (op === 'font') { x.font = a[0] + 'px sans-serif'; }
  else if (op === 'line') { x.beginPath(); x.moveTo(a[0], a[1]); x.lineTo(a[2], a[3]); x.stroke(); }
  else if (op === 'rect') { x.fillRect(a[0], a[1], a[2], a[3]); }
  else if (op === 'frame') { x.strokeRect(a[0], a[1], a[2], a[3]); }
  else if (op === 'circle') { x.beginPath(); x.arc(a[0], a[1], a[2], 0, 6.283185307); x.fill(); }
  else if (op === 'ring') { x.beginPath(); x.arc(a[0], a[1], a[2], 0, 6.283185307); x.stroke(); }
  else if (op === 'text') { x.fillText(a[2], a[0], a[1]); }
  else if (op === 'poly') { var p = a[0]; x.beginPath(); x.moveTo(p[0][0], p[0][1]); for (var i = 1; i < p.length; i++) x.lineTo(p[i][0], p[i][1]); x.closePath(); x.fill(); }
  else if (op === 'draw') { new Function('ctx', 'canvas', a[0])(x, c); }
};
`

func (a *App) cvScript() string {
	a.mu.Lock()
	defer a.mu.Unlock()
	var b strings.Builder
	b.WriteString("\n  " + cvJS)
	for _, id := range a.cvOrder {
		b.WriteString(a.cvLogs[id])
	}
	b.WriteString(a.cvMouseJs)
	return b.String()
}

func (a *App) Canvas(id string, w, h int) *Canvas {
	a.mu.Lock()
	if a.cvLogs == nil {
		a.cvLogs = map[string]string{}
	}
	a.cvLogs[id] = ""
	a.cvOrder = append(a.cvOrder, id)
	a.mu.Unlock()
	return &Canvas{app: a, id: id, w: w, h: h}
}

func (c *Canvas) Render() string {
	return fmt.Sprintf(`<canvas id="%s" width="%d" height="%d" style="width:%dpx;max-width:100%%;height:auto;border:1px solid rgba(128,128,128,.4);border-radius:8px;touch-action:none"></canvas>`,
		htmlEscape(c.id), c.w, c.h, c.w)
}

func (a *App) cv(id, op string, args ...any) {
	ab, _ := json.Marshal(args)
	js := fmt.Sprintf("__cv(%s,%s,%s)", jsonStr(id), jsonStr(op), string(ab))
	a.mu.Lock()
	if a.cvLogs == nil {
		a.cvLogs = map[string]string{}
	}
	if op == "clear" {
		a.cvLogs[id] = ""
	}
	a.cvLogs[id] += js + ";"
	run := a.running
	a.mu.Unlock()
	if run {
		a.evalTo("all", js)
	}
}

func (c *Canvas) Color(col string)            { c.app.cv(c.id, "color", col) }
func (c *Canvas) LineWidth(n float64)         { c.app.cv(c.id, "lw", n) }
func (c *Canvas) Font(size int)               { c.app.cv(c.id, "font", size) }
func (c *Canvas) Line(x1, y1, x2, y2 float64) { c.app.cv(c.id, "line", x1, y1, x2, y2) }
func (c *Canvas) Rect(x, y, w, h float64)     { c.app.cv(c.id, "rect", x, y, w, h) }
func (c *Canvas) Frame(x, y, w, h float64)    { c.app.cv(c.id, "frame", x, y, w, h) }
func (c *Canvas) Circle(x, y, r float64)      { c.app.cv(c.id, "circle", x, y, r) }
func (c *Canvas) Ring(x, y, r float64)        { c.app.cv(c.id, "ring", x, y, r) }
func (c *Canvas) Text(x, y float64, s string) { c.app.cv(c.id, "text", x, y, s) }

// Poly dibuja un polígono relleno con los puntos {x, y}.
func (c *Canvas) Poly(points [][2]float64) { c.app.cv(c.id, "poly", points) }
func (c *Canvas) Erase()                   { c.app.cv(c.id, "clear") }

// Draw ejecuta JS crudo con (ctx, canvas) en el ámbito.
func (c *Canvas) Draw(js string) { c.app.cv(c.id, "draw", js) }

func (c *Canvas) OnMouse(fn func(e map[string]any)) {
	a := c.app
	a.mu.Lock()
	a.cbCount++
	name := a.ev(fmt.Sprintf("m%d", a.cbCount))
	a.mu.Unlock()
	a.handle(name, func(p string) {
		var m map[string]any
		if json.Unmarshal([]byte(p), &m) == nil {
			fn(m)
		}
	})
	js := "(function(){var c=document.getElementById(" + jsonStr(c.id) + ");if(!c)return;function p(t,e){if(t==='move'){var n=Date.now();if(n-(c.__lm||0)<30)return;c.__lm=n;}var r=c.getBoundingClientRect();" +
		a.postJS(name, "JSON.stringify({type:t,x:Math.round((e.clientX-r.left)*c.width/r.width),y:Math.round((e.clientY-r.top)*c.height/r.height),button:e.button})") +
		"}['down','up','move','click'].forEach(function(t){c.addEventListener(t==='down'?'mousedown':t==='up'?'mouseup':t==='move'?'mousemove':'click',function(e){p(t,e)})})})();"
	a.mu.Lock()
	a.cvMouseJs += js
	run := a.running
	a.mu.Unlock()
	if run {
		a.evalTo("all", js)
	}
}

// ── Menús (barra de menú HTML con atajos de teclado) ─────────────────────────
//
//	app.Add(MenuBar(
//	    Menu("Archivo", MenuItem("Abrir...", app.OnClick(func() { ... }), "ctrl+o"), MenuSep(),
//	                    MenuItem("Salir", app.OnClick(func() { app.Quit() }))),
//	    Menu("Ayuda", MenuItem("Acerca de", app.OnClick(func() { ... }))),
//	), ...resto)
//
// Atajos: "ctrl+o", "ctrl+shift+s", "alt+x", "f5"... (orden: ctrl, shift, alt, tecla).

func MenuItem(label, js string, shortcut ...string) Widget {
	sc := ""
	if len(shortcut) > 0 {
		sc = shortcut[0]
	}
	kbd := ""
	if sc != "" {
		kbd = "<kbd>" + htmlEscape(sc) + "</kbd>"
	}
	return Raw(`<button type="button" class="sz-menu-item" onclick="` + strings.ReplaceAll(js, `"`, "&quot;") +
		`" data-accel="` + htmlEscape(sc) + `"><span>` + htmlEscape(label) + `</span>` + kbd + `</button>`)
}

func MenuSep() Widget { return Raw(`<div class="sz-menu-sep"></div>`) }

func Menu(title string, items ...Widget) Widget {
	var b strings.Builder
	for _, it := range items {
		b.WriteString(it.Render())
	}
	return Raw(`<div class="sz-menu"><button type="button" class="sz-menu-title">` + htmlEscape(title) +
		`</button><div class="sz-menu-list">` + b.String() + `</div></div>`)
}

const menuBarA = `<style>.sz-menubar{position:fixed;top:0;left:0;right:0;z-index:1000;display:flex;gap:2px;padding:3px 6px;background:var(--sz-surface,#fff);color:var(--sz-on-surface,#1d1b20);border-bottom:1px solid rgba(128,128,128,.3);font-size:14px}.sz-menubar-space{height:38px;width:100%;flex:none}.sz-menu{position:relative}.sz-menu-title{background:none;border:0;padding:6px 10px;border-radius:6px;color:inherit;font:inherit;cursor:pointer}.sz-menu-title:hover,.sz-menu.sz-open>.sz-menu-title{background:rgba(128,128,128,.18)}.sz-menu-list{display:none;position:absolute;top:100%;left:0;min-width:210px;padding:4px;background:var(--sz-surface,#fff);color:inherit;border:1px solid rgba(128,128,128,.35);border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.2)}.sz-menu.sz-open>.sz-menu-list{display:block}.sz-menu-item{display:flex;justify-content:space-between;gap:24px;width:100%;background:none;border:0;padding:6px 10px;border-radius:6px;color:inherit;font:inherit;cursor:pointer;text-align:left}.sz-menu-item:hover{background:rgba(128,128,128,.18)}.sz-menu-item kbd{opacity:.6;font:inherit;font-size:12px}.sz-menu-sep{height:1px;margin:4px 6px;background:rgba(128,128,128,.3)}.sz-native .sz-menubar,.sz-native .sz-menubar-space{display:none!important}</style><div class="sz-menubar">`
const menuBarB = `</div><div class="sz-menubar-space"></div><script>(function(){if(window.__menu)return;window.__menu=1;var bar=document.querySelector('.sz-menubar');function menus(){return bar.querySelectorAll(':scope > .sz-menu')}window.__vspk_menu_click=function(id){var p=id.split('.');var m=menus()[+p[0]];if(m)m.querySelector('.sz-menu-list').children[+p[1]].click()};window.__vspk_menu_ok=function(){document.documentElement.classList.add('sz-native')};if(bar&&window.ipc&&window.__vspk_native_menu_ok){var ms=[];Array.prototype.forEach.call(menus(),function(m,mi){var items=[];Array.prototype.forEach.call(m.querySelector('.sz-menu-list').children,function(c,ii){if(c.classList.contains('sz-menu-sep'))items.push({sep:true});else items.push({id:mi+'.'+ii,label:(c.querySelector('span')||c).textContent,accel:c.getAttribute('data-accel')||''})});ms.push({label:m.querySelector('.sz-menu-title').textContent,items:items})});window.ipc.postMessage(JSON.stringify({cmd:'setMenu',menu:ms}))}function closeAll(except){document.querySelectorAll('.sz-menu.sz-open').forEach(function(m){if(m!==except)m.classList.remove('sz-open')})}document.addEventListener('click',function(e){var t=e.target.closest?e.target.closest('.sz-menu-title'):null;closeAll(t?t.parentNode:null);if(t)t.parentNode.classList.toggle('sz-open');var it=e.target.closest?e.target.closest('.sz-menu-item'):null;if(it)closeAll(null)});document.addEventListener('mouseover',function(e){var t=e.target.closest?e.target.closest('.sz-menu-title'):null;var o=document.querySelector('.sz-menu.sz-open');if(t&&o&&o!==t.parentNode){closeAll(t.parentNode);t.parentNode.classList.add('sz-open')}});document.addEventListener('keydown',function(e){if(e.key==='Escape'){closeAll(null);return}if(document.documentElement.classList.contains('sz-native')&&!/Win/.test(navigator.platform))return;var k=(e.ctrlKey?'ctrl+':'')+(e.shiftKey?'shift+':'')+(e.altKey?'alt+':'')+e.key.toLowerCase();var items=document.querySelectorAll('.sz-menu-item[data-accel]');for(var i=0;i<items.length;i++){var a=items[i].getAttribute('data-accel');if(a&&a.toLowerCase()===k){e.preventDefault();items[i].click();return}}})})();</script>`

func MenuBar(menus ...Widget) Widget {
	var b strings.Builder
	for _, m := range menus {
		b.WriteString(m.Render())
	}
	return Raw(menuBarA + b.String() + menuBarB)
}

// ── Ventanas adicionales (otro proceso vspk que comparte el puente y los states) ──
//
//	aj := app.NewWindow("Ajustes", 360, 240)
//	aj.Add(Col(H4("Ajustes"), Input("Nombre", nombre)))   // los states se comparten entre ventanas
//	aj.Show(); aj.Close(); aj.OnClose(func() bool { return true }); aj.SetTitle("..."); aj.EvalJS("...")

type Win struct {
	app     *App
	id      string
	title   string
	w, h    int
	widgets []Widget
	want    bool
	closeOn bool
	closeJs string

	mu   sync.Mutex
	cmd  *exec.Cmd
	htv  string
	open bool
}

func (a *App) NewWindow(title string, width, height int) *Win {
	a.mu.Lock()
	defer a.mu.Unlock()
	w := &Win{app: a, id: fmt.Sprintf("w%d", len(a.wins)+1), title: title, w: width, h: height}
	a.wins = append(a.wins, w)
	return w
}

func (w *Win) Add(widgets ...Widget) *Win { w.widgets = append(w.widgets, widgets...); return w }
func (w *Win) Close()                     { w.app.evalTo(w.id, "__vspk.close()") }
func (w *Win) SetTitle(t string)          { w.app.evalTo(w.id, "__vspk.setTitle("+jsonStr(t)+")") }
func (w *Win) EvalJS(js string)           { w.app.evalTo(w.id, js) }

func (w *Win) IsOpen() bool {
	w.mu.Lock()
	defer w.mu.Unlock()
	return w.open
}

// Show abre la ventana (si ya está abierta no hace nada). Antes de Run() queda pendiente hasta que arranque.
func (w *Win) Show() {
	a := w.app
	a.mu.Lock()
	run := a.running
	a.mu.Unlock()
	if run {
		a.winOpen(w)
	} else {
		w.want = true
	}
}

// OnClose: fn devuelve false para cancelar el cierre. Llamar antes de Show().
func (w *Win) OnClose(fn func() bool) {
	a := w.app
	ev := a.ev("c" + w.id)
	w.closeOn = true
	w.closeJs = `window.addEventListener("vspk:closeRequested",function(){` + a.postJS(ev, `"{}"`) + `});`
	a.handle(ev, func(string) {
		if fn() {
			a.evalTo(w.id, "__vspk.confirmClose()")
		} else {
			a.evalTo(w.id, "__vspk.cancelClose()")
		}
	})
}

func (a *App) winOpen(w *Win) {
	w.mu.Lock()
	defer w.mu.Unlock()
	if w.open {
		return
	}
	if w.htv != "" {
		os.Remove(w.htv)
	}
	page := a.buildPage(w.title, w.widgets, w.id, false, w.closeJs)
	tb := make([]byte, 4)
	rand.Read(tb)
	w.htv = filepath.Join(os.TempDir(), fmt.Sprintf("vspk_%d_%s.htv", os.Getpid(), hex.EncodeToString(tb)))
	head := fmt.Sprintf("title: %s\nwidth: %d\nheight: %d\ndevtools: true\n", w.title, w.w, w.h)
	if ic := findIcon(); ic != "" {
		head += "icon: " + ic + "\n"
	}
	if w.closeOn {
		head += "on_close: confirm\n"
	}
	if err := os.WriteFile(w.htv, []byte(head+"\n"+page), 0o600); err != nil {
		vlogf("no se pudo escribir %s: %v\n", w.htv, err)
		return
	}
	cmd := exec.Command(a.vspkExe, w.htv)
	cmd.Stdout = os.Stdout
	if f := vlogFile(); f != nil {
		cmd.Stderr = f
	}
	if err := cmd.Start(); err != nil {
		vlogf("no se pudo abrir la ventana %s: %v\n", w.id, err)
		return
	}
	w.cmd = cmd
	w.open = true
	go func() {
		cmd.Wait()
		w.mu.Lock()
		w.open = false
		w.mu.Unlock()
	}()
}

// findIcon busca icon.ico/icon.png/favicon.* junto al ejecutable o en el directorio actual.
func findIcon() string {
	dirs := []string{}
	if wd, err := os.Getwd(); err == nil {
		dirs = append(dirs, wd)
	}
	if ex, err := os.Executable(); err == nil {
		dirs = append(dirs, filepath.Dir(ex))
	}
	for _, d := range dirs {
		for _, n := range []string{"icon.ico", "icon.png", "favicon.ico", "favicon.png"} {
			p := filepath.Join(d, n)
			if _, err := os.Stat(p); err == nil {
				return p
			}
		}
	}
	return ""
}
