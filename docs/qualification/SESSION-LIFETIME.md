# Graphical session ownership and native Wayland locking

Galinia's XFCE autostart now runs a small session owner. It identifies the XFCE
session-manager process through D-Bus, opens a pidfd, and waits for process exit
without polling. It stops galinia-session.target on exit; Galinia widgets,
search and portal services are attached to that target. A per-user runtime lock
prevents two owners from changing the shared user-service environment.

At login the owner imports display variables into both systemd and D-Bus,
clears stale values, replaces portals from the old display, and starts the
wlroots backend before the portal broker on Wayland. Failure of an optional
service is reported while startup of other services continues. Disabled widgets
remain disabled. --adopt attaches to an existing login without restarting
healthy services; --once --adopt refreshes configuration without creating an
additional lifetime owner.

The running reference session was adopted without restarting its audio widget.
After a subsequent reboot, the normal XFCE autostart owner was running, watching
the actual new session-manager PID, with galinia-session.target and the wlroots
portal active. The broker advertised a monitor capture source. Browser capture
and interactive permission behavior remain to be tested.

## Finish locking on the reference machine

The source profile adds swaylock, swayidle, wlopm and xdg-desktop-portal-wlr to
the optional Wayland package set. System package installation requires a normal
administrator terminal; the automation process has NoNewPrivs set and cannot
perform that installation. APT simulation selected three new packages and no
removals for the reference machine:

```
sudo apt install --no-remove swaylock swayidle wlopm
~/.local/bin/galinia-session --once --adopt
```

The second command checks providers and the packaged PAM configuration before
setting XFCE's LockCommand and starting the native idle handler. An existing
custom LockCommand is retained with a warning. The helper uses Swaylock on
Wayland and xfce4-screensaver-command on X11; it never calls xflock4 recursively.
The labwc Super+L binding uses that helper too.

The idle handler uses a 2400-second timeout, locks before turning monitors off,
restores monitor power on activity, and requests a lock before sleep and on
logind lock signals. Swaylock daemonizes only after lock acknowledgement, and
swayidle waits for that command. This follows the upstream Swaylock/Swayidle
integration. Logind's maximum delay still bounds pre-sleep execution; this is
not a promise that every hardware suspend path has been qualified.

The idle service deliberately does not enable NoNewPrivileges: PAM's password
helper may need its packaged privilege transition. No custom authentication
code or copied PAM files are shipped.

After installation, test Super+L with the user present: verify all displays are
covered, an incorrect password does not unlock, and the correct password does.
Then test suspend/resume and the 40-minute idle path. Do not mark locking passed
before those tests. The health tool now reports missing native providers and
zero portal capture sources instead of treating an active broker as sufficient.

## Panel appearance

The wallpaper theme generator now keeps the main panel background and plugin
containers fully transparent, without a bottom border or shadow. Foreground
icons remain opaque. This uses normal compositor blending and adds no blur
process. The live panel was visually checked after regeneration. The change is
in the generator, so wallpaper changes do not restore the old opaque bar.

## Verification and remaining work

78 repository tests passed, including real child-process exit observation,
startup failure recovery, environment clearing, session routing and adoption.
Configuration and systemd syntax checks passed. A fresh defaults .deb was built.
The current user's modified files were backed up under
~/.local/state/galinia/session-repairs and panel-repairs before deployment.

Interactive locking, browser screen sharing, keep-awake integration, compositor
and GPU crash reproduction, and ISO desktop/install qualification remain open.
The GTK portal's limited power-inhibition support is not fixed by starting the
capture backend. Existing crash records were preserved; no driver or kernel
changes were applied without a reproduction.

Primary integration references:
- https://labwc.github.io/integration.html
- https://github.com/swaywm/swayidle/blob/master/swayidle.1.scd
- https://github.com/swaywm/swaylock/blob/master/swaylock.1.scd
