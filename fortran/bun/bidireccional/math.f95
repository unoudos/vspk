module math_lib
  use iso_c_binding
  implicit none

contains

  function sumar(a, b) result(res) bind(c, name="sumar")
    integer(c_int), value :: a, b
    integer(c_int) :: res
    res = a + b
  end function sumar

end module math_lib