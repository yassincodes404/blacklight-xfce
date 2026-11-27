# Galinia keyboard shortcuts

Super is the Windows key. The reference profile provides the same bindings
on XFWM (X11) and labwc (Wayland).

| Shortcut | Action |
| --- | --- |
| Super + Space | Search installed apps |
| Super + / | Open the small offline keyboard-shortcut guide |
| Super + Enter | Open the preferred terminal |
| Super + E | Open the preferred file manager |
| Super + W | Open the preferred browser |
| Super + S | Open Galinia Control Center |
| Super + Left / Right | Tile to the left or right half |
| Super + Up / Down | Tile to the top or bottom half |
| Super + keypad 1 / 3 / 7 / 9 | Tile to bottom-left / bottom-right / top-left / top-right |
| Super + Shift + Up | Toggle maximize |
| Super + Shift + F | Toggle fullscreen |
| Alt + Tab | Switch windows |
| Alt + F4 | Close the focused window |
| Super + L | Lock the session |
| Print or Super + Shift + S | Open Flameshot on X11 / native capture on Wayland to select and annotate a region |
| Ctrl + Shift + Esc | Open Task Manager |

Search uses the installed desktop application entries, including their
names and keywords. Use Up and Down to choose a match, Enter to open it,
and Escape or Super + Space again to close the window.

The bindings live in the XFCE keyboard shortcuts XML and the labwc
configuration. ArtCraft is not part of the portable default profile.

For an unresponsive app, select its process in Task Manager and try
Terminate first. Use Kill only if Terminate fails. Install
xfce4-taskmanager to enable this shortcut. Snap confinement may prevent
an ordinary Task Manager from sending signals to a Snap app.

Settings and Task Manager use their standard GTK widget behavior.

For screenshots, press Print or Super + Shift + S to open Flameshot on X11 / native capture on Wayland, then
select and annotate an area. Ctrl + C copies; Ctrl + V pastes in an application
that accepts images. Ctrl + S saves a file. Escape cancels. The launcher requests
clipboard output; saving does not replace the explicit Copy action when needed.

Flameshot on X11 / native capture on Wayland is the default and starts once with XFCE so image clipboard requests
remain available. The launcher prefers the distribution package, supports an
existing extracted AppImage and avoids FUSE when using the AppImage fallback.
The custom Galinia capture UI and clipboard helper have been retired. Wayland
support depends on Flameshot on X11 / native capture on Wayland and a working screenshot portal; qualify it
separately from the supported preview's X11 path.

The XFCE session startup entry primes app search. Super + Space reuses
the search window for up to one minute after it closes. After that the
process exits and the next shortcut starts it on demand. The app index
updates when installed applications change.


XFWM stores one binding per action. Do not add keypad aliases for the half-screen actions or a second maximize binding; duplicate actions can select a different shortcut when the keymap reloads.
