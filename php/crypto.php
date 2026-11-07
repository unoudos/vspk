<?php
declare(strict_types=1);

require __DIR__ . '/vspk.php';

use Vspk\App;
use function Vspk\{Card, H1, H2, P, Select};

$app    = new App('CryptoPulse Tracker', width: 550, height: 460, theme: 'light', primary: '10b981');
$price  = $app->state('price',  'Cargando...');
$change = $app->state('change', '');
$crypto = $app->state('crypto', 'bitcoin');

// Widget para inyectar <script> en el HTML
$scriptWidget = new class extends \Vspk\Widget {
    public function tag(): string { return 'div'; }
    public function render(): string {
        return <<<'JS'
<script>
async function fetchCryptoPrice() {
    const asset = window.__state.crypto || 'bitcoin';
    const url   = 'https://api.coingecko.com/api/v3/simple/price?ids='
                + encodeURIComponent(asset)
                + '&vs_currencies=usd&include_24hr_change=true';
    try {
        // __vspk.fetch() — proxy nativo de vspk, sin restricciones CORS
        const text = await __vspk.fetch(url);
        const data = JSON.parse(typeof text === 'string' ? text : text.body);
        const quote = data?.[asset];
        if (!quote || typeof quote.usd !== 'number') throw new Error('Respuesta inválida');

        Spork.set('price', '$' + quote.usd.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 8
        }));

        const pct = quote.usd_24h_change;
        Spork.set('change', typeof pct === 'number'
            ? (pct >= 0 ? '+' : '') + pct.toFixed(2) + '% en 24 h'
            : '');
    } catch (e) {
        Spork.set('price',  'Error: ' + e.message);
        Spork.set('change', '');
        console.error('CoinGecko:', e);
    }
}

// Esperar a que __vspk esté disponible (lo inyecta vspk como init script)
function waitAndFetch() {
    if (typeof __vspk !== 'undefined' && typeof Spork !== 'undefined') {
        fetchCryptoPrice();
        setInterval(fetchCryptoPrice, 20000);
    } else {
        setTimeout(waitAndFetch, 100);
    }
}
waitAndFetch();

// Re-fetch cuando cambia el activo seleccionado (Select usa data-spork-bind)
document.addEventListener('change', function(e) {
    if (e.target.dataset.sporkBind === 'crypto') fetchCryptoPrice();
});
</script>
JS;
    }
};

$app->add(
    H1('CryptoPulse Live'),
    P('Precio en tiempo real desde CoinGecko.'),
    Card(
        H2('Activo seleccionado'),
        Select([
            ['bitcoin',  'Bitcoin (BTC)'],
            ['ethereum', 'Ethereum (ETH)'],
            ['solana',   'Solana (SOL)'],
            ['cardano',  'Cardano (ADA)'],
        ], bind: $crypto),
        P($price),
        P($change),
        $app->Button('Actualizar ahora', js: 'fetchCryptoPrice()'),
    ),
    $scriptWidget,
);

$app->run();
