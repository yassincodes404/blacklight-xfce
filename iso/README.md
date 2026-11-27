# Galinia image development

First image target: **Xubuntu 26.04 amd64 / XFCE / X11**. Reuse its installer,
kernel, signed boot components, firmware and update repositories. This folder
contains the customization recipe; no bootable Galinia ISO has been built or
qualified yet. Do not rename a defaults package or source archive as an ISO.

The [automated alpha pipeline](../docs/ALPHA-RELEASE.md) now verifies a pinned
source image and builds/observes it on an isolated CI runner. Build success
alone does not satisfy the qualification checklist below.

## Build the defaults package without root

On Ubuntu/Xubuntu with python3-gi, gir1.2-gdkpixbuf-2.0, librsvg2-common and
dpkg-deb available, from the repository root:

```sh
/usr/bin/python3 tools/build_defaults.py --output /absolute/path/to/output --version 0.1.0~dev
```

The package contains:

- Dependencies on the distribution's Papirus and JetBrains Mono packages,
  shared system-wide without conflicting with their file ownership.
- Portable per-user Galinia themes and runtime files, seeded before XFCE starts.
- A skeleton marker for fresh accounts; existing accounts are not automatically restyled.
- A Galinia OS session, LightDM GTK styling, Plymouth artwork and installed-system
  GRUB distributor/menu defaults. Ubuntu's `/etc/os-release` remains intact;
  Galinia's identity is recorded separately in `/etc/galinia-release`.
- A before-session initializer with backups and an error log. The welcome app
  runs after authentication. Inherited cursor fallbacks remain distribution-owned.

This is an experimental package, not a validated native installer. Its boot
assets are activated by the image recipe below. Test only in a disposable image
or VM until the release gates pass.
The script renderer retains its pinned icon/font archives; image packages use
the distribution versions and record their resolved versions in the ISO manifest.

## Customize an official live image with Cubic

1. Download Xubuntu 26.04 amd64 from its official download site. Verify the
   Ubuntu-provided SHA256SUMS signature and the ISO checksum before opening it
   in Cubic. Record the source ISO filename, checksum, download location and
   source repository commit in the build log. Do not use the owner's installed
   filesystem, private replica archive, browser profile or machine identities.
2. Use a separate Cubic project and a host that permits its root/mount operations.
   Copy the built `.deb` and `customize.sh` into Cubic's virtual environment.
   Run **inside that environment**, with the actual absolute package path:

   ```sh
   GALINIA_IMAGE_BUILD=1 sh /absolute/path/customize.sh /absolute/path/galinia-defaults_0.1.0~dev_all.deb
   ```

3. Preserve the upstream live installer, Casper configuration, Firefox Snap seed
   (when the base uses Snap), and installer removal manifests. Confirm Firefox
   is usable offline in the live session; a transitional APT package alone is
   not evidence that a browser is installed in an image.
4. In Cubic's boot configuration, change the visible labels to **Try or install
   Galinia OS** and **Galinia OS (safe graphics)**. Preserve the original kernel,
   initrd paths, Casper parameters, safe-graphics flags and boot entries. Do not
   rewrite EFI/shim binaries or claim Secure Boot qualification without testing.
5. Have Cubic regenerate the image and its boot files. Keep its build logs and
   package manifest. Use its supported SquashFS compression options; an ISO
   itself should remain a directly writable `.iso`, not be mislabeled `.xz` data.
6. Generate SHA256SUMS for the result, then test below. Do not install to a real
   disk until install/restore behavior has been tested in disposable VMs.

The repo's `customize.sh` requires an explicit image-build flag and root; it
must never be used to style the author's running host. It does not run
`update-grub` against the host disk. The installed system reads Galinia's GRUB
drop-in on its normal bootloader generation path; verify the result after
installing to a VM disk. Verify boot splash activation and disk-unlock prompts.

## Required image qualification

- [ ] UEFI and BIOS live boot reach Galinia's session.
- [ ] Live boot menu, splash, login and desktop show the intended identity.
- [ ] Fresh account initializes before xfconfd; a second account also works.
- [ ] Existing unmarked account is not automatically overwritten by package install.
- [ ] Welcome behavior is appropriate for live and installed users; shortcuts work.
- [ ] Firefox, Flameshot capture/paste, file pickers, media and archive handling work.
- [ ] Network/audio/USB and available Bluetooth hardware pass functional checks.
- [ ] Installation, encrypted-disk unlock, reboot, lock and suspend/resume pass.
- [ ] Idle RAM is measured at a fixed interval after login, without foreground apps.
- [ ] Source/licenses, package manifest and private-data checks are reviewed.
- [ ] ISO checksums and source commit match the published release notes.

## Publish through this repository's releases

Commit build recipes, package sources, release notes and verification metadata
to Git. Attach the tested ISO and SHA256SUMS to a **GitHub Release** in the same
repository. Do not put multi-gigabyte ISO history in regular Git. A future
website should link to that exact versioned release and its known issues.
Until the above checks pass, label artifacts as development previews and show
progress rather than a stable download promise.

References: [Cubic upstream](https://github.com/PJ-Singh-001/Cubic),
[Ubuntu live customization](https://help.ubuntu.com/community/LiveCDCustomization),
[GitHub large binary guidance](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).
