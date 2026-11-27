# Galinia website

Buildless static site: serve `dist/` using any static HTTP server. It has no
JavaScript runtime dependency, analytics, external font requests or download
promise for an unqualified image. Original logo/wallpaper and site source follow
the repository's GPL-2.0-or-later license; the settings screenshot is an actual
native Galinia control-center view. Terminal colors are an illustrative preview.

```sh
python3 -m http.server 8973 --bind 127.0.0.1 --directory website/dist
```

The matching Sites project is owner-private. Its opaque project ID is preserved
in `.openai/hosting.json`; there are no source credentials in this repository.
Hosting uses a separate Site source checkout; copy changes there and use the
Sites source/package workflow for that same project, rather than replacing the
Galinia Git origin. The first published source is Sites commit
9773b8b7b1e1f359ac27bad976734d4ac8b79746.

Before a public distro launch, update the release status from actual image
qualification evidence, add the exact versioned download/checksum and supported
scope, and review the audience explicitly. No stable ISO is advertised now.
Responsive checks passed at 375, 552 and 1280 pixel viewports; image loading,
anchor navigation and FAQ disclosure were checked in the browser.
