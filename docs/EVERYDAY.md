# Everyday components

Galinia uses maintained upstream applications and services. The public preview
targets Ubuntu/Xubuntu 26.04 amd64, XFCE and X11. A package being installed or a
service being active does not qualify hardware behavior; test the release gates
in [FIRST-LAUNCH.md](FIRST-LAUNCH.md).

| Need | Default components |
|---|---|
| Browser, files, text, calculator, PDFs | Firefox, Thunar, Mousepad, MATE Calculator, Evince |
| Images, video, audio and archives | gThumb, Celluloid, Amberol, File Roller, Thunar archive plugin |
| Screenshots and annotation | Flameshot; Print or Super+Shift+S opens capture |
| Clipboard continuity | Flameshot resident instance and XFCE Clipman |
| Audio and Bluetooth audio | PipeWire, PipeWire Pulse compatibility, WirePlumber, SPA Bluetooth support, pavucontrol |
| Networking and Bluetooth devices | NetworkManager and its applet; BlueZ and Blueman |
| Removable drives, phones, network locations | UDisks2, Thunar Volman, GVfs backends and FUSE support |
| File pickers and sandboxed app integration | XDG Desktop Portal and the GTK backend |
| Power and locking | UPower, XFCE Power Manager, XFCE Screensaver |
| Administrator prompts | MATE Polkit authentication agent |
| Software, updates and drivers | GNOME Software, Software Updater, Software & Updates |
| Personal backups and accessibility | Déjà Dup, Orca, Noto text and emoji fonts |

Office apps, printing and system snapshots remain optional package groups.
Do not start a print service on machines without that requirement. Do not add
second network managers, audio servers, lockers or authentication agents just
to achieve a particular visual style.

## Install and assess

```sh
python3 tools/install.py packages
python3 tools/install.py packages --apply
python3 tools/health.py
python3 tools/health.py --json
```

The package-only command simulates APT's resolution before offering to install
missing packages with sudo. APT removals are prohibited. It does not replace
desktop settings, add repositories, change services or install optional groups.
Refresh stale package indexes using the upstream updater if resolution fails.
Elevation must be available in the terminal where you run it.

The health report checks the package baseline, service state, portal support,
critical applets and duplicate authentication/locking processes. It makes no
network requests, changes no service state and reports missing hardware such
as a Bluetooth adapter separately. A readiness warning produces exit status 1.
Review the report instead of treating it as an automatic repair tool.

## Flameshot

Use Ctrl+C to copy a capture, Ctrl+V to paste into an image-capable application,
and Ctrl+S to save. The shortcut requests clipboard output and keeps Flameshot's
standard selection and annotation UI. Its resident instance starts once per
XFCE login; Clipman's upstream autostart provides general clipboard continuity.

The launcher tries `/usr/bin/flameshot`, then an existing
`~/.local/opt/flameshot/extracted/AppRun`, then an existing
`~/.local/opt/flameshot/Flameshot.AppImage` with `APPIMAGE_EXTRACT_AND_RUN=1`.
The last option avoids FUSE but extracts at launch; prefer the distro package
or a previously extracted copy for repeated use. Galinia does not download or
redistribute an AppImage. The packaged app receives updates from the configured
distribution repository; a manually supplied AppImage needs separate upkeep.

The custom Galinia selector, GTK clipboard helper and screenshot menu entry are
retired. Profile upgrade backs them up before removal; the compatibility
`galinia-screenshot` command now only launches Flameshot. Wayland capture needs
working portal/compositor support and remains separately unqualified.

## Background efficiency

Galinia's own services have bounded restarts, low CPU scheduling weight and
graphical-session lifetimes. The monitor updates every two seconds and the
palette service follows wallpaper events. The profile does not create daemons
for its welcome guide, offline documentation or backup setup shortcuts.

Keep core system services under the base distribution's service management.
Portals, GVfs and hardware helpers can start on demand. Do not disable an idle
service just to reduce a process count. Do not enable two providers of the same
desktop role or change working personal mounts/VPNs as part of profile setup.

## Required functional checks

Test browser downloads and file pickers; screenshot copy/paste; images, video,
audio output and microphone switching; Wi-Fi reconnect; available Bluetooth
hardware; USB hotplug; lock/unlock and suspend/resume; and backup/restore of a
sample personal file. Check CPU usage while idle and after repeated logins.
These checks and clean-VM qualification remain prerequisites for claiming a
reliable public release.

For memory accounting and opt-in Firefox tuning, see [MEMORY.md](MEMORY.md).
Keep idle-desktop measurements separate from the cost of open applications.

The profile suppresses GNOME Software's login autostart to keep the storefront
on demand. It remains available from the menu and welcome guide. The upstream
updater and distribution update timers are separate and are not disabled.
