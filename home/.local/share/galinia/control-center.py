#!/usr/bin/python3
"""Galinia's on-demand desktop control center."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk, Gio, Gtk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import preferences
import performance
import memory_preset


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
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        for name in ['Overview', 'Appearance', 'App priorities', 'Memory', 'System tools']:
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
        self.message = self.label('Changes stay in your account. Use Undo to reverse the last preference change.', 'muted')
        self.message.set_selectable(True)
        content.pack_end(self.message, False, False, 0)
        self.build_overview()
        self.build_appearance()
        self.build_apps()
        self.build_memory()
        self.build_tools()
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
        page = self.page('Overview', 'A calm desktop with clear controls for appearance, responsiveness and memory.')
        card = self.card(page, 'How your system is doing')
        self.overview = self.label('', 'muted')
        card.pack_start(self.overview, False, False, 0)
        self.button(card, 'Refresh snapshot', self.refresh)
        self.refresh()
        card = self.card(page, 'Find your flow', 'Super + Space finds applications. Super + / shows navigation and window shortcuts.')
        self.button(card, 'Keyboard shortcuts', lambda: self.launch([str(Path(__file__).resolve().parents[2] / 'bin/galinia-shortcuts')]))
        self.button(card, 'Undo last preference change', self.undo)

    def refresh(self):
        snap = performance.snapshot()
        cpu = snap['cpu_pressure'].get('some', {}).get('avg10')
        mem = snap['memory_pressure'].get('some', {}).get('avg10')
        pressure = lambda value: 'unavailable' if value is None else f'{value:.2f}% stalled over the last 10 seconds'
        self.overview.set_text(f"Memory available: {snap['available_mib'] / 1024:.1f} / {snap['total_mib'] / 1024:.1f} GiB\n\nCPU pressure: {pressure(cpu)}\nMemory pressure: {pressure(mem)}")
        return 'Snapshot refreshed. Available memory includes reclaimable cache.'

    def build_appearance(self):
        page = self.page('Appearance', 'Keep colors tied to your wallpaper or choose a readable accent. Changes are event-driven.')
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
                    panel_size=self.panel.get_value_as_int(), monitor_enabled=self.monitor.get_active())
        preferences.apply_desktop(data)
        return 'Appearance saved. Accent changes refresh through the wallpaper service.'

    def build_apps(self):
        page = self.page('App priorities', 'Decide which work should yield when the CPU is busy. No hard RAM caps or CPU reservations.')
        card = self.card(page, 'Priority for the next launch', 'Applies when opening the app through Galinia search. Close an existing app first; its running process is not moved.')
        self.apps = Gtk.ComboBoxText()
        entries = sorted([app for app in Gio.AppInfo.get_all() if app.should_show() and app.get_id()], key=lambda app: app.get_display_name().casefold())
        for app in entries:
            self.apps.append(app.get_id(), app.get_display_name())
        self.apps.set_active(0)
        card.pack_start(self.apps, False, False, 0)
        self.priority = Gtk.ComboBoxText()
        for key, label in [('normal', 'Normal'), ('interactive', 'Prefer during CPU contention'), ('background', 'Background — yield to other work')]:
            self.priority.append(key, label)
        card.pack_start(self.priority, False, False, 0)
        self.apps.connect('changed', lambda *_: self.priority.set_active_id(self.settings()['app_profiles'].get(self.apps.get_active_id(), 'normal')))
        self.priority.set_active_id(self.settings()['app_profiles'].get(self.apps.get_active_id(), 'normal'))
        self.button(card, 'Save app priority', self.save_priority)
        self.button(card, 'Reset this app to normal', lambda: self.save_priority(reset=True))

    def save_priority(self, reset=False):
        app_id = self.apps.get_active_id()
        if not app_id:
            raise ValueError('Choose an application first.')
        data = preferences.load()
        if reset:
            data['app_profiles'].pop(app_id, None); self.priority.set_active_id('normal')
        else:
            data['app_profiles'][app_id] = self.priority.get_active_id()
        preferences.save(data)
        return 'Priority saved for the next launch through Galinia app search.'

    def build_memory(self):
        page = self.page('Memory', 'Let inactive browser tabs yield memory sooner while keeping active work available.')
        card = self.card(page, 'Firefox memory behavior', 'Aggressive mode allows more reloads when revisiting tabs. These are memory-pressure preferences, not a fixed RAM cap or an inactivity timer.')
        self.profiles = Gtk.ComboBoxText()
        for root in [Path.home() / '.mozilla/firefox', Path.home() / 'snap/firefox/common/.mozilla/firefox']:
            if root.is_dir():
                for profile in sorted(root.iterdir()):
                    if profile.is_dir() and (profile / 'prefs.js').is_file():
                        self.profiles.append(str(profile), profile.name + (' (Snap)' if 'snap' in str(root) else ''))
        self.profiles.set_active(0)
        card.pack_start(self.profiles, False, False, 0)
        self.memory_mode = Gtk.ComboBoxText()
        self.memory_mode.append('balanced', 'Balanced'); self.memory_mode.append('aggressive', 'Aggressive')
        self.memory_mode.set_active_id('balanced'); card.pack_start(self.memory_mode, False, False, 0)
        self.button(card, 'Save for next Firefox startup', self.apply_memory)
        self.button(card, 'Undo latest Firefox preset', self.undo_memory)
        self.card(page, 'Understand what the numbers mean', 'Available memory includes reclaimable cache. A browser tab can use substantial RAM for active page content. Use Firefox’s about:unloads page for direct tab control.')

    def selected_profile(self):
        value = self.profiles.get_active_id()
        if not value:
            raise ValueError('No Firefox profile found. Start Firefox once to create one.')
        return Path(value)

    def apply_memory(self):
        backup = memory_preset.apply(self.selected_profile(), self.memory_mode.get_active_id())
        return 'Preset saved for the next Firefox startup. A private restore backup was created.' if backup else 'That preset is already saved.'

    def undo_memory(self):
        profile = self.selected_profile()
        current = profile / 'user.js'
        current_hash = memory_preset.digest(current.read_text()) if current.exists() else None
        for backup in reversed(sorted((profile / '.galinia-memory-backups').glob('*.json'))):
            data = json.loads(backup.read_text())
            if data.get('installed_sha256') == current_hash:
                memory_preset.restore(profile, backup)
                return 'Previous Firefox memory preferences restored.'
        raise ValueError('No matching preset backup was found; preserve any later user.js edits before restoring.')

    def undo(self):
        preferences.undo()
        data = preferences.load()
        self.accent_mode.set_active_id(data['accent_mode'])
        color = Gdk.RGBA(); color.parse(data['fixed_accent']); self.color.set_rgba(color)
        self.panel.set_value(data['panel_size']); self.monitor.set_active(data['monitor_enabled'])
        self.priority.set_active_id(data['app_profiles'].get(self.apps.get_active_id(), 'normal'))
        return 'Last desktop/app preference change undone.'

    def build_tools(self):
        page = self.page('System tools', 'Use the maintained system tools for hardware, updates, accessibility and recovery.')
        card = self.card(page, 'Everyday controls')
        for title, command in [('All XFCE settings', 'xfce4-settings-manager'), ('Displays', 'xfce4-display-settings'),
                               ('Keyboard', 'xfce4-keyboard-settings'), ('Power and suspend', 'xfce4-power-manager-settings'),
                               ('Audio', 'pavucontrol'), ('Bluetooth', 'blueman-manager'), ('Software', 'gnome-software'),
                               ('Updates', 'update-manager'), ('Backups', 'deja-dup')]:
            button = self.button(card, title, lambda cmd=command: self.launch([cmd]))
            if not shutil.which(command):
                button.set_sensitive(False); button.set_tooltip_text('Install ' + command + ' to enable this tool.')
        snap = performance.snapshot()
        self.card(page, 'Current kernel configuration', f"CPU governor: {snap['governor']}\nSwappiness: {snap['swappiness']}\nCompressed swap cache (zswap): {snap['zswap']}\nKernel settings are shown for diagnosis; desktop controls do not overwrite them.")


if __name__ == '__main__':
    raise SystemExit(ControlCenter().run(sys.argv))
