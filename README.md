# vspk

Ventana nativa ligera (tao/wry) para apps web/HTML, con bindings para varios lenguajes.
Un mismo `vspk` se usa desde C, Fortran, Go, JavaScript, PHP, Python, Spork y V.

Cada carpeta contiene el binding de un lenguaje y sus demos:

| Carpeta   | Lenguaje |
|-----------|----------|
| `c/`      | C        |
| `fortran/`| Fortran  |
| `go/`     | Go       |
| `js/`     | JavaScript |
| `php/`    | PHP      |
| `python/` | Python   |
| `spork/`  | Spork    |
| `v-lang/` | V        |

Los binarios (`*.exe`, `*.jar`) no se versionan; se generan con cada toolchain.

Formato de paquete: `.wsk` (ZIP sin compresión con `app.htv`/`app.htx`, `assets/`, `pkg/`, `backend.ts`).

by @uno_u_dos · https://github.com/unoudos
