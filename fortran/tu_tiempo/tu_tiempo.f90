program tiempo_malaga
  use vspk
  use iso_c_binding
  implicit none

  type(vspk_app) :: app
  type(vspk_state) :: s_ciudad, s_temp
  integer :: rc

  ! 1. Inicializar la App de la ventana
  app = init_app("Pronostico del Tiempo - Malaga", 450, 560)

  ! 2. Crear los estados reactivos de texto
  s_ciudad = create_state_str(app, "ciudad", "Málaga, España")
  s_temp   = create_state_str(app, "temp", "22 °C")

  ! 3. Añadir los widgets visuales a la ventana (para que no aparezca en blanco)
  call add_widget(app, h1(ref_state(s_ciudad)))
  call add_widget(app, h1(ref_state(s_temp)))

  ! 4. Ejecutar el bucle de la GUI nativa
  print *, "Abriendo panel del tiempo en Fortran..."
  rc = run_app(app)

  ! 5. Liberar memoria
  call free_app(app)
end program tiempo_malaga