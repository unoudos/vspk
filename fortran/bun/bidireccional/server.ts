import { dlopen, FFIType, suffix } from "bun:ffi";
import { join } from "path";

// Cargar la librería de Fortran
const path = join(import.meta.dir, `libmath.${suffix}`);
const lib = dlopen(path, {
  sumar: {
    args: [FFIType.i32, FFIType.i32],
    returns: FFIType.i32,
  },
});

const server = Bun.serve({
  port: 3000,
  async fetch(req) {
    const url = new URL(req.url);

    // Ruta para procesar el cálculo que envía el navegador
    if (url.pathname === "/calcular" && req.method === "POST") {
      try {
        const body = await req.json();
        const num1 = parseInt(body.a) || 0;
        const num2 = parseInt(body.b) || 0;

        // Llamada ultrarrápida a Fortran vía FFI
        const resultado = lib.symbols.sumar(num1, num2);

        return Response.json({ resultado });
      } catch (e) {
        return Response.json({ error: "Datos inválidos" }, { status: 400 });
      }
    }

    // Página HTML principal con la interfaz de usuario
    const html = `
      <!DOCTYPE html>
      <html lang="es">
      <head>
        <meta charset="UTF-8">
        <title>Bun + Fortran Bidireccional</title>
        <style>
          body { font-family: system-ui; text-align: center; margin-top: 50px; background: #0f172a; color: white; }
          .card { background: #1e293b; padding: 30px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
          input { padding: 8px; width: 80px; text-align: center; font-size: 16px; border-radius: 6px; border: 1px solid #475569; background: #334155; color: white; }
          button { padding: 9px 16px; font-size: 16px; background: #38bdf8; color: #0f172a; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; }
          button:hover { background: #7dd3fc; }
          h1 { color: #38bdf8; }
          .result { font-size: 24px; margin-top: 20px; color: #4ade80; }
        </style>
      </head>
      <body>
        <div class="card">
          <h1>Motor Fortran en la Web</h1>
          <p>Introduce dos números para sumarlos usando Fortran a través de Bun:</p>
          <input type="number" id="a" value="10"> + 
          <input type="number" id="b" value="32">
          <br><br>
          <button onclick="calcular()">Calcular en Fortran</button>
          <div class="result" id="res">Resultado: --</div>
        </div>

        <script>
          async function calcular() {
            const a = document.getElementById('a').value;
            const b = document.getElementById('b').value;

            const response = await fetch('/calcular', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ a, b })
            });

            const data = await response.json();
            document.getElementById('res').innerText = "Resultado: " + data.resultado;
          }
        </script>
      </body>
      </html>
    `;

    return new Response(html, {
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  },
});

console.log(`Servidor activo en http://localhost:${server.port}`);