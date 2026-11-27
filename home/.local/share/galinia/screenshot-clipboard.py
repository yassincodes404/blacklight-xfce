#!/usr/bin/python3
"""Serve a saved screenshot on X11 until another application owns the clipboard.

X11 clipboard data belongs to a running process. Keeping this small GTK process
alive makes image paste work even without a clipboard manager installed.
"""
import subprocess
import sys
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, GdkPixbuf, Gtk


def notify(title, message):
    try:
        subprocess.Popen(['notify-send', title, message], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def main(path):
    if not Gtk.init_check()[0]:
        raise RuntimeError('Could not open the graphical display')
    image = GdkPixbuf.Pixbuf.new_from_file(path)
    clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    clipboard.set_image(image)
    owner = Gdk.selection_owner_get(Gdk.SELECTION_CLIPBOARD)

    def replaced(clipboard, event):
        if event.owner != owner:
            Gtk.main_quit()

    clipboard.connect('owner-change', replaced)
    notify('Screenshot saved and copied', 'Press Ctrl+V to paste. Saved to ' + path)
    Gtk.main()


if __name__ == '__main__':
    try:
        main(sys.argv[1])
    except Exception as error:
        notify('Screenshot saved; clipboard failed', str(error))
        raise SystemExit(str(error)) from None
