#!/usr/bin/python3
"""Galinia's on-demand desktop control center."""
import copy
from pathlib import Path
import shutil
import subprocess
import sys

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gtk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preferences


class ControlCenter(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='org.galinia.ControlCenter')
        self.window = None

    def do_activate(self):
        if self.window:
            self.window.present()
            return
        self.window = Gtk.ApplicationWindow(application=self, title='Galinia Control Center')
        self.window.set_name('galinia-control-center')
        self.window.set_default_size(960, 680)
        self.window.set_position(Gtk.WindowPosition.CENTER)
        self.window.connect('destroy', lambda *_: setattr(self, 'window', None))
        css = Gtk.CssProvider()
        css.load_from_data(b'''
        #galinia-control-center { background: #141821; color: #f4eee7; }
        #galinia-control-center .sidebar { background: #191f2b; padding: 24px 14px; }
        #galinia-control-center .brand { color: #efb579; font-size: 22px; font-weight: bold; }
        #galinia-control-center .hero { font-size: 27px; font-weight: bold; }
        #galinia-control-center .muted { color: #c2c8d2; }
        #galinia-control-center .card { background: #202735; border: 1px solid #3d4757; border-radius: 14px; padding: 18px; }
        #galinia-control-center button { border-radius: 8px; padding: 8px 12px; }
        #galinia-control-center .settings-tile { min-height: 48px; background: #252d3b; }
        #galinia-control-center button:focus { outline: 2px solid #ffc17d; outline-offset: 2px; }
        ''')
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        root = Gtk.Box()
        self.window.add(root)
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        sidebar.set_size_request(205, -1)
        sidebar.get_style_context().add_class('sidebar')
        sidebar.pack_start(self.label('GALINIA', 'brand'), False, False, 0)
        sidebar.pack_start(self.label('Make it feel like yours.', 'muted'), False, False, 0)
        menu = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
        self.menu = menu
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        for name in ['Overview', 'Appearance', 'Desktop', 'Devices', 'System']:
            row = Gtk.ListBoxRow()
            row.name = name
            row.add(Gtk.Label(label=name, xalign=0, margin=12))
            menu.add(row)
        menu.connect('row-selected', lambda _, row: self.stack.set_visible_child_name(row.name) if row else None)
        sidebar.pack_start(menu, False, False, 0)
        sidebar.pack_end(self.label('Controls on demand.\nNo extra settings daemon.', 'muted'), False, False, 0)
        root.pack_start(sidebar, False, False, 0)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin=26)
        root.pack_start(content, True, True, 0)
        content.pack_start(self.stack, True, True, 0)
        self.message = self.label('Your desktop settings, together in one place.', 'muted')
        self.message.set_selectable(True)
        content.pack_end(self.message, False, False, 0)
        self.build_overview()
        self.build_appearance()
        self.build_categories()
        if getattr(self, 'preference_error', None):
            self.message.set_text('Preferences need repair: ' + self.preference_error)
        menu.select_row(menu.get_row_at_index(0))
        self.window.show_all()

    def label(self, text, style=None):
        label = Gtk.Label(label=text, xalign=0)
        label.set_line_wrap(True)
        label.set_max_width_chars(68)
        if style:
            label.get_style_context().add_class(style)
        return label

    def page(self, name, description):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, margin=2)
        box.pack_start(self.label(name, 'hero'), False, False, 0)
        box.pack_start(self.label(description, 'muted'), False, False, 0)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_overlay_scrolling(False)
        scroll.add(box)
        self.stack.add_named(scroll, name)
        return box

    def card(self, page, title, description=None):
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.get_style_context().add_class('card')
        card.pack_start(self.label(title), False, False, 0)
        if description:
            card.pack_start(self.label(description, 'muted'), False, False, 0)
        page.pack_start(card, False, False, 0)
        return card

    def button(self, box, title, callback):
        button = Gtk.Button.new_with_label(title)
        button.set_halign(Gtk.Align.START)
        button.connect('clicked', lambda *_: self.action(callback))
        box.pack_start(button, False, False, 0)
        return button

    def action(self, callback):
        try:
            result = callback()
            if isinstance(result, str):
                self.message.set_text(result)
        except Exception as error:
            detail = getattr(error, 'stderr', None) or str(error)
            self.message.set_text('Could not apply: ' + detail[:500])

    def launch(self, command):
        if not shutil.which(command[0]):
            raise ValueError('This tool is not installed: ' + command[0])
        subprocess.Popen(command, start_new_session=True)

    def settings(self):
        try:
            return preferences.load()
        except (OSError, ValueError) as error:
            self.preference_error = str(error)
            return copy.deepcopy(preferences.DEFAULTS)

    def build_overview(self):
        page = self.page('Overview', 'Your Galinia desktop. Make it comfortable, connected and ready for everyday work.')
        card = self.card(page, 'Make it yours', 'Choose your wallpaper, colors and desktop layout in Appearance.')
        self.button(card, 'Personalize desktop', lambda: self.stack.set_visible_child_name('Appearance'))
        card = self.card(page, 'Everyday settings', 'Manage displays, sound, connections and power in Devices.')
        self.button(card, 'Device settings', lambda: self.stack.set_visible_child_name('Devices'))
        card = self.card(page, 'Find your way', 'Super + Space opens app search. Super + / shows keyboard shortcuts.')
        self.button(card, 'Keyboard shortcuts', lambda: self.launch([str(Path(__file__).resolve().parents[2] / 'bin/galinia-shortcuts')]))
        self.button(card, 'Undo last appearance change', self.undo)

    def build_appearance(self):
        page = self.page('Appearance', 'Keep colors tied to your wallpaper or choose a readable accent. Make the desktop feel like yours.')
        data = self.settings()
        card = self.card(page, 'Your desktop palette')
        self.accent_mode = Gtk.ComboBoxText()
        self.accent_mode.append('wallpaper', 'Follow wallpaper')
        self.accent_mode.append('fixed', 'Use my accent')
        self.accent_mode.set_active_id(data['accent_mode'])
        card.pack_start(self.accent_mode, False, False, 0)
        self.color = Gtk.ColorButton()
        rgba = Gdk.RGBA(); rgba.parse(data['fixed_accent']); self.color.set_rgba(rgba)
        self.color.set_title('Choose a readable Galinia accent')
        self.color.set_halign(Gtk.Align.START)
        card.pack_start(self.color, False, False, 0)
        card = self.card(page, 'Comfort and space')
        row = Gtk.Box(spacing=16)
        row.pack_start(self.label('Main panel height'), True, True, 0)
        self.panel = Gtk.SpinButton.new_with_range(28, 48, 2)
        self.panel.set_value(data['panel_size'])
        try:
            actual = subprocess.check_output(['xfconf-query', '-c', 'xfce4-panel', '-p', '/panels/panel-1/size'], text=True, timeout=3)
            self.panel.set_value(int(actual.strip()))
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
        row.pack_end(self.panel, False, False, 0); card.pack_start(row, False, False, 0)
        self.monitor = Gtk.CheckButton.new_with_label('Show desktop system monitor')
        self.monitor.set_active(data['monitor_enabled'])
        card.pack_start(self.monitor, False, False, 0)
        self.audio = Gtk.CheckButton.new_with_label('Show desktop sound and music card')
        self.audio.set_active(data['audio_enabled'])
        card.pack_start(self.audio, False, False, 0)
        layout = Gtk.ComboBoxText()
        layout.append('custom', 'Choose a layout preset…')
        layout.append('compact', 'Compact — smaller panel, monitor hidden')
        layout.append('comfortable', 'Comfortable — larger panel, monitor visible')
        layout.set_active_id('custom')
        def choose_layout(combo):
            if combo.get_active_id() == 'compact':
                self.panel.set_value(30); self.monitor.set_active(False)
            elif combo.get_active_id() == 'comfortable':
                self.panel.set_value(40); self.monitor.set_active(True)
        layout.connect('changed', choose_layout)
        card.pack_start(layout, False, False, 0)
        self.button(card, 'Apply appearance', self.apply_appearance)
        self.button(card, 'Choose wallpaper', lambda: self.launch(['xfdesktop-settings']))

    def apply_appearance(self):
        data = preferences.load()
        color = self.color.get_rgba()
        data.update(accent_mode=self.accent_mode.get_active_id(),
                    fixed_accent='#' + ''.join(f'{round(v * 255):02x}' for v in (color.red, color.green, color.blue)),
                    panel_size=self.panel.get_value_as_int(), monitor_enabled=self.monitor.get_active(), audio_enabled=self.audio.get_active())
        preferences.apply_desktop(data)
        return 'Appearance saved.'

    def undo(self):
        preferences.undo()
        data = preferences.load()
        self.accent_mode.set_active_id(data['accent_mode'])
        color = Gdk.RGBA(); color.parse(data['fixed_accent']); self.color.set_rgba(color)
        self.panel.set_value(data['panel_size']); self.monitor.set_active(data['monitor_enabled'])
        self.audio.set_active(data['audio_enabled'])
        return 'Last preference change undone.'

    def build_categories(self):
        groups = [
            ('Desktop', 'Set up navigation, windows and your daily workspace.', [
                ('Windows', 'xfwm4-settings'), ('Window behavior', 'xfwm4-tweaks-settings'),
                ('Workspaces', 'xfwm4-workspace-settings'), ('Panel', 'xfce4-panel', '--preferences'),
                ('Keyboard and shortcuts', 'xfce4-keyboard-settings'), ('Mouse and touchpad', 'xfce4-mouse-settings'),
                ('Notifications', 'xfce4-notifyd-config'), ('Accessibility', 'xfce4-accessibility-settings'),
                ('Session and startup', 'xfce4-session-settings')]),
            ('Devices', 'Connect your devices and choose how they work.', [
                ('Displays', 'xfce4-display-settings'), ('Sound', 'pavucontrol'),
                ('Network connections', 'nm-connection-editor'), ('Bluetooth', 'blueman-manager'),
                ('Power and suspend', 'xfce4-power-manager-settings'),
                ('Screen lock', 'xfce4-screensaver-preferences'), ('Printers', 'system-config-printer')]),
            ('System', 'Keep your system up to date and your files protected.', [
                ('Software', 'gnome-software'), ('Updates', 'update-manager'),
                ('Software sources and drivers', 'software-properties-gtk'), ('Backups', 'deja-dup'),
                ('All XFCE settings', 'xfce4-settings-manager')]),
        ]
        for title, description, tools in groups:
            page = self.page(title, description)
            card = self.card(page, title + ' settings')
            grid = Gtk.Grid(column_spacing=12, row_spacing=12, column_homogeneous=True)
            card.pack_start(grid, False, False, 0)
            icons = {'Windows': 'preferences-system-windows', 'Window behavior': 'preferences-system-windows',
                     'Workspaces': 'preferences-desktop-workspaces', 'Panel': 'preferences-desktop',
                     'Keyboard and shortcuts': 'input-keyboard', 'Mouse and touchpad': 'input-mouse',
                     'Notifications': 'preferences-system-notifications', 'Accessibility': 'preferences-desktop-accessibility',
                     'Displays': 'video-display', 'Sound': 'audio-volume-high', 'Network connections': 'network-workgroup',
                     'Bluetooth': 'bluetooth', 'Power and suspend': 'battery', 'Screen lock': 'system-lock-screen',
                     'Printers': 'printer', 'Software': 'system-software-install', 'Updates': 'system-software-update',
                     'Backups': 'document-save'}
            for index, (label, *command) in enumerate(tools):
                button = Gtk.Button()
                button.get_style_context().add_class('settings-tile')
                row = Gtk.Box(spacing=12)
                row.pack_start(Gtk.Image.new_from_icon_name(icons.get(label, 'preferences-system'), Gtk.IconSize.LARGE_TOOLBAR), False, False, 0)
                row.pack_start(self.label(label), True, True, 0)
                button.add(row)
                button.connect('clicked', lambda _, cmd=command: self.action(lambda: self.launch(cmd)))
                grid.attach(button, index % 2, index // 2, 1, 1)
                if not shutil.which(command[0]):
                    button.set_sensitive(False)
                    button.set_tooltip_text('This tool is not installed.')
        import platform
        self.card(page, 'About Galinia', 'Galinia desktop • XFCE\nKernel ' + platform.release())


if __name__ == '__main__':
    raise SystemExit(ControlCenter().run(sys.argv))
