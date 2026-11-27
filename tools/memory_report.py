#!/usr/bin/env python3
"""One-shot Linux memory accounting; no daemon, process control or cache clearing."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

GROUPS = {'firefox': 'Firefox', 'firefox-bin': 'Firefox', 'code': 'VS Code',
          'chatgpt': 'ChatGPT / Codex', 'codex': 'ChatGPT / Codex',
          'motrix': 'Motrix', 'audiorelay': 'AudioRelay', 'opencode': 'OpenCode',
          'flameshot': 'Flameshot'}


def fields(text):
    result = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) > 1 and parts[0].endswith(':') and parts[1].isdigit():
            result[parts[0][:-1]] = int(parts[1])
    return result


def group(row, rows):
    seen = set()
    current = row
    while current and current['pid'] not in seen:
        seen.add(current['pid'])
        label = current.get('app') or GROUPS.get(current['name'].lower())
        if label:
            return label
        current = rows.get(current['ppid'])
    return 'Other user processes'


def collect():
    memory = fields(Path('/proc/meminfo').read_text())
    rows = {}
    skipped = 0
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            if proc.stat().st_uid != os.getuid():
                continue
            stat = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
            usage = fields((proc / 'smaps_rollup').read_text())
            row = {'pid': int(proc.name), 'ppid': int(stat[1]), 'name': (proc / 'comm').read_text().strip(),
                   'pss_kib': usage.get('Pss', 0), 'rss_kib': usage.get('Rss', 0)}
            if row['name'] == 'AppRun':
                try:
                    if 'flameshot' in str((proc / 'exe').readlink()).lower():
                        row['app'] = 'Flameshot'
                except OSError:
                    pass
            rows[row['pid']] = row
        except (OSError, ValueError, IndexError):
            skipped += 1
    groups = {}
    for row in rows.values():
        label = group(row, rows)
        groups[label] = groups.get(label, 0) + row['pss_kib']
    return {'utc': datetime.now(timezone.utc).isoformat(),
            'system_mib': {key: round(memory.get(key, 0) / 1024, 1) for key in
                           ['MemTotal', 'MemAvailable', 'MemFree', 'Cached', 'SReclaimable', 'SwapTotal', 'SwapFree']},
            'groups_pss_mib': {k: round(v / 1024, 1) for k, v in sorted(groups.items(), key=lambda item: item[1], reverse=True)},
            'processes': sorted(rows.values(), key=lambda row: row['pss_kib'], reverse=True),
            'skipped_processes': skipped,
            'scope': 'PSS for readable processes belonging to this user; excludes inaccessible/system processes and kernel allocations. A live snapshot is not a clean-login baseline.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    report = collect()
    if args.json:
        print(json.dumps(report, indent=2))
        return
    print('System memory, MiB:', json.dumps(report['system_mib']))
    print('Application groups, proportional memory (MiB):')
    for name, value in report['groups_pss_mib'].items():
        print(f'{value:8.1f}  {name}')
    print(report['scope'])


if __name__ == '__main__':
    main()
