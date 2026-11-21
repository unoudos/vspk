// Generado por Spork (target kt) desde tu_tiempo.spk
// No editar a mano — se regenera en cada compilación con: spork build kt tu_tiempo.spk
@file:Suppress("UNCHECKED_CAST", "NAME_SHADOWING", "UNUSED_VARIABLE", "USELESS_CAST", "REDUNDANT_CALL_OF_CONVERSION_METHOD", "UNNECESSARY_NOT_NULL_ASSERTION")

class SporkError(message: String) : Exception(message) {
    override fun toString(): String = "Error: $message"
}

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
@Suppress("EXTENSION_SHADOWED_BY_MEMBER")
private operator fun <T> List<T>.get(i: Any?): T = this[__sporkNum(i).toInt()]
private operator fun <T> MutableList<T>.set(i: Any?, v: T) { this[__sporkNum(i).toInt()] = v }
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

// ── Helpers XML ─────────────────────────────────────────────────────────────
private fun __sporkXmlTag(xml: Any?, tag: Any?): String {
    val s = xml.toString(); val t = tag.toString()
    val m = Regex("<${t}(?:\\s[^>]*)?>([\\s\\S]*?)</${t}>").find(s) ?: return "N/A"
    return m.groupValues.getOrElse(1) { "N/A" }.trim()
}
private fun __sporkXmlSection(xml: Any?, tag: Any?): String {
    val s = xml.toString(); val t = tag.toString()
    return Regex("<${t}(?:\\s[^>]*)?>[\\s\\S]*?</${t}>").find(s)?.value ?: ""
}

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
    } catch (_: Exception) {
        // Sin campo: ¿método con ese nombre? (p. ej. proc.exited(), proc.wait_exit()) → se devuelve como función
        val m = obj.javaClass.declaredMethods.firstOrNull { it.name == prop && !it.isSynthetic }
        if (m == null) null else {
            m.isAccessible = true
            when (m.parameterCount) {
                0 -> ({ -> m.invoke(obj) } as () -> Any?)
                1 -> ({ a: Any? -> m.invoke(obj, a) } as (Any?) -> Any?)
                else -> ({ a: Any?, b: Any? -> m.invoke(obj, a, b) } as (Any?, Any?) -> Any?)
            }
        }
    }
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
private class SporkProc(private val proc: Process) {
    fun exited(): Boolean = !proc.isAlive
    fun wait_exit(): Int = proc.waitFor()
}
@Suppress("UNCHECKED_CAST")
private fun spawn(args: Any?): SporkProc {
    val cmd = (args as List<Any?>).map { it.toString() }
    return SporkProc(ProcessBuilder(cmd).inheritIO().start())
}

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

private val __vspk_sse_queues  = java.util.concurrent.CopyOnWriteArrayList<java.util.concurrent.LinkedBlockingQueue<String>>()
private val __vspk_msg_queue   = java.util.concurrent.LinkedBlockingQueue<Map<String, Any?>>()
private val __vspk_state_cache = java.util.concurrent.ConcurrentHashMap<String, String>()
private var __vspk_started     = false
private fun vspk_bridge_start(port: Any?) {
    val p = __sporkNum(port).toInt()
    val srv = com.sun.net.httpserver.HttpServer.create(java.net.InetSocketAddress("127.0.0.1", p), 0)
    srv.createContext("/events") { ex ->
        ex.responseHeaders.add("Content-Type",                "text/event-stream")
        ex.responseHeaders.add("Cache-Control",               "no-cache")
        ex.responseHeaders.add("Access-Control-Allow-Origin", "*")
        ex.sendResponseHeaders(200, 0)
        val q   = java.util.concurrent.LinkedBlockingQueue<String>()
        val out = ex.responseBody.bufferedWriter(Charsets.UTF_8)
        __vspk_sse_queues.add(q)
        for ((_, cached) in __vspk_state_cache) q.offer(cached)
        try {
            while (true) {
                val msg = q.poll(30, java.util.concurrent.TimeUnit.SECONDS)
                if (msg != null) { out.write(msg); out.flush() }
            }
        } catch (_: Exception) {}
        __vspk_sse_queues.remove(q)
    }
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
    if (!__vspk_started) return
    val msg = "$data"
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

// ── import "vspk" ──────────────────────────────────────────────
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
    val from_env = System.getenv("VSPK_EXE") ?: ""
    if (from_env != "" && f_exists_q(from_env)) {
        return from_env
    }
    val beside_script = java.io.File(((java.io.File(((try { java.io.File(object {}::class.java.protectionDomain.codeSource.location.toURI()).parentFile?.absolutePath ?: System.getProperty("user.dir") } catch (_: Exception) { System.getProperty("user.dir") })).toString()).parent ?: "")).toString(), (exe).toString()).path
    if (f_exists_q(beside_script)) {
        return beside_script
    }
    val beside_lib = java.io.File(((try { java.io.File(object {}::class.java.protectionDomain.codeSource.location.toURI()).parentFile?.absolutePath ?: System.getProperty("user.dir") } catch (_: Exception) { System.getProperty("user.dir") })).toString(), (exe).toString()).path
    if (f_exists_q(beside_lib)) {
        return beside_lib
    }
    val in_path = which(exe)
    if (in_path != "") {
        return in_path
    }
    return exe
}
fun tag(t: Any?, css_class: Any?, attrs: Any?, vararg kids: Any?): Any? {
    val kids = kids.toList()
    val cls_attr = if ((css_class != "")) " class=\"${css_class}\"" else ""
    val attrs_str = ((__sporkCall(__sporkProp(attrs, "entries"), listOf<Any?>()) as Iterable<Any?>).map { __e -> ({ kv: Any? -> val k = __sporkIndex(kv, 0); val v = __sporkIndex(kv, 1); if (k == "onclick" || k == "oninput" || k == "onchange") {
        " ${k}=\"${(v).toString().replace("\"", "&quot;")}\""
    } else {
        " ${k}=\"${__sporkHtmlEscape(v)}\""
    } } as (Any?) -> Any?)(__e) }.toMutableList()).joinToString("")
    val inner_ = ((kids as Iterable<Any?>).map { __e -> ({ c: Any? -> if (((when (val __tv = (c)) { null -> "null"; is Map<*, *> -> "hash"; is MutableList<*>, is List<*> -> "array"; is String -> "string"; is Boolean -> "bool"; is Int, is Long, is Double, is Float -> "number"; else -> (__tv::class.simpleName ?: "object") }) == "hash" || (when (val __tv = (c)) { null -> "null"; is Map<*, *> -> "hash"; is MutableList<*>, is List<*> -> "array"; is String -> "string"; is Boolean -> "bool"; is Int, is Long, is Double, is Float -> "number"; else -> (__tv::class.simpleName ?: "object") }) == "object") && __sporkTruthy(__sporkProp(c, "to_html"))) {
        __sporkCall(__sporkProp(c, "to_html"), listOf<Any?>())
    } else {
        "${c}"
    } } as (Any?) -> Any?)(__e) }.toMutableList()).joinToString("\n")
    val void = t == "input" || t == "hr" || t == "br"
    if (void) {
        return "<${t}${cls_attr}${attrs_str}>"
    } else {
        if (inner_ == "") {
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
fun Hr(): Any? {
    return "<hr class=\"sz-divider\">"
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
fun P(c: Any?): Any? {
    return tag("p", "sz-p", mutableMapOf<String, Any?>(), c)
}
fun Button(text: Any?, js: Any? = "", variant: Any? = "filled", size: Any? = ""): Any? {
    val css_class = "sz-btn sz-btn-${variant}${if ((size != "")) " sz-btn-${size}" else ""}"
    val attrs = if ((js != "")) mutableMapOf<String, Any?>("data-ripple" to "", "onclick" to js) else mutableMapOf<String, String>("data-ripple" to "")
    return tag("button", css_class, attrs, text)
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
    return mutableMapOf<String, Any?>("name" to name, "to_html" to ::to_html, "js_get" to ::js_get, "js_set" to ::js_set, "js_inc" to { __a: Any? -> if (__a is Array<*>) { when (__a.size) { 0 -> js_inc(); 1 -> js_inc(__a[0]); else -> js_inc() } } else js_inc(__a) }, "js_dec" to { __a: Any? -> if (__a is Array<*>) { when (__a.size) { 0 -> js_dec(); 1 -> js_dec(__a[0]); else -> js_dec() } } else js_dec(__a) }, "get" to ::get_, "set" to ::set_, "inc" to { __a: Any? -> if (__a is Array<*>) { when (__a.size) { 0 -> inc(); 1 -> inc(__a[0]); else -> inc() } } else inc(__a) }, "dec" to { __a: Any? -> if (__a is Array<*>) { when (__a.size) { 0 -> dec(); 1 -> dec(__a[0]); else -> dec() } } else dec(__a) }, "__str__" to { to_html() })
}
fun on_click(fn_cb: Any?): Any? {
    _cb_count = _cb_count + 1
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
    return on_event(_ev("c"), { d: Any? -> val r = _safe_true(fn_cb); if (r == false) {
        eval_js("__vspk.cancelClose()")
    }; if (r != false) {
        eval_js("__vspk.confirmClose()")
    } })
}
fun _dialog(kind: Any?, title: Any?, fn_cb: Any?): Any? {
    _cb_count = _cb_count + 1
    val name = _ev("d${_cb_count}")
    on_event(name, { d: Any? -> _call1(fn_cb, __sporkIndex(d, "path")) })
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
val _on_error: Any? = null
fun call(expr: Any?, fn_cb: Any?): Any? {
    _cb_count = _cb_count + 1
    val name = _ev("r${_cb_count}")
    on_event(name, { d: Any? -> if (d != null && __sporkIndex(d, "ok") == true) {
        if (fn_cb != null) {
            _call1(fn_cb, __sporkIndex(d, "r"))
        }
    } else {
        val msg = if ((d != null)) "${__sporkIndex(d, "e")}" else "sin respuesta"
        if (_on_error != null) {
            _call1(_on_error, msg)
        } else {
            println("[vspk] error: ${msg}")
        }
    } })
    return eval_js("Promise.resolve(${expr}).then(function(r){${_post_js(name, "JSON.stringify({ok:true,r:r})")}}).catch(function(e){${_post_js(name, "JSON.stringify({ok:false,e:String(e&&e.message||e)})")}})")
}
fun _modal(call: Any?, kind: Any?, fn_cb: Any?): Any? {
    _cb_count = _cb_count + 1
    val name = _ev("m${_cb_count}")
    on_event(name, { d: Any? -> if (fn_cb != null) {
        if (kind == "message") {
            _call0(fn_cb)
        }
        if (kind == "confirm") {
            _call1(fn_cb, (__sporkIndex(d, "v") == true))
        }
        if (kind == "prompt") {
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
fun table_set_js(el_id: Any?, rows: Any?, cols: Any? = null): Any? {
    val c = if ((cols == null)) "null" else __sporkToJson(cols)
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
fun _timer(js_fn: Any?, ms: Any?, fn_cb: Any?): Any? {
    _cb_count = _cb_count + 1
    val name = _ev("t${_cb_count}")
    on_event(name, { d: Any? -> _call0(fn_cb) })
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
    if (op == "clear") {
        _cv_logs[(id as String)] = ""
    }
    _cv_logs[(id as String)] = "${_cv_logs[id]!!}${js};"
    if (_running) {
        _push_sse("all", js)
    }
    return true
}
fun _cv_on_mouse(id: Any?, fn_cb: Any?): Any? {
    _cb_count = _cb_count + 1
    val name = _ev("m${_cb_count}")
    on_event(name, fn_cb)
    val js = "(function(){var c=document.getElementById('${id}');if(!c)return;function p(t,e){if(t==='move'){var n=Date.now();if(n-(c.__lm||0)<30)return;c.__lm=n;}var r=c.getBoundingClientRect();${_post_js(name, "JSON.stringify({type:t,x:Math.round((e.clientX-r.left)*c.width/r.width),y:Math.round((e.clientY-r.top)*c.height/r.height),button:e.button})")}}['down','up','move','click'].forEach(function(t){c.addEventListener(t==='down'?'mousedown':t==='up'?'mouseup':t==='move'?'mousemove':'click',function(e){p(t,e)})})})();"
    _cv_mouse_js = _cv_mouse_js + js
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
    return mutableMapOf<String, Any?>("to_html" to ::to_html, "color" to ::_color, "line_width" to ::_line_width, "font" to ::_font, "line" to ::_line, "rect" to ::_rect, "frame" to ::_frame, "circle" to ::_circle, "ring" to ::_ring, "text" to ::_text, "poly" to ::_poly, "erase" to ::_clear, "draw" to ::_draw, "on_mouse" to ::_on_mouse, "__str__" to { to_html() })
}
fun _win_open(info: Any?): Any? {
    val p = __sporkIndex(info, "proc")
    if (p != false) {
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
    on_event(ev, { d: Any? -> val r = _safe_true(fn_cb); if (r == false) {
        _win_eval(info, "__vspk.cancelClose()")
    }; if (r != false) {
        _win_eval(info, "__vspk.confirmClose()")
    } })
    return true
}
fun _win_add(info: Any?, w1: Any?, w2: Any?, w3: Any?, w4: Any?): Any? {
    for (w in mutableListOf(w1, w2, w3, w4)) {
        if (w != "") {
            (__sporkIndex(info, "widgets") as MutableList<Any?>).add("${w}")
        }
    }
    return true
}
fun window(title: Any?, width: Any? = 480, height: Any? = 360): Any? {
    _win_count = _win_count + 1
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
    if (p == false) {
        return false
    }
    return !__sporkTruthy(__sporkCall(__sporkProp(p, "exited"), listOf<Any?>()))
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
    return _page_html(_title, _widgets.joinToString("\n"), "eval", true, "")
}
fun _page_html(title: Any?, body_html: Any?, eval_ev: Any?, is_main: Any?, child_close_js: Any?): Any? {
    val state_json = __sporkToJson(_states)
    val key_js = if (__sporkTruthy((_key_on && __sporkTruthy(is_main)))) "document.addEventListener('keydown',function(e){${_post_js(_ev("k"), "JSON.stringify({key:e.key,code:e.code,ctrl:e.ctrlKey,shift:e.shiftKey,alt:e.altKey,meta:e.metaKey})")}});" else ""
    val main_close_js = if (__sporkTruthy((_close_on && __sporkTruthy(is_main)))) "window.addEventListener('vspk:closeRequested',function(){${_post_js(_ev("c"), "'{}'")}});" else ""
    val close_js = sporkAdd(main_close_js, child_close_js)
    val timers_js = if (__sporkTruthy(is_main)) (_timers.joinToString(";") + ";") else ""
    val cv_js = "${(_cv_ids.map({ i: Any? -> _cv_logs[i]!! }).toMutableList()).joinToString("")}${_cv_mouse_js}"
    val accent_style = if ((_accent != "")) "<style>:root{--sz-accent:${_accent};} .sz-btn-filled{background:${_accent};border-color:${_accent};}</style>" else ""
    return "<!DOCTYPE html>\n<html data-theme=\"${_theme}\">\n<head>\n  <meta charset=\"UTF-8\">\n  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n  <title>${__sporkHtmlEscape(title)}</title>\n  <link rel=\"icon\" href=\"data:,\">\n  <link rel=\"stylesheet\" href=\"${SPORK_CSS}\" onerror=\"this.onerror=null;this.href='${SPORK_CSS_CDN}'\">\n  ${accent_style}\n</head>\n<body class=\"sz-body\">\n\n<div id=\"__app\" class=\"sz-page\">\n${body_html}\n</div>\n\n<script>\nwindow.__state = ${state_json};\nwindow.__win = '${eval_ev}';\n\nwindow.__set = function(name, value) {\n  window.__state[name] = value;\n  document.querySelectorAll('[data-spork-text=\"' + name + '\"]').forEach(function(el) {\n    el.textContent = value;\n  });\n  document.querySelectorAll('[data-spork-bind=\"' + name + '\"]').forEach(function(el) {\n    if (el.type === 'checkbox') el.checked = value;\n    else el.value = value;\n  });\n  document.querySelectorAll('[data-spork-style]').forEach(function(el) {\n    try { Object.assign(el.style, new Function('return (' + el.dataset.sporkStyle + ')')()) } catch(_){}\n  });\n  document.querySelectorAll('[data-spork-if]').forEach(function(el) {\n    try { el.style.display = new Function('return !!(' + el.dataset.sporkIf + ')')() ? '' : 'none' } catch(_){}\n  });\n  document.querySelectorAll('[data-spork-checked=\"' + name + '\"]').forEach(function(el) {\n    el.checked = !!value;\n  });\n};\n\n// Envía a Spork el valor que el usuario escribe/elige, para que state.get() lo vea\n// (los widgets enlazados solo actualizaban la página). POST simple (text/plain, no-cors).\nwindow.__sync = function(n, v) {\n  try {\n    fetch('http://127.0.0.1:${_port}/event/${_ev("v")}', {method: 'POST', mode: 'no-cors', headers: {'Content-Type': 'text/plain'}, body: JSON.stringify({n: n, v: v, w: window.__win})});\n  } catch(_) {}\n};\n\nwindow.__cv = function(id, op, a) {\n  var c = document.getElementById(id); if (!c) return;\n  var x = c.getContext('2d');\n  if (op === 'clear') { x.clearRect(0, 0, c.width, c.height); }\n  else if (op === 'color') { x.fillStyle = a[0]; x.strokeStyle = a[0]; }\n  else if (op === 'lw') { x.lineWidth = a[0]; }\n  else if (op === 'font') { x.font = a[0] + 'px sans-serif'; }\n  else if (op === 'line') { x.beginPath(); x.moveTo(a[0], a[1]); x.lineTo(a[2], a[3]); x.stroke(); }\n  else if (op === 'rect') { x.fillRect(a[0], a[1], a[2], a[3]); }\n  else if (op === 'frame') { x.strokeRect(a[0], a[1], a[2], a[3]); }\n  else if (op === 'circle') { x.beginPath(); x.arc(a[0], a[1], a[2], 0, 6.283185307); x.fill(); }\n  else if (op === 'ring') { x.beginPath(); x.arc(a[0], a[1], a[2], 0, 6.283185307); x.stroke(); }\n  else if (op === 'text') { x.fillText(a[2], a[0], a[1]); }\n  else if (op === 'poly') { var p = a[0]; x.beginPath(); x.moveTo(p[0][0], p[0][1]); for (var i = 1; i < p.length; i++) x.lineTo(p[i][0], p[i][1]); x.closePath(); x.fill(); }\n  else if (op === 'draw') { new Function('ctx', 'canvas', a[0])(x, c); }\n};\nObject.keys(window.__state).forEach(function(k) { window.__set(k, window.__state[k]); });\n${key_js}\n${close_js}\n${timers_js}\n${cv_js}\n\n(function connectSSE() {\n  var es = new EventSource('http://127.0.0.1:${_port}/events');\n  es.addEventListener('state', function(e) {\n    var d = JSON.parse(e.data);\n    if (d.src && d.src === window.__win) return;\n    window.__set(d.name, d.value);\n  });\n  ['${eval_ev}', 'all'].forEach(function(n) {\n    es.addEventListener(n, function(e) {\n      try { eval(JSON.parse(e.data)); } catch(err) { console.error(err); }\n    });\n  });\n  es.onerror = function() {\n    es.close();\n    setTimeout(connectSSE, 1000);\n  };\n})();\n</script>\n<script src=\"${SPORK_JS}\" onerror=\"var s=document.createElement('script');s.src='${SPORK_JS_CDN}';document.body.appendChild(s)\"></script>\n</body>\n</html>"
}
fun App(title: Any?, width: Any? = 1024, height: Any? = 768, theme: Any? = "light", accent: Any? = ""): Any? {
    _title = (title as String)
    _width = (width as Int)
    _height = (height as Int)
    _theme = (theme as String)
    _accent = (accent as String)
    _port = Math.floor((Math.random() * 10000).toDouble()).toInt() + 20000
    _token = (((Math.random() * 1000000000)).toInt()).toString() + (((Math.random() * 1000000000)).toInt()).toString() + (((Math.random() * 1000000000)).toInt()).toString()
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
            if (icon_path == "" && dir != "") {
                val candidate = java.io.File((dir).toString(), (name).toString()).path
                if (f_exists_q(candidate)) {
                    icon_path = candidate
                }
            }
        }
    }
    if (icon_path == "") {
        val from_env = System.getenv("VSPK_DEFAULT_ICON") ?: ""
        if (from_env != "" && f_exists_q(from_env)) {
            icon_path = from_env
        }
    }
    if (icon_path == "") {
        var dir = try { java.io.File(object {}::class.java.protectionDomain.codeSource.location.toURI()).parentFile?.absolutePath ?: System.getProperty("user.dir") } catch (_: Exception) { System.getProperty("user.dir") }
        for (i in mutableListOf(0, 1, 2, 3, 4, 5, 6, 7)) {
            if (icon_path == "") {
                val candidate = java.io.File((dir).toString(), ("vspk_default.ico").toString()).path
                if (f_exists_q(candidate)) {
                    icon_path = candidate
                }
                dir = java.io.File((dir).toString()).parent ?: ""
            }
        }
    }
    val icon_line = if ((icon_path != "")) "icon: ${icon_path}\n" else ""
    if ((System.getenv("VSPK_DEBUG") ?: "") != "") {
        val shown = if ((icon_path != "")) icon_path else "(ninguno: icono interno de vspk.exe)"
        println("[vspk] icono elegido: ${shown}")
        println("[vspk] buscado en: ${__pdIdx(icon_dirs, 0)} | ${__pdIdx(icon_dirs, 1)}")
    }
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
        if (msg != null) {
            if (__sporkProp(msg, "kind") == "cb") {
                if ((_callbacks).containsKey(__sporkProp(msg, "id"))) {
                    try {
                        __sporkCall(_callbacks[__sporkProp(msg, "id")]!!, listOf<Any?>())
                    } catch (e: Exception) {

                    }
                }
            } else {
                if (__sporkProp(msg, "kind") == "event") {
                    val data_ = run { try {                     (__sporkFromJson(__sporkProp(msg, "body").toString()) as MutableMap<String, Any?>) } catch (_ex: Exception) {                     null } }
                    val is_value = __sporkProp(msg, "name") == _ev("v")
                    if (is_value && data_ != null) {
                        val key = (data_["n"]).toString()
                        _states[key] = data_["v"]
                        if (run { val __o: Any? = (_wins); when (__o) { is String -> __o.length; is Collection<*> -> __o.size; is Iterable<*> -> __o.count(); else -> 0 } } > 0) {
                            var src = ""
                            if ((data_).containsKey("w")) {
                                src = "${__pdIdx(data_, "w")}"
                            }
                            _push_sse("state", mutableMapOf<String, Any?>("name" to key, "value" to data_["v"], "src" to src))
                        }
                    }
                    if (!is_value && __sporkTruthy((_events).containsKey(__sporkProp(msg, "name")))) {
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
        if (_win_is_open(info) == true) {
            _win_eval(info, "__vspk.close()")
        }
    }
    Thread.sleep((300).toLong())
    for (__info in _wins) {
        info = __info
        val hp = "${__sporkIndex(info, "htv")}"
        if (hp != "") {
            (java.io.File(hp).delete())
        }
    }
    return java.io.File(htv_path).delete()
}
// ── fin import "vspk" ─

val XML_URL = "http://xml.tutiempo.net/xml/3589.xml"

fun format_weather_icon(ico: Any?): Any? {
    if ((ico).toString().startsWith("http")) {
        return ico
    } else {
        val clean = (((ico).toString().trim()).replace(".svg", "")).replace(".png", "")
        return "https://v5i.tutiempo.net/wi/01/50/${clean}.png"
    }
}

fun format_moon_icon(ico: Any?): Any? {
    if ((ico).toString().startsWith("http")) {
        return ico
    } else {
        val clean = (((ico).toString().trim()).replace(".svg", "")).replace(".png", "")
        return "https://v5i.tutiempo.net/wmi/01/${clean}.png"
    }
}

fun Img(id: String, alt: String): String {
    return "<img id=\"${id}\" alt=\"${__sporkHtmlEscape(alt)}\" src=\"\" style=\"width:48px;height:48px;object-fit:contain;display:block;margin:8px auto;\">"
}

fun ImgScript(): String {
    return "<script>\n(function() {\n  function loadImg(id, url) {\n    if (!url) return;\n    var el = document.getElementById(id);\n    if (!el || el.dataset.loaded === url) return;\n    el.dataset.loaded = url;\n    function tryLoad() {\n      if (typeof __vspk !== 'undefined') {\n        el.src = url;\n      } else {\n        setTimeout(tryLoad, 100);\n      }\n    }\n    tryLoad();\n  }\n\n  var _orig = window.__set;\n  window.__set = function(k, v) {\n    if (_orig) _orig(k, v);\n    if (k === 'img_dia')  loadImg('img_dia',  v);\n    if (k === 'img_luna') loadImg('img_luna', v);\n  };\n\n  document.addEventListener('DOMContentLoaded', function() {\n    var check = setInterval(function() {\n      var s = window.__state || {};\n      if (s.img_dia || s.img_luna) {\n        clearInterval(check);\n        loadImg('img_dia',  s.img_dia);\n        loadImg('img_luna', s.img_luna);\n      }\n    }, 100);\n  });\n})();\n</script>"
}

fun load_weather(): Any? {
    return run { try {     val text = http_get(XML_URL);     val dia_section = __sporkXmlSection(text, "dia");     val hora_section = __sporkXmlSection(text, "hora");     val localidad = __sporkXmlTag(__sporkXmlSection(text, "localidad"), "nombre");     if (dia_section == "") {
        mutableMapOf<String, Any?>("ok" to false, "localidad" to "", "dia" to null, "temp_actual" to "N/A", "error" to "Sin datos de pronóstico")
    } else {
        val dia = mutableMapOf<String, Any?>("fecha_larga" to __sporkXmlTag(dia_section, "fecha_larga"), "temp_maxima" to __sporkXmlTag(dia_section, "temp_maxima"), "temp_minima" to __sporkXmlTag(dia_section, "temp_minima"), "humedad" to __sporkXmlTag(dia_section, "humedad"), "viento" to __sporkXmlTag(dia_section, "viento"), "dir_viento" to __sporkXmlTag(dia_section, "dir_viento"), "icono" to __sporkXmlTag(dia_section, "icono"), "ico_fase_luna" to __sporkXmlTag(dia_section, "ico_fase_luna"))
        val temp_actual = if ((hora_section != "")) __sporkXmlTag(hora_section, "temperatura") else "N/A"
        mutableMapOf<String, Any?>("ok" to true, "localidad" to localidad, "dia" to dia, "temp_actual" to temp_actual)
    } } catch (err: Exception) {     mutableMapOf<String, Any?>("ok" to false, "localidad" to "", "dia" to null, "temp_actual" to "N/A", "error" to "${err}") } }
}

val app = App("Pronóstico del Tiempo - Málaga", 450, 560, "light", "#0284c7")
val ciudad = __sporkCall(__sporkProp(app, "state"), listOf<Any?>("ciudad", "Cargando clima..."))
val fecha = __sporkCall(__sporkProp(app, "state"), listOf<Any?>("fecha", "--"))
val temp = __sporkCall(__sporkProp(app, "state"), listOf<Any?>("temp", "--"))
val maxmin = __sporkCall(__sporkProp(app, "state"), listOf<Any?>("maxmin", "-- | --"))
val humedad = __sporkCall(__sporkProp(app, "state"), listOf<Any?>("humedad", "Humedad: --"))
val viento = __sporkCall(__sporkProp(app, "state"), listOf<Any?>("viento", "Viento: --"))
val img_dia = __sporkCall(__sporkProp(app, "state"), listOf<Any?>("img_dia", ""))
val img_luna = __sporkCall(__sporkProp(app, "state"), listOf<Any?>("img_luna", ""))

fun update_ui(data_: Any?): Any? {
    if (__sporkProp(data_, "dia") == null) {
        return null
    }
    val d = __sporkProp(data_, "dia")
    __sporkCall(__sporkProp(ciudad, "set"), listOf<Any?>(__sporkProp(data_, "localidad")))
    __sporkCall(__sporkProp(fecha, "set"), listOf<Any?>(if (__sporkTruthy((__sporkProp(d, "fecha_larga") != "N/A"))) __sporkProp(d, "fecha_larga") else "--"))
    __sporkCall(__sporkProp(temp, "set"), listOf<Any?>("Temperatura actual: ${__sporkProp(data_, "temp_actual")} °C"))
    __sporkCall(__sporkProp(maxmin, "set"), listOf<Any?>("${__sporkProp(d, "temp_maxima")} °C  |  ${__sporkProp(d, "temp_minima")} °C"))
    __sporkCall(__sporkProp(humedad, "set"), listOf<Any?>("Humedad: ${__sporkProp(d, "humedad")}%"))
    __sporkCall(__sporkProp(viento, "set"), listOf<Any?>("Viento: ${__sporkProp(d, "viento")} km/h - ${__sporkProp(d, "dir_viento")}"))
    __sporkCall(__sporkProp(img_dia, "set"), listOf<Any?>(format_weather_icon(__sporkProp(d, "icono"))))
    return __sporkCall(__sporkProp(img_luna, "set"), listOf<Any?>(format_moon_icon(__sporkProp(d, "ico_fase_luna"))))
}

fun fetch_weather(): Any? {
    val data_ = load_weather()
    if (!__sporkTruthy(__sporkProp(data_, "ok"))) {
        __sporkCall(__sporkProp(ciudad, "set"), listOf<Any?>("Error: ${__sporkProp(data_, "error")}"))
        return null
    }
    return update_ui(data_)
}

fun main() {
    System.setOut(java.io.PrintStream(java.io.FileOutputStream(java.io.FileDescriptor.out), true, "UTF-8"))
    val data0 = load_weather()
    if (__sporkTruthy(__sporkProp(data0, "ok"))) {
        update_ui(data0)
    } else {
        __sporkCall(__sporkProp(ciudad, "set"), listOf<Any?>("Error: ${__sporkProp(data0, "error")}"))
    }
    __sporkCall(__sporkProp(app, "add"), listOf<Any?>(Col(H1(ciudad), P(fecha), Hr(), Card(H2(temp), P(maxmin), Row(P(humedad), P(viento))), Hr(), H3("Indicadores"), Row(Card(P("🌙 Fase Lunar"), Img("img_luna", "Fase Lunar")), Card(P("☀ Día"), Img("img_dia", "Icono del Día"))), ImgScript(), Hr(), Button("Actualizar Pronóstico", __sporkCall(__sporkProp(app, "on_click"), listOf<Any?>({ fetch_weather() })), "filled"))))
    __sporkCall(__sporkProp(app, "run"), listOf<Any?>())
    if (__vspk_started) kotlin.system.exitProcess(0)
}

// ── Prelude (funciones de librería Spork) ──
@Suppress("UNCHECKED_CAST")
fun __pdIdx(x: Any?, i: Any?): Any? = when (x) { is Map<*, *> -> x[i]; is List<*> -> (i as? Number)?.toInt()?.let { n -> if (n < 0) x.getOrNull(x.size + n) else x.getOrNull(n) }; is String -> (i as? Number)?.toInt()?.let { n -> (if (n < 0) x.getOrNull(x.length + n) else x.getOrNull(n))?.toString() }; else -> null }
