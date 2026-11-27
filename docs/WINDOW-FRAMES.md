# Window frames

Galinia's default XFWM frame hides active and inactive window-title text while
retaining window metadata for app switching, search and accessibility. The frame
and Kitty canvas are pure black; minimize/maximize/close and resizing remain.
The theme clips title painting outside the title strip and disables its shadow.
GTK title/subtitle labels in standard header bars are hidden separately; ordinary
application labels, navigation controls and document contents are not hidden.

XFWM has a shared frame theme, not arbitrary per-window background matching.
Black matches Kitty exactly. Standard GTK surfaces follow Galinia's palette;
apps with their own colored content or custom Chrome/Electron/Qt headers may
need application-specific styling. Do not rewrite window names or run a polling
script to erase metadata as a cosmetic workaround.

The palette generator maintains these choices when wallpapers change. The
reference change has a backup in the local workspace; the public installer also
keeps its usual per-file rollback journal. Selecting a different upstream window
theme can restore its normal titles; the Galinia generator reapplies its own
frame at the next palette refresh.
