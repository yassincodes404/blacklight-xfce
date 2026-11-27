#!/usr/bin/python3
"""Small offline shortcut reference; exits when closed."""
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib

SHORTCUTS = [
    ('Super + Space', 'Find and open applications'),
    ('Super + /', 'Open this shortcut reference'),
    ('Super + Enter', 'Open the preferred terminal'),
    ('Super + E', 'Open files'),
    ('Super + W', 'Open the preferred browser'),
    ('Super + S', 'Open desktop settings'),
    ('Super + Left / Right', 'Tile the current window'),
    ('Super + Shift + Up', 'Toggle maximize'),
    ('Alt + Tab', 'Switch applications'),
    ('Alt + F4', 'Close the current window'),
    ('Print / Super + Shift + S', 'Select and annotate with Flameshot'),
    ('Ctrl + C / Ctrl + V', 'Copy a capture in Flameshot / paste it'),
    ('Super + L', 'Lock the session'),
    ('Ctrl + Shift + Esc', 'Open Task Manager'),
]


def create_window():
    window = Gtk.Window(title='Galinia · Keyboard shortcuts')
    window.set_default_size(650, 600)
    window.set_position(Gtk.WindowPosition.CENTER)
    window.set_icon_name('preferences-desktop-keyboard-shortcuts')
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14, margin=24)
    window.add(root)
    heading = Gtk.Label(xalign=0)
    heading.set_markup('<span size="x-large" weight="bold">Move around Galinia</span>')
    root.pack_start(heading, False, False, 0)
    root.pack_start(Gtk.Label(label='Super is the Windows key. Escape closes this guide.', xalign=0), False, False, 0)
    scroll = Gtk.ScrolledWindow()
    scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    scroll.set_overlay_scrolling(False)
    grid = Gtk.Grid(row_spacing=8, column_spacing=24, margin=4)
    for row, (keys, action) in enumerate(SHORTCUTS):
        key = Gtk.Label(xalign=0)
        key.set_markup('<b>' + GLib.markup_escape_text(keys) + '</b>')
        grid.attach(key, 0, row, 1, 1)
        grid.attach(Gtk.Label(label=action, xalign=0), 1, row, 1, 1)
    scroll.add(grid)
    root.pack_start(scroll, True, True, 0)
    close = Gtk.Button.new_with_label('Close')
    close.set_halign(Gtk.Align.END)
    close.connect('clicked', lambda *_: window.destroy())
    root.pack_start(close, False, False, 0)
    window.connect('key-press-event', lambda widget, event: (widget.destroy() or True) if event.keyval == 65307 else False)
    return window


if __name__ == '__main__':
    window = create_window()
    window.connect('destroy', Gtk.main_quit)
    window.show_all()
    Gtk.main()
