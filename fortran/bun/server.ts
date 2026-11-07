import { dlopen, FFIType, suffix } from "bun:ffi";
import { join } from "path";

// 1. Cargar la librería de Fortran compilada
const path = join(import.meta.dir, `libmath.${suffix}`);
const lib = dlopen(path, {
  sumar: {
    args: [FFIType.i32, FFIType.i32],
    returns: FFIType.i32,
  },
});

// 2. Levantar el servidor HTTP con Bun
const server = Bun.serve({
  port: 3000,
  fetch(req) {
    // Llamamos a la función de Fortran (ej. sumar 20 + 22)
    const resultadoFortran = lib.symbols.sumar(20, 22);

    // Devolvemos una respuesta HTML con el resultado incrustado
    const html = `
      <!DOCTYPE html>
      <html lang="es">
      <head>
        <meta charset="UTF-8">
        <title>Bun + Fortran</title>
        <style>
          body { font-family: system-ui; text-align: center; margin-top: 50px; background: #0f172a; color: white; }
          .card { background: #1e293b; padding: 30px; border-radius: 12px; display: inline-block; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
          h1 { color: #38bdf8; }
        </style>
      </head>
      <body>
        <div class="card">
          <h1>Resultado desde Fortran</h1>
          <p>El cálculo de 20 + 22 procesado por Fortran y servido por Bun es:</p>
          <h2>${resultadoFortran}</h2>
        </div>
      </body>
      </html>
    `;

    return new Response(html, {
      headers: { "Content-Type": "text/html; charset=utf-8" },
    });
  },
});

console.log(`Servidor corriendo en http://localhost:${server.port}`);