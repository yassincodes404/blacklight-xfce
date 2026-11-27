# Reference desktop audit: 2026-11-27

Scope: read-only checks of the running XFCE/labwc Wayland session, service and
kernel logs, package state, Galinia startup source, and release evidence policy.
This is a targeted audit, not a claim that all defects have been found. No lock,
suspend, compositor restart, portal restart or driver change was performed.

## Priorities

1. **Screen sharing currently advertises no sources.** The portal's ScreenCast
   interface exists, but AvailableSourceTypes and AvailableCursorModes are both
   zero; the wlroots portal backend is not running. Browser capture must be
   tested after fixing session/backend lifecycle. A successful grim screenshot
   does not validate the browser's portal path.
2. **Locking is not qualified in this session.** No running screensaver/locker
   or org.freedesktop.ScreenSaver owner was found. Super+L invokes xflock4, which
   delegates to the session manager. xfce4-screensaver 4.20.1 is installed, but
   that does not prove working native Wayland lock and authentication. Test the
   actual lock/unlock and suspend/resume path with the user present; do not
   equate monitor blanking with locking.
3. **Power-inhibition failures are current.** The portal repeatedly reports
   that inhibition other than idle is unsupported. Its GTK backend also reports
   that org.freedesktop.ScreenSaver has no owner. Video playback and other
   keep-awake requests need end-to-end verification. The configured 40-minute
   AC/battery timeout values exist; their presence alone does not prove Wayland
   idle behavior.
4. **Graphical service lifetime needs work.** graphical-session.target is
   inactive despite Galinia services declaring PartOf that target. The portal
   frontend predates the current compositor session and retains its old labwc
   PID in its environment. galinia-session imports the new environment and
   restarts Galinia units, but does not coordinate portal lifetime. Logs show
   audio-widget retries against disconnected displays during session changes;
   the widget is currently healthy. Establish login/logout ownership and test
   repeated session switches; do not hide the issue by increasing retry limits.
5. **Actual crash records require reproduction.** This boot has a labwc SIGABRT
   record and repeated xiccd SIGSEGV events. Gamescope also segfaulted at 23:16
   local time inside libnvidia-glcore.so.595.99.02. The instruction location is
   evidence, not proof of the originating defect. Keep application, driver and
   compositor reproduction separate; do not disable random modules globally.
6. **Flameshot autostart is not session-aware in the profile.** Its desktop entry
   starts Flameshot on all XFCE logins, including Wayland, while the screenshot
   shortcut correctly routes Wayland to the native helper. The autostart policy
   should follow the same session distinction. No Flameshot process was running
   at the audit time; this is a source configuration finding.
7. **Hardware warnings need hardware-specific triage.** amd_pstate rejected
   reported frequency values; the active fallback is acpi-cpufreq with schedutil.
   There are also firmware RNG, IOMMU and NVIDIA USB-C controller warnings.
   These messages alone do not establish user-visible failure. Do not force CPU
   tuning or remove drivers without reproduction and measurement.
8. **Distribution release qualification remains incomplete.** The release gate
   reports no ISO-bound qualification report. Installation/reboot, account
   creation, updates, recovery, lock/unlock and reference hardware tests remain
   required. CI image-build success is not an installer or desktop pass.

## Checks that passed

- Installed libxfce4windowing is 4.20.5-1galinia1; the user confirmed the visible
  icon problem is solved.
- No system or user units are currently marked failed.
- dpkg --audit reported no incomplete package state.
- PipeWire, pipewire-pulse and WirePlumber are active.
- Galinia audio and GTK portal services are currently running.
- Root/home filesystem has ample free space.
- No OOM kills were found in the inspected boot log. Current memory PSI averages
  are zero and approximately 8.4 GiB is available. This is not a clean-login RAM
  benchmark.
- Galinia configuration verification passed for 633 tracked payloads.

## Next work order

Qualify locking first, then fix session/portal lifecycle and browser capture,
then reproduce compositor/GPU crashes. After those changes, test a fresh account
and repeated X11/Wayland logins, and qualify the actual ISO. Preserve the
currently working desktop while doing that work.

The latest completed ISO run (46037640446) was also reviewed: both BIOS and UEFI
180-second screenshots still display the Galinia starting splash. Neither
screenshot proves desktop arrival, and this observation window does not by
itself prove a permanent boot hang. Extend the boot investigation and inspect
guest logs before marking live boot passed.
