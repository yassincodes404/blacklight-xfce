"""On-demand notification page using the same channel as XFCE's panel and dialog."""
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Xfconf', '0')
from gi.repository import Gtk, Xfconf, Gio, GLib
from notifications import Settings


class NotificationPage:
    def __init__(self, app):
        self.app = app
        self.refreshing = False
        self.controls = {}
        page = app.page('Notifications', 'Choose what deserves your attention and how it appears.')
        Xfconf.init()
        self.channel = Xfconf.Channel.get('xfce4-notifyd')
        self.settings = Settings(self.channel)
        focus = app.card(page, 'Stay focused')
        self.switch(focus, 'do-not-disturb', 'Do Not Disturb', 'Pause ordinary popups. Critical alerts may still appear.')
        self.switch(focus, 'gauge-ignores-dnd', 'Keep volume and brightness indicators', 'Show hardware feedback even during Do Not Disturb.')
        display = app.card(page, 'Where notifications appear')
        self.combo(display, 'notify-location', 'Screen corner', [
            ('top-right', 'Top right'), ('top-left', 'Top left'), ('top-center', 'Top center'),
            ('bottom-right', 'Bottom right'), ('bottom-left', 'Bottom left'), ('bottom-center', 'Bottom center')])
        self.combo(display, 'show-notifications-on', 'Display', [
            ('active-monitor', 'Display with the pointer'), ('primary-monitor', 'Primary display'), ('all-monitors', 'All displays')])
        timing = app.card(page, 'Timing and feedback')
        self.switch(timing, 'expire-timeout-enabled', 'Dismiss ordinary notifications automatically')
        self.spin(timing, 'expire-timeout', 'Default duration', 1, 120, 'seconds')
        self.switch(timing, 'expire-timeout-allow-override', 'Let apps choose their duration', 'Critical alerts can remain until dismissed.')
        sound = self.sound_available = self.sound_supported()
        self.switch(timing, 'mute-sounds', 'Notification sounds',
                    None if sound else 'Notification sounds are unavailable from the current service. App audio is managed separately.', invert=True)
        self.controls['mute-sounds'][0].set_sensitive(sound)
        self.switch(timing, 'do-fadeout', 'Gentle fade when closing')
        history = app.card(page, 'History and privacy', 'Notification text may contain private messages. History is optional.')
        self.switch(history, 'notification-log', 'Save notification history')
        self.spin(history, 'log-max-size', 'History limit', 10, 10000, 'notifications')
        self.switch(history, 'log-max-size-enabled', 'Limit saved history')
        history.pack_start(app.label('Turning history off stops new entries. Existing entries can be reviewed or cleared in XFCE settings.', 'muted'), False, False, 0)
        actions = app.card(page, 'Applications and preview')
        app.button(actions, 'Manage apps and history', lambda: app.launch(['xfce4-notifyd-config']))
        app.button(actions, 'Send a preview', self.preview)
        self.refresh()
        self.handler = self.channel.connect('property-changed', self.changed)
        app.window.connect('destroy', self.close)

    def sound_supported(self):
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            reply = bus.call_sync('org.freedesktop.Notifications', '/org/freedesktop/Notifications',
                'org.freedesktop.Notifications', 'GetCapabilities', None, GLib.VariantType.new('(as)'),
                Gio.DBusCallFlags.NONE, 1500, None)
            return 'sound' in reply.unpack()[0]
        except GLib.Error:
            return False

    def row(self, box, title, widget, detail=None):
        row = Gtk.Box(spacing=18)
        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        text.pack_start(self.app.label(title), False, False, 0)
        if detail:
            label = self.app.label(detail, 'muted'); label.set_max_width_chars(44)
            text.pack_start(label, False, False, 0)
        row.pack_start(text, True, True, 0)
        widget.set_valign(Gtk.Align.CENTER)
        row.pack_end(widget, False, False, 0)
        box.pack_start(row, False, False, 0)

    def save(self, key, value):
        if self.refreshing:
            return
        try:
            self.settings.write(key, value)
            self.app.message.set_text('Notification settings saved.')
        except (ValueError, RuntimeError) as error:
            self.app.message.set_text(str(error))
        self.refresh()

    def switch(self, box, key, title, detail=None, invert=False):
        widget = Gtk.Switch()
        self.controls[key] = (widget, 'switch', invert)
        widget.connect('notify::active', lambda widget, _: self.save(key, not widget.get_active() if invert else widget.get_active()))
        self.row(box, title, widget, detail)

    def combo(self, box, key, title, options):
        widget = Gtk.ComboBoxText()
        for value, label in options:
            widget.append(value, label)
        self.controls[key] = (widget, 'combo', False)
        widget.connect('changed', lambda widget: self.save(key, widget.get_active_id()) if widget.get_active_id() else None)
        self.row(box, title, widget)

    def spin(self, box, key, title, lower, upper, unit):
        widget = Gtk.SpinButton.new_with_range(lower, upper, 1 if key == 'expire-timeout' else 10)
        widget.set_numeric(True)
        self.controls[key] = (widget, 'spin', False)
        widget.connect('value-changed', lambda widget: self.save(key, widget.get_value_as_int()))
        self.row(box, title, widget, unit)

    def refresh(self):
        self.refreshing = True
        try:
            for key, (widget, kind, invert) in self.controls.items():
                value = self.settings.read(key)
                if kind == 'switch':
                    widget.set_active(False if key == 'mute-sounds' and not self.sound_available else (not value if invert else value))
                elif kind == 'combo':
                    widget.set_active_id(value)
                else:
                    widget.set_value(value)
            self.controls['expire-timeout'][0].set_sensitive(self.settings.read('expire-timeout-enabled'))
            self.controls['log-max-size'][0].set_sensitive(self.settings.read('notification-log') and self.settings.read('log-max-size-enabled'))
        finally:
            self.refreshing = False

    def changed(self, channel, key, value):
        self.refresh()

    def close(self, *_):
        self.channel.disconnect(self.handler)

    def preview(self):
        import subprocess
        # Respect DND instead of temporarily overriding the user's focus setting.
        subprocess.run(['notify-send', '--app-name=Galinia', '--icon=preferences-system-notifications',
                        'A little less noise.', 'Your Galinia notification settings are ready.'], check=True, timeout=5)
        return 'Preview sent. Do Not Disturb and application rules still apply.'
