# Galinia login appearance

Requires LightDM GTK Greeter. The theme uses GTK's built-in Adwaita dark base.

Install Galinia-Greeter into /usr/share/themes/, the wallpaper into
/usr/share/backgrounds/galinia-dusk.png, and docs/logo.svg into
/usr/share/pixmaps/galinia.svg. Install 90-galinia.conf into
/etc/lightdm/lightdm-gtk-greeter.conf.d/. Files must be root-owned and
world-readable. The next greeter launch loads these settings.

The root-level greeter configuration can override drop-in settings.
Back up any existing appearance settings before replacing them.
Remove the 90-galinia.conf drop-in to return to the distribution defaults.

The CSS has been parsed with GTK 3. A complete login/logout cycle still
needs visual verification on the target system.
