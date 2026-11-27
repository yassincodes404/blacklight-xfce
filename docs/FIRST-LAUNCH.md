# First-launch preview

This is an experimental script preview for **Ubuntu/Xubuntu 26.04 amd64 with
XFCE already installed**, using X11. It is not an installer for a blank disk.
Other releases and Wayland are not qualified by this preview. A clean-VM
installation and physical-hardware testing remain release blockers.

## What is included

- Galinia desktop styling, original wallpaper, icons, fonts, shortcuts and
  app search, using the versioned home profile.
- First-login welcome, software and driver shortcuts, personal-backup setup
  and an offline First Steps entry in app search.
- A curated baseline for files, browser, text editing, calculator, PDF viewing,
  image/video/audio, archives and screenshots.
- Upstream network/Bluetooth, audio, power, notification, software/update,
  backup and accessibility tools.
- Flameshot as the default screenshot/annotation app, with native-package-first
  launching and existing AppImage support without FUSE. Clipman preserves
  copied text and images. The experimental custom screenshot UI is retired.
- XFCE screensaver locking enabled, including on suspend. Real lock/unlock and
  suspend/resume tests are mandatory before a public release.
- Preview installation with per-file backups and conflict-aware restore.

Packages come from the user's configured APT repositories. The script does not
add a repository, run a full system upgrade, configure cloud accounts, change
firewall settings or apply optional browser policies. The software manager and
upstream updater remain responsible for package installation and updates.

Boot splash and greeter integration are **separate**, documented in
[IDENTITY.md](IDENTITY.md). The preview does not change authentication,
bootloaders, partitioning, initramfs or `/etc/os-release`.

## Inspect before installing

Run from the repository root as the normal desktop user:

```sh
python3 tools/control.py verify
python3 tools/install.py plan
# Optional full file list:
python3 tools/install.py plan --list-files
```

The plan verifies payload checksums, checks the target platform, lists missing
baseline packages, renders to a temporary directory and counts files to create
or replace. It does not change packages or desktop configuration. Rendering
expands the bundled icon archive, so allow temporary disk space and time.

The package groups are in `config/first-launch.json`; `manifests/packages.lock.tsv`
is the owner's historical inventory and is not used as an installation list.
Optional Wayland, office, printing and system-snapshot extras are not installed.

You can check or install just the baseline packages from your normal desktop
terminal, without replacing the profile or logging out:

```sh
python3 tools/install.py packages          # read-only APT simulation
python3 tools/install.py packages --apply  # sudo + APT review prompt
python3 tools/health.py                    # read-only readiness report
```

Run the apply command from a normal host terminal with administrator access.
Agent/container sessions may prohibit elevation using `no_new_privs`; the
script does not work around that restriction. Log out and in after installing
packages to load new upstream applets. See [EVERYDAY.md](EVERYDAY.md).

APT simulation, if desired, can be run manually against the listed missing
packages with `apt-get --simulate --no-remove install PACKAGE...`. Refresh stale
repository indexes through the upstream updater before installation if needed.

## Install from a text console

Back up important data first. **Log out completely** from XFCE and labwc for
this account. Switching to a text console while leaving the desktop running is
not enough: xfconfd can overwrite settings in memory. The installer checks the
account's processes and refuses installation while they remain active.

Use Ctrl+Alt+F3 to reach a text console, log in as the same normal user, enter
the repository and run:

```sh
python3 tools/install.py install --install-packages
```

The installer presents its plan and asks to apply it. Missing packages are
installed through `sudo apt-get --no-remove install`; APT keeps its own review
and authentication prompts. If packages are already installed, omit
`--install-packages`. `--yes` skips only the profile confirmation.
Do not run the entire installer through sudo.

For an older owner setup, the plan may detect desktop services enabled under
`default.target`. Run the printed `systemctl --user disable` command without
`--now` before logging out, then repeat the plan. Desktop services should start
through Galinia's session integration after the display environment is available.

The profile backs up only changed destination files. It merges MIME defaults
while preserving unrelated handlers and adds a delimited block to `.xsessionrc`
while preserving unrelated commands. Other affected profile files are replaced
with a recoverable backup. Symlinked parent directories and malformed merge
inputs are rejected rather than followed or silently overwritten.
Retired custom screenshot files are also backed up and removed on profile
upgrade, with their paths explicitly listed in `config/retired-files.json`.

Installation prints a restore ID. Journals and originals live in
`~/.local/state/galinia/installs/RESTORE_ID/`. A per-user lock prevents overlapping
install/restore operations. Repeating the same profile is a no-op where files
are unchanged; runtime-generated or subsequently edited files may produce a
new plan and backup.

Log in to the Xfce X11 session. Welcome should open once for the account and
remain available in app search. Its completion marker is per user and is not
included in the distributed profile.

## Restore or recover an interrupted installation

Log out completely and run from a text console:

```sh
python3 tools/install.py restore RESTORE_ID
```

Restore newest installations first. The installer refuses a new installation
when an earlier transaction is unfinished. Ordinary write errors trigger an
automatic restore attempt. A process kill or power loss can leave a partial
transaction; use the printed journal's restore ID to recover it.

Restore checks backup integrity and all affected destinations before changing
them. If a file has been edited after installation, restore stops with that
path. Runtime palette generation can also cause this. To preserve all later
edits alongside the backup and then restore the earlier configuration, run:

```sh
python3 tools/install.py restore RESTORE_ID --save-conflicts
```

The command prints a new `conflicts/` directory under that backup, with a
manifest and copies of changed files. Keep it if you want to recover later edits.

Restore returns original files, permissions and symlinks and removes newly
installed profile files. It retains installed packages, empty directories,
welcome completion state and generated caches/runtime assets. It is a profile
restore, not an OS snapshot or personal-data backup. Keep recovery media for
system failures. File replacement and progress journaling help recover process
interruption; power-loss recovery still needs filesystem/VM qualification.

## Release gates

- [ ] Fresh supported VM: plan, package installation, install and first login.
- [ ] Existing account: browser handlers and unrelated settings survive merges.
- [ ] App search, file/media defaults, keyboard shortcuts and welcome work.
- [ ] Lock/unlock, automatic locking and suspend/resume work on real hardware.
- [ ] Update, driver, software and backup tools open and authenticate correctly.
- [ ] Repeat install, simulated interruption and restore work end to end.
- [ ] Network, Bluetooth, audio and monitor/scaling checks pass.
- [ ] Boot/greeter branding passes its separate reboot and login checks.

Offline automated tests cover profile portability and installer failure paths;
they do not replace these release gates. Until those pass, publish this only as
an experimental preview, not a stable ISO or a validated daily-use distribution.
