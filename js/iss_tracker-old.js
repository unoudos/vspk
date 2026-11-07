import { open } from "./vspk.js"

const ISS_API = "https://api.wheretheiss.at/v1/satellites/25544"

// ── SSE server nativo Bun ─────────────────────────────────────────────────────
const clients = new Set()

const sseServer = Bun.serve({
    port: 0, // puerto aleatorio
    fetch(req) {
        const url = new URL(req.url)

        if (url.pathname === "/events") {
            let controller
            const stream = new ReadableStream({
                start(c) {
                    controller = c
                    clients.add(controller)
                    // ping cada segundo para mantener viva la conexion
                    const iv = setInterval(() => {
                        try { controller.enqueue(": ping\n\n") }
                        catch { clearInterval(iv); clients.delete(controller) }
                    }, 1000)
                },
                cancel() {
                    clients.delete(controller)
                }
            })
            return new Response(stream, {
                headers: {
                    "Content-Type":                "text/event-stream",
                    "Cache-Control":               "no-cache",
                    "Access-Control-Allow-Origin": "*",
                }
            })
        }

        return new Response("not found", { status: 404 })
    }
})

const port = sseServer.port
console.log(`[ISS] SSE en puerto ${port}`)

// Escribir puerto para que el .htv lo encuentre via asset server de vspk
await Bun.write(".iss_port", String(port))

// ── Abrir ventana ─────────────────────────────────────────────────────────────
const win = await open("iss_tracker.htv")
console.log(`[ISS] Ventana abierta — ID: ${win.id}`)

// ── Push a todos los clientes SSE ─────────────────────────────────────────────
function push(data) {
    const msg = "data: " + JSON.stringify(data) + "\n\n"
    for (const client of clients) {
        try { client.enqueue(msg) }
        catch { clients.delete(client) }
    }
}

// ── Loop de datos ─────────────────────────────────────────────────────────────
async function loop() {
    while (true) {
        try {
            const res  = await fetch(ISS_API)
            const d    = await res.json()
            push({
                type:       "iss",
                lat:        d.latitude,
                lon:        d.longitude,
                alt:        d.altitude,
                vel:        d.velocity,
                visibility: d.visibility,
            })
            console.log(`[ISS] lat=${d.latitude.toFixed(2)} lon=${d.longitude.toFixed(2)} alt=${d.altitude.toFixed(1)}km vel=${Math.round(d.velocity)}km/h`)
        } catch(e) {
            push({ type: "error", msg: String(e) })
            console.error(`[ISS] Error: ${e}`)
        }
        await Bun.sleep(2000)
    }
}

loop()
await win.wait()
sseServer.stop()
try { Bun.file(".iss_port").unlink?.() } catch {}
console.log("[ISS] Cerrado.")
