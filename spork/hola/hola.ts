async function find_vspk() {
  let exe, from_env, beside_script, beside_lib, in_path;
  exe = (() => {
    if ((process.platform === "win32")) {
      return "vspk.exe";
    } else {
      return "vspk";
    }
  })();
  from_env = (process.env["VSPK_EXE"] ?? "");
  if (((from_env !== "") && (await Bun.file(from_env).exists()))) {
    return from_env;
  }
  beside_script = (await import('node:path')).join((await import('node:path')).dirname(import.meta.dir), exe);
  if ((await Bun.file(beside_script).exists())) {
    return beside_script;
  }
  beside_lib = (await import('node:path')).join(import.meta.dir, exe);
  if ((await Bun.file(beside_lib).exists())) {
    return beside_lib;
  }
  in_path = (await (async (__n) => { const { delimiter, join } = await import('node:path'); const __exts = process.platform === 'win32' ? ['', ...(process.env.PATHEXT ?? '.EXE;.CMD;.BAT;.COM').toLowerCase().split(';')] : ['']; for (const __d of (process.env.PATH ?? '').split(delimiter)) { if (!__d) continue; for (const __e of __exts) { const __p = join(__d, String(__n) + __e); if (await Bun.file(__p).exists()) return __p; } } return ''; })(exe));
  if ((in_path !== "")) {
    return in_path;
  }
  return exe;
}

function html_escape(s) {
  return s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll("\"", "&quot;");
}

function tag(t, css_class, attrs, ...kids) {
  let cls_attr, attrs_str, inner, _spk_void;
  cls_attr = (() => {
    if ((css_class !== "")) {
      return ` class=\"${css_class}\"`;
    } else {
      return "";
    }
  })();
  attrs_str = Object.entries(attrs).map((kv) => {
    let k, v;
    k = kv[0];
    v = kv[1];
    if ((((k === "onclick") || (k === "oninput")) || (k === "onchange"))) {
      return ` ${k}=\"${v.replaceAll("\"", "&quot;")}\"`;
    } else {
      return ` ${k}=\"${html_escape(v)}\"`;
    }
  }).join("");
  inner = kids.map((c) => {
    if (((((Array.isArray(c) ? 'array' : typeof c) === "hash") || ((Array.isArray(c) ? 'array' : typeof c) === "object")) && c.to_html)) {
      return c.to_html();
    } else {
      return `${c}`;
    }
  }).join("\n");
  _spk_void = (((t === "input") || (t === "hr")) || (t === "br"));
  if (_spk_void) {
    return `<${t}${cls_attr}${attrs_str}>`;
  } else if ((inner === "")) {
    return `<${t}${cls_attr}${attrs_str}></${t}>`;
  } else {
    return `<${t}${cls_attr}${attrs_str}>\n${inner}\n</${t}>`;
  }
}

function Row(...kids) {
  return tag("div", "sz-row", {  }, ...kids);
}

function Col(...kids) {
  return tag("div", "sz-col sz-center", {  }, ...kids);
}

function Card(...kids) {
  return tag("div", "sz-card", {  }, ...kids);
}

function Grid(...kids) {
  return tag("div", "sz-grid", {  }, ...kids);
}

function Hr() {
  return "<hr class=\"sz-divider\">";
}

function Spacer() {
  return "<div class=\"sz-grow\"></div>";
}

function H1(c) {
  return tag("h1", "sz-h1", {  }, c);
}

function H2(c) {
  return tag("h2", "sz-h2", {  }, c);
}

function H3(c) {
  return tag("h3", "sz-h3", {  }, c);
}

function H4(c) {
  return tag("h4", "sz-h4", {  }, c);
}

function P(c) {
  return tag("p", "sz-p", {  }, c);
}

function Label(c) {
  return tag("label", "sz-label", {  }, c);
}

function Badge(c) {
  return tag("span", "sz-badge", {  }, c);
}

function Chip(text, primary = false) {
  let css_class;
  css_class = (() => {
    if (primary) {
      return "sz-chip sz-chip-primary";
    } else {
      return "sz-chip";
    }
  })();
  return tag("span", css_class, {  }, text);
}

function Alert(c, variant = "") {
  let css_class;
  css_class = (() => {
    if ((variant !== "")) {
      return `sz-alert sz-alert-${variant}`;
    } else {
      return "sz-alert";
    }
  })();
  return tag("div", css_class, {  }, c);
}

function Button(text, js = "", variant = "filled", size = "") {
  let css_class, attrs;
  css_class = `sz-btn sz-btn-${variant}${(() => {
    if ((size !== "")) {
      return ` sz-btn-${size}`;
    } else {
      return "";
    }
  })()}`;
  attrs = (() => {
    if ((js !== "")) {
      return { "data-ripple": "", onclick: js };
    } else {
      return { "data-ripple": "" };
    }
  })();
  return tag("button", css_class, attrs, text);
}

function Input(placeholder = "", bind = null) {
  let attrs;
  attrs = { type: "text" };
  if ((placeholder !== "")) {
    attrs["placeholder"] = placeholder;
  }
  if ((bind !== null)) {
    attrs["data-spork-bind"] = bind.name;
    attrs["oninput"] = `window.__set('${bind.name}',this.value);window.__sync('${bind.name}',this.value)`;
  }
  return tag("input", "sz-input", attrs);
}

function Textarea(placeholder = "", rows = 4, bind = null) {
  let attrs;
  attrs = { rows: `${rows}` };
  if ((placeholder !== "")) {
    attrs["placeholder"] = placeholder;
  }
  if ((bind !== null)) {
    attrs["data-spork-bind"] = bind.name;
    attrs["oninput"] = `window.__set('${bind.name}',this.value);window.__sync('${bind.name}',this.value)`;
  }
  return tag("textarea", "sz-textarea", attrs);
}

function Checkbox(label_text, bind = null) {
  let attrs, chk, track, lbl;
  attrs = { type: "checkbox" };
  if ((bind !== null)) {
    attrs["data-spork-checked"] = bind.name;
    attrs["onchange"] = `window.__set('${bind.name}',this.checked);window.__sync('${bind.name}',this.checked)`;
  }
  chk = tag("input", "", attrs);
  track = "<span class=\"sz-switch-track\"><span class=\"sz-switch-thumb\"></span></span>";
  lbl = `<span class=\"sz-switch-label\">${label_text}</span>`;
  return tag("label", "sz-switch", {  }, chk, track, lbl);
}

function Select(options, bind = null) {
  let opts, attrs;
  opts = options.map((pair) => {
    let val, lbl;
    val = pair[0];
    lbl = pair[1];
    return `<option value=\"${html_escape(val)}\">${html_escape(lbl)}</option>`;
  }).join("\n");
  attrs = {  };
  if ((bind !== null)) {
    attrs["data-spork-bind"] = bind.name;
    attrs["onchange"] = `window.__set('${bind.name}',this.value);window.__sync('${bind.name}',this.value)`;
  }
  return `<select class=\"sz-select\"${Object.entries(attrs).map((kv) => ` ${kv[0]}=\"${kv[1]}\"`).join("")}>\n${opts}\n</select>`;
}

function Progress(state) {
  let style_expr;
  style_expr = html_escape(`{\"width\": window.__state.${state.name} + \"%\"}`);
  return `<div class=\"sz-progress\"><div class=\"sz-progress-bar\" data-spork-style=\"${style_expr}\"></div></div>`;
}

function Avatar(src, alt = "") {
  return `<img class=\"sz-avatar\" src=\"${html_escape(src)}\" alt=\"${html_escape(alt)}\">`;
}

function Divider() {
  return "<hr class=\"sz-divider\">";
}

function _push_sse(event, data) {
  return ((__t) => { const __e = new TextEncoder().encode(String(__t)); const __c = (globalThis.__vspkC ??= new Set()); for (const c of [...__c]) { try { c.enqueue(__e); } catch { __c.delete(c); } } return null; })(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
}

function _push_state(name, value) {
  _states[name] = value;
  return _push_sse("state", { name: name, value: value });
}

function state(name, initial) {
  _states[name] = initial;
  function to_html() {
    return `<span data-spork-text=\"${name}\"></span>`;
  }
  function js_get() {
    return `window.__state.${name}`;
  }
  function js_set(val) {
    return `window.__set('${name}',${JSON.stringify(val)})`;
  }
  function js_inc(by = 1) {
    return `window.__set('${name}',window.__state.${name}+${by})`;
  }
  function js_dec(by = 1) {
    return `window.__set('${name}',window.__state.${name}-${by})`;
  }
  function get() {
    return _states[name];
  }
  function set(val) {
    return _push_state(name, val);
  }
  function inc(by = 1) {
    return set((get() + by));
  }
  function dec(by = 1) {
    return set((get() - by));
  }
  return { name: name, to_html: to_html, js_get: js_get, js_set: js_set, js_inc: js_inc, js_dec: js_dec, get: get, set: set, inc: inc, dec: dec, __str__: () => to_html() };
}

function on_click(fn_cb) {
  let id;
  _cb_count = (_cb_count + 1);
  id = `cb_${_token}_${_cb_count}`;
  _callbacks[id] = fn_cb;
  return `fetch('http://127.0.0.1:${_port}/cb/${id}',{mode:'no-cors'})`;
}

function on_event(name, fn_cb) {
  _events[name] = fn_cb;
}

function _ev(name) {
  return `__${name}_${_token}`;
}

function _post_js(name, body_expr) {
  return `fetch('http://127.0.0.1:${_port}/event/${name}',{method:'POST',mode:'no-cors',headers:{'Content-Type':'text/plain'},body:${body_expr}})`;
}

function on_key(fn_cb) {
  _key_on = true;
  return on_event(_ev("k"), fn_cb);
}

function _safe_true(f) {
  try {
    return _call0(f);
  } catch (_e) {
    return true;
  }
}

function _call0(f) {
  let h;
  h = { f: f };
  return (h["f"])();
}

function _call1(f, a) {
  let h;
  h = { f: f };
  return (h["f"])(a);
}

function on_close(fn_cb) {
  _close_on = true;
  return on_event(_ev("c"), (d) => {
    let r;
    r = _safe_true(fn_cb);
    if ((r === false)) {
      eval_js("__vspk.cancelClose()");
    }
    if ((r !== false)) {
      eval_js("__vspk.confirmClose()");
    }
  });
}

function _dialog(kind, title, fn_cb) {
  let name;
  _cb_count = (_cb_count + 1);
  name = _ev(`d${_cb_count}`);
  on_event(name, (d) => _call1(fn_cb, d["path"]));
  return eval_js(`__vspk.dialog({kind:'${kind}',title:${JSON.stringify(title)}}).then(function(p){${_post_js(name, "JSON.stringify({path:p})")}})`);
}

function pick_file(title, fn_cb) {
  return _dialog("open", title, fn_cb);
}

function save_file(title, fn_cb) {
  return _dialog("save", title, fn_cb);
}

function pick_folder(title, fn_cb) {
  return _dialog("folder", title, fn_cb);
}

function _modal(call, kind, fn_cb) {
  let name;
  _cb_count = (_cb_count + 1);
  name = _ev(`m${_cb_count}`);
  on_event(name, (d) => {
    if ((fn_cb !== null)) {
      if ((kind === "message")) {
        _call0(fn_cb);
      }
      if ((kind === "confirm")) {
        _call1(fn_cb, (d["v"] === true));
      }
      if ((kind === "prompt")) {
        _call1(fn_cb, d["v"]);
      }
    }
  });
  return eval_js(`Promise.resolve(${call}).then(function(v){${_post_js(name, "JSON.stringify({v:v})")}})`);
}

function message(text, fn_cb) {
  return _modal(`alert(${JSON.stringify(text)})`, "message", fn_cb);
}

function confirm(text, fn_cb) {
  return _modal(`confirm(${JSON.stringify(text)})`, "confirm", fn_cb);
}

function prompt(text, fn_cb, default_value) {
  return _modal(`prompt(${JSON.stringify(text)},${JSON.stringify(default_value)})`, "prompt", fn_cb);
}

function _vt_ev(fn_cb) {
  let name;
  _cb_count = (_cb_count + 1);
  name = _ev(`v${_cb_count}`);
  on_event(name, (d) => _call1(fn_cb, d));
  return _post_js(name, "JSON.stringify(p)");
}

function _vt_attrs(el_id, cfg, on_select, on_dblclick, on_sort, style = "") {
  let attrs;
  attrs = { id: el_id, "data-vt": JSON.stringify(cfg) };
  if ((style !== "")) {
    attrs["style"] = style;
  }
  if ((on_select !== null)) {
    attrs["data-on-select"] = _vt_ev(on_select);
  }
  if ((on_dblclick !== null)) {
    attrs["data-on-dblclick"] = _vt_ev(on_dblclick);
  }
  if ((on_sort !== null)) {
    attrs["data-on-sort"] = _vt_ev(on_sort);
  }
  return attrs;
}

function _vt_id(prefix, el_id) {
  if ((el_id !== "")) {
    return el_id;
  }
  _vt_count = (_vt_count + 1);
  return `${prefix}${_vt_count}`;
}

function Table(cols, rows, on_select = null, on_dblclick = null, on_sort = null, sortable = true, multi = false, header = true, height = "", id = "") {
  let el_id, cfg;
  el_id = _vt_id("vt", id);
  cfg = { cols: cols, rows: rows, sortable: sortable, multi: multi, striped: true, header: header, selected: (-1) };
  if ((height !== "")) {
    cfg["height"] = height;
  }
  return tag("div", "vspk-table", _vt_attrs(el_id, cfg, on_select, on_dblclick, on_sort));
}

function Listbox(items, on_select = null, on_dblclick = null, height = "", id = "") {
  let rows, el_id, cfg;
  rows = items.map((x) => [x]);
  el_id = _vt_id("vt", id);
  cfg = { cols: [""], rows: rows, sortable: false, multi: false, striped: false, header: false, selected: (-1) };
  if ((height !== "")) {
    cfg["height"] = height;
  }
  return tag("div", "vspk-table", _vt_attrs(el_id, cfg, on_select, on_dblclick, null));
}

function Tree(nodes, on_select = null, on_dblclick = null, height = "", id = "") {
  let el_id, st;
  el_id = _vt_id("vtree", id);
  st = (() => {
    if ((height !== "")) {
      return `max-height:${height}`;
    } else {
      return "";
    }
  })();
  return tag("div", "vspk-tree", _vt_attrs(el_id, { nodes: nodes }, on_select, on_dblclick, null, st));
}

function table_set_js(el_id, rows, cols = null) {
  let c;
  c = (() => {
    if ((cols === null)) {
      return "null";
    } else {
      return JSON.stringify(cols);
    }
  })();
  return `window.__vspk_table_set(${JSON.stringify(el_id)},${c},${JSON.stringify(rows)})`;
}

function table_select_js(el_id, index) {
  return `window.__vspk_table_select(${JSON.stringify(el_id)},${index})`;
}

function table_sort_js(el_id, col, dir = 1) {
  return `window.__vspk_table_sort(${JSON.stringify(el_id)},${col},${dir})`;
}

function tree_set_js(el_id, nodes) {
  return `window.__vspk_tree_set(${JSON.stringify(el_id)},${JSON.stringify(nodes)})`;
}

function table_set(el_id, rows) {
  return eval_js(table_set_js(el_id, rows, null));
}

function table_set_cols(el_id, rows, cols) {
  return eval_js(table_set_js(el_id, rows, cols));
}

function table_select(el_id, index) {
  return eval_js(table_select_js(el_id, index));
}

function table_sort(el_id, col, dir) {
  return eval_js(table_sort_js(el_id, col, dir));
}

function tree_set(el_id, nodes) {
  return eval_js(tree_set_js(el_id, nodes));
}

function ColorPicker(bind) {
  return tag("input", "sz-input", { type: "color", "data-spork-bind": bind.name, oninput: `window.__set('${bind.name}',this.value);window.__sync('${bind.name}',this.value)` });
}

function DatePicker(bind, with_time = false) {
  let t;
  t = (() => {
    if (with_time) {
      return "datetime-local";
    } else {
      return "date";
    }
  })();
  return tag("input", "sz-input", { type: t, "data-spork-bind": bind.name, oninput: `window.__set('${bind.name}',this.value);window.__sync('${bind.name}',this.value)` });
}

function _timer(js_fn, ms, fn_cb) {
  let name, js;
  _cb_count = (_cb_count + 1);
  name = _ev(`t${_cb_count}`);
  on_event(name, (d) => _call0(fn_cb));
  js = `${js_fn}(function(){${_post_js(name, "'{}'")}},${ms})`;
  _timers.push(`${js}`);
  if (_running) {
    eval_js(js);
  }
  return true;
}

function run_every(ms, fn_cb) {
  return _timer("setInterval", ms, fn_cb);
}

function run_after(ms, fn_cb) {
  return _timer("setTimeout", ms, fn_cb);
}

function set_title(t) {
  return eval_js(`__vspk.setTitle(${JSON.stringify(t)})`);
}

function notify(title, body = "") {
  return eval_js(`__vspk.notify(${JSON.stringify(title)},${JSON.stringify(body)})`);
}

function copy_text(text) {
  return eval_js(`__vspk.clipboard.write(${JSON.stringify(text)})`);
}

function quit() {
  return eval_js("__vspk.close()");
}

function _cv_do(id, op, args) {
  let js;
  js = `__cv(${JSON.stringify(id)},${JSON.stringify(op)},${JSON.stringify(args)})`;
  if ((op === "clear")) {
    _cv_logs[id] = "";
  }
  _cv_logs[id] = `${_cv_logs[id]}${js};`;
  if (_running) {
    _push_sse("all", js);
  }
  return true;
}

function _cv_on_mouse(id, fn_cb) {
  let name, js;
  _cb_count = (_cb_count + 1);
  name = _ev(`m${_cb_count}`);
  on_event(name, fn_cb);
  js = `(function(){var c=document.getElementById('${id}');if(!c)return;function p(t,e){if(t==='move'){var n=Date.now();if(n-(c.__lm||0)<30)return;c.__lm=n;}var r=c.getBoundingClientRect();${_post_js(name, "JSON.stringify({type:t,x:Math.round((e.clientX-r.left)*c.width/r.width),y:Math.round((e.clientY-r.top)*c.height/r.height),button:e.button})")}}['down','up','move','click'].forEach(function(t){c.addEventListener(t==='down'?'mousedown':t==='up'?'mouseup':t==='move'?'mousemove':'click',function(e){p(t,e)})})})();`;
  _cv_mouse_js = (_cv_mouse_js + js);
  if (_running) {
    _push_sse("all", js);
  }
  return true;
}

function canvas(id, w, h) {
  _cv_logs[id] = "";
  _cv_ids.push(id);
  function to_html() {
    return `<canvas id=\"${((__a0) => (__a0))}\" width=\"${w}\" height=\"${h}\" style=\"width:${w}px;max-width:100%;height:auto;border:1px solid rgba(128,128,128,.4);border-radius:8px;touch-action:none\"></canvas>`;
  }
  function _color(c) {
    return _cv_do(((__a0) => (__a0)), "color", [c]);
  }
  function _line_width(n) {
    return _cv_do(((__a0) => (__a0)), "lw", [n]);
  }
  function _font(size) {
    return _cv_do(((__a0) => (__a0)), "font", [size]);
  }
  function _line(x1, y1, x2, y2) {
    return _cv_do(((__a0) => (__a0)), "line", [x1, y1, x2, y2]);
  }
  function _rect(x, y, rw, rh) {
    return _cv_do(((__a0) => (__a0)), "rect", [x, y, rw, rh]);
  }
  function _frame(x, y, rw, rh) {
    return _cv_do(((__a0) => (__a0)), "frame", [x, y, rw, rh]);
  }
  function _circle(x, y, r) {
    return _cv_do(((__a0) => (__a0)), "circle", [x, y, r]);
  }
  function _ring(x, y, r) {
    return _cv_do(((__a0) => (__a0)), "ring", [x, y, r]);
  }
  function _text(x, y, s) {
    return _cv_do(((__a0) => (__a0)), "text", [x, y, s]);
  }
  function _poly(points) {
    return _cv_do(((__a0) => (__a0)), "poly", [points]);
  }
  function _clear() {
    return _cv_do(((__a0) => (__a0)), "clear", []);
  }
  function _draw(js) {
    return _cv_do(((__a0) => (__a0)), "draw", [js]);
  }
  function _on_mouse(fn_cb) {
    return _cv_on_mouse(((__a0) => (__a0)), fn_cb);
  }
  return { to_html: to_html, color: _color, line_width: _line_width, font: _font, line: _line, rect: _rect, frame: _frame, circle: _circle, ring: _ring, text: _text, poly: _poly, erase: _clear, draw: _draw, on_mouse: _on_mouse, __str__: () => to_html() };
}

async function _win_open(info) {
  let p, page, close_line, htv_path;
  p = info["proc"];
  if ((p !== false)) {
    if ((!(p.exitCode !== null))) {
      return true;
    }
  }
  page = _page_html(info["title"], info["widgets"].join("\n"), `eval_${info["id"]}`, false, info["close_js"]);
  close_line = (() => {
    if (info["close_on"]) {
      return "on_close: confirm\n";
    } else {
      return "";
    }
  })();
  htv_path = (await (async()=>{const{tmpdir}=await import('node:os');const{join}=await import('node:path');return join(tmpdir(), ("vspk_"??'')+Math.random().toString(36).slice(2)+(".htv"??''))})());
  (await Bun.write(htv_path, ((__v) => (typeof __v === 'string' || ArrayBuffer.isView(__v) || __v instanceof ArrayBuffer || __v instanceof Blob) ? __v : String(__v))(`title: ${info["title"]}\nwidth: ${info["w"]}\nheight: ${info["h"]}\ndevtools: true\n${_icon_line}${close_line}\n${page}`)));
  info["htv"] = htv_path;
  info["proc"] = (Bun.spawn([(await find_vspk()), htv_path], { stdin: 'inherit', stdout: 'inherit', stderr: 'inherit' }));
  return true;
}

function _win_eval(info, js) {
  return _push_sse(`eval_${info["id"]}`, js);
}

async function _win_show(info) {
  if (_running) {
    (await _win_open(info));
  }
  if ((!_running)) {
    info["want"] = true;
  }
  return true;
}

function _win_on_close(info, fn_cb) {
  let ev;
  ev = _ev(`c${info["id"]}`);
  info["close_on"] = true;
  info["close_js"] = `window.addEventListener('vspk:closeRequested',function(){${_post_js(ev, "'{}'")}});`;
  on_event(ev, (d) => {
    let r;
    r = _safe_true(fn_cb);
    if ((r === false)) {
      _win_eval(info, "__vspk.cancelClose()");
    }
    if ((r !== false)) {
      _win_eval(info, "__vspk.confirmClose()");
    }
  });
  return true;
}

function _win_add(info, w1, w2, w3, w4) {
  let w;
  for (w of [w1, w2, w3, w4]) {
    if ((w !== "")) {
      info["widgets"].push(`${w}`);
    }
  }
  return true;
}

function window(title, width = 480, height = 360) {
  let info;
  _win_count = (_win_count + 1);
  info = { id: `w${_win_count}`, title: title, w: width, h: height, widgets: [], proc: false, htv: "", want: false, close_on: false, close_js: "" };
  _wins.push(info);
  function _add(a = "", b = "", c = "", d = "") {
    return _win_add(info, a, b, c, d);
  }
  async function _show() {
    return (await _win_show(info));
  }
  function _close() {
    return _win_eval(info, "__vspk.close()");
  }
  function _set_title(t) {
    return _win_eval(info, `__vspk.setTitle(${JSON.stringify(t)})`);
  }
  function _eval_js(js) {
    return _win_eval(info, js);
  }
  function _on_close(fn_cb) {
    return _win_on_close(info, fn_cb);
  }
  function _is_open() {
    return _win_is_open(info);
  }
  return { add: _add, show: _show, close: _close, set_title: _set_title, eval_js: _eval_js, on_close: _on_close, is_open: _is_open };
}

function _win_is_open(info) {
  let p;
  p = info["proc"];
  if ((p === false)) {
    return false;
  }
  return (!(p.exitCode !== null));
}

function MenuItem(label, js = "", shortcut = "") {
  let click, kbd;
  click = js.replaceAll("\"", "&quot;");
  kbd = (() => {
    if ((shortcut !== "")) {
      return `<kbd>${html_escape(shortcut)}</kbd>`;
    } else {
      return "";
    }
  })();
  return `<button type=\"button\" class=\"sz-menu-item\" onclick=\"${click}\" data-accel=\"${html_escape(shortcut)}\"><span>${html_escape(label)}</span>${kbd}</button>`;
}

function MenuSep() {
  return "<div class=\"sz-menu-sep\"></div>";
}

function Menu(title, ...items) {
  return `<div class=\"sz-menu\"><button type=\"button\" class=\"sz-menu-title\">${html_escape(title)}</button><div class=\"sz-menu-list\">${items.join("")}</div></div>`;
}

function MenuBar(...menus) {
  return `<style>.sz-menubar{position:fixed;top:0;left:0;right:0;z-index:1000;display:flex;gap:2px;padding:3px 6px;background:var(--sz-surface,#fff);color:var(--sz-on-surface,#1d1b20);border-bottom:1px solid rgba(128,128,128,.3);font-size:14px}.sz-menubar-space{height:38px;width:100%;flex:none}.sz-menu{position:relative}.sz-menu-title{background:none;border:0;padding:6px 10px;border-radius:6px;color:inherit;font:inherit;cursor:pointer}.sz-menu-title:hover,.sz-menu.sz-open>.sz-menu-title{background:rgba(128,128,128,.18)}.sz-menu-list{display:none;position:absolute;top:100%;left:0;min-width:210px;padding:4px;background:var(--sz-surface,#fff);color:inherit;border:1px solid rgba(128,128,128,.35);border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.2)}.sz-menu.sz-open>.sz-menu-list{display:block}.sz-menu-item{display:flex;justify-content:space-between;gap:24px;width:100%;background:none;border:0;padding:6px 10px;border-radius:6px;color:inherit;font:inherit;cursor:pointer;text-align:left}.sz-menu-item:hover{background:rgba(128,128,128,.18)}.sz-menu-item kbd{opacity:.6;font:inherit;font-size:12px}.sz-menu-sep{height:1px;margin:4px 6px;background:rgba(128,128,128,.3)}.sz-native .sz-menubar,.sz-native .sz-menubar-space{display:none!important}</style><div class=\"sz-menubar\">${menus.join("")}</div><div class=\"sz-menubar-space\"></div><script>(function(){if(window.__menu)return;window.__menu=1;var bar=document.querySelector('.sz-menubar');function menus(){return bar.querySelectorAll(':scope > .sz-menu')}window.__vspk_menu_click=function(id){var p=id.split('.');var m=menus()[+p[0]];if(m)m.querySelector('.sz-menu-list').children[+p[1]].click()};window.__vspk_menu_ok=function(){document.documentElement.classList.add('sz-native')};if(bar&&window.ipc&&window.__vspk_native_menu_ok){var ms=[];Array.prototype.forEach.call(menus(),function(m,mi){var items=[];Array.prototype.forEach.call(m.querySelector('.sz-menu-list').children,function(c,ii){if(c.classList.contains('sz-menu-sep'))items.push({sep:true});else items.push({id:mi+'.'+ii,label:(c.querySelector('span')||c).textContent,accel:c.getAttribute('data-accel')||''})});ms.push({label:m.querySelector('.sz-menu-title').textContent,items:items})});window.ipc.postMessage(JSON.stringify({cmd:'setMenu',menu:ms}))}function closeAll(except){document.querySelectorAll('.sz-menu.sz-open').forEach(function(m){if(m!==except)m.classList.remove('sz-open')})}document.addEventListener('click',function(e){var t=e.target.closest?e.target.closest('.sz-menu-title'):null;closeAll(t?t.parentNode:null);if(t)t.parentNode.classList.toggle('sz-open');var it=e.target.closest?e.target.closest('.sz-menu-item'):null;if(it)closeAll(null)});document.addEventListener('mouseover',function(e){var t=e.target.closest?e.target.closest('.sz-menu-title'):null;var o=document.querySelector('.sz-menu.sz-open');if(t&&o&&o!==t.parentNode){closeAll(t.parentNode);t.parentNode.classList.add('sz-open')}});document.addEventListener('keydown',function(e){if(e.key==='Escape'){closeAll(null);return}if(document.documentElement.classList.contains('sz-native')&&!/Win/.test(navigator.platform))return;var k=(e.ctrlKey?'ctrl+':'')+(e.shiftKey?'shift+':'')+(e.altKey?'alt+':'')+e.key.toLowerCase();var items=document.querySelectorAll('.sz-menu-item[data-accel]');for(var i=0;i<items.length;i++){var a=items[i].getAttribute('data-accel');if(a&&a.toLowerCase()===k){e.preventDefault();items[i].click();return}}})})();</script>`;
}

function add(...ws) {
  let w;
  for (w of ws) {
    _widgets.push(`${w}`);
  }
}

function eval_js(js) {
  return _push_sse("eval", js);
}

function _build_html() {
  return _page_html(_title, _widgets.join("\n"), "eval", true, "");
}

function _page_html(title, body_html, eval_ev, is_main, child_close_js) {
  let state_json, key_js, main_close_js, close_js, timers_js, cv_js, accent_style;
  state_json = JSON.stringify(_states);
  key_js = (() => {
    if ((_key_on && is_main)) {
      return `document.addEventListener('keydown',function(e){${_post_js(_ev("k"), "JSON.stringify({key:e.key,code:e.code,ctrl:e.ctrlKey,shift:e.shiftKey,alt:e.altKey,meta:e.metaKey})")}});`;
    } else {
      return "";
    }
  })();
  main_close_js = (() => {
    if ((_close_on && is_main)) {
      return `window.addEventListener('vspk:closeRequested',function(){${_post_js(_ev("c"), "'{}'")}});`;
    } else {
      return "";
    }
  })();
  close_js = (main_close_js + child_close_js);
  timers_js = (() => {
    if (is_main) {
      return (_timers.join(";") + ";");
    } else {
      return "";
    }
  })();
  cv_js = `${_cv_ids.map((i) => _cv_logs[i]).join("")}${_cv_mouse_js}`;
  accent_style = (() => {
    if ((_accent !== "")) {
      return `<style>:root{--sz-accent:${_accent};} .sz-btn-filled{background:${_accent};border-color:${_accent};}</style>`;
    } else {
      return "";
    }
  })();
  return `<!DOCTYPE html>
  <html data-theme=\"${_theme}\">
  <head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>${html_escape(title)}</title>
    <link rel=\"icon\" href=\"data:,\">
    <link rel=\"stylesheet\" href=\"${SPORK_CSS}\" onerror=\"this.onerror=null;this.href='${SPORK_CSS_CDN}'\">
    ${accent_style}
  </head>
  <body class=\"sz-body\">

  <div id=\"__app\" class=\"sz-page\">
  ${body_html}
  </div>

  <script>
  window.__state = ${state_json};
  window.__win = '${eval_ev}';

  window.__set = function(name, value) {
    window.__state[name] = value;
    document.querySelectorAll('[data-spork-text=\"' + name + '\"]').forEach(function(el) {
      el.textContent = value;
    });
    document.querySelectorAll('[data-spork-bind=\"' + name + '\"]').forEach(function(el) {
      if (el.type === 'checkbox') el.checked = value;
      else el.value = value;
    });
    document.querySelectorAll('[data-spork-style]').forEach(function(el) {
      try { Object.assign(el.style, new Function('return (' + el.dataset.sporkStyle + ')')()) } catch(_){}
    });
    document.querySelectorAll('[data-spork-if]').forEach(function(el) {
      try { el.style.display = new Function('return !!(' + el.dataset.sporkIf + ')')() ? '' : 'none' } catch(_){}
    });
    document.querySelectorAll('[data-spork-checked=\"' + name + '\"]').forEach(function(el) {
      el.checked = !!value;
    });
  };

  // Envía a Spork el valor que el usuario escribe/elige, para que state.get() lo vea
  // (los widgets enlazados solo actualizaban la página). POST simple (text/plain, no-cors).
  window.__sync = function(n, v) {
    try {
      fetch('http://127.0.0.1:${_port}/event/${_ev("v")}', {method: 'POST', mode: 'no-cors', headers: {'Content-Type': 'text/plain'}, body: JSON.stringify({n: n, v: v, w: window.__win})});
    } catch(_) {}
  };

  window.__cv = function(id, op, a) {
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
  Object.keys(window.__state).forEach(function(k) { window.__set(k, window.__state[k]); });
  ${key_js}
  ${close_js}
  ${timers_js}
  ${cv_js}

  (function connectSSE() {
    var es = new EventSource('http://127.0.0.1:${_port}/events');
    es.addEventListener('state', function(e) {
      var d = JSON.parse(e.data);
      if (d.src && d.src === window.__win) return;
      window.__set(d.name, d.value);
    });
    ['${eval_ev}', 'all'].forEach(function(n) {
      es.addEventListener(n, function(e) {
        try { eval(JSON.parse(e.data)); } catch(err) { console.error(err); }
      });
    });
    es.onerror = function() {
      es.close();
      setTimeout(connectSSE, 1000);
    };
  })();
  </script>
  <script src=\"${SPORK_JS}\" onerror=\"var s=document.createElement('script');s.src='${SPORK_JS_CDN}';document.body.appendChild(s)\"></script>
  </body>
  </html>`;
}

function App(title, width = 1024, height = 768, theme = "light", accent = "") {
  _title = title;
  _width = width;
  _height = height;
  _theme = theme;
  _accent = accent;
  _port = (Math.floor((Math.random() * 10000)) + 20000);
  _token = ((String(Math.trunc(Number((Math.random() * 1000000000)))) + String(Math.trunc(Number((Math.random() * 1000000000))))) + String(Math.trunc(Number((Math.random() * 1000000000)))));
  return { state: state, canvas: canvas, window: window, add: add, on_click: on_click, on_event: on_event, eval_js: eval_js, run: run, on_key: on_key, on_close: on_close, pick_file: pick_file, save_file: save_file, pick_folder: pick_folder, run_every: run_every, run_after: run_after, set_title: set_title, notify: notify, copy_text: copy_text, quit: quit, message: message, confirm: confirm, prompt: prompt, table_set: table_set, table_set_cols: table_set_cols, table_select: table_select, table_sort: table_sort, tree_set: tree_set };
}

async function run() {
  let _vspk_exe, html, icon_dirs, icon_names, icon_path, dir, name, candidate, icon_line, close_line, htv_content, htv_path, proc, info, data, is_value, key, src, hp;
  _vspk_exe = (await find_vspk());
  ((__p) => { const __q = (globalThis.__vspkQ ??= []); const __c = (globalThis.__vspkC ??= new Set()); const __enc = new TextEncoder(); const __cors = { 'Access-Control-Allow-Origin': '*' };
      globalThis.__vspkSrv = Bun.serve({ port: Number(__p), hostname: '0.0.0.0', idleTimeout: 0, async fetch(req) {
        const u = new URL(req.url);
        if (req.method === 'GET' && u.pathname === '/events') { let ctl; return new Response(new ReadableStream({ start(c) { ctl = c; __c.add(c); c.enqueue(__enc.encode(': ok\n\n')); }, cancel() { __c.delete(ctl); } }), { headers: { 'Content-Type': 'text/event-stream', 'Cache-Control': 'no-cache', ...__cors } }); }
        if (req.method === 'GET' && u.pathname.startsWith('/cb/')) { __q.push({ kind: 'cb', id: u.pathname.slice(4) }); return new Response('ok', { headers: __cors }); }
        if (req.method === 'POST' && u.pathname.startsWith('/event/')) { __q.push({ kind: 'event', name: u.pathname.slice(7), body: await req.text() }); return new Response('ok', { headers: __cors }); }
        if (u.pathname === '/favicon.ico') return new Response('', { status: 204 });
        return new Response('Not found', { status: 404 });
      } }); globalThis.__vspkSrv.unref(); return null; })(_port);
  html = _build_html();
  icon_dirs = [(await import('node:path')).dirname(import.meta.dir), import.meta.dir];
  icon_names = ["icon.ico", "icon.png", "favicon.ico", "favicon.png"];
  icon_path = "";
  for (dir of icon_dirs) {
    for (name of icon_names) {
      if ((icon_path === "")) {
        candidate = (await import('node:path')).join(dir, name);
        if ((await Bun.file(candidate).exists())) {
          icon_path = candidate;
        }
      }
    }
  }
  icon_line = (() => {
    if ((icon_path !== "")) {
      return `icon: ${icon_path}\n`;
    } else {
      return "";
    }
  })();
  close_line = (() => {
    if (_close_on) {
      return "on_close: confirm\n";
    } else {
      return "";
    }
  })();
  htv_content = `title: ${_title}\nwidth: ${_width}\nheight: ${_height}\ndevtools: true\n${icon_line}${close_line}\n${html}`;
  _icon_line = `${icon_line}`;
  htv_path = (await (async()=>{const{tmpdir}=await import('node:os');const{join}=await import('node:path');return join(tmpdir(), ("vspk_"??'')+Math.random().toString(36).slice(2)+(".htv"??''))})());
  (await Bun.write(htv_path, ((__v) => (typeof __v === 'string' || ArrayBuffer.isView(__v) || __v instanceof ArrayBuffer || __v instanceof Blob) ? __v : String(__v))(htv_content)));
  proc = (Bun.spawn([_vspk_exe, htv_path], { stdin: 'inherit', stdout: 'inherit', stderr: 'inherit' }));
  _running = true;
  for (info of _wins) {
    if (info["want"]) {
      (await _win_open(info));
    }
  }
  while ((!(proc.exitCode !== null))) {
    msg = ((globalThis.__vspkQ ??= []).shift() ?? null);
    if ((msg !== null)) {
      if ((msg.kind === "cb")) {
        if (((__o, __k) => __o != null && typeof __o === 'object' && !Array.isArray(__o) && Object.hasOwn(__o, __k))(_callbacks, msg.id)) {
          try {
            (_callbacks[msg.id])();
          } catch (_e) {

          }
        }
      } else if ((msg.kind === "event")) {
        data = (() => {
          try {
            return (JSON.parse(msg.body));
          } catch (_e) {
            return null;
          }
        })();
        is_value = (msg.name === _ev("v"));
        if ((is_value && (data !== null))) {
          key = String(data["n"]);
          _states[key] = data["v"];
          if (((typeof _wins === 'string' || Array.isArray(_wins) ? _wins.length : _wins == null ? 0 : typeof _wins === 'object' ? Object.keys(_wins).length : String(_wins).length) > 0)) {
            src = "";
            if (((__o, __k) => __o != null && typeof __o === 'object' && !Array.isArray(__o) && Object.hasOwn(__o, __k))(data, "w")) {
              src = `${data["w"]}`;
            }
            _push_sse("state", { name: key, value: data["v"], src: src });
          }
        }
        if (((!is_value) && ((__o, __k) => __o != null && typeof __o === 'object' && !Array.isArray(__o) && Object.hasOwn(__o, __k))(_events, msg.name))) {
          try {
            (_events[msg.name])(data);
          } catch (_e) {

          }
        }
      }
    }
    (await Bun.sleep(15));
  }
  for (info of _wins) {
    if ((_win_is_open(info) === true)) {
      _win_eval(info, "__vspk.close()");
    }
  }
  (await Bun.sleep(300));
  for (info of _wins) {
    hp = `${info["htv"]}`;
    if ((hp !== "")) {
      (await (async()=>{const{unlink}=await import('node:fs/promises');await unlink(hp)})());
    }
  }
  return (await (async()=>{const{unlink}=await import('node:fs/promises');await unlink(htv_path)})());
}

var SPORK_CSS = "spork.css";

var SPORK_JS = "spork.js";

var SPORK_CSS_CDN = "https://cdn.jsdelivr.net/gh/unoudos/spork-ui@main/spork.css";

var SPORK_JS_CDN = "https://cdn.jsdelivr.net/gh/unoudos/spork-ui@main/spork.js";

var _states = {  };

var _widgets = [];

var _callbacks = {  };

var _events = {  };

var _cb_count = 0;

var _port = 0;

var _title = "";

var _width = 1024;

var _height = 768;

var _theme = "light";

var _accent = "";

var _token = "";

var _key_on = false;

var _close_on = false;

var _running = false;

var _icon_line = "";

var _timers = [];

var _cv_ids = [];

var _wins = [];

var _win_count = 0;

var _cv_logs = {  };

var _cv_mouse_js = "";

var _vt_count = 0;

var gui = App("Hola Mundo", 400, 300);

var msg = ((typeof gui === 'object' && gui !== null && !Array.isArray(gui) && typeof gui.state === 'function') ? gui.state("msg", "Pulsa el boton") : state(gui, "msg", "Pulsa el boton"));

((typeof gui === 'object' && gui !== null && !Array.isArray(gui) && typeof gui.add === 'function') ? gui.add(Card(H1("Hola Mundo"), P(msg), Button("Saludar", ((typeof gui === 'object' && gui !== null && !Array.isArray(gui) && typeof gui.on_click === 'function') ? gui.on_click(() => msg.set("Hola desde Spork!")) : on_click(gui, () => msg.set("Hola desde Spork!")))))) : add(gui, Card(H1("Hola Mundo"), P(msg), Button("Saludar", ((typeof gui === 'object' && gui !== null && !Array.isArray(gui) && typeof gui.on_click === 'function') ? gui.on_click(() => msg.set("Hola desde Spork!")) : on_click(gui, () => msg.set("Hola desde Spork!")))))));

((typeof gui === 'object' && gui !== null && !Array.isArray(gui) && typeof gui.run === 'function') ? (await gui.run()) : (await run(gui)));

