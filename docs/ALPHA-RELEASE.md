# Galinia 0.1 alpha work

The first alpha targets Xubuntu 26.04.1 minimal amd64 and XFCE/X11. Debian is a
separate future image target; this work does not convert the owner's machine.
Kernel tuning remains a separate qualification experiment and is not enabled
in the ISO. The current desktop is never used as the root filesystem source.

## Automated image path

`.github/workflows/iso-alpha.yml` runs on the pull request carrying the
`build-iso` label, and supports manual dispatch once on the default branch.
It runs on an isolated root-capable runner, not the user's installed system.
Remove the label to stop subsequent automatic builds.

1. Authenticate the official SHA256SUMS signature with Ubuntu's archive keyring.
2. Check the explicitly pinned ISO hash in `iso/source.lock.json`.
3. Inspect boot and layer metadata; build the Galinia defaults package.
4. Customize installed and live roots separately. The read-only source media is
   mounted inside each chroot for its existing file:/cdrom APT source; network
   repositories still use their normal signature checks. Services are prevented
   from starting during image customization.
5. Reconstruct the live delta, including file deletions, and update package
   manifests, sizes, image identity and integrity metadata.
6. Replay the source ISO's BIOS/EFI boot layout using xorriso, retaining its signed
   kernel and matching the rebuilt initramfs to that kernel.
7. Observe BIOS and UEFI boots in disposable QEMU sessions; collect screenshots
   and logs without marking desktop or installation tests passed automatically.
8. Upload the development ISO, checksum, build metadata and evidence as a short-
   lived CI artifact. This does not publish a stable GitHub Release.

Allow at least 40 GiB free working space. The runner removes only unused,
preinstalled developer SDKs on its own disposable filesystem. Mounts are scoped
to image work paths and unmounted after each operation. The owner filesystem,
bootloader, kernel and installed packages are not changed.

APT repositories change over time. This is a repeatable recipe with recorded
package versions, not yet a bit-for-bit reproducible build. Archive snapshots,
source-package retention and verified redistribution metadata remain release
work. CI artifacts are not a substitute for a supported update repository.

## Evidence gates

`iso/release/alpha.json` enumerates required checks. No check is marked passed
by default. Running `python3 tools/release_gate.py` reports the current missing
evidence and exits nonzero. Supply `--report /path/report.json --iso /path/image.iso`
to validate a report bound to that exact ISO hash. Each required check needs
`status: pass` and at least one evidence file with its SHA256. Paths must remain
inside the report directory. Keep source_commit and the matching release version.

The gate checks completeness/hashes; reviewers must inspect the evidence and
confirm that claims are truthful. UEFI observations do not establish Secure Boot
support. QEMU running does not establish a usable desktop or a successful install.
No hardware result is inferred from a VM.

## Before inviting testers

Record BIOS/UEFI desktop arrival, first-login identity, offline browser behavior,
screenshot paste, installation to a disposable VM disk, installed reboot,
second account, updates, profile recovery and lock/unlock. Test a designated
reference machine for networking, playback/microphone, removable storage and
suspend/resume. Record unknown hardware and known issues explicitly.

The minimal source may require additional browser provisioning. A transitional
Firefox .deb alone does not satisfy the offline-browser gate. Do not bypass the
gate just to publish an image. Galinia defaults-package upgrades also need a
qualified user-profile migration policy that preserves local edits before we
promise ongoing installed-system support.

Publish source and license notices, supported scope, installation/recovery
instructions, checksums and known issues with the qualified alpha. A website
should link to that exact release. GitHub issue forms capture build identifiers,
reproduction steps and hardware details without asking for credentials.

GitHub Releases limits each asset to under 2 GiB. If the qualified ISO exceeds
that limit, use a suitable direct-download mirror or verified split assets with
clear reconstruction instructions; do not promise a single oversized release
asset. CI stores the development ISO separately from small qualification evidence.
Reference: https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases
