program main
  use vspk
  implicit none

  type(vspk_app) :: app
  type(vspk_state) :: mi_contador
  integer :: rc

  ! 1. Inicializar aplicación gráfica
  app = init_app("GUI en Fortran Puro", 400, 300)

  ! 2. Crear estado reactivo entero
  mi_contador = create_state(app, "n", 42)

  ! 3. Añadir componentes visuales
  call add_widget(app, h1(ref_state(mi_contador)))

  ! 4. Ejecutar la interfaz gráfica
  print *, "Abriendo ventana web nativa desde Fortran..."
  rc = run_app(app)

  ! 5. Liberar memoria
  call free_app(app)
end program main