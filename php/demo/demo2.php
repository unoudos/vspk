<?php
declare(strict_types=1);
require __DIR__ . '/vspk.php';
use function Vspk\{Card,H2,H3,H4,P,Row,Hr,Input,Checkbox,Select,Progress,Chip,Alert,Badge,Tabs,Modal,Slider};

$app = new Vspk\App('Demo vspk', 520, 720);
$n      = $app->state('n', 0);
$pct    = $app->state('pct', 0);
$nombre = $app->state('nombre', '');
$acepto = $app->state('acepto', false);
$color  = $app->state('color', 'azul');
$res    = $app->state('res', '—');
$vol    = $app->state('vol', 30);
$open   = $app->state('open', false);
$nombre->onChange(fn($v) => fwrite(STDERR, "onChange nombre=$v\n"));

$app->add(Card(
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
  P($res)
));
$app->after(300, fn() => $n->set(100));
$app->run();
echo "run() terminado\n";
