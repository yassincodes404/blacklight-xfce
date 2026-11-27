#!/usr/bin/env python3
"""Opt-in, reversible Firefox memory presets; no process killing or browser restart."""
import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import uuid

START = '// BEGIN GALINIA MEMORY'
END = '// END GALINIA MEMORY'
PROFILES = {
    'balanced': {
        'browser.tabs.unloadOnLowMemory': True,
        'browser.tabs.min_inactive_duration_before_unload': 300000,
        'browser.low_commit_space_threshold_percent': 10,
        'browser.low_commit_space_threshold_mb': 512,
        'browser.sessionstore.restore_on_demand': True,
        'browser.sessionstore.restore_pinned_tabs_on_demand': False,
        'browser.cache.memory.capacity': 65536,
        'dom.ipc.processPrelaunch.fission.number': 3,
    },
    'aggressive': {
        'browser.tabs.unloadOnLowMemory': True,
        'browser.tabs.min_inactive_duration_before_unload': 60000,
        'browser.low_commit_space_threshold_percent': 25,
        'browser.low_commit_space_threshold_mb': 1024,
        'browser.sessionstore.restore_on_demand': True,
        'browser.sessionstore.restore_pinned_tabs_on_demand': True,
        'browser.cache.memory.capacity': 32768,
        'dom.ipc.processPrelaunch.fission.number': 1,
    },
}
PREF = re.compile(r'^\s*user_pref\("([^"\\]+)",\s*(.*?)\);\s*(?://.*)?$')


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def values(text, keys):
    result = {}
    for line in text.splitlines():
        match = PREF.match(line)
        if match and match[1] in keys:
            result[match[1]] = json.loads(match[2])
    return result


def with_block(text, mode):
    if text.count(START) != text.count(END) or text.count(START) > 1:
        raise ValueError('Malformed existing Galinia memory block; review user.js manually.')
    block = START + '\n// ' + mode + ': memory-pressure based; not an idle-tab timer or hard RAM cap.\n'
    block += ''.join(f'user_pref({json.dumps(key)}, {json.dumps(value)});\n' for key, value in PROFILES[mode].items())
    block += END
    if START in text:
        before, remainder = text.split(START, 1)
        _, after = remainder.split(END, 1)
        return before + block + after
    return text + ('' if not text or text.endswith('\n') else '\n') + block + '\n'


def atomic_write(path, text):
    fd, temporary = tempfile.mkstemp(prefix='.galinia-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def validate_profile(profile):
    if not profile.is_dir() or not (profile / 'prefs.js').is_file():
        raise ValueError('Choose an existing Firefox profile containing prefs.js.')
    if any((profile / name).is_symlink() for name in ['user.js', 'prefs.js', '.galinia-memory-backups']):
        raise ValueError('Refusing symlinked preference or backup files.')


def apply(profile, mode):
    validate_profile(profile)
    user = profile / 'user.js'
    old = user.read_text() if user.exists() else None
    new = with_block(old or '', mode)
    if new == old:
        print('Memory preset is already configured. It takes effect on Firefox startup.')
        return None
    keys = list(PROFILES[mode])
    before = values((profile / 'prefs.js').read_text(), keys)
    before.update(values(old or '', keys))
    backups = profile / '.galinia-memory-backups'
    backups.mkdir(mode=0o700, exist_ok=True)
    identifier = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ-') + uuid.uuid4().hex[:8]
    backup = backups / (identifier + '.json')
    atomic_write(backup, json.dumps({'profile': str(profile), 'original_user_js': old,
                                    'original_prefs': before, 'keys': keys, 'installed_sha256': digest(new)}, indent=2) + '\n')
    atomic_write(user, new)
    print('Memory preset saved. Takes effect on the next Firefox startup; no running tabs were closed.')
    print('Restore backup:', backup)
    return backup


def require_closed(profile):
    lock = profile / 'lock'
    if lock.is_symlink():
        match = re.search(r'\+(\d+)$', os.readlink(lock))
        if match:
            try:
                os.kill(int(match[1]), 0)
            except ProcessLookupError:
                pass
            else:
                raise ValueError('Close Firefox for this profile before restoring.')
    parent = profile / '.parentlock'
    if parent.exists():
        with parent.open('r+b') as stream:
            try:
                fcntl.lockf(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError('Close Firefox for this profile before restoring.') from None
            fcntl.lockf(stream, fcntl.LOCK_UN)


def restore(profile, backup):
    validate_profile(profile)
    require_closed(profile)
    data = json.loads(backup.read_text())
    if data['profile'] != str(profile):
        raise ValueError('Backup belongs to a different Firefox profile.')
    user = profile / 'user.js'
    if not user.is_file() or digest(user.read_text()) != data['installed_sha256']:
        raise ValueError('user.js changed since this preset; restore the newest preset first or review the backup manually.')
    prefs = profile / 'prefs.js'
    lines = []
    for line in prefs.read_text().splitlines(keepends=True):
        match = PREF.match(line.rstrip('\n'))
        if not match or match[1] not in data['keys']:
            lines.append(line)
    text = ''.join(lines)
    if text and not text.endswith('\n'):
        text += '\n'
    text += ''.join(f'user_pref({json.dumps(k)}, {json.dumps(v)});\n' for k, v in data['original_prefs'].items())
    atomic_write(prefs, text)
    if data['original_user_js'] is None:
        user.unlink()
    else:
        atomic_write(user, data['original_user_js'])
    print('Previous memory preferences restored, including clearing newly introduced saved preferences.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--mode', choices=PROFILES, default='balanced')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--restore', type=Path)
    args = parser.parse_args()
    profile = args.profile.expanduser().resolve()
    if args.restore:
        restore(profile, args.restore.expanduser())
    elif args.apply:
        apply(profile, args.mode)
    else:
        validate_profile(profile)
        print(json.dumps(PROFILES[args.mode], indent=2))
        print('Read-only plan. Add --apply to save this preset for the next Firefox startup.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit('Galinia Firefox memory: ' + str(error)) from None
