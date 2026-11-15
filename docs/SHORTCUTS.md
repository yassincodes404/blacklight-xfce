# Galinia keyboard shortcuts

Super is the Windows key. The reference profile provides the same bindings
on XFWM (X11) and labwc (Wayland).

| Shortcut | Action |
| --- | --- |
| Super + Space | Search installed apps |
| Super + Enter | Open the preferred terminal |
| Super + E | Open the preferred file manager |
| Super + W | Open the preferred browser |
| Super + S | Open Galinia Settings Manager |
| Super + A | Open ArtCraft Launcher, if installed |
| Super + Left / Right | Tile to the left or right half |
| Super + Up / Down | Tile to the top or bottom half |
| Super + Shift + Up | Toggle maximize |
| Super + Shift + F | Toggle fullscreen |
| Alt + Tab | Switch windows |
| Alt + F4 | Close the focused window |
| Super + L | Lock the session |
| Print | Capture a screen region |
| Ctrl + Shift + Esc | Open Task Manager |

Search uses the installed desktop application entries, including their
names and keywords. Use Up and Down to choose a match, Enter to open it,
and Escape or Super + Space again to close the window.

The bindings live in the XFCE keyboard shortcuts XML and the labwc
configuration. The ArtCraft shortcut expects the optional launcher at
~/.local/bin/artcraft-launcher.

For an unresponsive app, select its process in Task Manager and try
Terminate first. Use Kill only if Terminate fails. Install
xfce4-taskmanager to enable this shortcut. Snap confinement may prevent
an ordinary Task Manager from sending signals to a Snap app.
