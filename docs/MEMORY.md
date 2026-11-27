# Memory efficiency and measurement

Keep the desktop's appearance and useful integrations, then measure their
cost separately from applications and reclaimable filesystem caches. There
is no validated 800 MiB idle-memory claim for this profile yet.

## A comparable baseline

```sh
python3 tools/memory_report.py
python3 tools/memory_report.py --json
```

For a desktop baseline, use a fresh login, wait for startup work to settle,
and measure before opening Firefox, editors, Electron applications or games.
Compare the same base release, driver, session, monitors and startup selection.
Do not compare a fresh XFCE session against a long-running desktop with apps
open. Keep the measurement method and time after login consistent.

`MemAvailable` estimates memory available for new allocations, including
reclaimable cache. `MemFree` alone is not a useful measure of memory pressure.
The report sums proportional set size (PSS) for each readable user-process
tree so shared library pages are not counted in full for every process. It
does not capture page contents, URLs, document names or process arguments.
Kernel/system processes outside the user's readable scope are not included in
the application totals. Process churn and permissions can make a snapshot incomplete.

Avoid cache-dropping timers, forced process killing and disabling security
isolation as ways to achieve a smaller displayed memory number. Keep the
base distribution's swap configuration unless a separately tested change is
needed; a swap entry does not prove current memory pressure.

## Firefox presets

The memory-only tool is separate from the older optional browser styling and
privacy-policy snapshot. It changes only eight memory/startup preferences.
It does not install an extension, cap Firefox's whole process tree or restart
the browser. Site isolation and hardware acceleration remain governed by the
existing browser setup.

Choose an actual Firefox profile containing `prefs.js`:

```sh
python3 tools/firefox_memory.py --profile /absolute/path/to/profile --mode aggressive
python3 tools/firefox_memory.py --profile /absolute/path/to/profile --mode aggressive --apply
```

| Behavior | Balanced | Aggressive |
|---|---|---|
| Automatic low-memory tab unloading | Enabled | Enabled |
| Minimum tab inactivity before eligibility | 5 minutes | 1 minute |
| Linux available-memory threshold | 10% or 512 MiB | 25% or 1024 MiB |
| Restore ordinary tabs on selection | Yes | Yes |
| Restore pinned tabs on selection | No | Yes |
| Memory cache preference | 64 MiB | 32 MiB |
| Spare preallocated content-process count preference | 3 | 1 |

The thresholds are deliberately earlier than upstream's Linux defaults.
Firefox checks system available memory; it unloads eligible inactive tabs
under memory pressure. **A one-minute minimum is not a one-minute discard
timer.** Tabs can remain loaded while memory is plentiful. Pinned tabs become
less convenient on restart in aggressive mode, and switching back to unloaded
tabs requires a reload. Notifications in lazy/unloaded tabs may wait for reload.
Cache and spare-process preferences do not limit the memory used by active pages.

Firefox's own unloader chooses candidates and protects active/media/WebRTC
tabs according to its implementation. Inspect `about:unloads`, or right-click
a tab and choose Unload Tab, for direct control. No preset can guarantee a
fixed amount of memory for arbitrary websites. Test with your real workload.

The apply command appends a delimited block to the profile's `user.js`,
preserves unrelated preferences and writes a private backup under
`.galinia-memory-backups/` in that profile. Changes take effect at the next
Firefox startup. It does not modify `prefs.js` while the browser is running.

To undo, close Firefox for that profile and use the backup path printed by apply:

```sh
python3 tools/firefox_memory.py --profile /absolute/path/to/profile --restore /absolute/path/to/backup.json
```

Restore checks for later `user.js` edits, restores the previous file and
restores/removes only the managed saved preferences in `prefs.js`. Unrelated
browser preference changes are retained. Restore newer presets first. Do not
publish backups or a personal browser profile in the Galinia repository.

Sources: [Mozilla tab unloading documentation](https://support.mozilla.org/en-US/kb/unload-inactive-tabs-save-system-memory-firefox),
[Linux available-memory watcher](https://github.com/mozilla-firefox/firefox/blob/main/xpcom/base/AvailableMemoryWatcherLinux.cpp),
[tab-unloader implementation](https://github.com/mozilla-firefox/firefox/blob/main/browser/components/tabbrowser/TabUnloader.sys.mjs),
[startup preference definitions](https://github.com/mozilla-firefox/firefox/blob/main/browser/app/profile/firefox.js),
and [static preference definitions](https://github.com/mozilla-firefox/firefox/blob/main/modules/libpref/init/StaticPrefList.yaml).

## Desktop startup

Galinia's monitor and wallpaper services are lower-priority and have bounded
restarts. Clipboard and screenshot tools use upstream implementations rather
than a second custom capture stack. Welcome and offline help do not remain
running in the background after closing them.

Large Electron applications and download managers can add hundreds of MiB
when started at login. Offer on-demand startup when the user accepts the
associated integration tradeoff. Do not silently remove personal startup
entries, close apps, or break active downloads in the name of optimization.
Install software managers and backup tools for availability; avoid adding
separate always-running Galinia agents for them.

An idle-memory target needs a repeatable clean-VM and real-hardware benchmark.
After that baseline exists, record changes to both startup RAM and application
responsiveness before accepting further tuning.
