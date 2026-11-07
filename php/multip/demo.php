<?php
declare(strict_types=1);
require is_file(__DIR__ . '/vspk.php') ? __DIR__ . '/vspk.php' : __DIR__ . '/../vspk.php';
use function Vspk\{Col,MenuBar,Menu,MenuItem,MenuSep,Card,H2,H3,H4,P,Row,Hr,Input,Checkbox,Select,Progress,Chip,Alert,Badge,Tabs,Modal,Slider};

$app = new Vspk\App('Demo vspk', 520, 720);
$n      = $app->state('n', 0);
$pct    = $app->state('pct', 0);
$nombre = $app->state('nombre', '');
$acepto = $app->state('acepto', false);
$color  = $app->state('color', 'azul');
$res    = $app->state('res', '—');
$vol    = $app->state('vol', 30);
$open   = $app->state('open', false);
$log    = $app->state('log', '—');
$tecla  = $app->state('tecla', '—');
$ticks  = $app->state('ticks', 0);
$arch   = $app->state('arch', '—');
$raton  = $app->state('raton', '—');
$lienzo = $app->canvas('lienzo', 300, 150);
$lienzo->color('#6750A4')->rect(10, 10, 100, 60);
$lienzo->color('#B3261E')->circle(200, 60, 40);
$lienzo->color('#000000')->lineWidth(2)->line(0, 0, 300, 150);
$lienzo->font(16)->text(10, 140, 'Spork');
$lienzo->onMouse(fn($e) => $raton->set("{$e['type']} {$e['x']},{$e['y']}"));
$nombre->onChange(fn($v) => fwrite(STDERR, "onChange nombre=$v\n"));

$ajustes = $app->newWindow('Ajustes', 360, 240);
$ajustes->add(Col(H4('Ajustes (otra ventana)'), Input('Tu nombre (compartido)', $nombre), P($nombre)));

$tarjeta = Card(
  H2('Demo'),
  Row($app->Button('-', fn() => $n->dec(), 'outlined'), H3($n), $app->Button('+', fn() => $n->inc())),
  Input('Nombre', $nombre), P($nombre),
  Checkbox('Acepto', $acepto),
  Select([['azul','Azul'],['verde','Verde'],['rojo','Rojo']], $color), P($color),
  Progress($pct), $app->Button('+10%', fn() => $pct->set(min(100, $pct->get()+10))),
  Slider($vol), Tabs([['label'=>'A','content'=>'uno'],['label'=>'B','content'=>P('dos')]]),
  Modal('Hola', P('cuerpo'), [], $open),
  $app->Button('Enviar', function() use ($res,$nombre,$acepto,$color,$app) {
      $res->set("nombre={$nombre->get()}  acepto=" . ($acepto->get() ? 'true':'false') . "  color={$color->get()}");
      $app->toast('Enviado', 'success');
  }),
  $app->Button('Boom', function() { throw new RuntimeException('prueba'); }),
  P($res),
  H4('9. Teclado, diálogos, temporizador, ventana'),
  P($tecla),
  Row(P('ticks:'), H3($ticks)),
  Row(
    $app->Button('Abrir archivo...', fn() => $app->pickFile('Elige un archivo', fn($p) => $arch->set("archivo: $p"))),
    $app->Button('Cambiar título', fn() => $app->setTitle('Hola desde PHP')),
    $app->Button('Notificar', fn() => $app->notify('PHP', 'Hecho'), 'outlined')
  ),
  P($arch),
  P($log),
  H4('10. Canvas'),
  $lienzo,
  P($raton),
  Row(
    $app->Button('Limpiar', fn() => $lienzo->erase(), 'outlined'),
    $app->Button('Dibujar', function() use ($lienzo) { $lienzo->color('#00AA00')->circle(150, 75, 20); })
  )
);

// Los menús se crean después de la tarjeta (los ids de callback siguen el orden de creación).
$menu = MenuBar(
  Menu('Archivo',
    MenuItem('Abrir ventana de ajustes', $app->onClick(fn() => $ajustes->show()), 'ctrl+shift+a'),
    MenuSep(),
    MenuItem('Cerrar ajustes', $app->onClick(fn() => $ajustes->close()))
  ),
  Menu('Ayuda', MenuItem('Acerca de', $app->onClick(fn() => $log->set('acerca de'))))
);
$app->add($menu, $tarjeta);
$app->onKey(fn($e) => $tecla->set('tecla: ' . $e['key']));
$app->onClose(function() use ($log) { $log->set('cerrando'); return true; });
$app->every(1000, fn() => $ticks->inc());
$app->run();
echo "run() terminado\n";
