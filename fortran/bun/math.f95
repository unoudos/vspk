module math_lib
  use iso_c_binding
  implicit none

contains

  ! La etiqueta bind(c, name="sumar") le dice a Fortran que exponga 
  ! la función exactamente con ese nombre para que Bun la encuentre.
  function sumar(a, b) result(res) bind(c, name="sumar")
    integer(c_int), value :: a, b
    integer(c_int) :: res
    res = a + b
  end function sumar

end module math_lib