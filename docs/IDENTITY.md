# Galinia identity

Galinia's visible identity uses its ring-of-fire logo, Galinia Dusk wallpaper,
dark blue-gray surfaces, warm amber accents and Noto Sans interface text.
Ubuntu/Xubuntu remains the package and security-update provider. Do not rewrite
`/etc/os-release` to suggest an independently maintained distribution.
Internal Blacklight paths remain compatible with existing installations;
renaming service/configuration identifiers needs a migration, not a text replace.

## Included surfaces

| Surface | Source | Validation status |
|---|---|---|
| Desktop and wallpaper | `home/` | Existing profile; clean-machine qualification still needed |
| Welcome application and menu entry | `home/.local/share/galinia/welcome.py` | GTK 3; no elevated privileges |
| First-login launch | `home/.config/autostart/galinia-welcome.desktop` | XFCE; skips completed accounts and detected Casper live sessions |
| Login screen | `optional/lightdm/` | Requires LightDM GTK Greeter; actual login testing still required |
| Boot splash | `optional/plymouth/galinia/` | Requires Plymouth script plugin; actual boot and encrypted-disk testing still required |

The welcome guide runs on first graphical login, not before authentication.
Skip or finish saves `$XDG_STATE_HOME/galinia/welcome-v1-complete` (default:
`~/.local/state/galinia/welcome-v1-complete`). Closing the window leaves it pending.
The application menu always allows reopening it. It works without network access;
updates and driver actions launch the installed upstream tools and report missing
tools instead of installing anything. It never changes system settings itself.
Image builders must exclude the completion marker from installed user templates.

## Stage and preview

Run from the repository root on Ubuntu/Xubuntu with Python 3 PyGObject,
GTK 3, GdkPixbuf and its SVG loader installed:

```sh
/usr/bin/python3 home/.local/share/galinia/welcome.py
/usr/bin/python3 tools/stage-identity.py --output /tmp/galinia-identity
```

The stage includes the root-relative `etc/` and `usr/` trees for greeter and boot
assets. It changes neither the running login screen nor the boot configuration.
The home renderer separately stages welcome and desktop files, resolving home
paths. Use the normal profile staging workflow in [RESTORE.md](RESTORE.md).

## System integration in a disposable VM first

1. Back up existing destination files, the current LightDM appearance
   configuration and the current `default.plymouth` alternative target.
2. Install staged system files root-owned with readable permissions; directories
   should be searchable by the greeter. Use the intended LightDM GTK Greeter;
   this theme does not configure another greeter or switch display managers.
3. Register `/usr/share/plymouth/themes/galinia/galinia.plymouth` with Ubuntu's
   `default.plymouth` update-alternatives group and select it. Rebuild the relevant
   initramfs with `update-initramfs` on the target system. Verify the script plugin
   is present and the boot configuration enables Plymouth. These are privileged
   installation steps, not part of the staging tool.
4. Boot from power-off, including an encrypted-disk unlock test. Check status
   messages, text-console fallback, login errors, session selection, accessibility,
   small displays, HiDPI and multiple monitors. Do not mark boot support validated
   from a static screenshot or source inspection.
5. Verify welcome shows for a fresh account, stays dismissed after skip/finish,
   and remains available from the menu. Test missing update/driver utilities.

Rollback: select the saved Plymouth alternative and rebuild the initramfs,
restore previous greeter files (or remove the Galinia drop-in if none existed),
and remove only the new Galinia system assets. Restore backed-up user files or
remove the newly installed welcome autostart/menu/runtime files. A production
installer must record file ownership, previous contents and conflicts first.

Plymouth API reference: [upstream script documentation](https://www.freedesktop.org/wiki/Software/Plymouth/Scripts/).
