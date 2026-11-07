<?php
require 'vspk.php';

$app = new Vspk\App("Contador Nativo PHP", width: 450, height: 320, theme: "dark", primary: "#7c3aed");

$count = $app->state("count", 0);

$app->add(
    Vspk\Card(
        Vspk\H2("Contador Reactivo"),
        Vspk\P("Aplicación nativa controlada desde PHP"),
        Vspk\Hr(),
        Vspk\H1($count),
        Vspk\Spacer(),
        Vspk\Row(
            $app->Button("-1",    js: $count->jsDec(1),    variant: "outlined"),
            $app->Button("Reset", js: $count->jsSet("0"),  variant: "danger"),
            $app->Button("+1",    js: $count->jsInc(1),    variant: "filled"),
        )
    )
);

$app->run();
