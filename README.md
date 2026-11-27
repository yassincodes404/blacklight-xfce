<div align="center">

<img src="docs/banner.svg" alt="Galinia — XFCE desktop customization" width="100%">

**Wallpaper-adaptive XFCE customization for Ubuntu and Xubuntu.**

Galinia (gah-LEE-nyah) takes its name from the Greek phrase for “serene fire.”

[![XFCE](https://img.shields.io/badge/XFCE-4.20-9bb6c7?style=flat-square)](https://xfce.org/)
[![Session](https://img.shields.io/badge/session-X11_%7C_labwc-282b32?style=flat-square)](docs/RESTORE.md)
[![Configuration](https://img.shields.io/badge/configuration-versioned-282b32?style=flat-square)](docs/MAINTENANCE.md)
[![Status](https://img.shields.io/badge/status-control_repository-282b32?style=flat-square)](#a-foundation-for-whats-next)

[The desktop](#the-desktop) · [Reproduce it](#reproduce-it) · [Make it yours](docs/MAINTENANCE.md) · [Credits](docs/ASSETS.md)

</div>

![Galinia desktop with a full-width top bar and text-only system monitor](docs/screenshots/01-desktop.png)

## The desktop

Galinia keeps XFCE familiar and gives the whole workspace a consistent visual language. The panel spans the screen. Windows settle underneath it. Controls stay readable. The wallpaper supplies the accent, while the working surfaces remain dark and calm.

| Detail | What you get |
|---|---|
| **A single main bar** | Full width, always visible, app buttons on the left and system controls on the right |
| **Color that follows the wallpaper** | Event-driven palette updates across GTK, window frames, terminal and desktop metrics |
| **A coherent set of controls** | Proportional switches, sliders, radio buttons, menus and tabs |
| **Sharper details** | Papirus icons, JetBrains Mono and original chibi pointer artwork |
| **Metrics without the dashboard** | CPU, RAM, GPU, storage and network as click-through text over the wallpaper |
| **A stable foundation** | No continuous window polling, no application-icon rewriting, bounded service restart behavior |

## Room to work

![Galinia workspace showing consistent windows, controls and typography](docs/screenshots/02-workspace.png)

The screenshots are captured from the real XFCE desktop and show its original Blacklight branding. The workspace image uses two staged demonstration windows with sample project text, not a fabricated terminal session. The hostname was temporarily replaced by the project name for the showcase; personal windows, account data and notifications are not part of the presentation.

<details>
<summary><strong>Another mood: monochrome</strong></summary>

![Galinia with a monochrome cloud wallpaper and neutral accents](docs/screenshots/03-monochrome.png)

The layout stays the same. The palette follows the wallpaper.

</details>

Press **Super + Space** to search installed apps. See the [shared keyboard shortcuts](docs/SHORTCUTS.md).

Galinia uses gThumb for images, Celluloid for video, and Amberol for local audio. See [default media apps](docs/RESTORE.md#default-media-apps).

Flameshot is the default screenshot and annotation app. The [everyday component
guide](docs/EVERYDAY.md) covers dependencies, service checks and package-only setup.

The [memory guide](docs/MEMORY.md) provides one-shot RAM accounting and optional,
reversible Firefox memory presets. Idle-memory targets require a fresh-login benchmark.

The [image-development guide](iso/README.md) describes the Xubuntu-based live
image workflow. A rootless defaults-package builder supplies the Galinia session,
boot/login assets and fresh-account initialization. No bootable ISO is qualified yet.

## Reproduce it

**Galinia is currently a development preview, with no clean-VM-qualified installer or bootable ISO.** An experimental installer now applies this desktop profile to an existing Ubuntu/Xubuntu 26.04 amd64 installation with XFCE. It provides a read-only plan, curated baseline packages, per-file backups and configuration restore. Start with the [first-launch guide](docs/FIRST-LAUNCH.md); boot/login branding remains a separate integration step.

```sh
git clone https://github.com/yassincodes404/blacklight-xfce.git
cd blacklight-xfce
python3 tools/control.py verify
python3 tools/control.py doctor
python3 tools/install.py plan
```

Start with the [restoration guide](docs/RESTORE.md). You can render the configuration into an empty staging directory without changing your desktop:

```sh
python3 tools/control.py render \
  --output /tmp/blacklight-stage \
  --target-home "$HOME" \
  --wallpaper "$HOME/Pictures/your-wallpaper.jpg"
```

**Reference platform:** Ubuntu 26.04.1 / XFCE 4.20 / X11 / 1920×1080. The shared desktop profile also supports XFCE’s labwc Wayland session. See the [session notes](docs/RESTORE.md#x11-and-labwc). The public profile bundles the exact icons, font and original pointer artwork. Wallpapers and inherited cursor roles with unverified redistribution terms are documented separately. A private owner archive preserves the complete original customization payload. See [what is exact, portable or external](docs/ASSETS.md).

## One place to keep improving it

```text
home/          portable desktop configuration and runtime scripts
assets/        pinned icon and font payloads
optional/      Firefox styling/policies and editor integration
manifests/     versions, provenance and content checksums
tools/         verify, inspect, stage and capture configuration
docs/          reproduction notes, maintenance and real screenshots
```

Edit the source, stage a change, verify it, then commit it. To bring back changes made through XFCE settings:

```sh
python3 tools/control.py capture --output /tmp/blacklight-capture
```

Capture uses an allowlist and a separate output folder. It never copies browser databases, credentials, SSH keys or the whole home directory. Read the [maintenance workflow](docs/MAINTENANCE.md) before promoting a snapshot.

## A foundation for what’s next

- [x] Central, versioned configuration
- [x] Real desktop screenshots and asset provenance
- [x] Safe staging and allowlisted configuration capture
- [x] Offline payload verification
- [ ] Clean-VM reproduction tests
- [x] Original Galinia Dusk wallpaper with editable SVG source
- [x] Experimental profile installer with dependency checks, backups and restore
- [ ] Clean-VM qualification of install, first login and restore
- [ ] Multi-monitor and scaling profiles

The Galinia flame is available as a [standalone SVG](docs/logo.svg).

---

Built on the work of XFCE, GTK, Papirus, JetBrains Mono and the original theme authors. [Credits & licenses](docs/ASSETS.md) · [Contributing](CONTRIBUTING.md) · [Security boundaries](SECURITY.md)

## Galinia identity

The ring of fire is Galinia’s primary emblem. Galinia Dusk is supplied at 3840 × 2160 and as a scalable SVG. Use XFCE’s zoomed layout for other aspect ratios.

![Galinia Dusk](home/.local/share/backgrounds/Galinia/galinia-dusk.png)

Original artwork and code use GPL-2.0-or-later. See [NOTICE](NOTICE) for scope. Optional LightDM styling provides rounded fields, amber focus borders and a clear login button.

The profile includes a Galinia first-login welcome guide, available again from
the application menu. Matching boot and login assets can be staged without
changing the running system. See [identity and integration](docs/IDENTITY.md)
for previews, installation boundaries, rollback and required boot testing.
