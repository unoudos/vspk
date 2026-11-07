#define VSPK_IMPLEMENTATION
#include "vspk.h"

void* ftn_vspk_app(const char* title, int w, int h) { return vspk_app(title, w, h); }
void* ftn_vspk_state_int(void* app, const char* name, int init) { return vspk_state_int((VspkApp*)app, name, init); }
void ftn_vspk_add(void* app, const char* html) { vspk_add((VspkApp*)app, html); }
const char* ftn_vspk_h1(const char* text) { return vspk_h1(text); }
const char* ftn_vspk_h1_ptr(const char* text_ptr) { return vspk_h1(text_ptr); }
const char* ftn_vspk_ref(void* state) { return vspk_ref((VspkState*)state); }
int ftn_vspk_run(void* app) { return vspk_run((VspkApp*)app); }
void ftn_vspk_free(void* app) { vspk_free((VspkApp*)app); }