#!/usr/bin/env python3
"""Read-only everyday desktop checks. Never starts services or changes settings."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

import install


def unit_state(unit, user=False):
    command = ['systemctl'] + (['--user'] if user else [])
    try:
        result = subprocess.run(command + ['show', unit, '--property=LoadState,ActiveState,UnitFileState'],
                                capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return {}
    if result.returncode:
        return {}
    return dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)


def service_result(name, state, demand=False):
    if not state or state.get('LoadState') == 'not-found':
        return {'name': name, 'status': 'warn', 'detail': 'service unavailable or bus not reachable'}
    if state.get('LoadState') in ('masked', 'error', 'bad-setting') or state.get('UnitFileState') == 'masked':
        return {'name': name, 'status': 'warn', 'detail': 'service masked or configuration invalid'}
    active = state.get('ActiveState', 'unknown')
    if active == 'failed':
        return {'name': name, 'status': 'warn', 'detail': 'service failed'}
    if active == 'active':
        return {'name': name, 'status': 'ok', 'detail': 'active'}
    if demand and active == 'inactive':
        return {'name': name, 'status': 'info', 'detail': 'inactive; starts on demand'}
    return {'name': name, 'status': 'warn', 'detail': active}


def process_check(label, names, running):
    count = sum(running.count(name) for name in names)
    return {'name': label, 'status': 'ok' if count == 1 else 'warn',
            'detail': 'one running instance' if count == 1 else f'{count} instances; review missing or duplicate startup entries'}


def collect():
    checks = []
    missing = install.package_status()
    checks.append({'name': 'Everyday package baseline', 'status': 'warn' if missing else 'ok',
                   'detail': 'missing: ' + ', '.join(missing) if missing else 'all baseline packages installed'})
    graphical = bool(os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))
    for name in ['NetworkManager.service', 'upower.service', 'udisks2.service']:
        checks.append(service_result(name, unit_state(name), demand=name != 'NetworkManager.service'))
    if Path('/sys/class/bluetooth').exists() and any(Path('/sys/class/bluetooth').iterdir()):
        checks.append(service_result('bluetooth.service', unit_state('bluetooth.service')))
    else:
        checks.append({'name': 'Bluetooth', 'status': 'info', 'detail': 'no Bluetooth adapter detected; pairing not tested'})
    if graphical:
        for name in ['pipewire.service', 'pipewire-pulse.service', 'wireplumber.service',
                     'blacklight-wallpaper-sync.service', 'sysmon-widget.service']:
            checks.append(service_result(name, unit_state(name, user=True)))
        for name in ['xdg-desktop-portal.service', 'xdg-desktop-portal-gtk.service', 'gvfs-daemon.service']:
            checks.append(service_result(name, unit_state(name, user=True), demand=True))
        result = subprocess.run(['ps', '-u', str(os.getuid()), '-o', 'comm='],
                                capture_output=True, text=True, check=True, timeout=5)
        running = result.stdout.split()
        for label, names in [
            ('Network applet', ['nm-applet']),
            ('Authentication agent', ['polkit-mate-aut', 'polkit-gnome-au', 'xfce-polkit', 'lxpolkit', 'polkit-kde-auth']),
        ]:
            checks.append(process_check(label, names, running))
        if os.environ.get('XDG_SESSION_TYPE') != 'wayland':
            checks.append(process_check('Screen locker', ['xfce4-screensav', 'light-locker', 'xscreensaver'], running))
        if 'pulseaudio' in running and 'pipewire-pulse' in running:
            checks.append({'name': 'Audio providers', 'status': 'warn', 'detail': 'PulseAudio and PipeWire Pulse servers both running; inspect before changing either'})
        checks.append({'name': 'Audio/lock/hardware validation', 'status': 'info',
                       'detail': 'active services do not prove microphone, playback, lock/unlock or suspend/resume functionality'})
    else:
        checks.append({'name': 'Graphical session', 'status': 'info', 'detail': 'run from the logged-in desktop to check applets and user services'})
    candidates = [Path('/usr/bin/flameshot'), Path.home() / '.local/opt/flameshot/extracted/AppRun',
                  Path.home() / '.local/opt/flameshot/Flameshot.AppImage']
    usable = any(p.is_file() and os.access(p, os.X_OK) for p in candidates)
    checks.append({'name': 'Flameshot provider', 'status': 'ok' if usable else 'warn',
                   'detail': 'launcher provider found; use Print to test capture and Ctrl+V paste' if usable else 'install flameshot'})
    for label, command in [('Software updater', 'update-manager'), ('Software manager', 'gnome-software'),
                           ('Personal backup', 'deja-dup'), ('Driver settings', 'software-properties-gtk')]:
        checks.append({'name': label, 'status': 'ok' if shutil.which(command) else 'warn',
                       'detail': 'available' if shutil.which(command) else 'missing: ' + command})
    return {'checks': checks, 'warnings': sum(c['status'] == 'warn' for c in checks),
            'scope': 'read-only readiness checks; no network probes, service changes or hardware guarantees'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    report = collect()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        for check in report['checks']:
            print(f"{check['status'].upper():4} {check['name']}: {check['detail']}")
        print(f"\n{report['warnings']} readiness warning(s). {report['scope']}")
    return 1 if report['warnings'] else 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, subprocess.SubprocessError) as error:
        raise SystemExit('Galinia health check could not finish: ' + str(error)) from None
