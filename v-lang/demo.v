import vspk

fn main() {
	app := vspk.new_app('Demo vspk', width: 520, height: 720)
	n := app.state('n', 0)
	pct := app.state('pct', 0)
	nombre := app.state('nombre', '')
	acepto := app.state('acepto', false)
	color := app.state('color', 'azul')
	res := app.state('res', '—')
	vol := app.state('vol', 30)
	log := app.state('log', '—')
	tecla := app.state('tecla', '—')
	ticks := app.state('ticks', 0)
	arch := app.state('arch', '—')
	raton := app.state('raton', '—')

	lienzo := app.canvas('lienzo', 300, 150)
	lienzo.color('#6750A4').rect(10, 10, 100, 60)
	lienzo.color('#B3261E').circle(200, 60, 40)
	lienzo.color('#000000').line_width(2).line(0, 0, 300, 150)
	lienzo.font(16).text(10, 140, 'Spork')
	lienzo.on_mouse(fn [raton] (e vspk.MouseEvent) {
		raton.set('${e.typ} ${e.x},${e.y}')
	})
	nombre.on_change(fn (v string) {
		eprintln('onChange nombre=${v}')
	})

	ajustes := app.window('Ajustes', 360, 240)
	ajustes.add(vspk.col(vspk.h4('Ajustes (otra ventana)'), vspk.input(nombre, 'Tu nombre (compartido)'),
		vspk.p(nombre.ref())))

	tarjeta := vspk.card(vspk.h2('Demo'),
		vspk.row(app.button('-', fn [n] () {
			n.dec(1)
		}, variant: 'outlined'), vspk.h3(n.ref()), app.button('+', fn [n] () {
			n.inc(1)
		})), vspk.input(nombre, 'Nombre'), vspk.p(nombre.ref()), vspk.checkbox('Acepto', acepto),
		vspk.select_input(color, [['azul', 'Azul']!, ['verde', 'Verde']!, ['rojo', 'Rojo']!]),
		vspk.p(color.ref()), vspk.progress(pct, 100), app.button('+10%', fn [pct] () {
			v := pct.as_int() + 10
			pct.set(if v > 100 { 100 } else { v })
		}), vspk.slider(vol, 0, 100, 1), app.button('Enviar', fn [res, nombre, acepto, color, app] () {
			res.set('nombre=${nombre.text()}  acepto=${acepto.as_bool()}  color=${color.text()}')
			app.toast('Enviado', 'success')
		}), vspk.p(res.ref()), vspk.h4('9. Teclado, diálogos, temporizador, ventana'),
		vspk.p(tecla.ref()), vspk.row(vspk.p('ticks:'), vspk.h3(ticks.ref())),
		vspk.row(app.button('Abrir archivo...', fn [app, arch] () {
			app.pick_file('Elige un archivo', fn [arch] (p string) {
				arch.set('archivo: ${p}')
			})
		}), app.button('Cambiar título', fn [app] () {
			app.set_title('Hola desde V')
		}), app.button('Notificar', fn [app] () {
			app.notify('V', 'Hecho')
		}, variant: 'outlined')), vspk.p(arch.ref()), vspk.p(log.ref()), vspk.h4('10. Canvas'),
		lienzo.html(), vspk.p(raton.ref()), vspk.row(app.button('Limpiar', fn [lienzo] () {
			lienzo.erase()
		}, variant: 'outlined'), app.button('Dibujar', fn [lienzo] () {
			lienzo.color('#00AA00').circle(150, 75, 20)
		})))

	// Los menús se crean después de la tarjeta (los ids de callback siguen el orden de creación).
	menu := vspk.menubar(vspk.menu('Archivo', vspk.menu_item('Abrir ventana de ajustes', app.on_click(fn [ajustes] () {
		ajustes.show()
	}), 'ctrl+shift+a'), vspk.menu_sep(), vspk.menu_item('Cerrar ajustes', app.on_click(fn [ajustes] () {
		ajustes.close()
	}), '')), vspk.menu('Ayuda', vspk.menu_item('Acerca de', app.on_click(fn [log] () {
		log.set('acerca de')
	}), '')))
	app.add(menu, tarjeta)

	app.on_key(fn [tecla] (e vspk.KeyEvent) {
		tecla.set('tecla: ${e.key}')
	})
	app.on_close(fn [log] () bool {
		log.set('cerrando')
		return true
	})
	app.run_every(1000, fn [ticks] () bool {
		ticks.inc(1)
		return true
	})
	app.run() or { eprintln(err) }
	println('run() terminado')
}
