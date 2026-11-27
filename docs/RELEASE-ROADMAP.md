# Galinia: from desktop profile to public release

Galinia aims to offer a consistent Linux desktop through an installer script,
then a live ISO. This is a release plan, not a claim that these features exist.
The current foundation is an Ubuntu/Xubuntu XFCE configuration repository.

## What a desktop distribution needs to deliver

| Area | Public-release expectation | Current repository evidence / next work |
|---|---|---|
| Supported base | Named releases, architecture, support lifetime and update source | Reference platform is recorded; choose and test an explicit support matrix rather than accepting every Ubuntu version. |
| Installation | Dependency checks, understandable progress, actionable failures | Safe rendering exists; no validated installer yet. |
| Desktop defaults | Coherent theme, fonts, icons, shortcuts, file associations | Profile and original wallpaper exist; verify them under a fresh account. |
| Everyday applications | Browser, file manager, terminal, settings, archive and media tools | Media defaults are documented; turn runtime dependencies into a curated package list. Do not install the entire owner package inventory. |
| Hardware | Network, sound, Bluetooth, brightness, graphics, suspend and removable drives | Test on real hardware; inherit base-distribution driver tools. |
| Software and updates | Working graphical app installation and clear security-update behavior | Verify inherited tools survive applying the profile; document who supplies updates. |
| First impression | Boot feedback, readable login, usable first-login guidance | Optional LightDM GTK theme exists; a real login cycle remains unverified. No validated first-run welcome flow. |
| Recovery | Backups, uninstall/restore, logs and recovery instructions | Staging exists; transactional installation and rollback remain work. |
| Accessibility | Keyboard access, readable focus, scaling and assistive technology | Preserve upstream controls; test login and desktop accessibility. |
| Release engineering | Reproducible artifacts, checksums, licenses, release notes, known issues | Payload checksums and provenance exist; no validated ISO pipeline. |

Examples of upstream practice:

- [Fedora Workstation specification](https://fedoraproject.org/wiki/Workstation/Technical_Specification): integrated desktop applications and graphical software management.
- [Linux Mint driver setup](https://linuxmint-installation-guide.readthedocs.io/en/latest/drivers.html): a visible path to hardware-driver configuration.
- [Linux Mint snapshots](https://linuxmint-installation-guide.readthedocs.io/en/latest/timeshift.html): recovery guidance as part of setup.

Galinia should reuse the base distribution's maintained system components.
Independent package repositories, a custom kernel and a new package manager
are not prerequisites for the first desktop-profile release.

## Milestone 1 — a reproducible script release

- [ ] Define the supported base release(s), architecture and primary session.
      Qualify X11 and labwc separately; shared configuration is not proof of parity.
- [ ] Create a curated dependency manifest separating required, optional and
      build-only packages. Resolve packages against the supported release.
- [ ] Implement a preflight/dry-run mode that reports packages and files to change.
- [ ] Verify source payloads before installation. Install user files as the target
      user; request elevation only for package and system-file operations.
- [ ] Back up affected files with their original permissions and symlink targets.
      Record newly created files so restore can remove them safely.
- [ ] Make repeat installation safe; preserve unrelated settings and report
      conflicts instead of overwriting user changes silently.
- [ ] Require logging out before replacing live XFCE configuration. Detect the
      active target session rather than trusting that an installer terminal is safe.
- [ ] Keep browser policies, editor integration and system greeter changes explicit
      opt-ins, separate from desktop appearance.
- [ ] Provide install logs and restore instructions; test interrupted installation,
      package failure, repeated execution and rollback in disposable VMs.
- [ ] Complete redistribution review for every default asset. Exclude the private
      owner archive and personal state from all public artifacts.

Release gate: a clean supported VM with an unrelated username can install,
reboot, use the desktop, update packages and restore its previous configuration.

## Milestone 2 — modern boot, login and first use

These are three separate surfaces with different responsibilities:

1. **Boot splash:** explore Plymouth branding after installation works. Preserve
   disk-unlock prompts, boot diagnostics and a text fallback. Any initramfs change
   needs a documented restore path and VM boot test.
2. **Login screen:** refine the existing LightDM GTK Greeter theme first. Use
   Galinia Dusk, a restrained dark card, clear typography, amber focus accents,
   readable errors and a prominent login action. Keep session selection,
   keyboard layout, power and accessibility controls discoverable. Test password
   failure, long usernames, multiple users, keyboard-only use, small screens,
   HiDPI and multiple monitors. Use system-readable assets; never depend on an
   encrypted or private home directory. Do not replace authentication machinery
   merely to change its appearance.
3. **First-login welcome:** build a small skippable application for installed
   accounts. Explain updates, drivers, software installation, desktop shortcuts,
   appearance, recovery and help. Open existing system tools rather than
   duplicating their settings. Work offline, store completion per user, and offer
   a way to reopen it. Handle live sessions separately so their state does not
   suppress onboarding for the installed user.

Release gate: test from powered-off VM through login, welcome completion,
logout and next login. Capture real screenshots; welcome should not reappear
after completion or skipping. Verify accessibility before calling it polished.

## Milestone 3 — hardware and everyday reliability

Record pass/fail results, base release, hardware, session and reproduction steps.

- [ ] Wi-Fi, Ethernet, Bluetooth pairing and reconnect after suspend.
- [ ] Speakers, microphone, headphones and audio-output switching.
- [ ] Brightness, volume keys, battery state and power actions.
- [ ] Suspend/resume, lock/unlock, logout, restart and shutdown.
- [ ] Intel/AMD graphics and an NVIDIA test when available; label untested cases.
- [ ] Single and multiple monitors, unplug/replug, 1366×768, 1080p and HiDPI.
- [ ] Keyboard layouts, non-Latin text, large text and keyboard navigation.
- [ ] Browser links, downloads, media, archives, USB drives and file associations.
- [ ] Notifications, authentication dialogs, app search and launched app lifetime.
- [ ] Fresh account and existing account; offline startup; no persistent service
      restart loop or unbounded resource growth.

## Milestone 4 — live ISO

Use the same versioned profile and dependency manifest as the script, with
separate live-session and installed-system configuration. Select a base-compatible
image builder and installer only after validating the script release.

- [ ] Build from a clean environment with pinned Galinia source and recorded
      base package versions; retain build logs and package/license inventories.
- [ ] Provide a live session with a clear install entry point and no owner data.
- [ ] Validate UEFI boot, partitioning, encrypted installation, account creation,
      timezone, keyboard layout and post-install reboot in disposable VMs.
- [ ] State Secure Boot support only after testing the complete boot chain.
- [ ] Test network-connected and offline paths; clearly state which require internet.
- [ ] Ensure the installed system updates through supported upstream repositories.
- [ ] Publish artifact checksums, verification instructions, release notes,
      requirements, support scope and known issues; plan release signing.

Release gate: someone other than the author can download, verify, boot, install
and update Galinia using only the published instructions.

## Website readiness

The website can show development progress before an ISO exists. Label the
project as in development, show real screenshots and distinguish available
features from planned work. Do not advertise an ISO download or one-command
installer until that artifact passes its release gate.

For the first public release, include the supported base and session, hardware
requirements, installation and restore guides, checksums, licenses, known issues
and an issue-reporting link. Explain Galinia's desktop changes and the upstream
distribution supplying its packages and security updates.

## Immediate order of work

1. Establish a clean-VM baseline and curated dependencies.
2. Implement and test the reversible installer.
3. Validate and refine the LightDM login; implement first-login welcome.
4. Complete the hardware/reliability matrix and publish a script preview.
5. Build the ISO from the proven profile and publish verified release material.

Visual experiments can proceed alongside installer work, but screenshots alone
do not satisfy the release gates.
