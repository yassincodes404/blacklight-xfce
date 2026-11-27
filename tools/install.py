#!/usr/bin/env python3
"""Galinia preview: plan, install and restore a per-user XFCE profile."""
import argparse
import configparser
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import uuid

import control

ROOT = Path(__file__).resolve().parents[1]


def manifest():
    return json.loads((ROOT / 'config/first-launch.json').read_text())


def packages():
    names = sorted({name for group in manifest()['packages'].values() for name in group})
    if any(not re.fullmatch(r'[a-z0-9][a-z0-9+.-]*', name) for name in names):
        raise ValueError('Invalid package name in first-launch manifest')
    return names


def package_status():
    result = subprocess.run(['dpkg-query', '-W', '-f=${binary:Package}\t${db:Status-Status}\n'],
                            capture_output=True, text=True, check=True)
    installed = {line.split('\t')[0].split(':')[0] for line in result.stdout.splitlines()
                 if line.endswith('\tinstalled')}
    return [name for name in packages() if name not in installed]


def platform_check():
    info = {}
    for line in Path('/etc/os-release').read_text().splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            info[key] = value.strip('"')
    arch = subprocess.check_output(['dpkg', '--print-architecture'], text=True).strip()
    supported = manifest()['platform']
    if (info.get('ID'), info.get('VERSION_ID')) != (supported['id'], supported['version']) or arch not in supported['architectures']:
        raise ValueError('This preview targets Ubuntu/Xubuntu 26.04 amd64 only.')
    print(f"Platform: {info.get('PRETTY_NAME')} / {arch} ({supported['status']})")


def require_logged_out():
    # Inspect processes, not just DISPLAY: switching to a TTY does not log XFCE out.
    for name in ['xfce4-session', 'xfconfd', 'labwc']:
        result = subprocess.run(['pgrep', '-u', str(os.getuid()), '-x', name], capture_output=True)
        if result.returncode == 0:
            raise ValueError('Log out of all XFCE/labwc sessions for this account, then use a TTY to install or restore.')
        if result.returncode != 1:
            raise ValueError('Could not check running sessions; no profile files changed.')


def legacy_units(home):
    units = ['sysmon-widget.service', 'blacklight-wallpaper-sync.service']
    return [unit for unit in units if (checked_path(home, '.config/systemd/user/default.target.wants/' + unit)).is_symlink()]


def checked_path(home, relative):
    """Reject path traversal and symlinked parents before accessing user files."""
    rel = Path(relative)
    if rel.is_absolute() or not rel.parts or any(part in ('..', '.') for part in rel.parts):
        raise ValueError('Unsafe relative path: ' + str(relative))
    dest = home / rel
    for parent in dest.parents:
        if parent == home:
            break
        if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
            raise ValueError('Destination parent must be a real directory: ' + str(parent))
    return dest


def signature(path):
    if path.is_symlink():
        return {'link': os.readlink(path)}
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError('Refusing to replace a directory or special file: ' + str(path))
    return {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'mode': path.stat().st_mode & 0o777}


def merged_mime(existing, incoming):
    def read(text):
        parser = configparser.ConfigParser(interpolation=None, strict=True, delimiters=('=',))
        parser.optionxform = str
        parser.read_string(text)
        return parser
    old, new = read(existing), read(incoming)
    for section in new.sections():
        if not old.has_section(section):
            old.add_section(section)
        for key, value in new.items(section):
            if section == 'Added Associations':
                values = [v for v in (value + ';' + old.get(section, key, fallback='')).split(';') if v]
                value = ';'.join(dict.fromkeys(values)) + ';'
            old.set(section, key, value)
    out = io.StringIO()
    old.write(out, space_around_delimiters=False)
    return out.getvalue()


def merged_xsession(existing, incoming):
    start, end = '# BEGIN GALINIA SESSION', '# END GALINIA SESSION'
    block = start + '\n' + incoming.rstrip() + '\n' + end
    if existing.count(start) != existing.count(end) or existing.count(start) > 1:
        raise ValueError('Malformed Galinia session block; review .xsessionrc manually.')
    if start in existing:
        before, remainder = existing.split(start, 1)
        _, after = remainder.split(end, 1)
        return before + block + after
    return existing.rstrip() + ('\n\n' if existing.strip() else '') + block + '\n'


def prepare_stage(stage, home):
    for rel, merge in [('.config/mimeapps.list', merged_mime), ('.xsessionrc', merged_xsession)]:
        dest = checked_path(home, rel)
        if dest.is_symlink():
            raise ValueError('Refusing to merge a symlink: ' + str(dest))
        incoming = stage / rel
        incoming.write_text(merge(dest.read_text() if dest.exists() else '', incoming.read_text()))


def changes(stage, home):
    result = []
    for source in sorted(stage.rglob('*')):
        if source.is_dir() and not source.is_symlink():
            continue
        if source.is_symlink() and not source.resolve().is_relative_to(stage.resolve()):
            raise ValueError('Staged symlink escapes the profile: ' + str(source))
        rel = str(source.relative_to(stage))
        dest = checked_path(home, rel)
        old, new = signature(dest), signature(source)
        if old != new:
            result.append({'path': rel, 'before': old, 'after': new})
    return result


def save_journal(path, data):
    temp = path.with_suffix('.tmp')
    with temp.open('w') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def copy_atomic(source, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.galinia-', dir=dest.parent)
    os.close(fd)
    temp = Path(temp)
    try:
        if source.is_symlink():
            temp.unlink()
            temp.symlink_to(os.readlink(source))
        else:
            shutil.copy2(source, temp)
        os.replace(temp, dest)
    finally:
        if temp.exists() or temp.is_symlink():
            temp.unlink()


@contextmanager
def installation_lock(home):
    state = checked_path(home, '.local/state/galinia/installs/.lock')
    if state.is_symlink():
        raise ValueError('Installer lock must not be a symlink.')
    state.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with state.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another Galinia install/restore is running.') from None
        yield state.parent


def restore_transaction(backup, home, save_conflicts=False):
    journal_path = backup / 'journal.json'
    journal = json.loads(journal_path.read_text())
    if journal['home'] != str(home):
        raise ValueError('Backup belongs to a different home directory.')
    if journal['status'] == 'restored':
        return
    # Preflight every entry before changing any file. Preserve post-install edits.
    progress_path = backup / 'progress.json'
    limit = json.loads(progress_path.read_text())['limit'] if progress_path.exists() else 0
    entries = journal['files'][:limit]
    conflicts = []
    for entry in entries:
        dest = checked_path(home, entry['path'])
        current = signature(dest)
        if current != entry['after'] and current != entry['before']:
            if not save_conflicts:
                raise ValueError('Restore conflict: ' + str(dest) + '. Use restore --save-conflicts to preserve later edits before restoring.')
            conflicts.append({'path': entry['path'], 'state': current})
        if entry['before'] is not None:
            original = checked_path(backup / 'originals', entry['path'])
            if signature(original) != entry['before']:
                raise ValueError('Backup integrity check failed: ' + entry['path'])
    if conflicts:
        saved = backup / 'conflicts' / uuid.uuid4().hex
        saved.mkdir(parents=True, mode=0o700)
        for conflict in conflicts:
            source = checked_path(home, conflict['path'])
            if signature(source) != conflict['state']:
                raise ValueError('File changed during conflict preservation: ' + conflict['path'])
            if conflict['state'] is not None:
                copy_atomic(source, saved / 'files' / conflict['path'])
                if signature(saved / 'files' / conflict['path']) != conflict['state']:
                    raise ValueError('Could not preserve conflict: ' + conflict['path'])
        save_journal(saved / 'manifest.json', conflicts)
        print('Later edits preserved in:', saved)
    for entry in reversed(entries):
        dest = checked_path(home, entry['path'])
        if signature(dest) == entry['before']:
            continue
        if entry['before'] is None:
            dest.unlink()
        else:
            copy_atomic(backup / 'originals' / entry['path'], dest)
    journal['status'] = 'restored'
    save_journal(journal_path, journal)


def install_transaction(stage, home, history):
    entries = changes(stage, home)
    if not entries:
        print('Galinia profile is already current; no files changed.')
        return None
    identifier = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ-') + uuid.uuid4().hex[:8]
    backup = history / identifier
    backup.mkdir(mode=0o700)
    journal = {'version': 1, 'home': str(home), 'status': 'preparing', 'files': entries}
    path = backup / 'journal.json'
    save_journal(path, journal)
    print('Recovery journal:', path, flush=True)
    try:
        # Finish all backups before the first profile write.
        for entry in entries:
            if signature(checked_path(home, entry['path'])) != entry['before']:
                raise ValueError('File changed during preparation: ' + entry['path'])
            if entry['before'] is not None:
                original = backup / 'originals' / entry['path']
                original.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(home / entry['path'], original, follow_symlinks=False)
        journal['status'] = 'installing'
        save_journal(path, journal)
        for index, entry in enumerate(entries):
            dest = checked_path(home, entry['path'])
            if signature(dest) != entry['before']:
                raise ValueError('File changed during installation: ' + entry['path'])
            # Journal a batch BEFORE writes. Restore recognizes untouched originals.
            # Keep progress separate: rewriting a 90k-icon manifest per file is quadratic.
            if index % 128 == 0:
                save_journal(backup / 'progress.json', {'limit': min(index + 128, len(entries))})
            copy_atomic(stage / entry['path'], dest)
        journal['status'] = 'installed'
        save_journal(path, journal)
    except (Exception, KeyboardInterrupt):
        try:
            restore_transaction(backup, home)
        except Exception as error:
            print('Automatic restore needs attention:', error)
        raise
    print(f'Installed {len(entries)} files. Restore ID: {identifier}')
    return backup


def confirm(yes):
    if not yes and input('Apply this plan? [y/N] ').strip().lower() != 'y':
        raise ValueError('Cancelled; no profile files changed.')


def refresh_caches(home):
    for command in [['systemctl', '--user', 'daemon-reload'], ['fc-cache', '-f'], ['update-desktop-database', str(home / '.local/share/applications')]]:
        if shutil.which(command[0]):
            result = subprocess.run(command, check=False)
            if result.returncode:
                print('Cache refresh failed; retry after login:', command[0])


def check_history(history, restore_id=None):
    for path in sorted(history.glob('*/journal.json')):
        data = json.loads(path.read_text())
        if data['status'] == 'restored':
            continue
        if restore_id is not None and path.parent.name > restore_id:
            raise ValueError('Restore the newer installation first: ' + path.parent.name)
        if restore_id is None and data['status'] != 'installed':
            raise ValueError('An interrupted installation needs restore first: ' + path.parent.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    for name in ['plan', 'install']:
        p = subs.add_parser(name)
        p.add_argument('--list-files', action='store_true')
        if name == 'install':
            p.add_argument('--install-packages', action='store_true', help='Run sudo apt-get; packages are not removed by profile restore')
            p.add_argument('--yes', action='store_true')
    restore = subs.add_parser('restore')
    restore.add_argument('id', help='Restore ID printed by installation')
    restore.add_argument('--yes', action='store_true')
    restore.add_argument('--save-conflicts', action='store_true', help='Save later edits alongside the backup before restoring original files')
    args = parser.parse_args()
    home = Path.home().resolve()
    if os.getuid() == 0:
        raise ValueError('Run as your normal desktop user, not root or sudo.')
    if args.command == 'restore':
        require_logged_out()
        if not re.fullmatch(r'[0-9]{8}T[0-9]{6}(?:[0-9]{6})?Z-[a-f0-9]{8}', args.id):
            raise ValueError('Invalid restore ID.')
        confirm(args.yes)
        with installation_lock(home) as history:
            check_history(history, args.id)
            backup = checked_path(home, '.local/state/galinia/installs/' + args.id + '/journal.json').parent
            restore_transaction(backup, home, save_conflicts=args.save_conflicts)
        refresh_caches(home)
        print('Profile restored. Installed packages and empty directories were retained.')
        return
    platform_check()
    control.verify()
    missing = package_status()
    print('Missing baseline packages:', ', '.join(missing) or 'none')
    legacy = legacy_units(home)
    if legacy:
        print('Legacy early-start links detected. Before installing, run: systemctl --user disable ' + ' '.join(legacy))
    print('Preview includes welcome, desktop settings and app defaults. Boot/login branding is staged separately.')
    with tempfile.TemporaryDirectory(prefix='galinia-preview-') as temp:
        stage = Path(temp) / 'home'
        control.render(argparse.Namespace(output=stage, target_home=home, wallpaper=None))
        prepare_stage(stage, home)
        entries = changes(stage, home)
        print(f'Profile plan: {len(entries)} changed files; {sum(e["before"] is not None for e in entries)} existing files will be backed up.')
        if args.list_files:
            for entry in entries:
                print(('replace ' if entry['before'] else 'create  ') + entry['path'])
        if args.command == 'plan':
            print('Read-only plan. No packages or desktop settings changed.')
            return
        require_logged_out()
        if legacy:
            raise ValueError('Disable the listed legacy early-start links, then review a fresh plan.')
        if missing and not args.install_packages:
            raise ValueError('Baseline packages are missing. Review the plan, then use --install-packages or install them manually.')
        confirm(args.yes)
        if missing:
            # APT handles dependency resolution; refuse removals. Keep its own prompt.
            subprocess.run(['sudo', 'apt-get', '--no-remove', 'install', *missing], check=True)
            if package_status():
                raise ValueError('Package installation incomplete; profile was not applied.')
        require_logged_out()
        with installation_lock(home) as history:
            check_history(history)
            # Another install/desktop edit may have changed merge inputs since the plan.
            # Refuse drift rather than overwriting edits based on a stale plan.
            if changes(stage, home) != entries:
                raise ValueError('Files changed since the plan. Run again to review the new plan.')
            install_transaction(stage, home, history)
        refresh_caches(home)
        print('Log in to the XFCE X11 session. Welcome will open for this account on first login.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        raise SystemExit('Galinia: ' + str(error)) from None
