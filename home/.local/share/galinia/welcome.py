#!/usr/bin/python3
"""Galinia first-login guide; runs without elevated privileges."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gio, GLib, Gtk, Gdk


def state_file():
    return Path(os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'galinia/welcome-v1-complete'


class Welcome(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='org.galinia.Welcome', flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.window = None
        self.page = 0
        self.pages = []

    def do_activate(self):
        if self.window:
            self.window.present()
            return
        css = Gtk.CssProvider()
        css.load_from_data(b'''
        #galinia-welcome { background: #141821; color: #f4eee7; }
        #galinia-welcome .brand { color: #efb579; font-size: 12px; font-weight: bold; letter-spacing: 3px; }
        #galinia-welcome .hero { font-size: 32px; font-weight: bold; }
        #galinia-welcome .subtitle { color: #c0c4ce; font-size: 15px; }
        #galinia-welcome .card { background: #202632; border: 1px solid #39414e; border-radius: 14px; padding: 16px; }
        #galinia-welcome .card-title { font-size: 18px; font-weight: bold; }
        #galinia-welcome button { border-radius: 9px; padding: 9px 16px; }
        #galinia-welcome button.suggested-action { background: #efb579; color: #211a14; text-shadow: none; }
        #galinia-welcome button:focus { outline: 2px solid #ffd8a5; outline-offset: 2px; }
        ''')
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.window = Gtk.ApplicationWindow(application=self, title='Welcome to Galinia')
        self.window.set_name('galinia-welcome')
        self.window.set_default_size(760, 600)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        icon = Path(__file__).resolve().parents[1] / 'icons/hicolor/scalable/apps/galinia.svg'
        if icon.exists():
            self.window.set_icon_from_file(str(icon))
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18, margin=28)
        self.window.add(root)
        header = Gtk.Box(spacing=18)
        if icon.exists():
            from gi.repository import GdkPixbuf
            header.pack_start(Gtk.Image.new_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(str(icon), 64, 64, True)), False, False, 0)
        heading = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        heading.pack_start(self.label('GALINIA', 'brand'), False, False, 0)
        heading.pack_start(self.label('Make yourself at home.', 'hero'), False, False, 0)
        header.pack_start(heading, True, True, 0)
        root.pack_start(header, False, False, 0)
        root.pack_start(self.label('A calm workspace. A little fire. Yours to explore.', 'subtitle'), False, False, 0)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_overlay_scrolling(False)
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        scroll.add(self.stack)
        root.pack_start(scroll, True, True, 0)
        self.add_page('Settle in', [
            ('Your desktop, your way', 'Choose a wallpaper and Galinia will follow its colors. Adjust fonts, display scaling and desktop preferences in Settings.', 'Open Settings', ['xfce4-settings-manager']),
            ('Find your flow', 'Press Super + Space to search your apps. Use the top panel for running apps and system controls.', None, None),
        ])
        self.add_page('Get ready', [
            ('Keep your system current', 'Galinia builds on Ubuntu / Xubuntu. Use the base system’s update tools for packages and security fixes.', 'Check for updates', ['update-manager']),
            ('Check your hardware', 'Review available graphics and wireless drivers. Some changes need an internet connection and a restart.', 'Open driver settings', ['software-properties-gtk', '--open-tab=4']),
        ])
        self.add_page('Make it yours', [
            ('A comfortable workspace', 'Set your wallpaper, keyboard layout and accessibility preferences. You can change these any time.', 'Desktop settings', ['xfdesktop-settings']),
            ('Find your applications', 'Browse and install software using the system software manager. Package availability depends on your configured repositories.', 'Open Software', ['gnome-software']),
        ])
        self.add_page('Stay safe', [
            ('Protect your files', 'Choose a backup location for your documents and personal files. Desktop configuration restore is separate from a personal-file backup.', 'Set up backups', ['deja-dup']),
            ('A little help', 'Read the offline first-steps guide for shortcuts, updates, screen locking and recovery. Reopen this welcome from the application menu any time.', 'Open first steps', ['xdg-open', str(Path(__file__).with_name('first-steps.html'))]),
        ])
        self.notice = self.label('', 'subtitle')
        self.notice.set_no_show_all(True)
        root.pack_start(self.notice, False, False, 0)
        footer = Gtk.Box(spacing=10)
        later = Gtk.Button.new_with_label('Skip welcome')
        later.connect('clicked', self.complete)
        footer.pack_start(later, False, False, 0)
        self.progress = Gtk.Label()
        footer.pack_start(self.progress, True, True, 0)
        self.back = Gtk.Button.new_with_label('Back')
        self.back.connect('clicked', self.navigate, -1)
        footer.pack_start(self.back, False, False, 0)
        self.next = Gtk.Button.new_with_label('Next')
        self.next.get_style_context().add_class('suggested-action')
        self.next.connect('clicked', self.advance)
        footer.pack_start(self.next, False, False, 0)
        root.pack_start(footer, False, False, 0)
        self.update_page()
        self.window.show_all()

    def label(self, text, style):
        label = Gtk.Label(label=text, xalign=0)
        label.set_line_wrap(True)
        label.set_max_width_chars(68)
        label.get_style_context().add_class(style)
        return label

    def add_page(self, name, cards):
        self.pages.append(name)
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for title, body, action, command in cards:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            card.get_style_context().add_class('card')
            card.pack_start(self.label(title, 'card-title'), False, False, 0)
            card.pack_start(self.label(body, 'subtitle'), False, False, 0)
            if action:
                button = Gtk.Button.new_with_label(action)
                button.set_halign(Gtk.Align.START)
                button.connect('clicked', self.launch, command)
                card.pack_start(button, False, False, 0)
            page.pack_start(card, False, False, 0)
        self.stack.add_named(page, name)

    def launch(self, button, command):
        if not shutil.which(command[0]):
            self.notice.set_text('This tool is not installed: ' + command[0] + '. Use your base system’s settings or package manager.')
            self.notice.show()
            return
        try:
            subprocess.Popen(command, start_new_session=True)
        except OSError as error:
            self.notice.set_text('Could not open the tool: ' + str(error))
            self.notice.show()

    def update_page(self):
        names = self.pages
        self.stack.set_visible_child_name(names[self.page])
        self.progress.set_text(f'{self.page + 1} / {len(names)} · {names[self.page]}')
        self.back.set_sensitive(self.page > 0)
        self.next.set_label('Start using Galinia' if self.page == len(names) - 1 else 'Next')

    def navigate(self, button, direction):
        self.page = max(0, min(len(self.pages) - 1, self.page + direction))
        self.update_page()

    def advance(self, button):
        if self.page == len(self.pages) - 1:
            self.complete(button)
        else:
            self.navigate(button, 1)

    def complete(self, button):
        try:
            path = state_file()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('1\n')
        except OSError as error:
            self.notice.set_text('Could not save your choice: ' + str(error))
            self.notice.show()
            return
        self.quit()


if __name__ == '__main__':
    if '--autostart' in sys.argv and (state_file().exists() or Path('/run/casper').exists()):
        sys.exit(0)
    sys.exit(Welcome().run([sys.argv[0]]))
