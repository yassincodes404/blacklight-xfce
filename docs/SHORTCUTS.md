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

Galinia Task Manager puts a wide process filter above a compact table.
Its GTK layout module keeps the CPU and memory totals and hides the graphs.
Build the shared utility module with a C compiler as described in RESTORE.md.

The XFCE session startup entry primes app search. Super + Space reuses
the search window for up to one minute after it closes. After that the
process exits and the next shortcut starts it on demand. The app index
updates when installed applications change.

The compact table displays executable names. Right-click a process and
choose Copy command line to inspect the original command. Set
GALINIA_TASK_FULL_COMMANDS=1 when launching galinia-task-manager to show
the native command text in the table.
