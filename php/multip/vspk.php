<?php
declare(strict_types=1);

namespace Vspk;

// vspk.php — GUI nativa para PHP usando vspk (WebView) como ventana.
//
// Igual que vspk.spk / vspk.go: el programa PHP abre un puente HTTP+SSE en 127.0.0.1 (puerto
// aleatorio, en el mismo proceso, sin segundo `php -S`), escribe un .htv temporal y lanza vspk.exe.
// Mientras la ventana está abierta, run() atiende los clics (/cb/<id>), los eventos (/event/<nombre>)
// y los valores que el usuario escribe en los campos (/event/__v), y empuja cambios de estado por SSE.
// spork.css y spork.js los sirve el propio vspk.exe (van incrustados), no hace falta CDN.
//
//   $app   = new Vspk\App('Mi app', 520, 720);
//   $n     = $app->state('n', 0);
//   $nombre= $app->state('nombre', '');
//   $app->add(
//       Vspk\Card(
//           Vspk\H2('Hola'),
//           Vspk\Row($app->Button('+', fn() => $n->inc()), Vspk\H3($n)),
//           Vspk\Input('Tu nombre', $nombre),
//           $app->Button('Enviar', fn() => $n->set('Hola ' . $nombre->get())),
//       )
//   );
//   $app->run();

function findVspk(): string
{
    $exe   = PHP_OS_FAMILY === 'Windows' ? 'vspk.exe' : 'vspk';
    $ds    = DIRECTORY_SEPARATOR;
    $dirs  = [];
    $script = $_SERVER['SCRIPT_FILENAME'] ?? '';
    if ($script !== '') {
        $sd = dirname((string)(realpath($script) ?: $script));
        $dirs[] = dirname($sd);   // vspk.exe junto a la carpeta del script (igual que vspk.spk)
        $dirs[] = $sd;
    }
    $dirs[] = dirname(__DIR__);
    $dirs[] = __DIR__;
    $dirs[] = (string)getcwd();

    $paths = [];
    $env = getenv('VSPK_EXE');
    if ($env !== false && $env !== '') $paths[] = $env;
    foreach ($dirs as $d) $paths[] = rtrim($d, '/\\') . $ds . $exe;
    foreach (explode(PHP_OS_FAMILY === 'Windows' ? ';' : ':', (string)getenv('PATH')) as $d) {
        if ($d !== '') $paths[] = rtrim($d, '/\\') . $ds . $exe;
    }
    foreach ($paths as $p) {
        if (is_file($p)) return $p;
    }
    throw new \RuntimeException(
        "[vspk.php] No se encontró {$exe}.\n"
        . "  1. Ponlo junto a tu script PHP (o en la carpeta superior)\n"
        . "  2. Añade vspk al PATH\n"
        . "  3. Define VSPK_EXE=/ruta/{$exe}"
    );
}

function jsonJs(mixed $v): string
{
    // JSON seguro para incrustar en <script> y en atributos
    return (string)json_encode($v, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_PARTIAL_OUTPUT_ON_ERROR);
}

function h(string $s): string
{
    return htmlspecialchars($s, ENT_QUOTES, 'UTF-8');
}

// ── Puente HTTP + SSE (en el mismo proceso, sin hilos) ────────────────────────
//
// Un solo socket de escucha no bloqueante; run() llama a pump() en bucle. Las peticiones normales se
// responden y se cierran; /events queda abierto (SSE) y recibe los cambios de estado.

final class Bridge
{
    public int $port;
    /** @var resource */
    private $server;
    /** @var array<int, array{sock: resource, buf: string, sse: bool}> */
    private array $clients = [];
    /** @var list<array<string, mixed>> */
    private array $queue = [];
    private float $lastPing;

    public function __construct()
    {
        $srv = @stream_socket_server('tcp://127.0.0.1:0', $errno, $errstr);
        if ($srv === false) throw new \RuntimeException("[vspk.php] No se pudo abrir el puente: {$errstr}");
        $this->server = $srv;
        stream_set_blocking($srv, false);
        $name = (string)stream_socket_get_name($srv, false);
        $this->port = (int)substr((string)strrchr($name, ':'), 1);
        $this->lastPing = microtime(true);
    }

    public function pump(float $timeout): void
    {
        $read = [$this->server];
        foreach ($this->clients as $c) $read[] = $c['sock'];
        $w = $e = null;
        $sec = (int)$timeout;
        $usec = (int)(($timeout - $sec) * 1_000_000);
        if (@stream_select($read, $w, $e, $sec, $usec) === false) return;

        foreach ($read as $s) {
            if ($s === $this->server) {
                while (($c = @stream_socket_accept($this->server, 0)) !== false) {
                    stream_set_blocking($c, false);
                    $this->clients[(int)$c] = ['sock' => $c, 'buf' => '', 'sse' => false];
                }
            } else {
                $this->readClient($s);
            }
        }

        if (microtime(true) - $this->lastPing > 15) {   // evita que el WebView corte el SSE por inactividad
            $this->lastPing = microtime(true);
            $this->writeSse(": ping\n\n");
        }
    }

    public function poll(): ?array
    {
        return array_shift($this->queue);
    }

    /** Empuja un evento SSE a todas las ventanas conectadas. */
    public function push(string $event, mixed $data): void
    {
        $this->writeSse("event: {$event}\ndata: " . json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PARTIAL_OUTPUT_ON_ERROR) . "\n\n");
    }

    public function close(): void
    {
        foreach ($this->clients as $c) @fclose($c['sock']);
        $this->clients = [];
        if (is_resource($this->server)) @fclose($this->server);
    }

    private function writeSse(string $msg): void
    {
        foreach ($this->clients as $id => $c) {
            if (!$c['sse']) continue;
            $n = @fwrite($c['sock'], $msg);
            if ($n === false || ($n === 0 && $msg !== '')) $this->drop($id);
        }
    }

    private function drop(int $id): void
    {
        if (isset($this->clients[$id])) {
            @fclose($this->clients[$id]['sock']);
            unset($this->clients[$id]);
        }
    }

    private function readClient($sock): void
    {
        $id = (int)$sock;
        if (!isset($this->clients[$id])) return;
        $data = @fread($sock, 65536);
        if ($data === false || ($data === '' && feof($sock))) { $this->drop($id); return; }
        if ($this->clients[$id]['sse']) return;     // los clientes SSE no envían nada útil
        $this->clients[$id]['buf'] .= $data;
        $buf = $this->clients[$id]['buf'];

        $end = strpos($buf, "\r\n\r\n");
        if ($end === false) {
            if (strlen($buf) > 1_000_000) $this->drop($id);
            return;
        }
        $head = substr($buf, 0, $end);
        $lines = explode("\r\n", $head);
        [$method, $path] = array_pad(explode(' ', $lines[0], 3), 2, '');
        $len = 0;
        foreach ($lines as $l) {
            if (stripos($l, 'content-length:') === 0) $len = (int)trim(substr($l, 15));
        }
        $body = substr($buf, $end + 4);
        if (strlen($body) < $len) return;           // falta cuerpo
        $body = substr($body, 0, $len);
        $path = explode('?', $path, 2)[0];

        if ($method === 'OPTIONS') {
            $this->respond($id, 204, '');
        } elseif ($method === 'GET' && $path === '/events') {
            @fwrite($sock, "HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\nCache-Control: no-cache\r\n"
                . "Connection: keep-alive\r\nAccess-Control-Allow-Origin: *\r\n\r\n: " . str_repeat(' ', 2048) . "\n\n");
            $this->clients[$id]['sse'] = true;
        } elseif ($method === 'GET' && str_starts_with($path, '/cb/')) {
            $this->queue[] = ['kind' => 'cb', 'id' => substr($path, 4)];
            $this->respond($id, 200, 'ok');
        } elseif ($method === 'POST' && str_starts_with($path, '/event/')) {
            $this->queue[] = ['kind' => 'event', 'name' => substr($path, 7), 'body' => $body];
            $this->respond($id, 200, 'ok');
        } elseif ($path === '/favicon.ico') {
            $this->respond($id, 204, '');
        } else {
            $this->respond($id, 404, '');
        }
    }

    private function respond(int $id, int $code, string $body): void
    {
        $sock = $this->clients[$id]['sock'];
        $text = [200 => 'OK', 204 => 'No Content', 404 => 'Not Found'][$code] ?? 'OK';
        @fwrite($sock, "HTTP/1.1 {$code} {$text}\r\nContent-Type: text/plain\r\nContent-Length: " . strlen($body) . "\r\n"
            . "Access-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
            . "Access-Control-Allow-Headers: *\r\nConnection: close\r\n\r\n" . $body);
        $this->drop($id);
    }
}

// ── State ─────────────────────────────────────────────────────────────────────

class State
{
    /** @var list<callable> */
    private array $watchers = [];

    public function __construct(
        private string $name,
        private mixed  $value,
        private ?App   $app = null
    ) {}

    public function name(): string { return $this->name; }
    public function get():  mixed  { return $this->value; }

    /** Cambia el valor y lo refleja en la ventana. */
    public function set(mixed $value): void
    {
        $this->value = $value;
        $this->app?->pushState($this->name, $value);
    }

    public function inc(int|float $by = 1): void { $this->set((is_numeric($this->value) ? $this->value : 0) + $by); }
    public function dec(int|float $by = 1): void { $this->inc(-$by); }

    /** Llama a $fn($nuevoValor) cada vez que el usuario cambia el campo enlazado a este estado. */
    public function onChange(callable $fn): static
    {
        $this->watchers[] = $fn;
        return $this;
    }

    /** @internal valor recibido de la página (no se reenvía a la ventana). */
    public function receive(mixed $value): void
    {
        $this->value = $value;
        foreach ($this->watchers as $w) $w($value);
    }

    public function jsGet(): string
    {
        return 'window.__state[' . jsonJs($this->name) . ']';
    }

    public function jsSet(mixed $value): string
    {
        return 'window.__set(' . jsonJs($this->name) . ',' . jsonJs($value) . ')';
    }

    public function jsInc(int|float $by = 1): string
    {
        $n = jsonJs($this->name);
        return 'window.__set(' . $n . ',(+window.__state[' . $n . ']||0)+' . $by . ')';
    }

    public function jsDec(int|float $by = 1): string
    {
        return $this->jsInc(-$by);
    }

    // El texto inicial va dentro del span para que no parpadee vacío antes de que cargue el JS.
    public function __toString(): string
    {
        $v = $this->value;
        $txt = is_bool($v) ? ($v ? 'true' : 'false') : (is_scalar($v) ? (string)$v : '');
        return '<span data-spork-text="' . h($this->name) . '">' . h($txt) . '</span>';
    }
}

// ── Widget base ───────────────────────────────────────────────────────────────

abstract class Widget
{
    public array     $children   = [];
    protected string $cls        = '';
    protected string $style      = '';
    protected string $elId       = '';
    protected array  $extraAttrs = [];

    abstract public function tag(): string;
    public function classes(): string { return ''; }

    public function __construct(array $props = [])
    {
        $this->style = (string)($props['style'] ?? '');
        $this->cls   = trim((string)($props['cls'] ?? '') . ' ' . (string)($props['class'] ?? ''));
        $this->elId  = (string)($props['id'] ?? '');
        if (array_key_exists('if_',    $props)) $this->extraAttrs['data-spork-if']    = self::jsExpr($props['if_']);
        if (array_key_exists('style_', $props)) $this->extraAttrs['data-spork-style'] = self::jsExpr($props['style_']);
        if (array_key_exists('class_', $props)) $this->extraAttrs['data-spork-class'] = self::jsExpr($props['class_']);
    }

    protected static function jsExpr(mixed $value): string
    {
        return $value instanceof State
            ? $value->jsGet()
            : (is_string($value) ? $value : jsonJs($value));
    }

    public function add(mixed ...$items): static
    {
        array_push($this->children, ...$items);
        return $this;
    }

    public function attr(string $key, string $value): static
    {
        $this->extraAttrs[$key] = $value;
        return $this;
    }

    public function renderAttrs(): string
    {
        $attrs = [];
        if ($this->elId !== '') $attrs[] = 'id="' . h($this->elId) . '"';
        $class = trim($this->classes() . ' ' . $this->cls);
        if ($class !== '') $attrs[] = 'class="' . h($class) . '"';
        if ($this->style !== '') $attrs[] = 'style="' . h($this->style) . '"';
        foreach ($this->extraAttrs as $key => $val) {
            $attrs[] = $key . '="' . h((string)$val) . '"';
        }
        return $attrs ? ' ' . implode(' ', $attrs) : '';
    }

    protected function child(mixed $value): string
    {
        if ($value instanceof Widget) return $value->render();
        if ($value instanceof State)  return (string)$value;
        if (is_bool($value))          return $value ? 'true' : 'false';
        return h((string)$value);
    }

    public function render(): string
    {
        $tag   = $this->tag();
        $attrs = $this->renderAttrs();
        if (in_array($tag, ['hr', 'input', 'meta', 'link', 'br'], true)) return "<{$tag}{$attrs}>";
        $content = implode('', array_map([$this, 'child'], $this->children));
        return "<{$tag}{$attrs}>{$content}</{$tag}>";
    }
}

class Box extends Widget
{
    public function __construct(private string $boxClass, array $props = [])
    {
        parent::__construct($props);
    }
    public function tag(): string     { return 'div'; }
    public function classes(): string { return $this->boxClass; }
}

// Campo enlazado a un State: el JS de la página lo mantiene sincronizado en los dos sentidos y
// avisa a PHP (State::get() devuelve lo que escribió el usuario).
function bindAttr(?State $bind): string
{
    return $bind ? ' data-spork-bind="' . h($bind->name()) . '"' : '';
}

// ── Widgets ───────────────────────────────────────────────────────────────────

function Row(mixed ...$items): Widget  { return (new Box('sz-row'))->add(...$items); }
function Col(mixed ...$items): Widget  { return (new Box('sz-col sz-center'))->add(...$items); }
function Card(mixed ...$items): Widget { return (new Box('sz-card'))->add(...$items); }
function Grid(mixed ...$items): Widget { return (new Box('sz-grid'))->add(...$items); }
function H1(mixed $text): Widget       { return (new Box('sz-h1'))->add($text); }
function H2(mixed $text): Widget       { return (new Box('sz-h2'))->add($text); }
function H3(mixed $text): Widget       { return (new Box('sz-h3'))->add($text); }
function H4(mixed $text): Widget       { return (new Box('sz-h4'))->add($text); }
function P(mixed $text): Widget        { return (new Box('sz-p'))->add($text); }

// Spacer — empuja el contenido restante (flex grow)
function Spacer(): Widget
{
    return new Box('sz-grow');
}

// sz-divider es la clase correcta (no sz-hr)
function Hr(): Widget
{
    return new class extends Widget {
        public function tag(): string     { return 'div'; }
        public function classes(): string { return 'sz-divider'; }
    };
}

function Divider(): Widget { return Hr(); }

function Alert(mixed $text, string $variant = ''): Widget
{
    $cls = 'sz-alert' . ($variant !== '' ? ' sz-alert-' . $variant : '');
    return (new Box($cls))->add($text);
}

function Chip(mixed $text, bool $primary = false): Widget
{
    return (new Box('sz-chip' . ($primary ? ' sz-chip-primary' : '')))->add($text);
}

// Progress — acepta un State (la barra se mueve sola cuando cambia) o un número fijo
function Progress(mixed $value, int $max = 100): Widget
{
    return new class($value, $max) extends Widget {
        public function __construct(private mixed $val, private int $max)
        {
            parent::__construct();
        }
        public function tag(): string { return 'div'; }
        public function render(): string
        {
            if ($this->val instanceof State) {
                $key = jsonJs($this->val->name());
                $pct = round(max(0.0, min(100.0, (float)$this->val->get() / $this->max * 100)), 1);
                $expr = '{"width":(Math.min(100,Math.max(0,(+window.__state[' . $key . ']||0)/' . $this->max . '*100)).toFixed(1)+"%")}';
                $ds = ' data-spork-style="' . h($expr) . '"';
            } else {
                $pct = round(max(0.0, min(100.0, (float)$this->val / $this->max * 100)), 1);
                $ds  = '';
            }
            return '<div class="sz-progress"><div class="sz-progress-bar" style="width:' . $pct . '%"' . $ds . '></div></div>';
        }
    };
}

function Input(string $placeholder = '', ?State $bind = null, string $type = 'text'): Widget
{
    return new class($placeholder, $bind, $type) extends Widget {
        public function __construct(private string $placeholder, private ?State $bind, private string $type)
        {
            parent::__construct(['class' => 'sz-input']);
        }
        public function tag(): string { return 'input'; }
        public function render(): string
        {
            $val = $this->bind ? ' value="' . h((string)$this->bind->get()) . '"' : '';
            return '<input' . $this->renderAttrs() . ' type="' . h($this->type) . '" placeholder="' . h($this->placeholder) . '"'
                 . $val . bindAttr($this->bind) . '>';
        }
    };
}

// Selector de color / fecha enlazados a un State.
function ColorPicker(?State $bind = null): Widget { return Input('', $bind, 'color'); }
function DatePicker(?State $bind = null, bool $time = false): Widget { return Input('', $bind, $time ? 'datetime-local' : 'date'); }

// Select — $options: [[valor, etiqueta], ...]
function Select(array $options, ?State $bind = null, string $onAfterChange = ''): Widget
{
    return new class($options, $bind, $onAfterChange) extends Widget {
        public function __construct(private array $options, private ?State $bind, string $after)
        {
            parent::__construct(['class' => 'sz-select']);
            if ($after !== '') $this->extraAttrs['onchange'] = $after;
        }
        public function tag(): string { return 'select'; }
        public function render(): string
        {
            $cur  = $this->bind ? (string)$this->bind->get() : null;
            $html = '';
            foreach ($this->options as [$value, $label]) {
                $sel   = ($cur !== null && (string)$value === $cur) ? ' selected' : '';
                $html .= '<option value="' . h((string)$value) . '"' . $sel . '>' . h((string)$label) . '</option>';
            }
            return '<select' . $this->renderAttrs() . bindAttr($this->bind) . '>' . $html . '</select>';
        }
    };
}

// Checkbox — usa sz-switch (la clase real de spork.css; no existe sz-checkbox)
function Checkbox(string $label, ?State $bind = null): Widget
{
    return new class($label, $bind) extends Widget {
        public function __construct(private string $label, private ?State $bind)
        {
            parent::__construct();
        }
        public function tag(): string { return 'label'; }
        public function render(): string
        {
            $checked = ($this->bind && $this->bind->get()) ? ' checked' : '';
            return '<label class="sz-switch">'
                 . '<input type="checkbox"' . $checked . bindAttr($this->bind) . '>'
                 . '<span class="sz-switch-track"><span class="sz-switch-thumb"></span></span>'
                 . '<span class="sz-switch-label">' . h($this->label) . '</span>'
                 . '</label>';
        }
    };
}

// ── Widgets adicionales ───────────────────────────────────────────────────────

function Caption(mixed $text): Widget  { return (new Box('sz-caption'))->add($text); }
function Subtitle(mixed $text): Widget { return (new Box('sz-subtitle'))->add($text); }
function Label(mixed $text): Widget    { return (new Box('sz-label'))->add($text); }

// Field — envuelve un input con label, hint y error
function Field(Widget $input, string $label = '', string $hint = '', string $error = ''): Widget
{
    $w = new Box('sz-field');
    if ($label !== '') $w->add(Label($label));
    $w->add($input);
    if ($error !== '') $w->add((new Box('sz-field-error'))->add($error));
    elseif ($hint !== '') $w->add((new Box('sz-field-hint'))->add($hint));
    return $w;
}

function Textarea(string $placeholder = '', ?State $bind = null, int $rows = 4): Widget
{
    return new class($placeholder, $bind, $rows) extends Widget {
        public function __construct(private string $placeholder, private ?State $bind, private int $rows)
        {
            parent::__construct(['class' => 'sz-textarea']);
        }
        public function tag(): string { return 'textarea'; }
        public function render(): string
        {
            $val = $this->bind ? h((string)$this->bind->get()) : '';
            return '<textarea' . $this->renderAttrs() . ' placeholder="' . h($this->placeholder) . '" rows="' . $this->rows . '"'
                 . bindAttr($this->bind) . '>' . $val . '</textarea>';
        }
    };
}

function Slider(?State $bind = null, int $min = 0, int $max = 100, int $step = 1): Widget
{
    return new class($bind, $min, $max, $step) extends Widget {
        public function __construct(private ?State $bind, private int $min, private int $max, private int $step)
        {
            parent::__construct(['class' => 'sz-slider']);
        }
        public function tag(): string { return 'input'; }
        public function render(): string
        {
            $val = $this->bind ? (int)$this->bind->get() : $this->min;
            return '<input' . $this->renderAttrs() . ' type="range" min="' . $this->min . '" max="' . $this->max
                 . '" step="' . $this->step . '" value="' . $val . '"' . bindAttr($this->bind) . '>';
        }
    };
}

function Badge(mixed $text, string $variant = ''): Widget
{
    $cls = 'sz-badge' . ($variant !== '' ? ' sz-badge-' . $variant : '');
    return (new Box($cls))->add($text);
}

function Avatar(string $text = '', string $src = '', string $size = ''): Widget
{
    $cls = 'sz-avatar' . ($size !== '' ? ' sz-avatar-' . $size : '');
    $w   = new Box($cls);
    if ($src !== '') {
        $w->add(new class($src) extends Widget {
            public function __construct(private string $src) { parent::__construct(); }
            public function tag(): string { return 'img'; }
            public function render(): string { return '<img src="' . h($this->src) . '" alt="">'; }
        });
    } else {
        $w->add($text);
    }
    return $w;
}

function Spinner(string $size = ''): Widget
{
    return new Box('sz-spinner' . ($size !== '' ? ' sz-spinner-' . $size : ''));
}

function SpinnerCenter(string $size = ''): Widget
{
    return (new Box('sz-spinner-center'))->add(Spinner($size));
}

function Skeleton(string $variant = 'text'): Widget
{
    return new Box('sz-skeleton sz-skeleton-' . $variant);
}

// Table — $headers: string[], $rows: array[]
function Table(array $headers, array $rows, bool $striped = false): Widget
{
    return new class($headers, $rows, $striped) extends Widget {
        public function __construct(private array $headers, private array $rows, private bool $striped)
        {
            parent::__construct();
        }
        public function tag(): string { return 'div'; }
        public function render(): string
        {
            $cls   = 'sz-table' . ($this->striped ? ' sz-table-striped' : '');
            $thead = '<thead><tr>' . implode('', array_map(fn($x) => '<th>' . h((string)$x) . '</th>', $this->headers)) . '</tr></thead>';
            $tbody = '<tbody>' . implode('', array_map(
                fn($row) => '<tr>' . implode('', array_map(fn($c) => '<td>' . h((string)$c) . '</td>', (array)$row)) . '</tr>',
                $this->rows
            )) . '</tbody>';
            return '<div class="sz-table-container"><table class="' . $cls . '">' . $thead . $tbody . '</table></div>';
        }
    };
}

// Tabs — $tabs: [['label' => 'A', 'content' => Widget|string], ...]
function Tabs(array $tabs, int $active = 0): Widget
{
    return new class($tabs, $active) extends Widget {
        private static bool $scriptDone = false;
        public function __construct(private array $tabs, private int $active) { parent::__construct(); }
        public function tag(): string { return 'div'; }
        public function render(): string
        {
            $id   = 'tabs_' . substr(md5(serialize(array_map(fn($t) => $t['label'] ?? '', $this->tabs))), 0, 6);
            $btns = '';
            $pnls = '';
            foreach ($this->tabs as $i => $tab) {
                $on      = $i === $this->active;
                $btns   .= '<button class="sz-tab-btn' . ($on ? ' sz-active' : '') . '" data-ttarget="' . $id . '" data-tidx="' . $i . '">'
                         . h((string)($tab['label'] ?? $i)) . '</button>';
                $content = ($tab['content'] ?? '') instanceof Widget ? $tab['content']->render() : h((string)($tab['content'] ?? ''));
                $pnls   .= '<div class="sz-tab-panel' . ($on ? ' sz-active' : '') . '" data-tpanel="' . $id . '" data-tidx="' . $i . '">' . $content . '</div>';
            }
            // el manejador de clics va una sola vez en la página (ver Page JS)
            return '<div class="sz-tabs" id="' . $id . '"><div class="sz-tab-list">' . $btns . '</div>' . $pnls . '</div>';
        }
    };
}

// Modal — visible mientras el State $open sea verdadero
function Modal(string $title, Widget $body, array $footer = [], ?State $open = null): Widget
{
    return new class($title, $body, $footer, $open) extends Widget {
        public function __construct(private string $title, private Widget $body, private array $footer, private ?State $open)
        {
            parent::__construct();
        }
        public function tag(): string { return 'div'; }
        public function render(): string
        {
            $ifAttr  = $this->open ? ' data-spork-if="' . h($this->open->jsGet()) . '"' : '';
            $closeJs = $this->open
                ? $this->open->jsSet(false)
                : 'this.closest(".sz-modal-overlay").style.display="none"';
            $footerHtml = implode('', array_map(fn($w) => $w instanceof Widget ? $w->render() : '', $this->footer));
            return '<div class="sz-modal-overlay"' . $ifAttr . '><div class="sz-modal">'
                 . '<div class="sz-modal-header"><span class="sz-modal-title">' . h($this->title) . '</span>'
                 . '<button class="sz-modal-close" onclick="' . h($closeJs) . '">✕</button></div>'
                 . '<div class="sz-modal-body">' . $this->body->render() . '</div>'
                 . ($footerHtml !== '' ? '<div class="sz-modal-footer">' . $footerHtml . '</div>' : '')
                 . '</div></div>';
        }
    };
}

// Contenedor de toasts (App::toast() lo usa; la página ya lo incluye siempre)
function ToastContainer(): Widget
{
    return new class extends Widget {
        public function tag(): string { return 'div'; }
        public function render(): string { return ''; }
    };
}

function Toolbar(mixed ...$items): Widget { return (new Box('sz-toolbar'))->add(...$items); }
function ToolbarTitle(string $text): Widget { return (new Box('sz-toolbar-title'))->add($text); }
function ToolbarSep(): Widget { return new Box('sz-toolbar-sep'); }
function ToolbarSpacer(): Widget { return new Box('sz-toolbar-spacer'); }
function ToolbarBtn(string $text, string $js = '', bool $wide = false, bool $active = false): Widget
{
    $w = new Box('sz-toolbar-btn' . ($wide ? ' sz-toolbar-btn-wide' : '') . ($active ? ' sz-active' : ''));
    $w->add($text);
    if ($js !== '') $w->attr('onclick', $js);
    return $w;
}

function Sidebar(mixed ...$items): Widget          { return (new Box('sz-sidebar'))->add(...$items); }
function SidebarSection(mixed ...$items): Widget   { return (new Box('sz-sidebar-section'))->add(...$items); }
function SidebarTitle(string $text): Widget        { return (new Box('sz-sidebar-section-title'))->add($text); }
function SidebarDivider(): Widget                  { return new Box('sz-sidebar-divider'); }
function SidebarItem(string $text, string $icon = '', string $js = '', bool $active = false): Widget
{
    $w = new Box('sz-sidebar-item' . ($active ? ' sz-active' : ''));
    if ($icon !== '') $w->add((new Box('sz-sidebar-icon'))->add($icon));
    $w->add((new Box('sz-sidebar-label'))->add($text));
    if ($js !== '') $w->attr('onclick', $js);
    return $w;
}

function StatusBar(mixed ...$items): Widget      { return (new Box('sz-statusbar'))->add(...$items); }
function StatusBarItem(mixed $text, string $js = ''): Widget
{
    $w = new Box('sz-statusbar-item');
    $w->add($text);
    if ($js !== '') $w->attr('onclick', $js);
    return $w;
}
function StatusBarSep(): Widget     { return new Box('sz-statusbar-sep'); }
function StatusBarSpacer(): Widget  { return new Box('sz-statusbar-spacer'); }

// AppShell — layout completo: toolbar + sidebar + main + statusbar
function AppShell(?Widget $toolbar = null, ?Widget $sidebar = null, ?Widget $main = null, ?Widget $statusbar = null): Widget
{
    return new class($toolbar, $sidebar, $main, $statusbar) extends Widget {
        public function __construct(private ?Widget $toolbar, private ?Widget $sidebar, private ?Widget $main, private ?Widget $statusbar)
        {
            parent::__construct();
        }
        public function tag(): string { return 'div'; }
        public function render(): string
        {
            $html = '<div class="sz-app-shell' . ($this->sidebar ? '' : ' sz-no-sidebar') . '">';
            if ($this->toolbar)   $html .= $this->toolbar->render();
            if ($this->sidebar)   $html .= $this->sidebar->render();
            $html .= '<main class="sz-main">' . ($this->main ? $this->main->render() : '') . '</main>';
            if ($this->statusbar) $html .= $this->statusbar->render();
            return $html . '</div>';
        }
    };
}

// Panels — paneles redimensionables (horizontal o vertical)
function Panels(bool $vertical = false, mixed ...$panels): Widget
{
    return new class($vertical, $panels) extends Widget {
        public function __construct(private bool $vertical, private array $panels) { parent::__construct(); }
        public function tag(): string { return 'div'; }
        public function render(): string
        {
            $html = '<div class="sz-panels' . ($this->vertical ? ' sz-vertical' : '') . '">';
            foreach ($this->panels as $i => $panel) {
                if ($i > 0) $html .= '<div class="sz-panel-resizer"></div>';
                $html .= '<div class="sz-panel">' . ($panel instanceof Widget ? $panel->render() : h((string)$panel)) . '</div>';
            }
            return $html . '</div>';
        }
    };
}

/**
 * Canvas 2D: $cv = $app->canvas('lienzo', 400, 300);
 *   $cv->color('#6750A4'); $cv->rect(10,10,100,60); $cv->circle(200,60,40); $cv->line(0,0,400,300);
 *   $cv->text(10,280,'hola'); $cv->erase(); $cv->onMouse(fn($e) => ...)  // $e: type down|up|move|click, x, y, button
 */
class Canvas extends Widget
{
    public function __construct(private App $app, private string $id, private int $w, private int $h)
    {
        parent::__construct([]);
    }
    public function tag(): string { return 'canvas'; }
    public function render(): string
    {
        $id = h($this->id);
        return "<canvas id=\"{$id}\" width=\"{$this->w}\" height=\"{$this->h}\" style=\"width:{$this->w}px;max-width:100%;height:auto;border:1px solid rgba(128,128,128,.4);border-radius:8px;touch-action:none\"></canvas>";
    }
    public function id(): string { return $this->id; }
    public function color(string $c): static     { $this->app->cv($this->id, 'color', [$c]); return $this; }
    public function lineWidth(float $n): static  { $this->app->cv($this->id, 'lw', [$n]); return $this; }
    public function font(int $size): static      { $this->app->cv($this->id, 'font', [$size]); return $this; }
    public function line(float $x1, float $y1, float $x2, float $y2): static { $this->app->cv($this->id, 'line', [$x1, $y1, $x2, $y2]); return $this; }
    public function rect(float $x, float $y, float $w, float $h): static     { $this->app->cv($this->id, 'rect', [$x, $y, $w, $h]); return $this; }
    public function frame(float $x, float $y, float $w, float $h): static    { $this->app->cv($this->id, 'frame', [$x, $y, $w, $h]); return $this; }
    public function circle(float $x, float $y, float $r): static { $this->app->cv($this->id, 'circle', [$x, $y, $r]); return $this; }
    public function ring(float $x, float $y, float $r): static   { $this->app->cv($this->id, 'ring', [$x, $y, $r]); return $this; }
    public function text(float $x, float $y, string $s): static  { $this->app->cv($this->id, 'text', [$x, $y, $s]); return $this; }
    /** @param list<array{0:float,1:float}> $points */
    public function poly(array $points): static  { $this->app->cv($this->id, 'poly', [$points]); return $this; }
    public function erase(): static              { $this->app->cv($this->id, 'clear', []); return $this; }
    /** JS crudo con (ctx, canvas) en el ámbito. */
    public function draw(string $js): static     { $this->app->cv($this->id, 'draw', [$js]); return $this; }
    public function onMouse(callable $fn): static { $this->app->cvMouse($this->id, $fn); return $this; }
}

class RawHtml extends Widget
{
    public function __construct(private string $html) { parent::__construct([]); }
    public function tag(): string { return 'div'; }
    public function render(): string { return $this->html; }
}

// ── Menús (barra de menú HTML con atajos de teclado) ─────────────────────────
//
//   $app->add(MenuBar(
//       Menu('Archivo', MenuItem('Abrir...', $app->onClick(fn() => ...), 'ctrl+o'), MenuSep(),
//                       MenuItem('Salir', $app->onClick(fn() => $app->quit()))),
//       Menu('Ayuda', MenuItem('Acerca de', $app->onClick(fn() => ...)))
//   ), ...resto);
//   Atajos: 'ctrl+o', 'ctrl+shift+s', 'alt+x', 'f5'... (orden: ctrl, shift, alt, tecla).

function MenuItem(string $label, string $js = '', string $shortcut = ''): Widget
{
    $click = str_replace('"', '&quot;', $js);
    $kbd = $shortcut !== '' ? '<kbd>' . h($shortcut) . '</kbd>' : '';
    return new RawHtml('<button type="button" class="sz-menu-item" onclick="' . $click . '" data-accel="' . h($shortcut) . '"><span>' . h($label) . '</span>' . $kbd . '</button>');
}

function MenuSep(): Widget { return new RawHtml('<div class="sz-menu-sep"></div>'); }

function Menu(string $title, Widget ...$items): Widget
{
    $in = implode('', array_map(fn(Widget $w) => $w->render(), $items));
    return new RawHtml('<div class="sz-menu"><button type="button" class="sz-menu-title">' . h($title) . '</button><div class="sz-menu-list">' . $in . '</div></div>');
}

function MenuBar(Widget ...$menus): Widget
{
    $in = implode('', array_map(fn(Widget $w) => $w->render(), $menus));
    return new RawHtml(<<<'MENU_A'
<style>.sz-menubar{position:fixed;top:0;left:0;right:0;z-index:1000;display:flex;gap:2px;padding:3px 6px;background:var(--sz-surface,#fff);color:var(--sz-on-surface,#1d1b20);border-bottom:1px solid rgba(128,128,128,.3);font-size:14px}.sz-menubar-space{height:38px;width:100%;flex:none}.sz-menu{position:relative}.sz-menu-title{background:none;border:0;padding:6px 10px;border-radius:6px;color:inherit;font:inherit;cursor:pointer}.sz-menu-title:hover,.sz-menu.sz-open>.sz-menu-title{background:rgba(128,128,128,.18)}.sz-menu-list{display:none;position:absolute;top:100%;left:0;min-width:210px;padding:4px;background:var(--sz-surface,#fff);color:inherit;border:1px solid rgba(128,128,128,.35);border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.2)}.sz-menu.sz-open>.sz-menu-list{display:block}.sz-menu-item{display:flex;justify-content:space-between;gap:24px;width:100%;background:none;border:0;padding:6px 10px;border-radius:6px;color:inherit;font:inherit;cursor:pointer;text-align:left}.sz-menu-item:hover{background:rgba(128,128,128,.18)}.sz-menu-item kbd{opacity:.6;font:inherit;font-size:12px}.sz-menu-sep{height:1px;margin:4px 6px;background:rgba(128,128,128,.3)}.sz-native .sz-menubar,.sz-native .sz-menubar-space{display:none!important}</style><div class="sz-menubar">
MENU_A
        . $in . <<<'MENU_B'
</div><div class="sz-menubar-space"></div><script>(function(){if(window.__menu)return;window.__menu=1;var bar=document.querySelector('.sz-menubar');function menus(){return bar.querySelectorAll(':scope > .sz-menu')}window.__vspk_menu_click=function(id){var p=id.split('.');var m=menus()[+p[0]];if(m)m.querySelector('.sz-menu-list').children[+p[1]].click()};window.__vspk_menu_ok=function(){document.documentElement.classList.add('sz-native')};if(bar&&window.ipc&&window.__vspk_native_menu_ok){var ms=[];Array.prototype.forEach.call(menus(),function(m,mi){var items=[];Array.prototype.forEach.call(m.querySelector('.sz-menu-list').children,function(c,ii){if(c.classList.contains('sz-menu-sep'))items.push({sep:true});else items.push({id:mi+'.'+ii,label:(c.querySelector('span')||c).textContent,accel:c.getAttribute('data-accel')||''})});ms.push({label:m.querySelector('.sz-menu-title').textContent,items:items})});window.ipc.postMessage(JSON.stringify({cmd:'setMenu',menu:ms}))}function closeAll(except){document.querySelectorAll('.sz-menu.sz-open').forEach(function(m){if(m!==except)m.classList.remove('sz-open')})}document.addEventListener('click',function(e){var t=e.target.closest?e.target.closest('.sz-menu-title'):null;closeAll(t?t.parentNode:null);if(t)t.parentNode.classList.toggle('sz-open');var it=e.target.closest?e.target.closest('.sz-menu-item'):null;if(it)closeAll(null)});document.addEventListener('mouseover',function(e){var t=e.target.closest?e.target.closest('.sz-menu-title'):null;var o=document.querySelector('.sz-menu.sz-open');if(t&&o&&o!==t.parentNode){closeAll(t.parentNode);t.parentNode.classList.add('sz-open')}});document.addEventListener('keydown',function(e){if(e.key==='Escape'){closeAll(null);return}if(document.documentElement.classList.contains('sz-native')&&!/Win/.test(navigator.platform))return;var k=(e.ctrlKey?'ctrl+':'')+(e.shiftKey?'shift+':'')+(e.altKey?'alt+':'')+e.key.toLowerCase();var items=document.querySelectorAll('.sz-menu-item[data-accel]');for(var i=0;i<items.length;i++){var a=items[i].getAttribute('data-accel');if(a&&a.toLowerCase()===k){e.preventDefault();items[i].click();return}}})})();</script>
MENU_B);
}

class Button extends Widget
{
    public function __construct(string $text, string $js = '', string $variant = 'filled', string $size = '')
    {
        parent::__construct(['class' => 'sz-btn sz-btn-' . $variant . ($size !== '' ? ' sz-btn-' . $size : '')]);
        $this->children[] = $text;
        if ($js !== '') $this->extraAttrs['onclick'] = $js;
    }
    public function tag(): string { return 'button'; }
}

// ── Window — control de ventana desde PHP ────────────────────────────────────

class Window
{
    public function __construct(private App $app) {}

    public function setTitle(string $title): void
    {
        $this->app->evalJs('window.__vspk_cmd("setTitle",' . jsonJs($title) . ')');
    }

    public function close(): void
    {
        $this->app->evalJs('window.__vspk_cmd("close")');
    }

    public function notify(string $title, string $body = ''): void
    {
        $this->app->evalJs('window.__vspk_cmd("notify",' . jsonJs($title) . ',' . jsonJs($body) . ')');
    }

    public function fullscreen(bool $on = true): void
    {
        $this->app->evalJs('window.__vspk_cmd("fullscreen")');
    }

    // Comandos via IPC (gestión entre ventanas)
    public function move(int $x, int $y, int $id = 1): void   { $this->ipc(['cmd' => 'move', 'id' => $id, 'x' => $x, 'y' => $y]); }
    public function resize(int $w, int $h, int $id = 1): void { $this->ipc(['cmd' => 'resize', 'id' => $id, 'w' => $w, 'h' => $h]); }
    public function focus(int $id = 1): void                  { $this->ipc(['cmd' => 'focus', 'id' => $id]); }
    public function snap(string $pos, int $id = 1): void      { $this->ipc(['cmd' => 'snap', 'id' => $id, 'pos' => $pos]); }
    public function listWindows(): array                      { return $this->ipc(['cmd' => 'list'])['windows'] ?? []; }
    public function broadcast(mixed $payload): void           { $this->ipc(['cmd' => 'broadcast', 'payload' => $payload]); }

    private function ipc(array $msg): array
    {
        try {
            $sock = PHP_OS_FAMILY === 'Windows'
                ? @fopen('\\\\.\\pipe\\vspk', 'r+b')
                : @fsockopen('unix:///tmp/vspk.sock', -1, $errno, $errstr, 1.0);
            if (!$sock) return ['ok' => false, 'error' => 'No se pudo conectar al IPC'];
            fwrite($sock, json_encode($msg) . "\n");
            $line = fgets($sock, 4096);
            fclose($sock);
            return $line ? (json_decode($line, true) ?? []) : [];
        } catch (\Throwable $e) {
            return ['ok' => false, 'error' => $e->getMessage()];
        }
    }
}

// ── ChildWindow — ventanas adicionales (otro proceso vspk que comparte el puente y los states) ──
//
//   $aj = $app->newWindow('Ajustes', 360, 240);
//   $aj->add(Col(H4('Ajustes'), Input('Nombre', $nombre)));   // los states se comparten entre ventanas
//   $aj->show();  $aj->close();  $aj->onClose(fn() => true);  $aj->setTitle('...');  $aj->evalJs('...');

final class ChildWindow
{
    public string $id;
    /** @var list<Widget|string> */
    public array $widgets = [];
    public mixed $proc = null;
    public string $htv = '';
    public bool $want = false;
    public bool $closeOn = false;
    public string $closeJs = '';

    public function __construct(private App $app, public string $title, public int $w, public int $h, string $id)
    {
        $this->id = $id;
    }

    public function add(mixed ...$items): static { foreach ($items as $i) $this->widgets[] = $i; return $this; }
    public function show(): static  { $this->app->winShow($this); return $this; }
    public function close(): void   { $this->app->winEval($this, '__vspk.close()'); }
    public function setTitle(string $t): void { $this->app->winEval($this, '__vspk.setTitle(' . jsonJs($t) . ')'); }
    public function evalJs(string $js): void  { $this->app->winEval($this, $js); }
    public function onClose(callable $fn): static { $this->app->winOnClose($this, $fn); return $this; }
    public function isOpen(): bool
    {
        if (!is_resource($this->proc)) return false;
        return (bool)(proc_get_status($this->proc)['running'] ?? false);
    }
}

// ── App ───────────────────────────────────────────────────────────────────────

class App
{
    /** @var array<string, State> */
    private array  $states    = [];
    /** @var array<string, callable> */
    private array  $callbacks = [];
    /** @var array<string, callable> */
    private array  $events    = [];
    /** @var list<array{at: float, every: ?float, fn: callable}> */
    private array  $timers    = [];
    private int    $cbCount   = 0;
    private string $token     = '';
    private bool   $keyOn     = false;
    private bool   $closeOn   = false;
    private bool   $running   = false;
    /** @var array<string,string> JS de dibujo por canvas (se reproduce al cargar la página) */
    private array  $cvLogs    = [];
    private string $cvMouseJs = '';
    /** @var list<string> JS de temporizadores de la página, se instalan al conectar */
    private array  $pageTimers = [];
    private Widget $root;
    private Bridge $bridge;
    private bool   $quit      = false;
    /** @var list<ChildWindow> */
    private array  $wins      = [];

    public function __construct(
        private string $title   = 'Vspk App',
        private int    $width   = 1024,
        private int    $height  = 768,
        private string $theme   = 'light',
        private string $primary = '6750A4',
        private string $onClose = ''
    ) {
        $this->root   = new Box('sz-col sz-center');
        $this->bridge = new Bridge();           // el puerto se conoce ya, antes de construir los widgets
        $this->token  = bin2hex(random_bytes(8)); // ids de callback/eventos internos no adivinables desde otra web
    }

    public function state(string $name, mixed $initial): State
    {
        return $this->states[$name] ??= new State($name, $initial, $this);
    }

    public function add(mixed ...$items): static
    {
        $this->root->add(...$items);
        return $this;
    }

    /** Registra un callback de PHP y devuelve el JS (para onclick) que lo dispara. */
    public function onClick(callable $fn): string
    {
        $id = 'cb_' . $this->token . '_' . (++$this->cbCount);
        $this->callbacks[$id] = $fn;
        return "fetch('http://127.0.0.1:{$this->bridge->port}/cb/{$id}',{mode:'no-cors'})";
    }

    /** Escucha un evento enviado desde la página: fetch('.../event/nombre', {method:'POST', body: JSON}). */
    public function onEvent(string $name, callable $fn): static
    {
        $this->events[$name] = $fn;
        return $this;
    }

    /** $js puede ser un string (JS puro en la página) o un callable de PHP. */
    public function Button(string $text, string|callable $js = '', string $variant = 'filled', string $size = ''): Widget
    {
        if (!is_string($js)) $js = $this->onClick($js);
        return new Button($text, $js, $variant, $size);
    }

    /** Ejecuta JS en la ventana. */
    public function evalJs(string $js): void
    {
        $this->bridge->push('eval', $js);
    }

    public function toast(string $msg, string $variant = '', int $ms = 3000): void
    {
        $this->evalJs('window.__toast(' . jsonJs($msg) . ',' . jsonJs($variant) . ',' . $ms . ')');
    }

    /** Ejecuta $fn una vez dentro de $ms milisegundos (mientras run() está activo). */
    public function after(int $ms, callable $fn): static
    {
        $this->timers[] = ['at' => microtime(true) + $ms / 1000, 'every' => null, 'fn' => $fn];
        return $this;
    }

    /** Ejecuta $fn cada $ms milisegundos. Devuelve false desde $fn para cancelarlo. */
    public function every(int $ms, callable $fn): static
    {
        $this->timers[] = ['at' => microtime(true) + $ms / 1000, 'every' => $ms / 1000, 'fn' => $fn];
        return $this;
    }

    public function quit(): void
    {
        $this->quit = true;
    }

    private function ev(string $name): string { return '__' . $name . '_' . $this->token; }

    private function postJs(string $name, string $bodyExpr): string
    {
        return "fetch('http://127.0.0.1:{$this->bridge->port}/event/{$name}',{method:'POST',mode:'no-cors',headers:{'Content-Type':'text/plain'},body:{$bodyExpr}})";
    }

    /** Teclado: $fn recibe ['key','code','ctrl','shift','alt','meta']. */
    public function onKey(callable $fn): static
    {
        $this->keyOn = true;
        $this->events[$this->ev('k')] = $fn;
        return $this;
    }

    /** Cierre de ventana: $fn devuelve false para cancelarlo. */
    public function onClose(callable $fn): static
    {
        $this->closeOn = true;
        $this->events[$this->ev('c')] = function () use ($fn) {
            try { $r = $fn(); } catch (\Throwable $e) { fwrite(STDERR, "[vspk.php] error en onClose: {$e}\n"); $r = true; }
            $this->evalJs($r === false ? '__vspk.cancelClose()' : '__vspk.confirmClose()');
        };
        return $this;
    }

    private function dialog(string $kind, string $title, callable $fn): static
    {
        $name = $this->ev('d' . (++$this->cbCount));
        $this->events[$name] = fn($d) => $fn(is_array($d) ? ($d['path'] ?? null) : null);
        $this->evalJs('__vspk.dialog({kind:' . jsonJs($kind) . ',title:' . jsonJs($title) . '}).then(function(p){'
            . $this->postJs($name, 'JSON.stringify({path:p})') . '})');
        return $this;
    }

    /** Diálogo nativo; $fn recibe la ruta elegida (o null si se cancela). */
    public function pickFile(string $title, callable $fn): static   { return $this->dialog('open', $title, $fn); }
    public function saveFile(string $title, callable $fn): static   { return $this->dialog('save', $title, $fn); }
    public function pickFolder(string $title, callable $fn): static { return $this->dialog('folder', $title, $fn); }

    // ── Diálogos modales (mensaje / confirmación / pedir texto) ──────────────

    private function modal(string $call, callable $conv, ?callable $fn): static
    {
        $name = $this->ev('m' . (++$this->cbCount));
        $this->events[$name] = function ($d) use ($conv, $fn) { if ($fn) $fn($conv(is_array($d) ? ($d['v'] ?? null) : null)); };
        $this->evalJs('Promise.resolve(' . $call . ').then(function(v){' . $this->postJs($name, 'JSON.stringify({v:v})') . '})');
        return $this;
    }

    /** Diálogo modal con un botón Aceptar. $fn() al cerrarlo (opcional). */
    public function message(string $text, ?callable $fn = null): static
    { return $this->modal('alert(' . jsonJs($text) . ')', fn($v) => null, $fn ? fn() => $fn() : null); }

    /** Modal Aceptar/Cancelar. $fn(bool). */
    public function confirm(string $text, callable $fn): static
    { return $this->modal('confirm(' . jsonJs($text) . ')', fn($v) => (bool)$v, $fn); }

    /** Modal que pide un texto. $fn(string) o $fn(null) si se cancela. */
    public function prompt(string $text, callable $fn, string $default = ''): static
    { return $this->modal('prompt(' . jsonJs($text) . ',' . jsonJs($default) . ')', fn($v) => is_string($v) ? $v : null, $fn); }

    // ── Tabla, árbol, lista (se hidratan en la página; ver vspk_ui.js incrustado en vspk.exe) ──

    private int $vtCount = 0;

    private function vtWidget(string $cls, string $prefix, array $cfg, array $o): Widget
    {
        $id = (string)($o['id'] ?? ($prefix . (++$this->vtCount)));
        $w = new Box($cls, ['id' => $id, 'style' => isset($o['height']) && $cls === 'vspk-tree'
            ? 'max-height:' . (is_int($o['height']) ? $o['height'] . 'px' : $o['height']) : '']);
        $w->attr('data-vt', jsonJs($cfg));
        foreach (['onSelect' => 'data-on-select', 'onDblclick' => 'data-on-dblclick', 'onSort' => 'data-on-sort'] as $k => $attr) {
            if (!empty($o[$k])) {
                $name = $this->ev('v' . (++$this->cbCount));
                $this->events[$name] = $o[$k];
                $w->attr($attr, $this->postJs($name, 'JSON.stringify(p)'));
            }
        }
        return $w;
    }

    /**
     * $app->Table(['Nombre','Edad'], [['Ana',31],['Luis',28]], ['onSelect' => fn($d) => ..., 'id' => 'tabla'])
     * Opciones: onSelect, onDblclick, onSort, sortable, multi, striped, header, height, selected, id.
     * onSelect($d) → $d['index'] (posición original), $d['row'], $d['indexes'], $d['rows'].
     * Clic en la cabecera ordena. Para cambiar datos: $app->tableSet('tabla', $filas).
     */
    public function Table(array $cols, array $rows, array $o = []): Widget
    {
        $cfg = ['cols' => $cols, 'rows' => $rows, 'sortable' => $o['sortable'] ?? true, 'multi' => $o['multi'] ?? false,
                'striped' => $o['striped'] ?? true, 'header' => $o['header'] ?? true, 'selected' => $o['selected'] ?? -1];
        if (isset($o['height'])) $cfg['height'] = $o['height'];
        return $this->vtWidget('vspk-table', 'vt', $cfg, $o);
    }

    /** Lista de una columna sin cabecera. onSelect($d) → $d['row'][0] es el elemento. */
    public function Listbox(array $items, array $o = []): Widget
    {
        $cfg = ['cols' => [''], 'rows' => array_map(fn($x) => [$x], array_values($items)), 'sortable' => false,
                'multi' => false, 'striped' => false, 'header' => false, 'selected' => -1];
        if (isset($o['height'])) $cfg['height'] = $o['height'];
        return $this->vtWidget('vspk-table', 'vt', $cfg, $o);
    }

    /** $app->Tree([['label'=>'src','open'=>true,'children'=>[['label'=>'main.rs','id'=>7]]]], ['onSelect' => fn($d) => ...]) → $d['path'], $d['label'], $d['id'] */
    public function Tree(array $nodes, array $o = []): Widget
    {
        return $this->vtWidget('vspk-tree', 'vtree', ['nodes' => $nodes], $o);
    }

    /** $win = ventana extra (ChildWindow) donde vive el widget; null = la principal. */
    private function evalIn(?ChildWindow $win, string $js): void { $win ? $win->evalJs($js) : $this->evalJs($js); }

    public function tableSet(string $id, array $rows, ?array $cols = null, ?ChildWindow $win = null): void
    { $this->evalIn($win, 'window.__vspk_table_set(' . jsonJs($id) . ',' . jsonJs($cols) . ',' . jsonJs($rows) . ')'); }
    public function tableSelect(string $id, int $index, ?ChildWindow $win = null): void
    { $this->evalIn($win, 'window.__vspk_table_select(' . jsonJs($id) . ',' . $index . ')'); }
    public function tableSort(string $id, int $col, bool $desc = false, ?ChildWindow $win = null): void
    { $this->evalIn($win, 'window.__vspk_table_sort(' . jsonJs($id) . ',' . $col . ',' . ($desc ? -1 : 1) . ')'); }
    public function treeSet(string $id, array $nodes, ?ChildWindow $win = null): void
    { $this->evalIn($win, 'window.__vspk_tree_set(' . jsonJs($id) . ',' . jsonJs($nodes) . ')'); }

    public function setTitle(string $t): void
    {
        $this->evalJs('__vspk.setTitle(' . jsonJs($t) . ')');
    }

    public function notify(string $title, string $body = ''): void
    {
        $this->evalJs('__vspk.notify(' . jsonJs($title) . ',' . jsonJs($body) . ')');
    }

    public function copyText(string $text): void
    {
        $this->evalJs('__vspk.clipboard.write(' . jsonJs($text) . ')');
    }

    public function canvas(string $id, int $w, int $h): Canvas
    {
        $this->cvLogs[$id] = '';
        return new Canvas($this, $id, $w, $h);
    }

    /** @internal */
    public function cv(string $id, string $op, array $args): void
    {
        $js = '__cv(' . jsonJs($id) . ',' . jsonJs($op) . ',' . jsonJs($args) . ')';
        if ($op === 'clear') $this->cvLogs[$id] = '';
        $this->cvLogs[$id] = ($this->cvLogs[$id] ?? '') . $js . ';';
        if ($this->running) $this->bridge->push('all', $js);
    }

    /** @internal */
    public function cvMouse(string $id, callable $fn): void
    {
        $name = $this->ev('m' . (++$this->cbCount));
        $this->events[$name] = $fn;
        $js = "(function(){var c=document.getElementById(" . jsonJs($id) . ");if(!c)return;function p(t,e){if(t==='move'){var n=Date.now();if(n-(c.__lm||0)<30)return;c.__lm=n;}var r=c.getBoundingClientRect();"
            . $this->postJs($name, 'JSON.stringify({type:t,x:Math.round((e.clientX-r.left)*c.width/r.width),y:Math.round((e.clientY-r.top)*c.height/r.height),button:e.button})')
            . "}['down','up','move','click'].forEach(function(t){c.addEventListener(t==='down'?'mousedown':t==='up'?'mouseup':t==='move'?'mousemove':'click',function(e){p(t,e)})})})();";
        $this->cvMouseJs .= $js;
        if ($this->running) $this->bridge->push('all', $js);
    }

    public function window(): Window
    {
        return new Window($this);
    }

    /** Ventana adicional. Comparte states, canvas y puente con la principal. */
    public function newWindow(string $title, int $width = 480, int $height = 360): ChildWindow
    {
        $w = new ChildWindow($this, $title, $width, $height, 'w' . (count($this->wins) + 1));
        $this->wins[] = $w;
        return $w;
    }

    /** @internal */
    public function winEval(ChildWindow $w, string $js): void
    {
        $this->bridge->push('eval_' . $w->id, $js);
    }

    /** @internal */
    public function winShow(ChildWindow $w): void
    {
        if ($this->running) $this->winOpen($w); else $w->want = true;
    }

    /** @internal */
    public function winOnClose(ChildWindow $w, callable $fn): void
    {
        $ev = $this->ev('c' . $w->id);
        $w->closeOn = true;
        $w->closeJs = 'window.addEventListener("vspk:closeRequested",function(){' . $this->postJs($ev, '"{}"') . '});';
        $this->events[$ev] = function () use ($fn, $w) {
            try { $r = $fn(); } catch (\Throwable $e) { fwrite(STDERR, "[vspk.php] error en onClose: {$e}\n"); $r = true; }
            $this->winEval($w, $r === false ? '__vspk.cancelClose()' : '__vspk.confirmClose()');
        };
    }

    private function winOpen(ChildWindow $w): void
    {
        if ($w->isOpen()) return;
        if ($w->htv !== '') @unlink($w->htv);
        $page = $this->buildPage($w->title, implode("\n", array_map(fn($x) => $x instanceof Widget ? $x->render() : (string)$x, $w->widgets)),
            'eval_' . $w->id, false, $w->closeJs);
        $w->htv = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'vspk_' . getmypid() . '_' . bin2hex(random_bytes(3)) . '.htv';
        file_put_contents($w->htv, "title: {$w->title}\nwidth: {$w->w}\nheight: {$w->h}\ndevtools: true\n"
            . (($ic = $this->findIcon()) !== '' ? "icon: {$ic}\n" : '')
            . ($w->closeOn ? "on_close: confirm\n" : '') . "\n" . $page);
        $proc = @proc_open([findVspk(), $w->htv], [0 => STDIN, 1 => STDOUT, 2 => STDERR], $pipes);
        $w->proc = is_resource($proc) ? $proc : null;
    }

    /** @internal */
    public function pushState(string $name, mixed $value): void
    {
        $this->bridge->push('state', ['name' => $name, 'value' => $value]);
    }

    private function buildHtml(): string
    {
        return $this->buildPage($this->title, $this->root->render(), 'eval', true, '');
    }

    private function buildPage(string $pageTitle, string $body, string $evalEv, bool $isMain, string $childCloseJs): string
    {
        $states = [];
        foreach ($this->states as $name => $s) $states[$name] = $s->get();
        $statesJson = $states ? jsonJs($states) : '{}';
        $primary = ltrim($this->primary, '#');
        $theme   = $this->theme === 'dark' ? 'dark' : 'light';

        $js = <<<'JS'
window.__state = %STATE%;
window.__win = %WIN%;
window.__set = function(name, value) {
  window.__state[name] = value;
  document.querySelectorAll('[data-spork-text="' + name + '"]').forEach(function(el) { el.textContent = value; });
  document.querySelectorAll('[data-spork-bind="' + name + '"]').forEach(function(el) {
    if (el.type === 'checkbox') el.checked = !!value;
    else if (el.value != value) el.value = value;
  });
  var ev = function(code) { return new Function('return (' + code + ')')(); };
  document.querySelectorAll('[data-spork-style]').forEach(function(el) { try { Object.assign(el.style, ev(el.dataset.sporkStyle)); } catch(_) {} });
  document.querySelectorAll('[data-spork-if]').forEach(function(el) { try { el.style.display = ev(el.dataset.sporkIf) ? '' : 'none'; } catch(_) {} });
  document.querySelectorAll('[data-spork-class]').forEach(function(el) { try { var c = ev(el.dataset.sporkClass); if (typeof c === 'string') el.className = (el.dataset.sporkBase || (el.dataset.sporkBase = el.className)) + ' ' + c; } catch(_) {} });
};
// Valor que el usuario escribe/elige → a PHP (State::get() lo ve) y a los demás widgets enlazados.
window.__sync = function(n, v) {
  try { fetch('http://127.0.0.1:%PORT%/event/%VEV%', {method: 'POST', mode: 'no-cors', headers: {'Content-Type': 'text/plain'}, body: JSON.stringify({n: n, v: v, w: window.__win})}); } catch(_) {}
};
(function() {
  function onUser(e) {
    var el = e.target && e.target.closest ? e.target.closest('[data-spork-bind]') : null;
    if (!el) return;
    var v = el.type === 'checkbox' ? el.checked : (el.type === 'range' || el.type === 'number') ? Number(el.value) : el.value;
    var n = el.getAttribute('data-spork-bind');
    window.__set(n, v);
    window.__sync(n, v);
  }
  document.addEventListener('input', onUser);
  document.addEventListener('change', onUser);
})();
document.addEventListener('click', function(e) {      // Tabs
  var b = e.target.closest ? e.target.closest('[data-ttarget]') : null;
  if (!b) return;
  var g = b.dataset.ttarget, i = +b.dataset.tidx;
  document.querySelectorAll('[data-tpanel]').forEach(function(p) { if (p.dataset.tpanel === g) p.classList.toggle('sz-active', +p.dataset.tidx === i); });
  document.querySelectorAll('[data-ttarget]').forEach(function(x) { if (x.dataset.ttarget === g) x.classList.toggle('sz-active', +x.dataset.tidx === i); });
});
window.__toast = function(msg, v, ms) {
  var c = document.getElementById('__vspk_toasts');
  if (!c) { c = document.createElement('div'); c.className = 'sz-toast-container'; c.id = '__vspk_toasts'; document.body.appendChild(c); }
  var t = document.createElement('div'); t.className = 'sz-toast' + (v ? ' sz-toast-' + v : ''); t.textContent = msg; c.appendChild(t);
  setTimeout(function() { t.style.opacity = '0'; t.style.transition = 'opacity .3s'; setTimeout(function() { t.remove(); }, 300); }, ms || 3000);
};
window.__vspk_cmd = function(cmd, a, b) {
  try {
    if (cmd === 'close' || cmd === 'fullscreen') window.ipc && window.ipc.postMessage(JSON.stringify({cmd: cmd === 'close' ? 'close' : 'toggleFullscreen'}));
    else if (cmd === 'setTitle' && window.__vspk_api) window.__vspk_api.setTitle(a);
    else if (cmd === 'setTitle' && typeof __vspk !== 'undefined') __vspk.setTitle(a);
    else if (cmd === 'notify' && typeof __vspk !== 'undefined') __vspk.notify(a, b);
  } catch(err) { console.error(err); }
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
(function connectSSE() {
  var es = new EventSource('http://127.0.0.1:%PORT%/events');
  es.addEventListener('state', function(e) { var d = JSON.parse(e.data); if (d.src && d.src === window.__win) return; window.__set(d.name, d.value); });
  [%EVALEV%, 'all'].forEach(function(n) { es.addEventListener(n, function(e) { try { (0, eval)(JSON.parse(e.data)); } catch(err) { console.error(err); } }); });
  es.onerror = function() { es.close(); setTimeout(connectSSE, 1000); };
})();
JS;
        $keyJs = ($isMain && $this->keyOn) ? 'document.addEventListener("keydown",function(e){' . $this->postJs($this->ev('k'),
            'JSON.stringify({key:e.key,code:e.code,ctrl:e.ctrlKey,shift:e.shiftKey,alt:e.altKey,meta:e.metaKey})') . '});' : '';
        $closeJs = $childCloseJs . (($isMain && $this->closeOn) ? 'window.addEventListener("vspk:closeRequested",function(){' . $this->postJs($this->ev('c'), '"{}"') . '});' : '');
        $js = str_replace(['%STATE%', '%PORT%', '%VEV%', '%WIN%', '%EVALEV%'], [$statesJson, (string)$this->bridge->port, $this->ev('v'), jsonJs($evalEv), jsonJs($evalEv)], $js) . "\n" . $keyJs . $closeJs . implode('', $this->cvLogs) . $this->cvMouseJs;

        $title = h($pageTitle);
        $css   = "https://cdn.jsdelivr.net/gh/unoudos/spork-ui@main/spork.css";
        $jsCdn = "https://cdn.jsdelivr.net/gh/unoudos/spork-ui@main/spork.js";

        return <<<HTML
<!DOCTYPE html>
<html data-theme="{$theme}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{$title}</title>
  <link rel="icon" href="data:,">
  <link rel="stylesheet" href="spork.css" onerror="this.onerror=null;this.href='{$css}'">
  <style>:root { --sz-primary: #{$primary}; }</style>
</head>
<body class="sz-body">

<div id="__app" class="sz-page">
{$body}
</div>

<script>
{$js}
</script>
<script src="spork.js" onerror="var s=document.createElement('script');s.src='{$jsCdn}';document.body.appendChild(s)"></script>
</body>
</html>
HTML;
    }

    private function dispatch(): void
    {
        while (($m = $this->bridge->poll()) !== null) {
            try {
                if ($m['kind'] === 'cb') {
                    ($this->callbacks[$m['id']] ?? static fn() => null)();
                    continue;
                }
                $data = json_decode((string)$m['body'], true);
                if ($m['name'] === $this->ev('v')) {
                    if (is_array($data) && isset($data['n']) && isset($this->states[(string)$data['n']])) {
                        $this->states[(string)$data['n']]->receive($data['v'] ?? null);
                        if ($this->wins) $this->bridge->push('state', ['name' => (string)$data['n'], 'value' => $data['v'] ?? null, 'src' => (string)($data['w'] ?? '')]);
                    }
                } elseif (isset($this->events[$m['name']])) {
                    ($this->events[$m['name']])($data);
                }
            } catch (\Throwable $e) {
                fwrite(STDERR, "[vspk.php] error en callback: {$e}\n");
            }
        }
    }

    private function runTimers(): void
    {
        $now = microtime(true);
        foreach ($this->timers as $i => $t) {
            if ($t['at'] > $now) continue;
            try {
                $r = ($t['fn'])();
            } catch (\Throwable $e) {
                fwrite(STDERR, "[vspk.php] error en temporizador: {$e}\n");
                $r = false;
            }
            if ($t['every'] === null || $r === false) unset($this->timers[$i]);
            else $this->timers[$i]['at'] = $now + $t['every'];
        }
    }

    private function findIcon(): string
    {
        $script = $_SERVER['SCRIPT_FILENAME'] ?? '';
        $dir  = $script !== '' ? dirname((string)(realpath($script) ?: $script)) : (string)getcwd();
        $base = basename($dir);
        foreach ([$base . '.ico', $base . '.png', 'icon.ico', 'icon.png', 'favicon.ico', 'favicon.png'] as $n) {
            if (is_file($dir . DIRECTORY_SEPARATOR . $n)) return $dir . DIRECTORY_SEPARATOR . $n;
        }
        return '';
    }

    public function run(): void
    {
        $exe  = findVspk();
        $html = $this->buildHtml();
        $icon = $this->findIcon();

        $htv = sys_get_temp_dir() . DIRECTORY_SEPARATOR . 'vspk_' . getmypid() . '_' . bin2hex(random_bytes(3)) . '.htv';
        file_put_contents($htv,
            "title: {$this->title}\nwidth: {$this->width}\nheight: {$this->height}\ndevtools: true\n"
            . ($icon !== '' ? "icon: {$icon}\n" : '')
            . ($this->onClose !== '' ? "on_close: {$this->onClose}\n" : ($this->closeOn ? "on_close: confirm\n" : ''))
            . "\n" . $html
        );

        $proc = @proc_open([$exe, $htv], [0 => STDIN, 1 => STDOUT, 2 => STDERR], $pipes);
        if (!is_resource($proc)) {
            @unlink($htv);
            throw new \RuntimeException("[vspk.php] No se pudo lanzar {$exe}");
        }

        $exit = 0;
        $this->running = true;
        foreach ($this->wins as $w) if ($w->want) $this->winOpen($w);
        try {
            while (!$this->quit) {
                $st = proc_get_status($proc);
                if (!$st['running']) {
                    $exit = $st['exitcode'];
                    break;
                }
                $this->bridge->pump(0.015);
                $this->dispatch();
                $this->runTimers();
            }
            if ($this->quit) {
                proc_terminate($proc);
                $exit = 0;
            }
        } finally {
            // Al cerrar la principal se cierran las demás.
            foreach ($this->wins as $w) if ($w->isOpen()) $this->winEval($w, '__vspk.close()');
            if ($this->wins) { $t = microtime(true); while (microtime(true) - $t < 0.3) { $this->bridge->pump(0.02); } }
            foreach ($this->wins as $w) {
                if (is_resource($w->proc)) { @proc_terminate($w->proc); @proc_close($w->proc); }
                if ($w->htv !== '') @unlink($w->htv);
            }
            $this->bridge->close();
            $code = proc_close($proc);
            if ($exit === -1) $exit = $code;
            @unlink($htv);
        }

        if ($exit !== 0 && $exit !== -1) {
            $err = "vspk terminó con código {$exit}";
            fwrite(STDERR, "[vspk.php] {$err}\n");
            throw new \RuntimeException($err);
        }
    }
}
