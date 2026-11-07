<?php
require 'vspk.php';
use function Vspk\{Row, Card, H1, H2, P, Hr, Spacer, Select};

$app = new Vspk\App("CryptoPulse Tracker", width: 550, height: 460, theme: "dark", primary: "#10b981");

$price  = $app->state("price",  "Cargando...");
$change = $app->state("change", "");
$crypto = $app->state("crypto", "bitcoin");

$app->add(
    Card(
        H2("🪙 CryptoPulse Live"),
        P("Precios en tiempo real vía CoinGecko"),
        Hr(),
        Spacer(),

        // onAfterChange dispara fetchPrice() después de actualizar el estado
        Select([
            ["bitcoin",  "Bitcoin (BTC)"],
            ["ethereum", "Ethereum (ETH)"],
            ["solana",   "Solana (SOL)"],
            ["cardano",  "Cardano (ADA)"],
        ], bind: $crypto, onAfterChange: "setTimeout(fetchPrice, 50)"),

        Spacer(),
        H1($price),
        P($change),
        Spacer(),

        Row(
            $app->Button("Actualizar", js: "fetchPrice()", variant: "filled"),
        )
    ),

    new class extends Vspk\Widget {
        public function tag(): string { return 'div'; }
        public function render(): string {
            return <<<'JS'
<script>
function fetchPrice() {
    if (typeof __vspk === 'undefined' || typeof Spork === 'undefined') {
        setTimeout(fetchPrice, 100);
        return;
    }

    var coin = window.__state.crypto || 'bitcoin';
    var url  = 'https://api.coingecko.com/api/v3/simple/price'
             + '?ids=' + coin
             + '&vs_currencies=eur'
             + '&include_24hr_change=true';

    __vspk.fetch(url)
        .then(function(res) {
            var data = JSON.parse(typeof res === 'string' ? res : res.body);
            var info = data[coin];
            if (!info) { Spork.set('price', 'Sin datos'); return; }

            var price = info.eur != null
                ? info.eur.toLocaleString('es-ES', {minimumFractionDigits: 2}) + ' €'
                : '---';
            var chg = info.eur_24h_change != null
                ? (info.eur_24h_change > 0 ? '▲ ' : '▼ ')
                  + Math.abs(info.eur_24h_change).toFixed(2) + '% (24h)'
                : '';

            Spork.set('price',  price);
            Spork.set('change', chg);
        })
        .catch(function(err) {
            Spork.set('price',  'Error de red');
            Spork.set('change', err.message || '');
        });
}

setTimeout(fetchPrice, 300);
setInterval(fetchPrice, 15000);
</script>
JS;
        }
    }
);

$app->run();
