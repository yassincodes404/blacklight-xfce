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
| Super + Left / Right | Tile to the left or right half |
| Super + Up / Down | Tile to the top or bottom half |
| Super + keypad 1 / 3 / 7 / 9 | Tile to bottom-left / bottom-right / top-left / top-right |
| Super + Shift + Up | Toggle maximize |
| Super + Shift + F | Toggle fullscreen |
| Alt + Tab | Switch windows |
| Alt + F4 | Close the focused window |
| Super + L | Lock the session |
| Print or Super + Shift + S | Select a region, save it and copy the image |
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

For screenshots, press Print or Super + Shift + S, then drag across the area.
The image is saved under Pictures/Screenshots and copied automatically. Use
Ctrl + V in an application that accepts pasted images. Escape cancels.
Ctrl + S retains its ordinary Save action; it does not copy an image.

X11 shows a full-brightness frozen desktop with an amber selection outline.
The crop comes from the snapshot taken before the selection UI appears, so
the outline is never included. A small GTK clipboard owner stays alive until
the clipboard is replaced. This works without a clipboard manager or the
optional Flameshot AppImage. Wayland uses grim, slurp and wl-clipboard.
Flameshot remains optional for annotation; its own Ctrl + C copies and Ctrl + S saves.

The XFCE session startup entry primes app search. Super + Space reuses
the search window for up to one minute after it closes. After that the
process exits and the next shortcut starts it on demand. The app index
updates when installed applications change.


XFWM stores one binding per action. Do not add keypad aliases for the half-screen actions or a second maximize binding; duplicate actions can select a different shortcut when the keymap reloads.
