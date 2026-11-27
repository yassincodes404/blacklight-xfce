#!/usr/bin/env python3
"""Bounded userspace wake-up probe; not a gaming or whole-system benchmark."""
import argparse
import json
import math
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'home/.local/share/galinia'))
import performance


def probe(seconds=5, interval=.02):
    if not 1 <= seconds <= 30 or not .01 <= interval <= .5:
        raise ValueError('Use 1–30 seconds and an interval of 0.01–0.5 seconds.')
    before = performance.snapshot()
    samples = []
    start, cpu = time.perf_counter(), time.process_time()
    deadline = start + seconds
    while time.perf_counter() < deadline:
        target = time.perf_counter() + interval
        time.sleep(interval)
        samples.append(max(0, (time.perf_counter() - target) * 1000))
    ordered = sorted(samples)
    return {'duration_s': time.perf_counter() - start, 'process_cpu_s': time.process_time() - cpu,
            'samples': len(samples), 'median_delay_ms': ordered[len(ordered) // 2],
            'p99_delay_ms': ordered[max(0, math.ceil(.99 * len(ordered)) - 1)],
            'worst_delay_ms': ordered[-1], 'before': before, 'after': performance.snapshot(),
            'scope': 'Local sleep/wake scheduling delay under the current workload. Not frame time, input latency, browser speed or a cross-distro comparison.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=float, default=5)
    args = parser.parse_args()
    try:
        print(json.dumps(probe(args.seconds), indent=2))
    except ValueError as error:
        raise SystemExit(str(error)) from None
