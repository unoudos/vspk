// mi_app.js
import { open } from "./vspk.js"

const win = await open("test_emit.htv")

win.on("boton_a", (payload) => {
    console.log("[Bun] boton_a:", payload)
    win.send({ respuesta: "Recibi boton_a desde Bun!" })
})

win.on("texto", (payload) => {
    const valor = payload.valor ?? ""
    win.send({ respuesta: `Echo: ${valor.toUpperCase()}` })
})

await win.wait()