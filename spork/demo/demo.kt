// Generado por Spork (target kt) desde demo.spk
// No editar a mano — se regenera en cada compilación con: spork build kt demo.spk
@file:Suppress("UNCHECKED_CAST", "NAME_SHADOWING", "UNUSED_VARIABLE", "USELESS_CAST", "REDUNDANT_CALL_OF_CONVERSION_METHOD")

class SporkError(message: String) : Exception(message) {
    override fun toString(): String = "Error: $message"
}

// ── Runtime dinámico — operandos sin tipo estático conocido ─────────────────
// Generado porque este archivo mezcla aritmética con parámetros o retornos
// sin tipo declarado en el .spk. Equivalente ligero del SporkValue +
// spork_add/sub/mul/div del target Rust: solo entra en juego para los
// valores dinámicos — todo lo demás sigue siendo Kotlin nativo normal.
private fun __sporkNum(v: Any?): Double = when (v) {
    is Int -> v.toDouble()
    is Long -> v.toDouble()
    is Double -> v
    is Float -> v.toDouble()
    is java.math.BigInteger -> v.toDouble()
    is String -> v.toDoubleOrNull() ?: 0.0
    is Boolean -> if (v) 1.0 else 0.0
    else -> 0.0
}
// Coacciona cualquier valor dinámico a BigInteger SIN pasar por Double
// — a diferencia de __sporkNum, que trunca cualquier BigInteger a
// Double (y con él, toda la precisión de un entero de más de 15-17
// dígitos). Usado por sporkAdd/Sub/Mul/Div/Mod cuando detectan que
// alguno de los dos lados YA es BigInteger: ahí hay que mantener el
// otro lado también como BigInteger de punta a punta, en vez de volver
// a Double para la operación y perder justo la precisión por la que se
// usó BigInteger/i128/u128 en primer lugar. Bug real (sum.spk):
// "n + 1n" con "n" un BigInteger de 70 dígitos pasado vía bigint() —
// antes de este fix, sporkAdd solo miraba Int/String y caía al
// else -> __sporkNum(a) + __sporkNum(b), que convertía el BigInteger a
// Double y devolvía un resultado truncado/aproximado.
private fun __sporkBig(v: Any?): java.math.BigInteger = when (v) {
    is java.math.BigInteger -> v
    is Int -> java.math.BigInteger.valueOf(v.toLong())
    is Long -> java.math.BigInteger.valueOf(v)
    is Double -> v.toBigDecimal().toBigInteger()
    is Float -> v.toDouble().toBigDecimal().toBigInteger()
    is String -> v.toBigIntegerOrNull() ?: java.math.BigInteger.ZERO
    is Boolean -> if (v) java.math.BigInteger.ONE else java.math.BigInteger.ZERO
    else -> java.math.BigInteger.ZERO
}
private fun sporkAdd(a: Any?, b: Any?): Any? = when {
    a is java.math.BigInteger || b is java.math.BigInteger -> __sporkBig(a) + __sporkBig(b)
    a is String || b is String -> "${a}${b}"
    a is Int && b is Int       -> a + b
    else                        -> __sporkNum(a) + __sporkNum(b)
}
private fun sporkSub(a: Any?, b: Any?): Any? = when {
    a is java.math.BigInteger || b is java.math.BigInteger -> __sporkBig(a) - __sporkBig(b)
    a is Int && b is Int -> a - b
    else -> __sporkNum(a) - __sporkNum(b)
}
private fun sporkMul(a: Any?, b: Any?): Any? = when {
    a is java.math.BigInteger || b is java.math.BigInteger -> __sporkBig(a) * __sporkBig(b)
    a is Int && b is Int -> a * b
    else -> __sporkNum(a) * __sporkNum(b)
}
private fun sporkDiv(a: Any?, b: Any?): Any? = when {
    a is java.math.BigInteger || b is java.math.BigInteger -> {
        val bb = __sporkBig(b)
        if (bb == java.math.BigInteger.ZERO) 0.0 else __sporkBig(a) / bb
    }
    a is Int && b is Int && b != 0 && a % b == 0 -> a / b
    else -> __sporkNum(a) / __sporkNum(b)
}
private fun sporkMod(a: Any?, b: Any?): Any? = when {
    a is java.math.BigInteger || b is java.math.BigInteger -> __sporkBig(a) % __sporkBig(b)
    a is Int && b is Int -> a % b
    else -> __sporkNum(a) % __sporkNum(b)
}
// '<'/'>'/'<='/'>=' sobre Any? no compilan en Kotlin (Any? no implementa
// Comparable) — a diferencia de sporkAdd, aquí no hace falta el caso
// especial de String porque, igual que en sporkSub/Mul/Div/Mod, solo se
// usan cuando al menos un lado es dinámico de origen numérico (contador
// de bucle, resultado de int()/parse_int, etc.); si algún día hace falta
// comparar Strings dinámicos habrá que añadir ese caso aquí también.
// Igual que arriba, con BigInteger de por medio se compara vía
// __sporkBig (no __sporkNum) para no perder precisión en la propia
// comparación.
private fun sporkLt(a: Any?, b: Any?): Boolean =
    if (a is java.math.BigInteger || b is java.math.BigInteger) __sporkBig(a) < __sporkBig(b) else __sporkNum(a) < __sporkNum(b)
private fun sporkGt(a: Any?, b: Any?): Boolean =
    if (a is java.math.BigInteger || b is java.math.BigInteger) __sporkBig(a) > __sporkBig(b) else __sporkNum(a) > __sporkNum(b)
private fun sporkLte(a: Any?, b: Any?): Boolean =
    if (a is java.math.BigInteger || b is java.math.BigInteger) __sporkBig(a) <= __sporkBig(b) else __sporkNum(a) <= __sporkNum(b)
private fun sporkGte(a: Any?, b: Any?): Boolean =
    if (a is java.math.BigInteger || b is java.math.BigInteger) __sporkBig(a) >= __sporkBig(b) else __sporkNum(a) >= __sporkNum(b)

// ── Runtime JSON — sin dependencias externas (Gson no está disponible) ──────
private fun __sporkJsonEscape(s: String): String {
    val sb = StringBuilder()
    for (c in s) {
        when (c) {
            '"' -> sb.append("\\\"")
            '\\' -> sb.append("\\\\")
            '\n' -> sb.append("\\n")
            '\r' -> sb.append("\\r")
            '\t' -> sb.append("\\t")
            else -> sb.append(c)
        }
    }
    return sb.toString()
}
private fun __sporkToJson(v: Any?): String = when (v) {
    null -> "null"
    is String -> "\"" + __sporkJsonEscape(v) + "\""
    is Boolean -> v.toString()
    is Int, is Long, is Double, is Float, is java.math.BigInteger -> v.toString()
    is Map<*, *> -> "{" + v.entries.joinToString(",") { (k, vv) -> "\"" + __sporkJsonEscape(k.toString()) + "\":" + __sporkToJson(vv) } + "}"
    is List<*> -> "[" + v.joinToString(",") { __sporkToJson(it) } + "]"
    else -> "\"" + __sporkJsonEscape(v.toString()) + "\""
}
private class __SporkJsonParser(val s: String) {
    var i = 0
    fun parse(): Any? { skipWs(); return parseValue() }
    private fun skipWs() { while (i < s.length && s[i].isWhitespace()) i++ }
    private fun parseValue(): Any? {
        skipWs()
        return when {
            i >= s.length -> null
            s[i] == '{' -> parseObject()
            s[i] == '[' -> parseArray()
            s[i] == '"' -> parseString()
            s.startsWith("true", i) -> { i += 4; true }
            s.startsWith("false", i) -> { i += 5; false }
            s.startsWith("null", i) -> { i += 4; null }
            else -> parseNumber()
        }
    }
    private fun parseObject(): MutableMap<String, Any?> {
        val m = mutableMapOf<String, Any?>()
        i++
        skipWs()
        if (i < s.length && s[i] == '}') { i++; return m }
        while (true) {
            skipWs()
            val k = parseString()
            skipWs(); i++
            m[k] = parseValue()
            skipWs()
            if (i < s.length && s[i] == ',') { i++; continue }
            break
        }
        skipWs(); i++
        return m
    }
    private fun parseArray(): MutableList<Any?> {
        val l = mutableListOf<Any?>()
        i++
        skipWs()
        if (i < s.length && s[i] == ']') { i++; return l }
        while (true) {
            l.add(parseValue())
            skipWs()
            if (i < s.length && s[i] == ',') { i++; continue }
            break
        }
        skipWs(); i++
        return l
    }
    private fun parseString(): String {
        i++
        val sb = StringBuilder()
        while (i < s.length && s[i] != '"') {
            if (s[i] == '\\' && i + 1 < s.length) {
                i++
                when (s[i]) {
                    'n' -> sb.append('\n')
                    't' -> sb.append('\t')
                    'r' -> sb.append('\r')
                    else -> sb.append(s[i])
                }
            } else sb.append(s[i])
            i++
        }
        i++
        return sb.toString()
    }
    private fun parseNumber(): Any {
        val start = i
        if (i < s.length && (s[i] == '-' || s[i] == '+')) i++
        while (i < s.length && (s[i].isDigit() || s[i] == '.' || s[i] == 'e' || s[i] == 'E' || s[i] == '+' || s[i] == '-')) i++
        val numStr = s.substring(start, i)
        return if (numStr.contains('.') || numStr.contains('e') || numStr.contains('E')) numStr.toDouble()
               else (numStr.toIntOrNull() ?: numStr.toLong())
    }
}
private fun __sporkFromJson(s: String): Any? = __SporkJsonParser(s).parse()

// ── Acceso a propiedad dinámico — obj.campo sobre hash o struct ────────────
private fun __sporkHtmlEscape(s: Any?): String = s.toString().replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"'.toString(), "&quot;").replace("'", "&#39;")
@Suppress("UNCHECKED_CAST")
fun __sporkProp(obj: Any?, prop: String): Any? {
    if (obj == null) return null
    if (obj is Map<*, *>) return when (prop) {
        // Métodos de mapa que Spork llama como obj.method()
        "entries" -> ({ -> obj.entries.map { listOf(it.key, it.value) } } as () -> Any?)
        "keys"    -> ({ -> obj.keys.toList() } as () -> Any?)
        "values"  -> ({ -> obj.values.toList() } as () -> Any?)
        "has"     -> ({ k: Any? -> obj.containsKey(k) } as (Any?) -> Any?)
        "size", "length" -> obj.size
        else      -> obj[prop]
    }
    if (obj is List<*>) return when (prop) {
        "size", "length" -> obj.size
        "join"    -> ({ sep: Any? -> obj.joinToString(sep?.toString() ?: "") } as (Any?) -> Any?)
        "push"    -> ({ v: Any? -> (obj as MutableList<Any?>).add(v) } as (Any?) -> Any?)
        "includes", "contains" -> ({ v: Any? -> obj.contains(v) } as (Any?) -> Any?)
        "reverse" -> ({ -> (obj as MutableList<Any?>).reversed() } as () -> Any?)
        "first"   -> obj.firstOrNull()
        "last"    -> obj.lastOrNull()
        else      -> null
    }
    if (obj is String) return when (prop) {
        "length", "size" -> obj.length
        else -> null
    }
    return try {
        val field = obj.javaClass.getDeclaredField(prop)
        field.isAccessible = true
        field.get(obj)
    } catch (_: Exception) { null }
}

// ── Indexación dinámica — obj[idx] sobre un valor sin tipo conocido ────────
private fun __sporkIndex(obj: Any?, idx: Any?): Any? = try {
    when (obj) {
        is List<*>   -> obj[__sporkNum(idx).toInt()]
        is Map<*, *>  -> obj[idx]
        is String    -> obj[__sporkNum(idx).toInt()].toString()
        else          -> null
    }
} catch (e: Exception) { null }
@Suppress("UNCHECKED_CAST")
private fun __sporkSetIndex(obj: Any?, idx: Any?, v: Any?) {
    when (obj) {
        is MutableList<*> -> (obj as MutableList<Any?>)[__sporkNum(idx).toInt()] = v
        is MutableMap<*, *> -> (obj as MutableMap<Any?, Any?>)[idx] = v
        else -> {}
    }
}

// ── Invocación dinámica de un callee arbitrario — hola()(), arr[0](), etc. ─
private fun __sporkCall(fn: Any?, args: List<Any?>): Any? {
    if (fn == null) return null
    return try {
        when (args.size) {
            0 -> (fn as Function0<Any?>)()
            1 -> (fn as Function1<Any?, Any?>)(args[0])
            2 -> (fn as Function2<Any?, Any?, Any?>)(args[0], args[1])
            3 -> (fn as Function3<Any?, Any?, Any?, Any?>)(args[0], args[1], args[2])
            4 -> (fn as Function4<Any?, Any?, Any?, Any?, Any?>)(args[0], args[1], args[2], args[3])
            else -> throw SporkError("__sporkCall: aridad no soportada (${args.size} argumentos)")
        }
    } catch (e: ClassCastException) {
        // Función vararg (::add, ::spawn…): en JVM la referencia tiene firma
        // Function1<Array<Any?>, Any?> — pasar todos los args como array.
        @Suppress("UNCHECKED_CAST")
        (fn as Function1<Any?, Any?>)(args.toTypedArray())
    }
}
// Truthiness estilo Spork/Ruby: nil y false son falsy, todo lo demás truthy.
// Usado en condiciones de if/while cuando el test es un valor dinámico (Any?).
fun __sporkTruthy(v: Any?): Boolean = v != null && v != false
// Itera un resultado dinámico como Iterable<Any?> (p.ej. el retorno de __sporkCall).
@Suppress("UNCHECKED_CAST")
fun __sporkIter(v: Any?): Iterable<Any?> = v as Iterable<Any?>

// ── Prelude OS — filesystem, procesos, plataforma ───────────────────────────
private fun platform(): String = System.getProperty("os.name")?.lowercase()?.let {
    when { it.contains("win") -> "win32"; it.contains("mac") -> "darwin"; else -> "linux" }
} ?: "linux"
private fun f_exists_q(path: Any?): Boolean = java.io.File(path.toString()).exists()
private fun which(exe: Any?): String {
    val name = exe.toString()
    val paths = System.getenv("PATH")?.split(java.io.File.pathSeparator) ?: emptyList()
    for (dir in paths) {
        val f = java.io.File(dir, name)
        if (f.canExecute()) return f.absolutePath
    }
    return ""
}
private fun temp_file(prefix: Any?, suffix: Any?): String =
    java.io.File.createTempFile(prefix.toString(), suffix.toString()).absolutePath
private fun f_delete(path: Any?) { java.io.File(path.toString()).delete() }
// spawn — lanza un proceso y devuelve un objeto con .exited()
private class SporkProc(private val proc: Process) {
    fun exited(): Boolean = !proc.isAlive
    fun wait_exit(): Int = proc.waitFor()
}
@Suppress("UNCHECKED_CAST")
private fun spawn(args: Any?): SporkProc {
    val cmd = (args as List<Any?>).map { it.toString() }
    return SporkProc(ProcessBuilder(cmd).inheritIO().start())
}
// http_get — petición HTTP GET síncrona (JVM HttpURLConnection, sin deps)
// Sigue redirecciones 301/302/303/307/308 incluso entre HTTP↔HTTPS.
// HttpURLConnection NO sigue redirecciones cross-protocol automáticamente
// (bug histórico de Java). Solución canónica de Stack Overflow #1884230.
private fun http_get(url: Any?): String {
    var target = url.toString()
    val visited = mutableMapOf<String, Int>()
    while (true) {
        visited[target] = (visited[target] ?: 0) + 1
        if ((visited[target] ?: 0) > 5) throw RuntimeException("http_get: demasiadas redirecciones → $target")
        val base = java.net.URI.create(target)
        val conn = base.toURL().openConnection() as java.net.HttpURLConnection
        conn.requestMethod = "GET"
        conn.setRequestProperty("User-Agent", "Mozilla/5.0")
        conn.connectTimeout = 10_000
        conn.readTimeout    = 10_000
        conn.instanceFollowRedirects = false
        val code = conn.responseCode
        if (code in 301..303 || code == 307 || code == 308) {
            val loc = conn.getHeaderField("Location")
                ?: throw RuntimeException("http_get: redireccion $code sin Location")
            conn.disconnect()
            target = base.resolve(loc).toString()
            continue
        }
        return try {
            conn.inputStream.bufferedReader(Charsets.UTF_8).readText()
        } catch (e: Exception) {
            val err = conn.errorStream?.bufferedReader(Charsets.UTF_8)?.readText() ?: ""
            throw RuntimeException("http_get($url) → HTTP $code: $err")
        } finally {
            conn.disconnect()
        }
    }
}
// ── Puente vspk — implementación JVM con HttpServer del JDK ─────────────────
// El target Rust usa prelude.rs (WebView nativo). En JVM levantamos un
// servidor HTTP/SSE con com.sun.net.httpserver.HttpServer (JDK puro, sin deps)
// para que vspk.exe pueda conectarse y recibir actualizaciones de estado.
// Cada cliente SSE tiene su propia cola — push_sse encola el mensaje y el
// hilo del handler lo escribe desde su propio contexto (thread-safe).
private val __vspk_sse_queues  = java.util.concurrent.CopyOnWriteArrayList<java.util.concurrent.LinkedBlockingQueue<String>>()
private val __vspk_msg_queue   = java.util.concurrent.LinkedBlockingQueue<Map<String, Any?>>()
private val __vspk_state_cache = java.util.concurrent.ConcurrentHashMap<String, String>()
private var __vspk_started     = false
private fun vspk_bridge_start(port: Any?) {
    val p = __sporkNum(port).toInt()
    val srv = com.sun.net.httpserver.HttpServer.create(java.net.InetSocketAddress("127.0.0.1", p), 0)
    // SSE: el WebView conecta aquí y recibe eventos "state"/"eval"
    srv.createContext("/events") { ex ->
        ex.responseHeaders.add("Content-Type",                "text/event-stream")
        ex.responseHeaders.add("Cache-Control",               "no-cache")
        ex.responseHeaders.add("Access-Control-Allow-Origin", "*")
        ex.sendResponseHeaders(200, 0)
        val q   = java.util.concurrent.LinkedBlockingQueue<String>()
        val out = ex.responseBody.bufferedWriter(Charsets.UTF_8)
        __vspk_sse_queues.add(q)
        // Replay último valor de cada estado al nuevo cliente para que
        // el DOM quede en sync aunque SSE haya reconectado tarde
        for ((_, cached) in __vspk_state_cache) q.offer(cached)
        try {
            while (true) {
                // poll con timeout para detectar cierre del cliente
                val msg = q.poll(30, java.util.concurrent.TimeUnit.SECONDS)
                if (msg != null) { out.write(msg); out.flush() }
            }
        } catch (_: Exception) {}
        __vspk_sse_queues.remove(q)
    }
    // Callbacks: onclick="fetch('/cb/cb_1',{mode:'no-cors'})" → encola para poll()
    srv.createContext("/cb/") { ex ->
        ex.responseHeaders.add("Access-Control-Allow-Origin",  "*")
        ex.responseHeaders.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        if (ex.requestMethod == "OPTIONS") {
            ex.sendResponseHeaders(204, -1)
            return@createContext
        }
        val id = ex.requestURI.path.removePrefix("/cb/")
        val ok = "OK".toByteArray()
        ex.sendResponseHeaders(200, ok.size.toLong())
        ex.responseBody.use { it.write(ok) }
        __vspk_msg_queue.offer(mapOf("kind" to "cb", "id" to id))
    }
    // Eventos con cuerpo: POST /event/<nombre> (valores de Input/Checkbox/Select enlazados -> "__v")
    srv.createContext("/event/") { ex ->
        ex.responseHeaders.add("Access-Control-Allow-Origin",  "*")
        ex.responseHeaders.add("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        ex.responseHeaders.add("Access-Control-Allow-Headers", "*")
        if (ex.requestMethod == "OPTIONS") {
            ex.sendResponseHeaders(204, -1)
            return@createContext
        }
        val name = ex.requestURI.path.removePrefix("/event/")
        val body = ex.requestBody.readBytes().toString(Charsets.UTF_8)
        val ok = "OK".toByteArray()
        ex.sendResponseHeaders(200, ok.size.toLong())
        ex.responseBody.use { it.write(ok) }
        __vspk_msg_queue.offer(mapOf("kind" to "event", "name" to name, "body" to body))
    }
    // Favicon: 204 sin contenido en vez de 404 (la página ya declara link rel=icon data:,
    // pero cualquier cliente que lo pida igualmente no debe ver un error en consola)
    srv.createContext("/favicon.ico") { ex ->
        ex.responseHeaders.add("Access-Control-Allow-Origin", "*")
        ex.sendResponseHeaders(204, -1)
        ex.close()
    }
    srv.executor = java.util.concurrent.Executors.newCachedThreadPool()
    srv.start()
    __vspk_started = true
}
private fun vspk_bridge_push_sse(data: Any?) {
    // Antes de run() los set() pre-run son inofensivos: _states ya tiene el
    // valor y _build_html() lo serializa en window.__state del HTML inicial.
    if (!__vspk_started) return
    val msg = "$data"
    // Cachear eventos de estado para replay a clientes SSE que reconecten
    if (msg.startsWith("event: state\n")) {
        try {
            val dataLine = msg.lineSequence().firstOrNull { it.startsWith("data:") }
            if (dataLine != null) {
                val nameMatch = Regex(""""name"\s*:\s*"([^"]+)"""").find(dataLine)
                if (nameMatch != null) __vspk_state_cache[nameMatch.groupValues[1]] = msg
            }
        } catch (_: Exception) {}
    }
    for (q in __vspk_sse_queues) q.offer(msg)
}
private fun vspk_bridge_poll(): Any? = __vspk_msg_queue.poll()
private fun vspk_bridge_icon_dir(): String = try {
    java.io.File(object {}::class.java.protectionDomain.codeSource.location.toURI()).parent ?: ""
} catch (_: Exception) { "" }
// ── Utilidades XML (misma semántica que el prelude Python) ───────────────────
private fun xml_tag(text: Any?, tag: Any?): String {
    val t = text?.toString() ?: return "N/A"
    val g = tag?.toString() ?: return "N/A"
    if (t.isEmpty()) return "N/A"
    val re = Regex("<${g}(?:[^>]*)?>([^<]*)</${g}>")
    return re.find(t)?.groupValues?.get(1)?.trim() ?: "N/A"
}
private fun xml_section(text: Any?, tag: Any?): String {
    val t = text?.toString() ?: return ""
    val g = tag?.toString() ?: return ""
    if (t.isEmpty()) return ""
    val re = Regex("<${g}(?:[^>]*)?>(.+?)</${g}>", RegexOption.DOT_MATCHES_ALL)
    return re.find(t)?.value ?: ""
}

// ── import "vspk.spk" ──────────────────────────────────────────────
val SPORK_CSS = "spork.css"
val SPORK_JS = "spork.js"
val SPORK_CSS_CDN = "https://cdn.jsdelivr.net/gh/unoudos/spork-ui@main/spork.css"
val SPORK_JS_CDN = "https://cdn.jsdelivr.net/gh/unoudos/spork-ui@main/spork.js"
val _states = mutableMapOf<String, Any?>()
val _widgets = mutableListOf<Any?>()
val _callbacks = mutableMapOf<String, Any?>()
val _events = mutableMapOf<String, Any?>()
var _cb_count = 0
var _port = 0
var _title = ""
var _width = 1024
var _height = 768
var _theme = "light"
var _accent = ""
var _token = ""
var _key_on = false
var _close_on = false
var _running = false
var _icon_line = ""
val _timers = mutableListOf<Any?>()
val _cv_ids = mutableListOf<Any?>()
val _wins = mutableListOf<Any?>()
var _win_count = 0
val _cv_logs = mutableMapOf<String, Any?>()
var _cv_mouse_js = ""
fun find_vspk(): Any? {
    val exe = if (__sporkTruthy((platform() == "win32"))) "vspk.exe" else "vspk"
    val from_env = (System.getenv("VSPK_EXE") ?: "")
    if (((from_env != "") && f_exists_q(from_env))) {
        return from_env
    }
    val beside_script = (java.io.File(((java.io.File(((try { java.io.File(object {}::class.java.protectionDomain.codeSource.location.toURI()).parentFile?.absolutePath ?: System.getProperty("user.dir") } catch (_: Exception) { System.getProperty("user.dir") })).toString()).parent ?: "")).toString(), (exe).toString()).path)
    if (f_exists_q(beside_script)) {
        return beside_script
    }
    val beside_lib = (java.io.File(((try { java.io.File(object {}::class.java.protectionDomain.codeSource.location.toURI()).parentFile?.absolutePath ?: System.getProperty("user.dir") } catch (_: Exception) { System.getProperty("user.dir") })).toString(), (exe).toString()).path)
    if (f_exists_q(beside_lib)) {
        return beside_lib
    }
    val in_path = which(exe)
    if ((in_path != "")) {
        return in_path
    }
    return exe
}
fun html_escape(s: Any?): Any? {
    return ((((s).toString().replace("&", "&amp;")).replace("<", "&lt;")).replace(">", "&gt;")).replace("\"", "&quot;")
}
fun tag(t: Any?, css_class: Any?, attrs: Any?, vararg kids: Any?): Any? {
    val kids = kids.toList()
    val cls_attr = if (__sporkTruthy((css_class != ""))) " class=\"${css_class}\"" else ""
    val attrs_str = ((__sporkCall(__sporkProp(attrs, "entries"), listOf<Any?>()) as Iterable<Any?>).map { __e -> ({ kv: Any? ->     val k = __sporkIndex(kv, 0);     val v = __sporkIndex(kv, 1);     if ((((k == "onclick") || (k == "oninput")) || (k == "onchange"))) {
        " ${k}=\"${(v).toString().replace("\"", "&quot;")}\""
    } else {
        " ${k}=\"${__sporkHtmlEscape(v)}\""
    } } as (Any?) -> Any?)(__e) }.toMutableList()).joinToString("")
    val inner_ = ((kids as Iterable<Any?>).map { __e -> ({ c: Any? ->     if (((((when (val __tv = (c)) { null -> "null"; is Map<*, *> -> "hash"; is MutableList<*>, is List<*> -> "array"; is String -> "string"; is Boolean -> "bool"; is Int, is Long, is Double, is Float -> "number"; else -> (__tv::class.simpleName ?: "object") }) == "hash") || ((when (val __tv = (c)) { null -> "null"; is Map<*, *> -> "hash"; is MutableList<*>, is List<*> -> "array"; is String -> "string"; is Boolean -> "bool"; is Int, is Long, is Double, is Float -> "number"; else -> (__tv::class.simpleName ?: "object") }) == "object")) && __sporkTruthy(__sporkProp(c, "to_html")))) {
        __sporkCall(__sporkProp(c, "to_html"), listOf<Any?>())
    } else {
        "${c}"
    } } as (Any?) -> Any?)(__e) }.toMutableList()).joinToString("\n")
    val void = (((t == "input") || (t == "hr")) || (t == "br"))
    if (void) {
        return "<${t}${cls_attr}${attrs_str}>"
    } else {
        if ((inner_ == "")) {
            return "<${t}${cls_attr}${attrs_str}></${t}>"
        } else {
            return "<${t}${cls_attr}${attrs_str}>\n${inner_}\n</${t}>"
        }
    }
}
fun Row(vararg kids: Any?): Any? {
    val kids = kids.toList()
    return tag("div", "sz-row", mutableMapOf<String, Any?>(), *kids.toTypedArray())
}
fun Col(vararg kids: Any?): Any? {
    val kids = kids.toList()
    return tag("div", "sz-col sz-center", mutableMapOf<String, Any?>(), *kids.toTypedArray())
}
fun Card(vararg kids: Any?): Any? {
    val kids = kids.toList()
    return tag("div", "sz-card", mutableMapOf<String, Any?>(), *kids.toTypedArray())
}
fun Grid(vararg kids: Any?): Any? {
    val kids = kids.toList()
    return tag("div", "sz-grid", mutableMapOf<String, Any?>(), *kids.toTypedArray())
}
fun Hr(): Any? {
    return "<hr class=\"sz-divider\">"
}
fun Spacer(): Any? {
    return "<div class=\"sz-grow\"></div>"
}
fun H1(c: Any?): Any? {
    return tag("h1", "sz-h1", mutableMapOf<String, Any?>(), c)
}
fun H2(c: Any?): Any? {
    return tag("h2", "sz-h2", mutableMapOf<String, Any?>(), c)
}
fun H3(c: Any?): Any? {
    return tag("h3", "sz-h3", mutableMapOf<String, Any?>(), c)
}
fun H4(c: Any?): Any? {
    return tag("h4", "sz-h4", mutableMapOf<String, Any?>(), c)
}
fun P(c: Any?): Any? {
    return tag("p", "sz-p", mutableMapOf<String, Any?>(), c)
}
fun Label(c: Any?): Any? {
    return tag("label", "sz-label", mutableMapOf<String, Any?>(), c)
}
fun Badge(c: Any?): Any? {
    return tag("span", "sz-badge", mutableMapOf<String, Any?>(), c)
}
fun Chip(text: Any?, primary: Any? = false): Any? {
    val css_class = if (__sporkTruthy(primary)) "sz-chip sz-chip-primary" else "sz-chip"
    return tag("span", css_class, mutableMapOf<String, Any?>(), text)
}
fun Alert(c: Any?, variant: Any? = ""): Any? {
    val css_class = if (__sporkTruthy((variant != ""))) "sz-alert sz-alert-${variant}" else "sz-alert"
    return tag("div", css_class, mutableMapOf<String, Any?>(), c)
}
fun Button(text: Any?, js: Any? = "", variant: Any? = "filled", size: Any? = ""): Any? {
    val css_class = "sz-btn sz-btn-${variant}${if (__sporkTruthy((size != ""))) " sz-btn-${size}" else ""}"
    val attrs = if (__sporkTruthy((js != ""))) mutableMapOf<String, Any?>("data-ripple" to "", "onclick" to js) else mutableMapOf<String, Any?>("data-ripple" to "")
    return tag("button", css_class, attrs, text)
}
fun Input(placeholder: Any? = "", bind: Any? = null): Any? {
    val attrs = mutableMapOf<String, Any?>("type" to "text")
    if ((placeholder != "")) {
        attrs["placeholder"] = placeholder
    }
    if ((bind != null)) {
        attrs["data-spork-bind"] = __sporkProp(bind, "name")
        attrs["oninput"] = "window.__set('${__sporkProp(bind, "name")}',this.value);window.__sync('${__sporkProp(bind, "name")}',this.value)"
    }
    return tag("input", "sz-input", attrs)
}
fun Textarea(placeholder: Any? = "", rows: Any? = 4, bind: Any? = null): Any? {
    val attrs = mutableMapOf<String, Any?>("rows" to "${rows}")
    if ((placeholder != "")) {
        attrs["placeholder"] = placeholder
    }
    if ((bind != null)) {
        attrs["data-spork-bind"] = __sporkProp(bind, "name")
        attrs["oninput"] = "window.__set('${__sporkProp(bind, "name")}',this.value);window.__sync('${__sporkProp(bind, "name")}',this.value)"
    }
    return tag("textarea", "sz-textarea", attrs)
}
fun Checkbox(label_text: Any?, bind: Any? = null): Any? {
    val attrs = mutableMapOf<String, Any?>("type" to "checkbox")
    if ((bind != null)) {
        attrs["data-spork-checked"] = __sporkProp(bind, "name")
        attrs["onchange"] = "window.__set('${__sporkProp(bind, "name")}',this.checked);window.__sync('${__sporkProp(bind, "name")}',this.checked)"
    }
    val chk = tag("input", "", attrs)
    val track = "<span class=\"sz-switch-track\"><span class=\"sz-switch-thumb\"></span></span>"
    val lbl = "<span class=\"sz-switch-label\">${label_text}</span>"
    return tag("label", "sz-switch", mutableMapOf<String, Any?>(), chk, track, lbl)
}
fun Select(options: Any?, bind: Any? = null): Any? {
    val opts = ((options as Iterable<Any?>).map { __e -> ({ pair: Any? ->     val val_ = __sporkIndex(pair, 0);     val lbl = __sporkIndex(pair, 1);     "<option value=\"${__sporkHtmlEscape(val_)}\">${__sporkHtmlEscape(lbl)}</option>" } as (Any?) -> Any?)(__e) }.toMutableList()).joinToString("\n")
    val attrs = mutableMapOf<String, Any?>()
    if ((bind != null)) {
        attrs["data-spork-bind"] = __sporkProp(bind, "name")
        attrs["onchange"] = "window.__set('${__sporkProp(bind, "name")}',this.value);window.__sync('${__sporkProp(bind, "name")}',this.value)"
    }
    return "<select class=\"sz-select\"${((__sporkCall(__sporkProp(attrs, "entries"), listOf<Any?>()) as Iterable<Any?>).map { __e -> ({ kv: Any? ->     " ${__sporkIndex(kv, 0)}=\"${__sporkIndex(kv, 1)}\"" } as (Any?) -> Any?)(__e) }.toMutableList()).joinToString("")}>\n${opts}\n</select>"
}
fun Progress(state: Any?): Any? {
    val style_expr = __sporkHtmlEscape("{\"width\": window.__state.${__sporkProp(state, "name")} + \"%\"}")
    return "<div class=\"sz-progress\"><div class=\"sz-progress-bar\" data-spork-style=\"${style_expr}\"></div></div>"
}
fun Avatar(src: Any?, alt: Any? = ""): Any? {
    return "<img class=\"sz-avatar\" src=\"${__sporkHtmlEscape(src)}\" alt=\"${__sporkHtmlEscape(alt)}\">"
}
fun Divider(): Any? {
    return "<hr class=\"sz-divider\">"
}
fun _push_sse(event: Any?, data_: Any?): Any? {
    return vspk_bridge_push_sse("event: ${event}\ndata: ${__sporkToJson(data_)}\n\n")
}
fun _push_state(name: Any?, value_: Any?): Any? {
    _states[(name as String)] = value_
    return _push_sse("state", mutableMapOf<String, Any?>("name" to name, "value" to value_))
}
fun state(name: Any?, initial: Any?): Any? {
    _states[(name as String)] = initial
    fun to_html(): Any? {
        return "<span data-spork-text=\"${name}\"></span>"
    }
    fun js_get(): Any? {
        return "window.__state.${name}"
    }
    fun js_set(val_: Any?): Any? {
        return "window.__set('${name}',${__sporkToJson(val_)})"
    }
    fun js_inc(by_: Any? = 1): Any? {
        return "window.__set('${name}',window.__state.${name}+${by_})"
    }
    fun js_dec(by_: Any? = 1): Any? {
        return "window.__set('${name}',window.__state.${name}-${by_})"
    }
    fun get_(): Any? {
        return _states[name]!!
    }
    fun set_(val_: Any?): Any? {
        return _push_state(name, val_)
    }
    fun inc(by_: Any? = 1): Any? {
        return set_(sporkAdd(get_(), by_))
    }
    fun dec(by_: Any? = 1): Any? {
        return set_(sporkSub(get_(), by_))
    }
    return mutableMapOf<String, Any?>("name" to name, "to_html" to ::to_html, "js_get" to ::js_get, "js_set" to ::js_set, "js_inc" to { __a: Any? -> if (__a is Array<*>) { when (__a.size) { 0 -> js_inc(); 1 -> js_inc(__a[0]); else -> js_inc() } } else js_inc(__a) }, "js_dec" to { __a: Any? -> if (__a is Array<*>) { when (__a.size) { 0 -> js_dec(); 1 -> js_dec(__a[0]); else -> js_dec() } } else js_dec(__a) }, "get" to ::get_, "set" to ::set_, "inc" to { __a: Any? -> if (__a is Array<*>) { when (__a.size) { 0 -> inc(); 1 -> inc(__a[0]); else -> inc() } } else inc(__a) }, "dec" to { __a: Any? -> if (__a is Array<*>) { when (__a.size) { 0 -> dec(); 1 -> dec(__a[0]); else -> dec() } } else dec(__a) }, "__str__" to {     to_html() })
}
fun on_click(fn_cb: Any?): Any? {
    _cb_count = (_cb_count + 1)
    val id = "cb_${_token}_${_cb_count}"
    _callbacks[id] = fn_cb
    return "fetch('http://127.0.0.1:${_port}/cb/${id}',{mode:'no-cors'})"
}
fun on_event(name: Any?, fn_cb: Any?) {
    _events[(name as String)] = fn_cb
}
fun _ev(name: Any?): Any? {
    return "__${name}_${_token}"
}
fun _post_js(name: Any?, body_expr: Any?): Any? {
    return "fetch('http://127.0.0.1:${_port}/event/${name}',{method:'POST',mode:'no-cors',headers:{'Content-Type':'text/plain'},body:${body_expr}})"
}
fun on_key(fn_cb: Any?): Any? {
    _key_on = true
    return on_event(_ev("k"), fn_cb)
}
fun _safe_true(f: Any?): Any? {
    return run { try {     _call0(f) } catch (_ex: Exception) {     true } }
}
fun _call0(f: Any?): Any? {
    val h = mutableMapOf<String, Any?>("f" to f)
    return __sporkCall(h["f"]!!, listOf<Any?>())
}
fun _call1(f: Any?, a: Any?): Any? {
    val h = mutableMapOf<String, Any?>("f" to f)
    return __sporkCall(h["f"]!!, listOf<Any?>(a))
}
fun on_close(fn_cb: Any?): Any? {
    _close_on = true
    return on_event(_ev("c"), { d: Any? ->     val r = _safe_true(fn_cb);     if ((r == false)) {
        eval_js("__vspk.cancelClose()")
    };     if ((r != false)) {
        eval_js("__vspk.confirmClose()")
    } })
}
fun _dialog(kind: Any?, title: Any?, fn_cb: Any?): Any? {
    _cb_count = (_cb_count + 1)
    val name = _ev("d${_cb_count}")
    on_event(name, { d: Any? ->     _call1(fn_cb, __sporkIndex(d, "path")) })
    return eval_js("__vspk.dialog({kind:'${kind}',title:${__sporkToJson(title)}}).then(function(p){${_post_js(name, "JSON.stringify({path:p})")}})")
}
fun pick_file(title: Any?, fn_cb: Any?): Any? {
    return _dialog("open", title, fn_cb)
}
fun save_file(title: Any?, fn_cb: Any?): Any? {
    return _dialog("save", title, fn_cb)
}
fun pick_folder(title: Any?, fn_cb: Any?): Any? {
    return _dialog("folder", title, fn_cb)
}
fun _modal(call: Any?, kind: Any?, fn_cb: Any?): Any? {
    _cb_count = (_cb_count + 1)
    val name = _ev("m${_cb_count}")
    on_event(name, { d: Any? ->     if ((fn_cb != null)) {
        if ((kind == "message")) {
            _call0(fn_cb)
        }
        if ((kind == "confirm")) {
            _call1(fn_cb, (__sporkIndex(d, "v") == true))
        }
        if ((kind == "prompt")) {
            _call1(fn_cb, __sporkIndex(d, "v"))
        }
    } })
    return eval_js("Promise.resolve(${call}).then(function(v){${_post_js(name, "JSON.stringify({v:v})")}})")
}
fun message(text: Any?, fn_cb: Any?): Any? {
    return _modal("alert(${__sporkToJson(text)})", "message", fn_cb)
}
fun confirm(text: Any?, fn_cb: Any?): Any? {
    return _modal("confirm(${__sporkToJson(text)})", "confirm", fn_cb)
}
fun prompt(text: Any?, fn_cb: Any?, default_value: Any?): Any? {
    return _modal("prompt(${__sporkToJson(text)},${__sporkToJson(default_value)})", "prompt", fn_cb)
}
var _vt_count = 0
fun _vt_ev(fn_cb: Any?): Any? {
    _cb_count = (_cb_count + 1)
    val name = _ev("v${_cb_count}")
    on_event(name, { d: Any? ->     _call1(fn_cb, d) })
    return _post_js(name, "JSON.stringify(p)")
}
fun _vt_attrs(el_id: Any?, cfg: Any?, on_select: Any?, on_dblclick: Any?, on_sort: Any?, style: Any? = ""): Any? {
    val attrs = mutableMapOf<String, Any?>("id" to el_id, "data-vt" to __sporkToJson(cfg))
    if ((style != "")) {
        attrs["style"] = style
    }
    if ((on_select != null)) {
        attrs["data-on-select"] = _vt_ev(on_select)
    }
    if ((on_dblclick != null)) {
        attrs["data-on-dblclick"] = _vt_ev(on_dblclick)
    }
    if ((on_sort != null)) {
        attrs["data-on-sort"] = _vt_ev(on_sort)
    }
    return attrs
}
fun _vt_id(prefix: Any?, el_id: Any?): Any? {
    if ((el_id != "")) {
        return el_id
    }
    _vt_count = (_vt_count + 1)
    return "${prefix}${_vt_count}"
}
fun Table(cols: Any?, rows: Any?, on_select: Any? = null, on_dblclick: Any? = null, on_sort: Any? = null, sortable: Any? = true, multi: Any? = false, header: Any? = true, height: Any? = "", id: Any? = ""): Any? {
    val el_id = _vt_id("vt", id)
    val cfg = mutableMapOf<String, Any?>("cols" to cols, "rows" to rows, "sortable" to sortable, "multi" to multi, "striped" to true, "header" to header, "selected" to -1)
    if ((height != "")) {
        cfg["height"] = height
    }
    return tag("div", "vspk-table", _vt_attrs(el_id, cfg, on_select, on_dblclick, on_sort))
}
fun Listbox(items: Any?, on_select: Any? = null, on_dblclick: Any? = null, height: Any? = "", id: Any? = ""): Any? {
    val rows = (items as Iterable<Any?>).map { __e -> ({ x: Any? ->     mutableListOf(x) } as (Any?) -> Any?)(__e) }.toMutableList()
    val el_id = _vt_id("vt", id)
    val cfg = mutableMapOf<String, Any?>("cols" to mutableListOf(""), "rows" to rows, "sortable" to false, "multi" to false, "striped" to false, "header" to false, "selected" to -1)
    if ((height != "")) {
        cfg["height"] = height
    }
    return tag("div", "vspk-table", _vt_attrs(el_id, cfg, on_select, on_dblclick, null))
}
fun Tree(nodes: Any?, on_select: Any? = null, on_dblclick: Any? = null, height: Any? = "", id: Any? = ""): Any? {
    val el_id = _vt_id("vtree", id)
    val st = if (__sporkTruthy((height != ""))) "max-height:${height}" else ""
    return tag("div", "vspk-tree", _vt_attrs(el_id, mutableMapOf<String, Any?>("nodes" to nodes), on_select, on_dblclick, null, st))
}
fun table_set_js(el_id: Any?, rows: Any?, cols: Any? = null): Any? {
    val c = if (__sporkTruthy((cols == null))) "null" else __sporkToJson(cols)
    return "window.__vspk_table_set(${__sporkToJson(el_id)},${c},${__sporkToJson(rows)})"
}
fun table_select_js(el_id: Any?, index: Any?): Any? {
    return "window.__vspk_table_select(${__sporkToJson(el_id)},${index})"
}
fun table_sort_js(el_id: Any?, col: Any?, dir: Any? = 1): Any? {
    return "window.__vspk_table_sort(${__sporkToJson(el_id)},${col},${dir})"
}
fun tree_set_js(el_id: Any?, nodes: Any?): Any? {
    return "window.__vspk_tree_set(${__sporkToJson(el_id)},${__sporkToJson(nodes)})"
}
fun table_set(el_id: Any?, rows: Any?): Any? {
    return eval_js(table_set_js(el_id, rows, null))
}
fun table_set_cols(el_id: Any?, rows: Any?, cols: Any?): Any? {
    return eval_js(table_set_js(el_id, rows, cols))
}
fun table_select(el_id: Any?, index: Any?): Any? {
    return eval_js(table_select_js(el_id, index))
}
fun table_sort(el_id: Any?, col: Any?, dir: Any?): Any? {
    return eval_js(table_sort_js(el_id, col, dir))
}
fun tree_set(el_id: Any?, nodes: Any?): Any? {
    return eval_js(tree_set_js(el_id, nodes))
}
fun ColorPicker(bind: Any?): Any? {
    return tag("input", "sz-input", mutableMapOf<String, Any?>("type" to "color", "data-spork-bind" to __sporkProp(bind, "name"), "oninput" to "window.__set('${__sporkProp(bind, "name")}',this.value);window.__sync('${__sporkProp(bind, "name")}',this.value)"))
}
fun DatePicker(bind: Any?, with_time: Any? = false): Any? {
    val t = if (__sporkTruthy(with_time)) "datetime-local" else "date"
    return tag("input", "sz-input", mutableMapOf<String, Any?>("type" to t, "data-spork-bind" to __sporkProp(bind, "name"), "oninput" to "window.__set('${__sporkProp(bind, "name")}',this.value);window.__sync('${__sporkProp(bind, "name")}',this.value)"))
}
fun _timer(js_fn: Any?, ms: Any?, fn_cb: Any?): Any? {
    _cb_count = (_cb_count + 1)
    val name = _ev("t${_cb_count}")
    on_event(name, { d: Any? ->     _call0(fn_cb) })
    val js = "${js_fn}(function(){${_post_js(name, "'{}'")}},${ms})"
    (_timers as MutableList<Any?>).add("${js}")
    if (_running) {
        eval_js(js)
    }
    return true
}
fun run_every(ms: Any?, fn_cb: Any?): Any? {
    return _timer("setInterval", ms, fn_cb)
}
fun run_after(ms: Any?, fn_cb: Any?): Any? {
    return _timer("setTimeout", ms, fn_cb)
}
fun set_title(t: Any?): Any? {
    return eval_js("__vspk.setTitle(${__sporkToJson(t)})")
}
fun notify(title: Any?, body: Any? = ""): Any? {
    return eval_js("__vspk.notify(${__sporkToJson(title)},${__sporkToJson(body)})")
}
fun copy_text(text: Any?): Any? {
    return eval_js("__vspk.clipboard.write(${__sporkToJson(text)})")
}
fun quit(): Any? {
    return eval_js("__vspk.close()")
}
fun _cv_do(id: Any?, op: Any?, args: Any?): Any? {
    val js = "__cv(${__sporkToJson(id)},${__sporkToJson(op)},${__sporkToJson(args)})"
    if ((op == "clear")) {
        _cv_logs[(id as String)] = ""
    }
    _cv_logs[(id as String)] = "${_cv_logs[id]!!}${js};"
    if (_running) {
        _push_sse("all", js)
    }
    return true
}
fun _cv_on_mouse(id: Any?, fn_cb: Any?): Any? {
    _cb_count = (_cb_count + 1)
    val name = _ev("m${_cb_count}")
    on_event(name, fn_cb)
    val js = "(function(){var c=document.getElementById('${id}');if(!c)return;function p(t,e){if(t==='move'){var n=Date.now();if(n-(c.__lm||0)<30)return;c.__lm=n;}var r=c.getBoundingClientRect();${_post_js(name, "JSON.stringify({type:t,x:Math.round((e.clientX-r.left)*c.width/r.width),y:Math.round((e.clientY-r.top)*c.height/r.height),button:e.button})")}}['down','up','move','click'].forEach(function(t){c.addEventListener(t==='down'?'mousedown':t==='up'?'mouseup':t==='move'?'mousemove':'click',function(e){p(t,e)})})})();"
    _cv_mouse_js = (_cv_mouse_js + js)
    if (_running) {
        _push_sse("all", js)
    }
    return true
}
fun canvas(id: Any?, w: Any?, h: Any?): Any? {
    _cv_logs[(id as String)] = ""
    (_cv_ids as MutableList<Any?>).add(id)
    fun to_html(): Any? {
        return "<canvas id=\"${id}\" width=\"${w}\" height=\"${h}\" style=\"width:${w}px;max-width:100%;height:auto;border:1px solid rgba(128,128,128,.4);border-radius:8px;touch-action:none\"></canvas>"
    }
    fun _color(c: Any?): Any? {
        return _cv_do(id, "color", mutableListOf(c))
    }
    fun _line_width(n: Any?): Any? {
        return _cv_do(id, "lw", mutableListOf(n))
    }
    fun _font(size: Any?): Any? {
        return _cv_do(id, "font", mutableListOf(size))
    }
    fun _line(x1: Any?, y1: Any?, x2: Any?, y2: Any?): Any? {
        return _cv_do(id, "line", mutableListOf(x1, y1, x2, y2))
    }
    fun _rect(x: Any?, y: Any?, rw: Any?, rh: Any?): Any? {
        return _cv_do(id, "rect", mutableListOf(x, y, rw, rh))
    }
    fun _frame(x: Any?, y: Any?, rw: Any?, rh: Any?): Any? {
        return _cv_do(id, "frame", mutableListOf(x, y, rw, rh))
    }
    fun _circle(x: Any?, y: Any?, r: Any?): Any? {
        return _cv_do(id, "circle", mutableListOf(x, y, r))
    }
    fun _ring(x: Any?, y: Any?, r: Any?): Any? {
        return _cv_do(id, "ring", mutableListOf(x, y, r))
    }
    fun _text(x: Any?, y: Any?, s: Any?): Any? {
        return _cv_do(id, "text", mutableListOf(x, y, s))
    }
    fun _poly(points: Any?): Any? {
        return _cv_do(id, "poly", mutableListOf(points))
    }
    fun _clear(): Any? {
        return _cv_do(id, "clear", mutableListOf<Any?>())
    }
    fun _draw(js: Any?): Any? {
        return _cv_do(id, "draw", mutableListOf(js))
    }
    fun _on_mouse(fn_cb: Any?): Any? {
        return _cv_on_mouse(id, fn_cb)
    }
    return mutableMapOf<String, Any?>("to_html" to ::to_html, "color" to ::_color, "line_width" to ::_line_width, "font" to ::_font, "line" to ::_line, "rect" to ::_rect, "frame" to ::_frame, "circle" to ::_circle, "ring" to ::_ring, "text" to ::_text, "poly" to ::_poly, "erase" to ::_clear, "draw" to ::_draw, "on_mouse" to ::_on_mouse, "__str__" to {     to_html() })
}
fun _win_open(info: Any?): Any? {
    val p = __sporkIndex(info, "proc")
    if ((p != false)) {
        if (!__sporkTruthy(__sporkCall(__sporkProp(p, "exited"), listOf<Any?>()))) {
            return true
        }
    }
    val page = _page_html(__sporkIndex(info, "title"), (__sporkIter(__sporkIndex(info, "widgets"))).joinToString("\n"), "eval_${__sporkIndex(info, "id")}", false, __sporkIndex(info, "close_js"))
    val close_line = if (__sporkTruthy(__sporkIndex(info, "close_on"))) "on_close: confirm\n" else ""
    val htv_path = temp_file("vspk_", ".htv")
    (java.io.File(htv_path).writeText("title: ${__sporkIndex(info, "title")}\nwidth: ${__sporkIndex(info, "w")}\nheight: ${__sporkIndex(info, "h")}\ndevtools: true\n${_icon_line}${close_line}\n${page}"))
    __sporkSetIndex(info, "htv", htv_path)
    __sporkSetIndex(info, "proc", spawn(mutableListOf(find_vspk(), htv_path)))
    return true
}
fun _win_eval(info: Any?, js: Any?): Any? {
    return _push_sse("eval_${__sporkIndex(info, "id")}", js)
}
fun _win_show(info: Any?): Any? {
    if (_running) {
        _win_open(info)
    }
    if (!_running) {
        __sporkSetIndex(info, "want", true)
    }
    return true
}
fun _win_on_close(info: Any?, fn_cb: Any?): Any? {
    val ev = _ev("c${__sporkIndex(info, "id")}")
    __sporkSetIndex(info, "close_on", true)
    __sporkSetIndex(info, "close_js", "window.addEventListener('vspk:closeRequested',function(){${_post_js(ev, "'{}'")}});")
    on_event(ev, { d: Any? ->     val r = _safe_true(fn_cb);     if ((r == false)) {
        _win_eval(info, "__vspk.cancelClose()")
    };     if ((r != false)) {
        _win_eval(info, "__vspk.confirmClose()")
    } })
    return true
}
fun _win_add(info: Any?, w1: Any?, w2: Any?, w3: Any?, w4: Any?): Any? {
    for (w in mutableListOf(w1, w2, w3, w4)) {
        if ((w != "")) {
            (__sporkIndex(info, "widgets") as MutableList<Any?>).add("${w}")
        }
    }
    return true
}
fun window(title: Any?, width: Any? = 480, height: Any? = 360): Any? {
    _win_count = (_win_count + 1)
    val info = mutableMapOf<String, Any?>("id" to "w${_win_count}", "title" to title, "w" to width, "h" to height, "widgets" to mutableListOf<Any?>(), "proc" to false, "htv" to "", "want" to false, "close_on" to false, "close_js" to "")
    (_wins as MutableList<Any?>).add(info)
    fun _add(a: Any? = "", b: Any? = "", c: Any? = "", d: Any? = ""): Any? {
        return _win_add(info, a, b, c, d)
    }
    fun _show(): Any? {
        return _win_show(info)
    }
    fun _close(): Any? {
        return _win_eval(info, "__vspk.close()")
    }
    fun _set_title(t: Any?): Any? {
        return _win_eval(info, "__vspk.setTitle(${__sporkToJson(t)})")
    }
    fun _eval_js(js: Any?): Any? {
        return _win_eval(info, js)
    }
    fun _on_close(fn_cb: Any?): Any? {
        return _win_on_close(info, fn_cb)
    }
    fun _is_open(): Any? {
        return _win_is_open(info)
    }
    return mutableMapOf<String, Any?>("add" to { __a: Any? -> if (__a is Array<*>) { when (__a.size) { 0 -> _add(); 1 -> _add(__a[0]); 2 -> _add(__a[0], __a[1]); 3 -> _add(__a[0], __a[1], __a[2]); 4 -> _add(__a[0], __a[1], __a[2], __a[3]); else -> _add() } } else _add(__a) }, "show" to ::_show, "close" to ::_close, "set_title" to ::_set_title, "eval_js" to ::_eval_js, "on_close" to ::_on_close, "is_open" to ::_is_open)
}
fun _win_is_open(info: Any?): Any? {
    val p = __sporkIndex(info, "proc")
    if ((p == false)) {
        return false
    }
    return !__sporkTruthy(__sporkCall(__sporkProp(p, "exited"), listOf<Any?>()))
}
fun MenuItem(label: Any?, js: Any? = "", shortcut: Any? = ""): Any? {
    val click = (js).toString().replace("\"", "&quot;")
    val kbd = if (__sporkTruthy((shortcut != ""))) "<kbd>${__sporkHtmlEscape(shortcut)}</kbd>" else ""
    return "<button type=\"button\" class=\"sz-menu-item\" onclick=\"${click}\" data-accel=\"${__sporkHtmlEscape(shortcut)}\"><span>${__sporkHtmlEscape(label)}</span>${kbd}</button>"
}
fun MenuSep(): Any? {
    return "<div class=\"sz-menu-sep\"></div>"
}
fun Menu(title: Any?, vararg items: Any?): Any? {
    val items = items.toList()
    return "<div class=\"sz-menu\"><button type=\"button\" class=\"sz-menu-title\">${__sporkHtmlEscape(title)}</button><div class=\"sz-menu-list\">${(items).joinToString("")}</div></div>"
}
fun MenuBar(vararg menus: Any?): Any? {
    val menus = menus.toList()
    return "<style>.sz-menubar{position:fixed;top:0;left:0;right:0;z-index:1000;display:flex;gap:2px;padding:3px 6px;background:var(--sz-surface,#fff);color:var(--sz-on-surface,#1d1b20);border-bottom:1px solid rgba(128,128,128,.3);font-size:14px}.sz-menubar-space{height:38px;width:100%;flex:none}.sz-menu{position:relative}.sz-menu-title{background:none;border:0;padding:6px 10px;border-radius:6px;color:inherit;font:inherit;cursor:pointer}.sz-menu-title:hover,.sz-menu.sz-open>.sz-menu-title{background:rgba(128,128,128,.18)}.sz-menu-list{display:none;position:absolute;top:100%;left:0;min-width:210px;padding:4px;background:var(--sz-surface,#fff);color:inherit;border:1px solid rgba(128,128,128,.35);border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.2)}.sz-menu.sz-open>.sz-menu-list{display:block}.sz-menu-item{display:flex;justify-content:space-between;gap:24px;width:100%;background:none;border:0;padding:6px 10px;border-radius:6px;color:inherit;font:inherit;cursor:pointer;text-align:left}.sz-menu-item:hover{background:rgba(128,128,128,.18)}.sz-menu-item kbd{opacity:.6;font:inherit;font-size:12px}.sz-menu-sep{height:1px;margin:4px 6px;background:rgba(128,128,128,.3)}.sz-native .sz-menubar,.sz-native .sz-menubar-space{display:none!important}</style><div class=\"sz-menubar\">${(menus).joinToString("")}</div><div class=\"sz-menubar-space\"></div><script>(function(){if(window.__menu)return;window.__menu=1;var bar=document.querySelector('.sz-menubar');function menus(){return bar.querySelectorAll(':scope > .sz-menu')}window.__vspk_menu_click=function(id){var p=id.split('.');var m=menus()[+p[0]];if(m)m.querySelector('.sz-menu-list').children[+p[1]].click()};window.__vspk_menu_ok=function(){document.documentElement.classList.add('sz-native')};if(bar&&window.ipc&&window.__vspk_native_menu_ok){var ms=[];Array.prototype.forEach.call(menus(),function(m,mi){var items=[];Array.prototype.forEach.call(m.querySelector('.sz-menu-list').children,function(c,ii){if(c.classList.contains('sz-menu-sep'))items.push({sep:true});else items.push({id:mi+'.'+ii,label:(c.querySelector('span')||c).textContent,accel:c.getAttribute('data-accel')||''})});ms.push({label:m.querySelector('.sz-menu-title').textContent,items:items})});window.ipc.postMessage(JSON.stringify({cmd:'setMenu',menu:ms}))}function closeAll(except){document.querySelectorAll('.sz-menu.sz-open').forEach(function(m){if(m!==except)m.classList.remove('sz-open')})}document.addEventListener('click',function(e){var t=e.target.closest?e.target.closest('.sz-menu-title'):null;closeAll(t?t.parentNode:null);if(t)t.parentNode.classList.toggle('sz-open');var it=e.target.closest?e.target.closest('.sz-menu-item'):null;if(it)closeAll(null)});document.addEventListener('mouseover',function(e){var t=e.target.closest?e.target.closest('.sz-menu-title'):null;var o=document.querySelector('.sz-menu.sz-open');if(t&&o&&o!==t.parentNode){closeAll(t.parentNode);t.parentNode.classList.add('sz-open')}});document.addEventListener('keydown',function(e){if(e.key==='Escape'){closeAll(null);return}if(document.documentElement.classList.contains('sz-native')&&!/Win/.test(navigator.platform))return;var k=(e.ctrlKey?'ctrl+':'')+(e.shiftKey?'shift+':'')+(e.altKey?'alt+':'')+e.key.toLowerCase();var items=document.querySelectorAll('.sz-menu-item[data-accel]');for(var i=0;i<items.length;i++){var a=items[i].getAttribute('data-accel');if(a&&a.toLowerCase()===k){e.preventDefault();items[i].click();return}}})})();</script>"
}
fun add(vararg ws: Any?) {
    val ws = ws.toList()
    for (w in (ws as Iterable<Any?>)) {
        (_widgets as MutableList<Any?>).add("${w}")
    }
}
fun eval_js(js: Any?): Any? {
    return _push_sse("eval", js)
}
fun _build_html(): Any? {
    return _page_html(_title, (_widgets).joinToString("\n"), "eval", true, "")
}
fun _page_html(title: Any?, body_html: Any?, eval_ev: Any?, is_main: Any?, child_close_js: Any?): Any? {
    val state_json = __sporkToJson(_states)
    val key_js = if (__sporkTruthy((_key_on && __sporkTruthy(is_main)))) "document.addEventListener('keydown',function(e){${_post_js(_ev("k"), "JSON.stringify({key:e.key,code:e.code,ctrl:e.ctrlKey,shift:e.shiftKey,alt:e.altKey,meta:e.metaKey})")}});" else ""
    val main_close_js = if (__sporkTruthy((_close_on && __sporkTruthy(is_main)))) "window.addEventListener('vspk:closeRequested',function(){${_post_js(_ev("c"), "'{}'")}});" else ""
    val close_js = sporkAdd(main_close_js, child_close_js)
    val timers_js = if (__sporkTruthy(is_main)) ((_timers).joinToString(";") + ";") else ""
    val cv_js = "${((_cv_ids).map({ i: Any? ->     _cv_logs[i]!! }).toMutableList()).joinToString("")}${_cv_mouse_js}"
    val accent_style = if (__sporkTruthy((_accent != ""))) "<style>:root{--sz-accent:${_accent};} .sz-btn-filled{background:${_accent};border-color:${_accent};}</style>" else ""
    return "<!DOCTYPE html>\n<html data-theme=\"${_theme}\">\n<head>\n  <meta charset=\"UTF-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n  <title>${__sporkHtmlEscape(title)}</title>\n  <link rel=\"icon\" href=\"data:,\">\n  <link rel=\"stylesheet\" href=\"${SPORK_CSS}\" onerror=\"this.onerror=null;this.href='${SPORK_CSS_CDN}'\">\n  ${accent_style}\n</head>\n<body class=\"sz-body\">\n\n<div id=\"__app\" class=\"sz-page\">\n${body_html}\n</div>\n\n<script>\nwindow.__state = ${state_json};\nwindow.__win = '${eval_ev}';\n\nwindow.__set = function(name, value) {\n  window.__state[name] = value;\n  document.querySelectorAll('[data-spork-text=\"' + name + '\"]').forEach(function(el) {\n    el.textContent = value;\n  });\n  document.querySelectorAll('[data-spork-bind=\"' + name + '\"]').forEach(function(el) {\n    if (el.type === 'checkbox') el.checked = value;\n    else el.value = value;\n  });\n  document.querySelectorAll('[data-spork-style]').forEach(function(el) {\n    try { Object.assign(el.style, new Function('return (' + el.dataset.sporkStyle + ')')()) } catch(_){}\n  });\n  document.querySelectorAll('[data-spork-if]').forEach(function(el) {\n    try { el.style.display = new Function('return !!(' + el.dataset.sporkIf + ')')() ? '' : 'none' } catch(_){}\n  });\n  document.querySelectorAll('[data-spork-checked=\"' + name + '\"]').forEach(function(el) {\n    el.checked = !!value;\n  });\n};\n\n// Envía a Spork el valor que el usuario escribe/elige, para que state.get() lo vea\n// (los widgets enlazados solo actualizaban la página). POST simple (text/plain, no-cors).\nwindow.__sync = function(n, v) {\n  try {\n    fetch('http://127.0.0.1:${_port}/event/${_ev("v")}', {method: 'POST', mode: 'no-cors', headers: {'Content-Type': 'text/plain'}, body: JSON.stringify({n: n, v: v, w: window.__win})});\n  } catch(_) {}\n};\n\nwindow.__cv = function(id, op, a) {\n  var c = document.getElementById(id); if (!c) return;\n  var x = c.getContext('2d');\n  if (op === 'clear') { x.clearRect(0, 0, c.width, c.height); }\n  else if (op === 'color') { x.fillStyle = a[0]; x.strokeStyle = a[0]; }\n  else if (op === 'lw') { x.lineWidth = a[0]; }\n  else if (op === 'font') { x.font = a[0] + 'px sans-serif'; }\n  else if (op === 'line') { x.beginPath(); x.moveTo(a[0], a[1]); x.lineTo(a[2], a[3]); x.stroke(); }\n  else if (op === 'rect') { x.fillRect(a[0], a[1], a[2], a[3]); }\n  else if (op === 'frame') { x.strokeRect(a[0], a[1], a[2], a[3]); }\n  else if (op === 'circle') { x.beginPath(); x.arc(a[0], a[1], a[2], 0, 6.283185307); x.fill(); }\n  else if (op === 'ring') { x.beginPath(); x.arc(a[0], a[1], a[2], 0, 6.283185307); x.stroke(); }\n  else if (op === 'text') { x.fillText(a[2], a[0], a[1]); }\n  else if (op === 'poly') { var p = a[0]; x.beginPath(); x.moveTo(p[0][0], p[0][1]); for (var i = 1; i < p.length; i++) x.lineTo(p[i][0], p[i][1]); x.closePath(); x.fill(); }\n  else if (op === 'draw') { new Function('ctx', 'canvas', a[0])(x, c); }\n};\nObject.keys(window.__state).forEach(function(k) { window.__set(k, window.__state[k]); });\n${key_js}\n${close_js}\n${timers_js}\n${cv_js}\n\n(function connectSSE() {\n  var es = new EventSource('http://127.0.0.1:${_port}/events');\n  es.addEventListener('state', function(e) {\n    var d = JSON.parse(e.data);\n    if (d.src && d.src === window.__win) return;\n    window.__set(d.name, d.value);\n  });\n  ['${eval_ev}', 'all'].forEach(function(n) {\n    es.addEventListener(n, function(e) {\n      try { eval(JSON.parse(e.data)); } catch(err) { console.error(err); }\n    });\n  });\n  es.onerror = function() {\n    es.close();\n    setTimeout(connectSSE, 1000);\n  };\n})();\n</script>\n<script src=\"${SPORK_JS}\" onerror=\"var s=document.createElement('script');s.src='${SPORK_JS_CDN}';document.body.appendChild(s)\"></script>\n</body>\n</html>"
}
fun App(title: Any?, width: Any? = 1024, height: Any? = 768, theme: Any? = "light", accent: Any? = ""): Any? {
    _title = (title as String)
    _width = (width as Int)
    _height = (height as Int)
    _theme = (theme as String)
    _accent = (accent as String)
    _port = (Math.floor((Math.random() * 10000).toDouble()).toInt() + 20000)
    _token = (((((Math.random() * 1000000000)).toInt()).toString() + (((Math.random() * 1000000000)).toInt()).toString()) + (((Math.random() * 1000000000)).toInt()).toString())
    return mutableMapOf<String, Any?>("state" to ::state, "canvas" to ::canvas, "window" to ::window, "add" to ::add, "on_click" to ::on_click, "on_event" to ::on_event, "eval_js" to ::eval_js, "run" to ::run_, "on_key" to ::on_key, "on_close" to ::on_close, "pick_file" to ::pick_file, "save_file" to ::save_file, "pick_folder" to ::pick_folder, "run_every" to ::run_every, "run_after" to ::run_after, "set_title" to ::set_title, "notify" to ::notify, "copy_text" to ::copy_text, "quit" to ::quit, "message" to ::message, "confirm" to ::confirm, "prompt" to ::prompt, "table_set" to ::table_set, "table_set_cols" to ::table_set_cols, "table_select" to ::table_select, "table_sort" to ::table_sort, "tree_set" to ::tree_set)
}
fun run_(): Any? {
    var dir: Any? = null
    var candidate: Any? = null
    var info: Any? = null
    var src: Any? = null
    val _vspk_exe = find_vspk()
    vspk_bridge_start(_port)
    val html = _build_html()
    val icon_dirs = mutableListOf((System.getenv("SPORK_SCRIPT_DIR") ?: ""), (try { java.io.File(object {}::class.java.protectionDomain.codeSource.location.toURI()).parentFile?.absolutePath ?: System.getProperty("user.dir") } catch (_: Exception) { System.getProperty("user.dir") }))
    val icon_names = mutableListOf("icon.ico", "icon.png", "favicon.ico", "favicon.png")
    var icon_path = ""
    for (__dir in icon_dirs) {
        dir = __dir
        for (name in icon_names) {
            if (((icon_path == "") && (dir != ""))) {
                val candidate = (java.io.File((dir).toString(), (name).toString()).path)
                if (f_exists_q(candidate)) {
                    icon_path = candidate
                }
            }
        }
    }
    if ((icon_path == "")) {
        val from_env = (System.getenv("VSPK_DEFAULT_ICON") ?: "")
        if (((from_env != "") && f_exists_q(from_env))) {
            icon_path = from_env
        }
    }
    if ((icon_path == "")) {
        var dir = (try { java.io.File(object {}::class.java.protectionDomain.codeSource.location.toURI()).parentFile?.absolutePath ?: System.getProperty("user.dir") } catch (_: Exception) { System.getProperty("user.dir") })
        for (i in mutableListOf(0, 1, 2, 3, 4, 5, 6, 7)) {
            if ((icon_path == "")) {
                val candidate = (java.io.File((dir).toString(), ("vspk_default.ico").toString()).path)
                if (f_exists_q(candidate)) {
                    icon_path = candidate
                }
                dir = (java.io.File((dir).toString()).parent ?: "")
            }
        }
    }
    val icon_line = if (__sporkTruthy((icon_path != ""))) "icon: ${icon_path}\n" else ""
    val close_line = if (__sporkTruthy(_close_on)) "on_close: confirm\n" else ""
    val htv_content = "title: ${_title}\nwidth: ${_width}\nheight: ${_height}\ndevtools: true\n${icon_line}${close_line}\n${html}"
    _icon_line = "${icon_line}"
    val htv_path = temp_file("vspk_", ".htv")
    (java.io.File(htv_path).writeText(htv_content))
    val proc = spawn(mutableListOf(_vspk_exe, htv_path))
    _running = true
    for (__info in _wins) {
        info = __info
        if (__sporkTruthy(__sporkIndex(info, "want"))) {
            _win_open(info)
        }
    }
    while (!__sporkTruthy(__sporkCall(__sporkProp(proc, "exited"), listOf<Any?>()))) {
        val msg = vspk_bridge_poll()
        if ((msg != null)) {
            if ((__sporkProp(msg, "kind") == "cb")) {
                if ((_callbacks).containsKey(__sporkProp(msg, "id"))) {
                    try {
                        __sporkCall(_callbacks[__sporkProp(msg, "id")]!!, listOf<Any?>())
                    } catch (e: Exception) {

                    }
                }
            } else {
                if ((__sporkProp(msg, "kind") == "event")) {
                    val data_ = run { try {                     (__sporkFromJson(__sporkProp(msg, "body").toString()) as MutableMap<String, Any?>) } catch (_ex: Exception) {                     null } }
                    val is_value = (__sporkProp(msg, "name") == _ev("v"))
                    if ((is_value && (data_ != null))) {
                        val key = (data_["n"]).toString()
                        _states[key] = data_["v"]
                        if ((run { val __o: Any? = (_wins); when (__o) { is String -> __o.length; is Collection<*> -> __o.size; is Iterable<*> -> __o.count(); else -> 0 } } > 0)) {
                            var src = ""
                            if ((data_).containsKey("w")) {
                                src = "${data_["w"]}"
                            }
                            _push_sse("state", mutableMapOf<String, Any?>("name" to key, "value" to data_["v"], "src" to src))
                        }
                    }
                    if ((!is_value && __sporkTruthy((_events).containsKey(__sporkProp(msg, "name"))))) {
                        try {
                            __sporkCall(_events[__sporkProp(msg, "name")]!!, listOf<Any?>(data_))
                        } catch (e: Exception) {

                        }
                    }
                }
            }
        }
        Thread.sleep((15).toLong())
    }
    for (__info in _wins) {
        info = __info
        if ((_win_is_open(info) == true)) {
            _win_eval(info, "__vspk.close()")
        }
    }
    Thread.sleep((300).toLong())
    for (__info in _wins) {
        info = __info
        val hp = "${__sporkIndex(info, "htv")}"
        if ((hp != "")) {
            (java.io.File(hp).delete())
        }
    }
    return (java.io.File(htv_path).delete())
}
// ── fin import "vspk.spk" ─

val gui = App("Demo vspk", 520, 720)

val n = __sporkCall(__sporkProp(gui, "state"), listOf<Any?>("n", 0))

val m = __sporkCall(__sporkProp(gui, "state"), listOf<Any?>("m", 0))

val pct = __sporkCall(__sporkProp(gui, "state"), listOf<Any?>("pct", 0))

val nombre = __sporkCall(__sporkProp(gui, "state"), listOf<Any?>("nombre", ""))

val acepto = __sporkCall(__sporkProp(gui, "state"), listOf<Any?>("acepto", false))

val color = __sporkCall(__sporkProp(gui, "state"), listOf<Any?>("color", "azul"))

val log = __sporkCall(__sporkProp(gui, "state"), listOf<Any?>("log", "—"))


fun main() {
__sporkCall(__sporkProp(gui, "add"), listOf<Any?>(Card(H2("Demo vspk"), H4("1. Contador en Spork (cada clic va al puente)"), Row(Button("-", __sporkCall(__sporkProp(gui, "on_click"), listOf<Any?>({ __sporkCall(__sporkProp(n, "dec"), listOf<Any?>()); __sporkCall(__sporkProp(log, "set"), listOf<Any?>("n bajó")) })), "outlined"), H3(n), Button("+", __sporkCall(__sporkProp(gui, "on_click"), listOf<Any?>({ __sporkCall(__sporkProp(n, "inc"), listOf<Any?>()); __sporkCall(__sporkProp(log, "set"), listOf<Any?>("n subió")) })))), Hr(), H4("2. Contador solo JS (sin puente, debe ser instantáneo)"), Row(Button("-", __sporkCall(__sporkProp(m, "js_dec"), listOf<Any?>()), "outlined"), H3(m), Button("+", __sporkCall(__sporkProp(m, "js_inc"), listOf<Any?>()))), Hr(), H4("3. Input enlazado"), Input("Escribe tu nombre", nombre), P(nombre), Hr(), H4("4. Checkbox y Select"), Checkbox("Acepto las condiciones", acepto), Select(mutableListOf(mutableListOf("azul", "Azul"), mutableListOf("verde", "Verde"), mutableListOf("rojo", "Rojo")), color), P(color), Hr(), H4("5. Progreso (Spork actualiza la barra)"), Progress(pct), Row(Button("+10%", __sporkCall(__sporkProp(gui, "on_click"), listOf<Any?>({ if (sporkLt(__sporkCall(__sporkProp(pct, "get"), listOf<Any?>()), 100)) {
    __sporkCall(__sporkProp(pct, "set"), listOf<Any?>(sporkAdd(__sporkCall(__sporkProp(pct, "get"), listOf<Any?>()), 10)))
}; __sporkCall(__sporkProp(log, "set"), listOf<Any?>("progreso ${__sporkCall(__sporkProp(pct, "get"), listOf<Any?>())}")) }))), Button("Reiniciar", __sporkCall(__sporkProp(gui, "on_click"), listOf<Any?>({ __sporkCall(__sporkProp(pct, "set"), listOf<Any?>(0)); __sporkCall(__sporkProp(log, "set"), listOf<Any?>("reiniciado")) })), "outlined")), Hr(), H4("6. Variantes y alertas"), Row(Chip("normal"), Chip("primario", true), Badge("badge")), Alert("Todo correcto", "success"), Alert("Cuidado", "warning"), Row(Button("Texto", "", "text"), Button("Peligro", "", "danger"), Button("Pequeño", "", "filled", "sm")), Hr(), H4("7. eval_js desde Spork"), Row(Button("Teñir fondo", __sporkCall(__sporkProp(gui, "on_click"), listOf<Any?>({ __sporkCall(__sporkProp(gui, "eval_js"), listOf<Any?>("document.body.style.background = '#fff3cd'")); __sporkCall(__sporkProp(log, "set"), listOf<Any?>("fondo teñido desde Spork")) }))), Button("Quitar", __sporkCall(__sporkProp(gui, "on_click"), listOf<Any?>({ __sporkCall(__sporkProp(gui, "eval_js"), listOf<Any?>("document.body.style.background = ''")); __sporkCall(__sporkProp(log, "set"), listOf<Any?>("fondo restaurado")) })), "outlined")), P(log))))
__sporkCall(__sporkProp(gui, "run"), listOf<Any?>())
}