#!/usr/bin/env python3
"""Text-only, click-through desktop metrics. Collection runs off the GTK thread."""
import fcntl
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import ctypes
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib
HISTORY_LEN = 2
PALETTE_PATH = (Path.home() / ".config/blacklight-rice/palette.json")

class SystemCollector:
    def __init__(self):
        self.prev_cpu_totals = {}
        self.cpu_history = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)
        self.net_rx_history = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)
        self.net_tx_history = deque([0.0] * HISTORY_LEN, maxlen=HISTORY_LEN)

        self.prev_net = None
        self.prev_net_time = None
        self.last_gpu_time = 0.0
        self.gpu_cache = {
            "available": shutil.which("nvidia-smi") is not None,
            "name": "GPU",
            "util": 0.0,
            "temp": 0,
            "mem_used": 0.0,
            "mem_total": 0.0,
            "mem_pct": 0.0,
        }
        self.cpu_model = self._detect_cpu_model()
        self.hwmon_map = self._discover_hwmon()
        self.read_cpu()

    def _detect_cpu_model(self) -> str:
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("model name"):
                        raw = line.split(":", 1)[1].strip()
                        for token in ["AMD ", "Processor", "Eight-Core", "8-Core", "Six-Core", "(TM)", "(R)"]:
                            raw = raw.replace(token, "")
                        return " ".join(raw.split())
        except OSError:
            pass
        return "CPU"

    def _discover_hwmon(self) -> dict:
        mapping = {}
        hwmon_root = Path("/sys/class/hwmon")
        if hwmon_root.exists():
            for d in hwmon_root.iterdir():
                try:
                    name = (d / "name").read_text().strip()
                    temp_file = d / "temp1_input"
                    if temp_file.exists():
                        mapping[name] = temp_file
                except OSError:
                    continue
        return mapping

    def read_temp(self, sensor_names) -> float:
        for name in sensor_names:
            p = self.hwmon_map.get(name)
            if p and p.exists():
                try:
                    return int(p.read_text().strip()) / 1000.0
                except (OSError, ValueError):
                    pass
        return 0.0

    def read_uptime(self) -> str:
        try:
            with open("/proc/uptime", "r", encoding="utf-8") as f:
                secs = int(float(f.read().split()[0]))
            days, rem = divmod(secs, 86400)
            hours, rem = divmod(rem, 3600)
            mins = rem // 60
            if days > 0:
                return f"UP {days}d {hours}h"
            return f"UP {hours}h {mins:02d}m"
        except OSError:
            return "UP --"

    def read_cpu(self) -> dict:
        total_pct = 0.0
        core_pcts = []
        try:
            with open("/proc/stat", "r", encoding="utf-8") as f:
                for line in f:
                    if not line.startswith("cpu"):
                        continue
                    parts = line.split()
                    key = parts[0]
                    vals = [int(x) for x in parts[1:]]
                    idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
                    total = sum(vals)
                    prev = self.prev_cpu_totals.get(key)
                    self.prev_cpu_totals[key] = (idle, total)
                    if prev is not None:
                        d_idle = idle - prev[0]
                        d_total = total - prev[1]
                        pct = 100.0 * (1.0 - d_idle / d_total) if d_total > 0 else 0.0
                        pct = max(0.0, min(100.0, pct))
                        if key == "cpu":
                            total_pct = pct
                        else:
                            core_pcts.append(pct)
        except OSError:
            pass

        freq_ghz = 0.0
        try:
            freqs = []
            with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("cpu MHz"):
                        freqs.append(float(line.split(":", 1)[1].strip()))
            if freqs:
                freq_ghz = max(freqs) / 1000.0
        except (OSError, ValueError):
            pass

        self.cpu_history.append(total_pct)
        return {
            "pct": total_pct,
            "cores": core_pcts,
            "temp": self.read_temp(["k10temp", "coretemp", "zenpower"]),
            "freq_ghz": freq_ghz,
            "history": list(self.cpu_history),
        }

    def read_memory(self) -> dict:
        info = {}
        try:
            with open("/proc/meminfo", "r", encoding="utf-8") as f:
                for line in f:
                    if ":" in line:
                        k, v = line.split(":", 1)
                        info[k.strip()] = int(v.split()[0])
        except OSError:
            pass

        total_kb = info.get("MemTotal", 1)
        avail_kb = info.get("MemAvailable", info.get("MemFree", 0))
        cached_kb = info.get("Cached", 0) + info.get("Buffers", 0)
        used_kb = max(0, total_kb - avail_kb)

        pct = (used_kb / total_kb) * 100.0 if total_kb else 0.0
        return {
            "pct": pct,
            "used_gb": used_kb / 1048576.0,
            "total_gb": total_kb / 1048576.0,
            "cached_gb": cached_kb / 1048576.0,
            "avail_gb": avail_kb / 1048576.0,
        }

    def read_gpu(self) -> dict:
        now = time.monotonic()
        if self.gpu_cache["available"] and (now - self.last_gpu_time >= 5.0):
            self.last_gpu_time = now
            try:
                out = subprocess.check_output(
                    [
                        "nvidia-smi",
                        "--query-gpu=name,utilization.gpu,temperature.gpu,memory.used,memory.total",
                        "--format=csv,noheader,nounits",
                    ],
                    timeout=1.2,
                    text=True,
                ).strip()
                if out:
                    first = out.splitlines()[0]
                    parts = [p.strip() for p in first.split(",")]
                    if len(parts) >= 5:
                        name = parts[0].replace("NVIDIA GeForce ", "")
                        util = float(parts[1])
                        temp = int(float(parts[2]))
                        mem_used = float(parts[3]) / 1024.0
                        mem_total = max(0.1, float(parts[4]) / 1024.0)
                        self.gpu_cache.update(
                            {
                                "name": name,
                                "util": util,
                                "temp": temp,
                                "mem_used": mem_used,
                                "mem_total": mem_total,
                                "mem_pct": (mem_used / mem_total) * 100.0,
                            }
                        )
            except Exception:
                pass
        return self.gpu_cache

    def read_disk(self) -> dict:
        usage = shutil.disk_usage("/")
        total_gb = usage.total / (1024 ** 3)
        used_gb = usage.used / (1024 ** 3)
        pct = (usage.used / usage.total) * 100.0 if usage.total else 0.0
        return {
            "pct": pct,
            "used_gb": used_gb,
            "total_gb": total_gb,
            "temp": self.read_temp(["nvme"]),
        }

    def read_network(self) -> dict:
        rx_bytes = 0
        tx_bytes = 0
        iface_name = "net"
        try:
            with open("/proc/net/dev", "r", encoding="utf-8") as f:
                for line in f.readlines()[2:]:
                    if ":" not in line:
                        continue
                    iface, data = line.split(":", 1)
                    iface = iface.strip()
                    if iface in ("lo", "tailscale0") or iface.startswith(("docker", "veth", "br-")):
                        continue
                    fields = data.split()
                    rx = int(fields[0])
                    tx = int(fields[8])
                    if rx > 0 or tx > 0:
                        iface_name = iface
                        rx_bytes += rx
                        tx_bytes += tx
        except OSError:
            pass

        now = time.monotonic()
        rx_rate = 0.0
        tx_rate = 0.0
        if self.prev_net is not None and self.prev_net_time is not None:
            dt = max(0.1, now - self.prev_net_time)
            rx_rate = max(0.0, (rx_bytes - self.prev_net[0]) / dt)
            tx_rate = max(0.0, (tx_bytes - self.prev_net[1]) / dt)
        self.prev_net = (rx_bytes, tx_bytes)
        self.prev_net_time = now

        peak = max(131072.0, rx_rate, tx_rate)
        self.net_rx_history.append(min(100.0, (rx_rate / peak) * 100.0))
        self.net_tx_history.append(min(100.0, (tx_rate / peak) * 100.0))

        return {
            "iface": iface_name,
            "rx_rate": rx_rate,
            "tx_rate": tx_rate,
            "rx_hist": list(self.net_rx_history),
            "tx_hist": list(self.net_tx_history),
        }


def fmt_rate(bytes_per_sec: float) -> str:
    if bytes_per_sec >= 1048576.0:
        return f"{bytes_per_sec / 1048576.0:4.1f} MB/s"
    return f"{bytes_per_sec / 1024.0:4.1f} KB/s"


class SysMonWidget(Gtk.Window):
    def __init__(self):
        super().__init__(title="System Monitor Widget")
        self.set_name("desktop-metrics")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_app_paintable(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_keep_below(True)
        self.set_accept_focus(False)
        self.set_focus_on_map(False)
        self.stick()
        visual = self.get_screen().get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.wayland = "Wayland" in Gdk.Display.get_default().__gtype__.name
        if self.wayland:
            self.configure_layer()
        self.connect("realize", self.realized)
        self.collector = SystemCollector()
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.pending = None
        self.palette_mtime = None
        self.css = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(self.get_screen(), self.css, 800)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_size_request(310, -1)
        self.add(box)
        self.labels = {}
        for key in ["host", "uptime", "CPU", "RAM", "GPU", "DISK", "NET"]:
            row = Gtk.Box(spacing=14)
            if key not in ("host", "uptime"):
                name = Gtk.Label(label=key, xalign=0)
                name.set_width_chars(4)
                row.pack_start(name, False, False, 0)
            value = Gtk.Label(xalign=0 if key in ("host", "uptime") else 1)
            row.pack_start(value, True, True, 0)
            self.labels[key] = value
            box.pack_start(row, False, False, 0)
        self.labels["host"].set_text(socket.gethostname().upper())
        self.labels["host"].get_style_context().add_class("heading")
        self.reload_palette()
        self.tick()
        GLib.timeout_add_seconds(2, self.tick)

    @staticmethod
    def native_pointer(widget):
        pointer = ctypes.pythonapi.PyCapsule_GetPointer
        pointer.argtypes = [ctypes.py_object, ctypes.c_char_p]
        pointer.restype = ctypes.c_void_p
        return pointer(widget.__gpointer__, None)

    def configure_layer(self):
        layer = ctypes.CDLL("libgtk-layer-shell.so.0")
        if not layer.gtk_layer_is_supported():
            raise RuntimeError("The compositor does not support Wayland layer shell")
        window = self.native_pointer(self)
        layer.gtk_layer_init_for_window.argtypes = [ctypes.c_void_p]
        layer.gtk_layer_init_for_window(window)
        layer.gtk_layer_set_layer.argtypes = [ctypes.c_void_p, ctypes.c_int]
        layer.gtk_layer_set_layer(window, 1)  # Bottom, above wallpaper and behind apps.
        layer.gtk_layer_set_anchor.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        layer.gtk_layer_set_margin.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        for edge, margin in [(1, 24), (2, 24)]:  # Right, top.
            layer.gtk_layer_set_anchor(window, edge, 1)
            layer.gtk_layer_set_margin(window, edge, margin)
        layer.gtk_layer_set_keyboard_mode.argtypes = [ctypes.c_void_p, ctypes.c_int]
        layer.gtk_layer_set_keyboard_mode(window, 0)

    def realized(self, *_):
        if self.wayland:
            cairo = ctypes.CDLL("libcairo.so.2")
            gdk = ctypes.CDLL("libgdk-3.so.0")
            # GTK 3 may send a null Wayland input region for an empty Cairo region.
            # A rectangle outside the surface gives the compositor no hit area.
            class Rectangle(ctypes.Structure):
                _fields_ = [(name, ctypes.c_int) for name in ("x", "y", "width", "height")]

            cairo.cairo_region_create_rectangle.argtypes = [ctypes.POINTER(Rectangle)]
            cairo.cairo_region_create_rectangle.restype = ctypes.c_void_p
            cairo.cairo_region_destroy.argtypes = [ctypes.c_void_p]
            gdk.gdk_window_input_shape_combine_region.argtypes = [
                ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int
            ]
            region = cairo.cairo_region_create_rectangle(ctypes.byref(Rectangle(-2, -2, 1, 1)))
            try:
                gdk.gdk_window_input_shape_combine_region(
                    self.native_pointer(self.get_window()), region, 0, 0
                )
            finally:
                cairo.cairo_region_destroy(region)
            return
        # Empty input region lets desktop clicks pass through the text.
        x = ctypes.CDLL("libX11.so.6")
        fix = ctypes.CDLL("libXfixes.so.3")
        x.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x.XOpenDisplay.restype = ctypes.c_void_p
        x.XCloseDisplay.argtypes = [ctypes.c_void_p]
        fix.XFixesCreateRegion.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
        fix.XFixesCreateRegion.restype = ctypes.c_ulong
        fix.XFixesSetWindowShapeRegion.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ulong]
        fix.XFixesDestroyRegion.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        dpy = x.XOpenDisplay(None)
        if dpy:
            region = fix.XFixesCreateRegion(dpy, None, 0)
            fix.XFixesSetWindowShapeRegion(dpy, self.get_window().get_xid(), 2, 0, 0, region)
            fix.XFixesDestroyRegion(dpy, region)
            x.XCloseDisplay(dpy)
        display = Gdk.Display.get_default()
        monitor = display.get_primary_monitor() or display.get_monitor(0)
        area = monitor.get_workarea()
        self.move(area.x + area.width - 334, area.y + 24)

    def reload_palette(self):
        try:
            stamp = PALETTE_PATH.stat().st_mtime_ns
            if stamp == self.palette_mtime:
                return
            pal = json.loads(PALETTE_PATH.read_text())
            accent = pal.get("accent_hex", "#f2f2f8")
            self.css.load_from_data((
                '#desktop-metrics, #desktop-metrics box { background: transparent; '
                'border: none; border-radius: 0; box-shadow: none; padding: 0; } '
                '#desktop-metrics label { font-family: "JetBrains Mono"; font-size: 11px; '
                'color: #f2f2f8; text-shadow: 0 1px 3px rgba(0,0,0,0.95); } '
                '#desktop-metrics .heading { font-size: 13px; font-weight: bold; color: ' + accent + '; }'
            ).encode())
            self.palette_mtime = stamp
        except (OSError, ValueError, GLib.Error) as exc:
            print(f"Palette unavailable: {exc}", file=sys.stderr)

    def collect(self):
        c = self.collector
        return c.read_uptime(), c.read_cpu(), c.read_memory(), c.read_gpu(), c.read_disk(), c.read_network()

    def tick(self):
        self.reload_palette()
        if self.pending and self.pending.done():
            try:
                up, cpu, ram, gpu, disk, net = self.pending.result()
                self.labels["uptime"].set_text(up)
                self.labels["CPU"].set_text(f"{cpu['pct']:.0f}%   {cpu['temp']:.0f}°C   {cpu['freq_ghz']:.2f} GHz")
                self.labels["RAM"].set_text(f"{ram['used_gb']:.1f} / {ram['total_gb']:.1f} GiB")
                self.labels["GPU"].set_text(f"{gpu['util']:.0f}%   {gpu['temp']:.0f}°C   {gpu['mem_used']:.1f} GiB" if gpu['available'] else "Unavailable")
                self.labels["DISK"].set_text(f"{disk['used_gb']:.0f} / {disk['total_gb']:.0f} GiB")
                self.labels["NET"].set_text(f"↓ {fmt_rate(net['rx_rate']).strip()}  ↑ {fmt_rate(net['tx_rate']).strip()}")
            except Exception as exc:
                print(f"Metrics unavailable: {exc}", file=sys.stderr, flush=True)
            self.pending = None
        if self.pending is None:
            self.pending = self.pool.submit(self.collect)
        return True


LOCK_FILE = Path("/tmp/sysmon-widget.lock")
_lock_fd = None


def acquire_single_instance_lock():
    global _lock_fd
    try:
        _lock_fd = open(LOCK_FILE, "a+")
        fcntl.flock(_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _lock_fd.seek(0)
        _lock_fd.truncate()
        _lock_fd.write(str(os.getpid()))
        _lock_fd.flush()
    except (IOError, BlockingIOError):
        # Another instance is already running; exit silently
        sys.exit(0)


def main():
    acquire_single_instance_lock()
    win = SysMonWidget()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
