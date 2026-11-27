#!/usr/bin/env python3
"""Reversible, runtime-only MGLRU/autogroup/zswap qualification trial.

Run status without root. Apply/restore require a normal administrator terminal.
No boot arguments, packages, governor, swap devices or application limits change.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import platform
import sys

PATHS = {
    'mglru': 'sys/kernel/mm/lru_gen/enabled',
    'autogroup': 'proc/sys/kernel/sched_autogroup_enabled',
    'zswap_pool': 'sys/module/zswap/parameters/max_pool_percent',
    'zswap': 'sys/module/zswap/parameters/enabled',
}
TARGET = {'mglru': '7', 'autogroup': '1', 'zswap_pool': '20', 'zswap': 'Y'}
JOURNAL = Path('/var/lib/galinia/kernel-trial.json')


def normalize(key, value):
    if key == 'zswap':
        if value.lower() in ('y', '1'):
            return 'Y'
        if value.lower() in ('n', '0'):
            return 'N'
        raise ValueError('Invalid zswap switch')
    return str(int(value, 16 if value.startswith('0x') else 10))


def state(root=Path('/')):
    return {key: (root / name).read_text().strip() for key, name in PATHS.items()}


def boot_id(root):
    return (root / 'proc/sys/kernel/random/boot_id').read_text().strip()


def plan(root=Path('/')):
    before = state(root)
    swaps = (root / 'proc/swaps').read_text().splitlines()[1:]
    if not swaps:
        raise ValueError('An active disk swap device/file is required for zswap fallback.')
    if any('zram' in row.split()[0] for row in swaps if row.split()):
        raise ValueError('Existing zram detected; do not stack this trial over another compression policy.')
    # Preserve an existing zswap deployment rather than replacing its policy.
    if normalize('zswap', before['zswap']) == 'Y':
        raise ValueError('zswap is already enabled; retain and audit the existing policy.')
    return {key: {'before': before[key], 'after': value} for key, value in TARGET.items()
            if normalize(key, before[key]) != normalize(key, value)}


def write_setting(root, key, value):
    (root / PATHS[key]).write_text(value + '\n')
    if normalize(key, state(root)[key]) != normalize(key, value):
        raise RuntimeError('Kernel did not accept ' + key)


def apply(root=Path('/'), journal=JOURNAL, writer=write_setting):
    changes = plan(root)
    record = {'version': 1, 'boot_id': boot_id(root), 'kernel': platform.release(), 'changes': changes}
    journal.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation preserves earlier recovery state. Written before any mutation.
    with open(journal, 'x', opener=lambda path, flags: os.open(path, flags, 0o600)) as stream:
        json.dump(record, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    completed = []
    try:
        for key, change in changes.items():
            completed.append(key)  # also roll back a write whose verification fails
            writer(root, key, change['after'])
    except Exception:
        errors = []
        for key in reversed(completed):
            try:
                writer(root, key, changes[key]['before'])
            except Exception as error:
                errors.append(str(error))
        if not errors:
            journal.unlink()
        else:
            print('Rollback incomplete; recovery journal retained: ' + '; '.join(errors), file=sys.stderr)
        raise
    return record


def restore(root=Path('/'), journal=JOURNAL, writer=write_setting):
    record = json.loads(journal.read_text())
    if record.get('version') != 1 or record.get('boot_id') != boot_id(root):
        raise ValueError('Different boot or journal version. Runtime trials reset at reboot; inspect the journal before removing it.')
    changes = record['changes']
    if set(changes) - set(PATHS):
        raise ValueError('Unknown journal setting')
    current = state(root)
    for key, change in changes.items():
        if normalize(key, current[key]) not in (normalize(key, change['after']), normalize(key, change['before'])):
            raise ValueError('Later administrator edit to ' + key + '; refusing to overwrite.')
    # A partially restored journal is safe to retry.
    for key in reversed(list(changes)):
        writer(root, key, changes[key]['before'])
    journal.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--apply', action='store_true')
    mode.add_argument('--restore', action='store_true')
    args = parser.parse_args()
    if not args.apply and not args.restore:
        print(json.dumps({'current': state(), 'trial_targets': TARGET,
                          'persistent': False, 'note': 'Candidate for measurement, not a proven performance improvement.'}, indent=2))
        return
    if os.geteuid() != 0:
        raise PermissionError('Use sudo from a normal terminal; this agent cannot elevate privileges.')
    JOURNAL.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (JOURNAL.parent / 'kernel-trial.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.restore:
            restore()
            print('Previous runtime settings restored. Cached zswap pages may remain until faulted in; swapoff was not used.')
        else:
            print(json.dumps(apply(), indent=2))
            print('Runtime trial applied. No boot configuration changed. Restore with --restore before comparing results.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        raise SystemExit(str(error)) from None
