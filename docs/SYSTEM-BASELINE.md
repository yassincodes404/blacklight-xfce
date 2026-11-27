# Galinia system baseline and qualification

## Reference-machine audit, 2026-11-27

The reference machine is Ubuntu 26.04.1 with kernel 7.0.0-44-generic. Its active
X11 session reports XFCE / xfce. xfce4-session, xfwm4 and xfce4-panel run;
no GNOME Shell, Plasma shell or KWin process was found. The installed upstream
`xfce.desktop` entry executes startxfce4; the Galinia session also executes it.
Galinia adds the user's settings, palette, launcher and monitor to that XFCE
core. This confirms an XFCE desktop, **not** a measured pristine-XFCE baseline:
the same account's Xsession/autostart configuration is shared between sessions.
An untouched baseline needs a fresh test account or a matching VM.

Installed linux-generic 7.0.0-44.44, linux-firmware
20260319.git217ca6e4.1ubuntu and Mesa Vulkan 26.0.8-1ubuntu0.3 matched the
configured APT candidates at audit time. APT lists can be stale; update them
before release qualification. Track supported kernel/firmware/graphics packages
and retain a known-good kernel. Do not replace the working kernel with an
unsigned mainline build or mix Debian and Ubuntu repositories in place.

Observed kernel configuration:

- Multi-generation LRU: 0x0007 (all supported components enabled).
- Scheduler autogroup: enabled; CONFIG_PREEMPT_DYNAMIC=y,
  CONFIG_PREEMPT_LAZY=y and CONFIG_HZ_1000=y. Build configuration does not prove
  the selected runtime preemption mode; debugfs was inaccessible to this agent.
- schedutil governor; transparent huge pages madvise; swappiness 30.
- 4 GiB disk swap, unused in the sampled snapshot; zswap disabled.

The stock kernel already provides modern scheduling and memory reclaim. Keep
its scheduler and power policy while comparing actual interactive workloads.
Do not add early-OOM-kill policies, cache-flushing timers, blanket memory caps,
forced performance governors or scheduler debugfs values to the release.

## Reversible kernel memory trial

`tools/kernel_trial.py` is a runtime qualification tool, **not an applied or
packaged release default**. It retains disk swap and swappiness, enables MGLRU
and scheduler autogroup only if needed, and tries zswap with a 20% pool ceiling.
The pool grows on demand; 20% is not reserved at startup. It retains the kernel's
compressor rather than changing it while applications are running. On this
reference machine only the zswap enable switch would change.

```sh
python3 tools/kernel_trial.py                  # read-only status
sudo python3 tools/kernel_trial.py --apply    # normal administrator terminal
sudo python3 tools/kernel_trial.py --restore  # restore this boot's previous values
```

The Codex process has NoNewPrivs and cannot apply root changes. No kernel
settings were changed by the agent. The trial checks active swap, rejects zram
stacking and an existing zswap policy, and journals original values before
writes. Failed application attempts roll back. Restore preserves later admin
edits. Trials expire on reboot; a stale journal is not restored onto another
boot. Inspect `/var/lib/galinia/kernel-trial.json` before removing a stale file.
Disable does not immediately evacuate already compressed pages; no swapoff is
performed. No initramfs, bootloader, sysctl file or service is installed.

Zswap trades compression CPU work for potentially less disk swap I/O. Test
before and after with the same browser workload, build/download activity and
memory pressure. Record app/window response times, PSI, swap I/O, PSS, power
and repeated-run variance. Use a VM for deliberate memory-pressure/OOM tests.
A lower displayed Used number alone does not establish a faster desktop.
`tools/memory_report.py`, `home/.local/share/galinia/performance.py` and the
bounded `tools/latency_probe.py` provide snapshots and wake-delay observations;
these do not constitute an application benchmark. Persist only a profile that
passes memory pressure, suspend/resume, audio, battery and regression tests.
The earlier zram recipe stays an alternative experiment; never combine both
compression policies by default.

## Ubuntu component review

An APT purge simulation of apport, its handlers, Ubuntu Pro and its desktop
integration also selected software-properties-gtk, update-manager-core,
xubuntu-desktop-minimal, ubuntu-minimal, xorg and xserver-xorg for removal.
A narrower attempt to remove ubuntu-advantage-desktop-daemon and apport-symptoms
still selected software-properties-gtk. **Neither plan was applied.** No
`autoremove` or force-dependency operation is part of this work.

Apport is configured enabled, but an active oneshot unit is not evidence of a
resident daemon consuming significant RAM. The Pro desktop daemon was inactive.
Removing those packages cannot be advertised as an idle-RAM saving from this
snapshot. Review optional crash reporting and subscription integration at image
construction, where dependencies and replacements can be qualified together.

Retain networking/DNS, authentication/keyring, accessibility, audio, GVfs and
portals, screen lock, updater, firmware/driver tools and removable-disk support.
Printing, Bluetooth, mobile broadband and mDNS are normal hardware features;
shipping them should depend on supported hardware/use cases, not the distro
name. Tailscale and developer apps on the owner's machine are personal choices,
not additions to the Galinia baseline. Snap is currently needed for the image's
Firefox delivery; removing it first breaks that route. A Debian-oriented build
can use maintained Debian browser packages, but needs a separate base image.

## Lean image direction

The current Cubic/Xubuntu recipe remains available to reproduce existing work.
For a genuinely lean Debian-based edition, build a separate Debian live-build
profile from explicit packages: XFCE core, LightDM, kernel/firmware, supported
graphics, networking, PipeWire, portals, lock/power, package updates, browser,
file/media/document tools and Galinia defaults. Choose a supported Debian suite
and supported backports where available; "newest upstream" and maximum
stability cannot be guaranteed simultaneously. This is future image work,
not a claim that the current Ubuntu installation was converted to Debian.

Release gates: paired fresh-account XFCE/Galinia measurements; boot/install;
GPU/Wi-Fi/audio; suspend/resume; updates and kernel rollback; browser/media;
pressure tests and idle wakeups. Keep ISO downloads marked development until
these pass. Preserve the user's current desktop during this qualification.

Primary references:
- [Multi-gen LRU](https://docs.kernel.org/admin-guide/mm/multigen_lru.html)
- [zswap](https://docs.kernel.org/admin-guide/mm/zswap.html)
- [EEVDF scheduling](https://docs.kernel.org/scheduler/sched-eevdf.html)
