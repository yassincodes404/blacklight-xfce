# Galinia settings

Super+S opens the on-demand native Galinia Control Center. It exits when closed.
The navigation is organized around daily desktop tasks:

- Overview: quick access to personalization, devices and shortcuts.
- Appearance: wallpaper-adaptive/fixed readable accents, panel size, compact or
  comfortable layouts and desktop monitor/audio card visibility, with Undo.
- Desktop: windows, workspaces, panel, keyboard, mouse, notifications,
  accessibility and login startup.
- Devices: displays, sound, network, Bluetooth, power, locking and printing.
- System: software, updates, sources/drivers, backups and all upstream XFCE settings.

Missing tools are disabled. Existing XFCE dialogs perform hardware and session
changes; the control center does not replace them with incomplete imitations.
The previous Firefox-profile and per-app CPU-priority pages have been removed.
Existing Firefox preferences are preserved. The optional command-line tools in
`docs/MEMORY.md` remain available for previous choices and recovery.

Appearance preferences live in `$XDG_CONFIG_HOME/galinia/preferences.json`.
Validation and runtime rollback protect failed changes; a previous snapshot
supports Undo. Fixed accents require readable contrast. The existing palette
service uses filesystem events; there is no new settings daemon.

System optimization belongs below the settings UI. See [the system baseline,
audit and kernel qualification work](SYSTEM-BASELINE.md).

The profile uses 40 minutes for screen blanking, monitor power-off and idle
suspend on AC and battery. Screen locking remains enabled.
