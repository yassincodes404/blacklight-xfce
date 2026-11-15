# One control repository

## Source of truth

| Change | Edit |
|---|---|
| Palette extraction, controls, menus, panel CSS, XFWM frame generation | `home/.local/bin/blacklight-wallpaper-sync.py` |
| Text-only monitor layout and collection | `home/.local/bin/sysmon-widget.py` |
| Panel composition, shortcuts, window behavior | `home/.config/xfce4/xfconf/xfce-perchannel-xml/` |
| Fonts and cursor selection | `home/.config/fontconfig/`, `home/.config/environment.d/`, GTK settings |
| Background task priorities and privilege restrictions | `home/.config/systemd/user/` |
| Firefox and editor integration | `optional/` |
| Original chibi artwork | `tools/draw-chibi.py` |

Generated CSS and theme assets are included as a reference snapshot. The generator wins whenever wallpaper colors change. Keep both aligned when making a release.

## Save changes made on the desktop

```sh
python3 tools/control.py capture --output /tmp/blacklight-capture
# Review against home/; never commit a complete ~/.config or browser profile.
git diff
```

Capture is deliberately allowlisted and writes to a separate new folder. It sanitizes the home path and removes remembered plugin/player items. It captures text settings only; update dependency archives and their checksums deliberately when assets change. Monitor identifiers must be reviewed for portability.

After editing, regenerate `manifests/content.sha256.json` with `python3 tools/update-manifest.py`, run `python3 tools/control.py verify`, render to an empty staging directory and inspect the diff. Commit only the intended changes. The CI check is offline and validates the committed snapshot; it does not touch a desktop.

## Before an installer release

1. Test in a fresh Ubuntu/Xubuntu VM with a second user and a different monitor name.
2. Implement dependency detection, explicit opt-ins, backup/rollback and idempotence.
3. Resolve redistribution for external artwork or commission an original default.
4. Add screenshot, accessibility, multi-monitor and fractional-scaling checks.
5. Keep security policies, cloud accounts and firmware outside default appearance installation.

There is intentionally no `curl | sh` installer in this first control-repository release.
