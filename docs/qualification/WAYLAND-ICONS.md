# Wayland application icons

The reference XFCE Wayland session exposes XWayland instance names through
libxfce4windowing. Version 4.20.5 looks for a matching desktop filename and then
uses GIO's name/keyword search. It does not match StartupWMClass metadata.
Consequently valid installed icons can become generic executable icons: the
application identity fails before the icon theme is consulted. A second defect
uses gtk_icon_theme_has_icon(), which excludes unthemed standard pixmaps even
when GTK lookup can load them. The patch uses the actual GTK lookup path.

Galinia's candidate fix is in `packaging/windowing/resolve-app.c`. It retains
exact and lowercase desktop-file matching, then checks for a unique exact
StartupWMClass match. It also recognizes an absolute profile-directory suffix
on an instance name, accepting its prefix only if an installed desktop entry
exists. Ambiguous window-class matches are rejected. The original search
fallback remains. There is no app-specific icon table or background process.

AudioRelay's reference launcher also omitted the `desktop` component of its
actual Java window class. Correcting that launcher metadata is necessary;
changing icon themes cannot repair an incorrect application identity.

## Build and qualification

`tools/build_windowing.py --output dist` builds on Ubuntu 26.04 amd64 with the
headers installed by `.github/workflows/windowing-fix.yml`. The source URL and
SHA256 are locked in `packaging/windowing/source.json`. The builder runs six
native C resolver regression tests plus an Xvfb GTK test that creates and loads
an unthemed pixmaps fixture and repackages the original distribution
package with the rebuilt library. It retains both X11 and Wayland backends,
original package dependencies and SONAME. Version 4.20.5-1galinia1 permits later
distribution versions to supersede it; no APT pin is installed.

Before installation, extract the package and run a disposable native window
probe with LD_LIBRARY_PATH pointing to its library directory. Compare its
exported symbols and runtime dependencies with the installed distribution
library. Test against running affected windows using their original icon files
and without per-application icon aliases or a profile-specific ChatGPT launcher.
A resolver test passing alone does not establish panel integration.

Installing the qualification package requires administrator access. Reload
xfce4-panel after installation because existing application objects cache their
icons. Do not restart user applications or the compositor. The patch remains a
qualification candidate until installation and panel behavior are confirmed;
it is not yet automatically injected into release ISOs.

Upstream source:
https://github.com/xfce-mirror/libxfce4windowing/blob/main/libxfce4windowing/libxfce4windowing-private.c
