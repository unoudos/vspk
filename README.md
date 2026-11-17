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

## API nativa de vspk.exe en los bindings (nov 2026)

Python, JS, Spork, C, Go, PHP y V comparten el mismo modelo: llamadas **asíncronas** que ejecutan `__vspk.*` en la página y devuelven el resultado a tu código por callback.

| Grupo | Funciones (nombre según el lenguaje: `sql_open` / `sqlOpen` / `SQLOpen`…) |
|---|---|
| Genérico | `call(expr_js, cb)` · `invoke(cmd, args, cb)` — cualquier comando nuevo de vspk.exe sin esperar a un binding |
| SQLite | `sql_open` · `sql_exec` · `sql_query` · `sql_close` |
| Procesos | `proc_open(ruta, on_line, on_exit/…)` · `proc_send` · `proc_close` — ejecutable/script de la carpeta de la app |
| Serie / BLE | `serial_list` · `ble_scan` · `serial_open` · `serial_write` · `serial_close` (`"ble:<id>"` como puerto) |
| Red / sistema | `ping` · `wifi_scan` · `http_fetch` · `env` · `clipboard_read` |
| Ficheros | `read_file` · `write_file` · `file_exists` · `read_dir` |

Estado: Python, JS, C y Go probados con simulación del bridge; Spork solo analizado sintácticamente; PHP y V escritos pero sin compilar. Fortran usa `vspk.h` (cabecera actualizada) pero su envoltorio `vspk.f90` sigue exponiendo solo lo básico.
