<?php
require 'vspk.php';
use function Vspk\{Col, Row, Card, H1, H2, H3, P, Hr, Alert, Progress, Chip, Input, Select, Checkbox};

$app = new Vspk\App("Demo vspk", width: 500, height: 700, theme: "dark", primary: "#7c3aed");

$count  = $app->state("count",  0);
$nombre = $app->state("nombre", "");
$plan   = $app->state("plan",   "free");
$activo = $app->state("activo", true);

$app->add(Col(
    H1("Demo vspk"),
    P("Todo lo que puedes hacer ahora"),
    Hr(),

    H2("Contador"),
    H1($count),
    Progress($count),
    Row(
        $app->Button("+1",    js: $count->jsInc(),    variant: "filled",   size: "lg"),
        $app->Button("Reset", js: $count->jsSet("0"), variant: "outlined"),
        $app->Button("-1",    js: $count->jsDec(),    variant: "danger",   size: "sm"),
    ),
    Hr(),

    H2("Input reactivo"),
    Input(placeholder: "Escribe tu nombre...", bind: $nombre),
    H3($nombre),
    Hr(),

    H2("Select"),
    Select(
        [["free","Plan Gratuito"], ["pro","Plan Pro"], ["biz","Plan Business"]],
        bind: $plan,
    ),
    Alert($plan),
    Hr(),

    H2("Cards"),
    Card(
        Row(H3("Spork vspk"), Chip("v1.0", primary: true), Chip("Beta")),
        P("GUI nativa para PHP. Tauri pero con PHP."),
        Row(
            $app->Button("Docs",   variant: "text"),
            $app->Button("GitHub", variant: "outlined", size: "sm"),
        ),
    ),
    Hr(),

    H2("Alertas"),
    Alert("Todo correcto — operación completada."),
    Alert("¡Algo salió mal!", variant: "error"),
    Hr(),

    H2("Checkbox"),
    Checkbox("Activar modo avanzado", bind: $activo),
));

$app->run();
