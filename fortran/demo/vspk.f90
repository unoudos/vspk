module vspk
  use iso_c_binding
  implicit none

  private
  public :: vspk_app, vspk_state, init_app, create_state, add_widget, h1, ref_state, run_app, free_app

  type :: vspk_app
     type(c_ptr) :: ptr = c_null_ptr
  end type vspk_app

  type :: vspk_state
     type(c_ptr) :: ptr = c_null_ptr
  end type vspk_state

  interface
     function c_vspk_app(title, w, h) bind(c, name="ftn_vspk_app")
       import :: c_ptr, c_char, c_int
       character(kind=c_char), dimension(*) :: title
       integer(c_int), value :: w, h
       type(c_ptr) :: c_vspk_app
     end function c_vspk_app

     function c_vspk_state_int(app, name, init) bind(c, name="ftn_vspk_state_int")
       import :: c_ptr, c_char, c_int
       type(c_ptr), value :: app
       character(kind=c_char), dimension(*) :: name
       integer(c_int), value :: init
       type(c_ptr) :: c_vspk_state_int
     end function c_vspk_state_int

     subroutine c_vspk_add(app, html) bind(c, name="ftn_vspk_add")
       import :: c_ptr, c_char
       type(c_ptr), value :: app
       type(c_ptr), value :: html
     end subroutine c_vspk_add

     function c_vspk_h1(text) bind(c, name="ftn_vspk_h1")
       import :: c_ptr, c_char
       character(kind=c_char), dimension(*) :: text
       type(c_ptr) :: c_vspk_h1
     end function c_vspk_h1

     function c_vspk_h1_ptr(text_ptr) bind(c, name="ftn_vspk_h1_ptr")
       import :: c_ptr
       type(c_ptr), value :: text_ptr
       type(c_ptr) :: c_vspk_h1_ptr
     end function c_vspk_h1_ptr

     function c_vspk_ref(state) bind(c, name="ftn_vspk_ref")
       import :: c_ptr
       type(c_ptr), value :: state
       type(c_ptr) :: c_vspk_ref
     end function c_vspk_ref

     function c_vspk_run(app) bind(c, name="ftn_vspk_run")
       import :: c_ptr, c_int
       type(c_ptr), value :: app
       integer(c_int) :: c_vspk_run
     end function c_vspk_run

     subroutine c_vspk_free(app) bind(c, name="ftn_vspk_free")
       import :: c_ptr
       type(c_ptr), value :: app
     end subroutine c_vspk_free
  end interface

contains

  function init_app(title, w, h) result(app)
     character(len=*), intent(in) :: title
     integer, intent(in) :: w, h
     type(vspk_app) :: app
     app%ptr = c_vspk_app(trim(title)//c_null_char, int(w, c_int), int(h, c_int))
  end function init_app

  function create_state(app, name, init) result(st)
     type(vspk_app), intent(in) :: app
     character(len=*), intent(in) :: name
     integer, intent(in) :: init
     type(vspk_state) :: st
     st%ptr = c_vspk_state_int(app%ptr, trim(name)//c_null_char, int(init, c_int))
  end function create_state

  subroutine add_widget(app, html_ptr)
     type(vspk_app), intent(in) :: app
     type(c_ptr), intent(in) :: html_ptr
     call c_vspk_add(app%ptr, html_ptr)
  end subroutine add_widget

  function h1(text) result(ptr)
     type(c_ptr), intent(in) :: text
     type(c_ptr) :: ptr
     ptr = c_vspk_h1_ptr(text)
  end function h1

  function ref_state(st) result(ptr)
     type(vspk_state), intent(in) :: st
     type(c_ptr) :: ptr
     ptr = c_vspk_ref(st%ptr)
  end function ref_state

  function run_app(app) result(rc)
     type(vspk_app), intent(in) :: app
     integer :: rc
     rc = int(c_vspk_run(app%ptr))
  end function run_app

  subroutine free_app(app)
     type(vspk_app), intent(in) :: app
     call c_vspk_free(app%ptr)
  end subroutine free_app

end module vspk