# Asset provenance and exactness

| Component | Public repository | Reference-machine replica |
|---|---|---|
| Adaptive GTK/XFWM generation, widget and controls | Source + generated snapshot | Exact live source |
| Papirus / Papirus-Dark | Exact compressed icon trees; GPL-3.0 | Same bytes |
| JetBrains Mono | Exact font tree with upstream notices; OFL-1.1 | Same bytes |
| Original chibi pointer and link artwork | Binary cursors + rendering source | Same pointers |
| Inherited Blacklight cursor roles | Adwaita fallback in public profile | Exact original role files |
| Wallpaper collection | Filename/hash manifest and provenance | Exact original files |
| Personal monitor/session settings | Portable reference layout | Exact captured XML |

The public payload intentionally does not claim to relicense the wallpaper collection or inherited cursor assets. The upstream wallpaper collection states that images belong to their respective artists. Screenshots showcase the configured desktop; they do not grant a license to extract or redistribute the underlying artwork. For exact owner reproduction, use the separate private archive. For a public installer, obtain licensed assets or supply your own wallpaper.

The artwork shown is sourced from the [dharmx/walls collection](https://github.com/dharmx/walls), including the minimal island/bridge scene and monochrome clouds. Exact original filenames and SHA-256 hashes are in `manifests/external-assets.json`. Its [upstream source notice](https://github.com/dharmx/walls/blob/main/.github/README.md) attributes the images to their respective artists.

Other credits:

- [XFCE](https://xfce.org/) — the desktop and panel infrastructure.
- [GTK / Adwaita](https://gitlab.gnome.org/GNOME/gtk) — base control rendering; imported from the installed GTK runtime, not copied as a separate distribution.
- [Papirus](https://github.com/PapirusDevelopmentTeam/papirus-icon-theme) — application and system icons. Exact dependency payload is pinned by SHA-256 in the content manifest.
- [JetBrains Mono](https://github.com/JetBrains/JetBrainsMono) — interface and terminal typography.
- Blacklight-Ultra / Materia — historical theme base. The theme's included GPL license and original notices remain with the payload. This project is an independent configuration, not an official upstream edition.
- [Kenkyoo/MyDotfiles](https://github.com/Kenkyoo/MyDotfiles) — the starting inspiration for the original environment; upstream reference commit `738398acea6ad934c2f784768255c7beb20e0ca5`. No blanket license is asserted over that repository.
- [Flameshot](https://flameshot.org/) — region screenshots and annotation; optional separately installed application.

Original project scripts, pointer artwork and documentation are offered under GPL-2.0-or-later (see LICENSE), except where a file carries a different upstream notice. Third-party artifacts retain their own licenses; screenshots and external artwork are excluded from that grant.

The bundled legacy Metacity XML escapes a raw `<` in version attributes so it parses correctly. XFCE uses the unchanged XFWM theme.
