# Galinia control center and performance work

Super+S opens Galinia Control Center. The native XFCE Settings Manager remains
available under System tools and through its upstream application entry.
The control center exits when closed; no settings or optimization daemon is added.

## Working controls

- **Appearance:** choose wallpaper-adaptive or a fixed readable accent. The
  palette engine watches preference changes using filesystem events, updating
  GTK, frames, terminal colors and desktop metrics through the existing pipeline.
- **Layout:** set the main panel height, hide/show the monitor, or start from
  compact/comfortable presets. Changes use live XFconf APIs and user services,
  not hot replacement of in-memory XML. Monitor visibility survives login.
- **App priorities:** save normal, interactive or background CPU preferences
  per desktop application ID. Galinia app search launches independent user
  services in app.slice with relative CPU weights; background work also gets a
  lower scheduling priority. These are not CPU reservations or hard RAM limits.
- **Memory:** apply or restore the existing Firefox presets from a graphical
  profile chooser. They remain explicit opt-ins and require the next browser
  startup. Undo requires that profile to be closed and checks later edits.
- **Overview:** refresh available RAM and CPU/memory pressure on demand.
  Pressure means time tasks waited for resources, not percent CPU utilization.
- **System tools:** open maintained display, keyboard, power, audio, Bluetooth,
  software, update and backup tools. Missing tools are disabled with an explanation.

The user preference file is `$XDG_CONFIG_HOME/galinia/preferences.json`, normally
`~/.config/galinia/preferences.json`. Validation rejects malformed values and
fixed accents that cannot reach 4.5:1 against the reference dark surface.
The previous preference snapshot supports Undo. Failed panel/monitor changes
attempt to roll back already-applied runtime changes. App priority changes do
not trigger a theme rebuild. Firefox backups remain separate and private.

App priorities take effect only on the next launch through Galinia search.
Already-running apps, single-instance browser processes and apps launched
elsewhere are not silently moved into new cgroups. Weights need a delegated
CPU controller; effects depend on sibling workloads and the parent hierarchy.
No real-time policy, negative nice level, CPU quota, memory maximum, security
isolation change or process killer is applied. Disk weighting is not offered
because controller delegation varies by host.

## Current tuning decisions

The reference system uses the distribution kernel and schedutil CPU governor.
An initial snapshot showed no CPU or memory pressure, disk swap configured
and zswap disabled. That observation is not an optimization benchmark.
Replacing a scheduler or changing every machine's VM tunables without a
controlled workload would provide no evidence of a benefit.

Keep the upstream CPU scheduler for the preview. Swappiness is a relative
reclaim/IO cost preference, not a target percentage of RAM used. Do not set it
to zero, drop filesystem caches on a timer, disable swap or force a performance
governor as blanket optimizations. Evaluate power and latency tradeoffs on the
actual hardware.

`iso/experiments/zram-generator.conf` is an **unapplied VM experiment** using
the upstream generator's bounded half-RAM/4-GiB size with zstd and higher swap
priority than disk. It consumes RAM as compressed pages are stored. Check
existing zram/zswap managers, preserve disk fallback, and benchmark compression
CPU cost, stalls and application behavior before adopting it. Do not copy it
to production systems or the ISO defaults without qualification. Changing
system swap/governor configuration still requires host administrator access.

## Measure instead of advertising a speed claim

```sh
python3 tools/memory_report.py
python3 home/.local/share/galinia/performance.py
python3 tools/latency_probe.py --seconds 5
```

The wake-up probe measures its own sleep/wake delay for a bounded interval.
It does not stress the machine, infer game FPS, measure browser interaction
or demonstrate superiority to another distribution. Compare repeated runs on
the same hardware and kernel with a controlled workload, alongside idle PSS,
pressure, power and actual app responsiveness. Keep raw results and test setup.

The distinguishing experience under development is coherent customization,
clear app priorities and reversible controls with observable results. Claims
about lower idle RAM or better performance require clean-VM/hardware evidence.

## Idle behavior

The reference and shipped X11 profile now use 40 minutes for display blanking,
monitor power-off and idle suspend on AC and battery. Screensaver activation
also waits 40 minutes, with screen locking enabled. Lid and critical-battery
actions remain under the base distribution's power manager. Change these
through System tools → Power and suspend when a different policy is needed.

References: [kernel cgroup v2](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html),
[systemd resource control](https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html),
[kernel VM tuning](https://www.kernel.org/doc/html/latest/admin-guide/sysctl/vm.html),
[EEVDF](https://www.kernel.org/doc/html/latest/scheduler/sched-eevdf.html),
[zram-generator](https://github.com/systemd/zram-generator).
