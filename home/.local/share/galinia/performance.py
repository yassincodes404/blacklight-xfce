"""Fast, read-only pressure and configuration snapshot; no tuning or background loop."""
import json
from pathlib import Path


def read(path):
    try:
        return path.read_text().strip()
    except OSError:
        return ''


def pressure(text):
    result = {}
    for line in text.splitlines():
        parts = line.split()
        if parts:
            try:
                result[parts[0]] = {k: float(v) for k, v in (part.split('=', 1) for part in parts[1:])}
            except ValueError:
                continue
    return result


def snapshot(root=Path('/')):
    values = {}
    for line in read(root / 'proc/meminfo').splitlines():
        parts = line.split()
        if len(parts) > 1 and parts[1].isdigit():
            values[parts[0].rstrip(':')] = int(parts[1])
    swaps = []
    for line in read(root / 'proc/swaps').splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 4:
            swaps.append({'type': 'zram' if 'zram' in parts[0] else parts[1],
                          'size_mib': int(parts[2]) / 1024, 'used_mib': int(parts[3]) / 1024})
    return {'total_mib': values.get('MemTotal', 0) / 1024,
            'available_mib': values.get('MemAvailable', 0) / 1024,
            'cpu_pressure': pressure(read(root / 'proc/pressure/cpu')),
            'memory_pressure': pressure(read(root / 'proc/pressure/memory')),
            'governor': read(root / 'sys/devices/system/cpu/cpu0/cpufreq/scaling_governor') or 'unavailable',
            'swappiness': read(root / 'proc/sys/vm/swappiness') or 'unavailable',
            'zswap': read(root / 'sys/module/zswap/parameters/enabled') or 'unavailable',
            'swaps': swaps}


if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))
