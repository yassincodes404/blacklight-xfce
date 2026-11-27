"""GTK3 Wayland desktop anchoring without an additional GI typelib dependency."""
import ctypes


def anchor_audio(window, library=None):
    layer = library or ctypes.CDLL('libgtk-layer-shell.so.0')
    layer.gtk_layer_is_supported.restype = ctypes.c_int
    if not layer.gtk_layer_is_supported():
        raise RuntimeError('This Wayland compositor does not support desktop layer surfaces.')
    pointer = ctypes.pythonapi.PyCapsule_GetPointer
    pointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
    pointer.restype = ctypes.c_void_p
    native = pointer(window.__gpointer__, None)
    calls = [
        ('gtk_layer_init_for_window', [ctypes.c_void_p], [native]),
        ('gtk_layer_set_namespace', [ctypes.c_void_p, ctypes.c_char_p], [native, b'galinia-audio']),
        ('gtk_layer_set_layer', [ctypes.c_void_p, ctypes.c_int], [native, 1]),
        ('gtk_layer_set_exclusive_zone', [ctypes.c_void_p, ctypes.c_int], [native, 0]),
        ('gtk_layer_set_keyboard_mode', [ctypes.c_void_p, ctypes.c_int], [native, 2]),
    ]
    # RIGHT=1, BOTTOM=3. Leave input enabled: this widget has real controls.
    for edge in [1, 3]:
        calls += [('gtk_layer_set_anchor', [ctypes.c_void_p, ctypes.c_int, ctypes.c_int], [native, edge, 1]),
                  ('gtk_layer_set_margin', [ctypes.c_void_p, ctypes.c_int, ctypes.c_int], [native, edge, 24])]
    for name, types, args in calls:
        function = getattr(layer, name)
        function.argtypes = types
        function.restype = None
        function(*args)
    return layer
