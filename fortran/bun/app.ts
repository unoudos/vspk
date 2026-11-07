import { dlopen, FFIType, suffix } from "bun:ffi";
import { join } from "path";

// Cargar la librería compilada desde Fortran
const path = join(import.meta.dir, `libmath.${suffix}`);

const lib = dlopen(path, {
  sumar: {
    args: [FFIType.i32, FFIType.i32],
    returns: FFIType.i32,
  },
});

// ¡Llamar a Fortran desde JavaScript como si fuera una función local!
const resultado = lib.symbols.sumar(40, 2);

console.log(`Resultado calculado en Fortran: ${resultado}`); // 42