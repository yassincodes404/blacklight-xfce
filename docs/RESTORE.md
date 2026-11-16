# Reproduction, with boundaries stated honestly

This repository is a versioned XFCE configuration, not a disk image or a new operating system. The reference machine runs Ubuntu 26.04.1, XFCE 4.20 and X11 at 1920×1080. Package versions are recorded in `manifests/packages.lock.tsv`; that file is an inventory, **not an instruction to install every package**.

## First, inspect

```sh
python3 tools/control.py verify
python3 tools/control.py doctor
```

Core runtime requirements: XFCE panel/desktop/window manager/settings/terminal, the notification, power, PulseAudio and tray panel plugins, Python 3 with PyGObject, GTK 3, GdkPixbuf SVG support, Xfconf introspection, libX11, libXfixes, systemd user services, and JetBrains Mono. Pillow and xcursorgen are needed only to rebuild the original pointer artwork. `nvidia-smi` is optional; the monitor handles its absence. Flameshot is an optional screenshot dependency: the reference shortcut calls `~/.local/bin/flameshot`, whose wrapper expects the official AppImage under `~/.local/opt/flameshot/Flameshot.AppImage`. Install that dependency before enabling the shortcut.

## Stage a portable home tree

```sh
python3 tools/control.py render \
  --output /tmp/blacklight-stage \
  --target-home "$HOME" \
  --monitor HDMI-0 \
  --wallpaper "$HOME/Pictures/your-wallpaper.jpg"
```

This resolves `@HOME@`, expands the pinned Papirus/font archives and adjusts the monitor property. It **does not install anything**. Use the actual output name from `xfconf-query -c xfce4-desktop -lv`. The reference wallpaper and inherited non-pointer cursor set are external assets; see [ASSETS.md](ASSETS.md).

For a manual restore, back up your configuration first. Copy the staged home tree while logged out of XFCE, using a TTY or another session. Do not overwrite running xfconfd XML: its in-memory state can overwrite the files. Preserve permissions and symlinks. Log back in, run `systemctl --user daemon-reload`, import the graphical environment with `systemctl --user import-environment DISPLAY XAUTHORITY XDG_SESSION_TYPE`, then enable/start `blacklight-wallpaper-sync.service` and `sysmon-widget.service`. Keep the theme `-Live` aliases: the sync engine alternates identical theme aliases to reload colors without flashing a different theme.

Choose a wallpaper in XFCE settings after login. The sync service generates GTK CSS, XFWM assets, terminal colors and the palette consumed by the monitor. Never edit generated colors as the long-term source; edit the generator.

The capture contains both `.config/gtk-*` settings and fontconfig preferences, including the deliberate system-wide JetBrains Mono preference. It also contains Xresources, panel plugins, shortcuts, decoration geometry, compositor settings and cursor environment settings.

## Exact owner replica

A separate **local-only** `blacklight-replica-private.tar.xz` was made alongside this repository, with an explicit allowlist recorded in `manifests/private-replica-scope.json`. It includes exact wallpapers, original inherited cursor roles, active icons/fonts/themes, hardware/display/session XML and the owner-specific integration configurations. It excludes credentials, browser databases and personal documents. The archive has `home/` and `etc/` top-level namespaces. Extract into a new staging directory first, never blindly over `/`.

This is the complete captured customization payload, not a promise of pixel-identical results on different drivers, monitors, font renderers or XFCE/GTK versions. A clean-machine end-to-end installation has **not** yet been tested. The public installer is the next milestone.

## Optional integrations

- `optional/firefox`: browser chrome CSS and privacy/storage policy snapshots. Copy styling into your chosen profile, never into somebody else's randomized profile name. Policies affect camera/microphone, local networking and app launching; review separately from appearance.
- `optional/code`: editor settings and extension identifiers. The Java path is an optional reference toolchain, not a prerequisite for the desktop.
- The Firefox Snap cursor wrapper adjusts the cursor search path after Snap's command chain. It does not disable Snap confinement. Copy the staged `.local/share/icons/Blacklight-Chibi` and `default` directories into `~/snap/firefox/common/.icons/` as well; keep the pointer alias symlinks inside the copied theme.
- Do not replicate personal Drive mounts, Tailscale identities, SSH credentials, firmware options or firewall rules from screenshots. Those are not desktop styling dependencies.

## X11 and labwc

Galinia shares the XFCE panel, GTK and terminal colors, and one wallpaper
across both sessions. Changing the wallpaper in XFCE settings updates
the shared selection and the saved monitor entries. Galinia Dusk is the
default. labwc uses a generated decoration theme with the same palette as
XFWM. The system monitor uses native Wayland layer shell under labwc and
XFixes under X11. Both use the same metrics, layout and palette.

For Wayland, install labwc and the GTK 3 layer-shell runtime library
(libgtk-layer-shell.so.0). The XFCE autostart entry refreshes the
service environment at login so the monitor can follow session changes.
The compositor reads its cursor settings when it starts.

XFWM and labwc draw their own decorations, and screenshot and global
shortcut support depend on the compositor and application.

On labwc, Print, Alt+Print and Shift+Print open a native drag selector.
Install the packages grim, slurp and wl-clipboard. Captures go to the
Screenshots folder under your configured Pictures directory and are copied
to the clipboard. Escape cancels selection. X11 still opens Flameshot.
For a persistent manual wallpaper selection, leave wallpaper cycling off
in XFCE Desktop Settings.

On physical Wayland outputs, the wallpaper service also fills in the
connector entries XFCE 4.20 uses to draw the desktop. Desktop Settings can
write a monitor model entry while xfdesktop reads a connector entry such as
HDMI-A-1. The service mirrors the selected image to both. Connector
discovery uses connected DRM outputs exposed in /sys/class/drm.

The desktop uses Noto Sans for interface text and JetBrains Mono for
monospace text. Install the Noto core fonts if they are absent. Settings
Manager launched from its desktop entry can center its search field using
a small GTK 3 module. The launcher compiles the module into the user cache
when a C compiler is available and otherwise opens stock Settings Manager.

## Default media apps

On Ubuntu or Xubuntu, install the three default Galinia media apps:

```sh
sudo apt install gthumb celluloid amberol
```

The staged `.config/mimeapps.list` maps common images to gThumb, videos to
Celluloid, and local audio to Amberol. With an existing profile, merge
those entries into the existing `[Default Applications]` section so other
file associations and URL handlers stay available.

Install `file-roller` and `thunar-archive-plugin` for ZIP and TAR archives
and Thunar’s Create Archive / Extract Here context menu. Galinia’s MIME
profile routes common archive types to File Roller. The included launcher
uses GTK’s OpenGL renderer for File Roller. Keep ~/.local/bin on the
session PATH so Thunar’s archive commands use that launcher too.

When merging an existing MIME profile, merge the archive entries under
`[Added Associations]` as well as `[Default Applications]`. Thunar
discovers archive tools through the registered associations. After copying
the launcher, refresh the local desktop cache:

```sh
update-desktop-database ~/.local/share/applications
```

Relaunch Thunar if it was running before the archive plugin was installed.
