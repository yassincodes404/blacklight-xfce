#!/usr/bin/python3
"""Search installed desktop applications without a shell or a network lookup."""
import gi
import os
import subprocess

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango

APP_ID = "org.galinia.AppSearch"
IDLE_SECONDS = 60


class AppSearch(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)
        self.window = None
        self.idle_source = 0
        self.index_dirty = True

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.hold()
        self.app_monitor = Gio.AppInfoMonitor.get()
        self.app_monitor.connect("changed", self.apps_changed)
        self.schedule_idle_exit()

    def do_activate(self):
        if self.window is not None and self.window.get_visible():
            self.hide_window()
            return
        if self.idle_source:
            GLib.source_remove(self.idle_source)
            self.idle_source = 0
        if self.index_dirty:
            self.reload_apps()
        if self.window is None:
            self.build_window()
        elif self.entry.get_text():
            self.entry.set_text("")
        else:
            self.refresh()
        self.window.show_all()
        self.entry.grab_focus()
        self.window.present()

    def schedule_idle_exit(self):
        if not self.idle_source:
            self.idle_source = GLib.timeout_add_seconds(IDLE_SECONDS, self.exit_when_idle)

    def exit_when_idle(self):
        self.idle_source = 0
        self.quit()
        return GLib.SOURCE_REMOVE

    def apps_changed(self, *_):
        self.index_dirty = True
        if self.window is not None and self.window.get_visible():
            self.reload_apps()
            self.refresh()

    def reload_apps(self):
        self.apps = {}
        self.search_index = []
        for app in Gio.AppInfo.get_all():
            if not app.should_show():
                continue
            label = app.get_display_name()
            name = label.casefold()
            keywords = app.get_keywords() if hasattr(app, "get_keywords") else []
            terms = " ".join([name, app.get_description() or "",
                              app.get_executable() or "", *(keywords or [])]).casefold()
            self.apps.setdefault(app.get_id(), app)
            self.search_index.append((name, terms, app))
        self.index_dirty = False

    def build_window(self):
        self.window = Gtk.ApplicationWindow(application=self, title="Search apps")
        self.window.connect("delete-event", self.hide_window)
        self.window.connect("key-press-event", self.key_pressed)
        self.window.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.window.set_resizable(False)
        self.window.set_decorated(False)
        self.window.set_skip_taskbar_hint(True)
        self.window.set_name("galinia-search-window")
        visual = self.window.get_screen().get_rgba_visual()
        if visual:
            self.window.set_visual(visual)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_name("galinia-search-card")
        box.set_size_request(580, -1)
        self.window.add(box)
        self.entry = Gtk.SearchEntry(placeholder_text="Search installed apps…")
        self.entry.set_name("galinia-search-entry")
        self.entry.connect("changed", self.refresh)
        box.pack_start(self.entry, False, False, 0)

        # Reserve the same space for zero, one, or six matches. Wayland places
        # the toplevel at map time, so changing its height would shift its center.
        self.body = Gtk.Stack()
        self.body.set_size_request(-1, 240)
        box.pack_start(self.body, False, False, 0)
        self.results = Gtk.ListBox()
        self.results.set_name("galinia-app-results")
        self.results.connect("row-activated", self.open_row)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.results)
        self.body.add_named(scroll, "results")
        self.message = Gtk.Label()
        self.message.get_style_context().add_class("dim-label")
        self.body.add_named(self.message, "message")

        hints = Gtk.Label(label="↑ ↓  Select     ↵  Open     Esc  Close", xalign=1)
        hints.set_name("galinia-search-hints")
        box.pack_end(hints, False, False, 0)
        self.css = Gtk.CssProvider()
        self.css.load_from_data(b"""
            #galinia-search-window {
                background: transparent;
            }
            #galinia-search-card {
                background: @theme_bg_color;
                border: 1px solid alpha(@theme_fg_color, 0.20);
                border-radius: 18px;
                padding: 14px;
            }
            #galinia-search-entry {
                min-height: 38px;
                border-radius: 11px;
                font-size: 16px;
            }
            #galinia-app-results, #galinia-app-results row {
                background: transparent;
            }
            #galinia-app-results row {
                border-radius: 8px;
            }
            #galinia-app-results row:hover, #galinia-app-results row:selected {
                background: @theme_selected_bg_color;
                color: @theme_selected_fg_color;
            }
            #galinia-search-hints {
                color: alpha(@theme_fg_color, 0.68);
                font-size: 11px;
                padding: 4px 2px 0;
                border-top: 1px solid alpha(@theme_fg_color, 0.12);
            }
        """)
        Gtk.StyleContext.add_provider_for_screen(
            self.window.get_screen(), self.css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.refresh()

    def hide_window(self, *_):
        self.window.hide()
        self.schedule_idle_exit()
        return True

    def refresh(self, *_):
        for row in self.results.get_children():
            self.results.remove(row)
        query = self.entry.get_text().strip().casefold()
        matches = []
        if not query:
            favorites = ("thunar.desktop", "firefox.desktop", "xfce4-terminal.desktop",
                         "xfce-settings-manager.desktop", "ai.storyteller.artcraft-launcher.desktop")
            for rank, name in enumerate(favorites):
                app = self.apps.get(name)
                if app is not None:
                    matches.append((rank, name, app))
        else:
            words = query.split()
            for name, terms, app in self.search_index:
                if all(word in terms for word in words):
                    rank = 0 if name.startswith(query) else 1 if query in name else 2
                    matches.append((rank, name, app))
        for _, _, app in sorted(matches, key=lambda item: item[:2])[:6]:
            row = Gtk.ListBoxRow()
            row.app = app
            content = Gtk.Box(spacing=12, border_width=6)
            icon = app.get_icon() or Gio.ThemedIcon.new("application-x-executable")
            theme = Gtk.IconTheme.get_default()
            pixbuf = None
            for candidate in (icon, Gio.ThemedIcon.new("application-x-executable")):
                info = theme.lookup_by_gicon(candidate, 22, Gtk.IconLookupFlags.FORCE_SIZE)
                if info is not None:
                    try:
                        pixbuf = info.load_icon()
                        break
                    except GLib.Error:
                        pass
            image = Gtk.Image.new_from_pixbuf(pixbuf) if pixbuf else Gtk.Image()
            image.set_pixel_size(22)
            content.pack_start(image, False, False, 0)
            label = Gtk.Label(label=app.get_display_name(), xalign=0, ellipsize=Pango.EllipsizeMode.END)
            content.pack_start(label, True, True, 0)
            row.add(content)
            self.results.add(row)
        self.results.show_all()
        first = self.results.get_row_at_index(0)
        self.results.select_row(first)
        self.message.set_text("No matching apps" if query else "Type an app name")
        self.body.set_visible_child_name("results" if first else "message")

    def key_pressed(self, _, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide_window()
            return True
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self.launch_selected()
            return True
        if event.keyval in (Gdk.KEY_Up, Gdk.KEY_Down):
            row = self.results.get_selected_row()
            if row:
                direction = -1 if event.keyval == Gdk.KEY_Up else 1
                target = self.results.get_row_at_index(row.get_index() + direction)
                if target:
                    self.results.select_row(target)
            return True
        return False

    def launch_selected(self, *_):
        row = self.results.get_selected_row()
        if row:
            self.open_row(self.results, row)

    def open_row(self, _, row):
        try:
            # Keep every descendant outside the search service's cgroup.
            # gio may exit before the application, so retain its unit until
            # all descendants exit, including Chromium's helper processes.
            command = ["systemd-run", "--user", "--collect", "--quiet",
                       "--property=ExitType=cgroup", "--service-type=exec"]
            for name in ("DISPLAY", "WAYLAND_DISPLAY", "XAUTHORITY",
                         "XDG_SESSION_TYPE", "XDG_CURRENT_DESKTOP"):
                if name in os.environ:
                    command.append(f"--setenv={name}={os.environ[name]}")
            filename = row.app.get_filename()
            if not filename:
                raise RuntimeError("Application has no desktop file")
            command.extend(["--", "/usr/bin/gio", "launch", filename])
            subprocess.run(command, check=True, capture_output=True, text=True, timeout=10)
            self.hide_window()
        except (GLib.Error, OSError, subprocess.SubprocessError, RuntimeError) as error:
            detail = getattr(error, "stderr", None) or str(error)
            self.message.set_text(f"Could not open {row.app.get_display_name()}: {detail}")
            self.body.set_visible_child_name("message")


if __name__ == "__main__":
    GLib.set_prgname("galinia-search")
    import sys
    raise SystemExit(AppSearch().run(sys.argv))
