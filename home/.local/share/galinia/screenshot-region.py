#!/usr/bin/python3
"""X11 region selection over an undimmed, frozen desktop snapshot."""
import sys


def crop_rectangle(start, end, view_size, image_size):
    """Translate a drag in logical coordinates to bounded source-image pixels."""
    width, height = view_size
    pixels_w, pixels_h = image_size
    left, right = sorted((max(0, min(width, start[0])), max(0, min(width, end[0]))))
    top, bottom = sorted((max(0, min(height, start[1])), max(0, min(height, end[1]))))
    x, y = round(left * pixels_w / width), round(top * pixels_h / height)
    right, bottom = round(right * pixels_w / width), round(bottom * pixels_h / height)
    return x, y, right - x, bottom - y


def select_region(path):
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Gdk', '3.0')
    from gi.repository import Gdk, GdkPixbuf, Gtk

    if not Gtk.init_check()[0]:
        raise RuntimeError('Could not open the graphical display')
    display = Gdk.Display.get_default()
    if 'Wayland' in type(display).__name__:
        raise RuntimeError('Use grim/slurp for the Wayland session')
    root = Gdk.get_default_root_window()
    width, height = root.get_width(), root.get_height()
    # Capture BEFORE showing any selection UI. The outline can never enter the crop.
    snapshot = Gdk.pixbuf_get_from_window(root, 0, 0, width, height)
    if snapshot is None:
        raise RuntimeError('The X11 display did not return an image')
    preview = snapshot.scale_simple(width, height, GdkPixbuf.InterpType.BILINEAR)
    css = Gtk.CssProvider()
    css.load_from_data(b'''
      #galinia-capture, #galinia-capture * { box-shadow: none; background-image: none; }
      #galinia-capture { background-color: #141821; border: none; padding: 0; }
      #galinia-capture #capture-outline { background-color: transparent; border: 2px solid #ffc17d; border-radius: 0; padding: 0; margin: 0; min-width: 0; min-height: 0; }
      #galinia-capture #capture-hint { color: #fff5e8; background-color: #202632; border: 1px solid #efb579; border-radius: 8px; padding: 10px 16px; font: 14px Sans; }
    ''')
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    window = Gtk.Window(type=Gtk.WindowType.POPUP)
    window.set_name('galinia-capture')
    window.set_decorated(False)
    window.set_skip_taskbar_hint(True)
    window.set_skip_pager_hint(True)
    window.set_accept_focus(True)
    window.move(0, 0)
    window.set_default_size(width, height)
    fixed = Gtk.Fixed()
    window.add(fixed)
    fixed.put(Gtk.Image.new_from_pixbuf(preview), 0, 0)
    outline = Gtk.Frame()
    outline.set_name('capture-outline')
    outline.set_no_show_all(True)
    fixed.put(outline, 0, 0)
    hint = Gtk.Label(label='Drag to select an area  ·  Esc to cancel')
    hint.set_name('capture-hint')
    fixed.put(hint, 24, 24)
    state = {'start': None, 'error': None}
    seat = display.get_default_seat()

    def finish():
        seat.ungrab()
        window.destroy()
        Gtk.main_quit()

    def point(event):
        return max(0, min(width, event.x_root)), max(0, min(height, event.y_root))

    def press(widget, event):
        if event.button == 3:
            finish()
        elif event.button == 1:
            state['start'] = point(event)
            hint.hide()
        return True

    def motion(widget, event):
        if state['start'] is not None:
            x, y, w, h = crop_rectangle(state['start'], point(event), (width, height), (width, height))
            fixed.move(outline, x, y)
            outline.set_size_request(max(4, w), max(4, h))
            outline.show()
        return True

    def release(widget, event):
        if event.button != 1 or state['start'] is None:
            return True
        rectangle = crop_rectangle(state['start'], point(event), (width, height), (snapshot.get_width(), snapshot.get_height()))
        if rectangle[2] < 2 or rectangle[3] < 2:
            state['start'] = None
            outline.hide()
            hint.show()
            return True
        try:
            snapshot.new_subpixbuf(*rectangle).savev(path, 'png', [], [])
        except Exception as error:
            state['error'] = error
        finish()
        return True

    def key(widget, event):
        if event.keyval == Gdk.KEY_Escape:
            finish()
        return True

    window.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.KEY_PRESS_MASK)
    window.connect('button-press-event', press)
    window.connect('motion-notify-event', motion)
    window.connect('button-release-event', release)
    window.connect('key-press-event', key)
    window.show_all()
    cursor = Gdk.Cursor.new_from_name(display, 'crosshair')
    status = seat.grab(window.get_window(), Gdk.SeatCapabilities.POINTER | Gdk.SeatCapabilities.KEYBOARD, False, cursor, None, None, None)
    if status != Gdk.GrabStatus.SUCCESS:
        window.destroy()
        raise RuntimeError('Another application is using the pointer; try again')
    Gtk.main()
    if state['error']:
        raise state['error']


if __name__ == '__main__':
    try:
        select_region(sys.argv[1])
    except Exception as error:
        raise SystemExit('Galinia capture: ' + str(error)) from None
