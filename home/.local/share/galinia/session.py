"""Own graphical services for one XFCE login; wait on its pidfd, without polling."""
import argparse
import fcntl
import os
from pathlib import Path
import select
import shlex
import signal
import subprocess
import sys

from preferences import load

DISPLAY_VARIABLES = ('DISPLAY', 'XAUTHORITY', 'WAYLAND_DISPLAY', 'LABWC_PID',
                     'XDG_SESSION_TYPE', 'XDG_CURRENT_DESKTOP', 'XCURSOR_THEME',
                     'XCURSOR_SIZE', 'XCURSOR_PATH', 'QT_QPA_PLATFORMTHEME')
UNITS = ('galinia-audio.service', 'sysmon-widget.service',
         'blacklight-wallpaper-sync.service', 'galinia-search.service')
PORTALS = ('xdg-desktop-portal.service', 'xdg-desktop-portal-gtk.service',
           'xdg-desktop-portal-wlr.service')


def run(*args, check=True):
    return subprocess.run(args, check=check, text=True, capture_output=True, timeout=30)


def systemctl(*args, check=True):
    return run('systemctl', '--user', *args, check=check)


def import_environment(env):
    present = [key for key in DISPLAY_VARIABLES if key in env]
    absent = [key for key in DISPLAY_VARIABLES if key not in env]
    if present:
        systemctl('import-environment', *present)
        # D-Bus activation has its own environment, distinct from systemd's.
        run('dbus-update-activation-environment', '--systemd', *present)
    if absent:
        systemctl('unset-environment', *absent)
        # D-Bus has no unset API; clear stale display values explicitly.
        run('dbus-update-activation-environment', *[key + '=' for key in absent])


def start_services(env, preferences, adopt=False):
    import_environment(env)
    systemctl('start', 'galinia-session.target')
    errors = []

    def attempt(label, function, *args, **kwargs):
        try:
            function(*args, **kwargs)
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            errors.append(label + ': ' + str(error))

    # At login, discard portal processes associated with the previous display.
    if not adopt:
        attempt('stop old portals', systemctl, 'stop', PORTALS[0], PORTALS[1])
        systemctl('stop', PORTALS[2], check=False)
    attempt('start GTK portal', systemctl, 'start', 'xdg-desktop-portal-gtk.service')
    if env.get('XDG_SESSION_TYPE') == 'wayland':
        attempt('start Wayland portal', systemctl, 'start', 'xdg-desktop-portal-wlr.service')
    attempt('start portal broker', systemctl, 'start', 'xdg-desktop-portal.service')
    for unit in UNITS:
        enabled = not ((unit == 'galinia-audio.service' and not preferences['audio_enabled'])
                       or (unit == 'sysmon-widget.service' and not preferences['monitor_enabled']))
        if enabled:
            systemctl('reset-failed', unit, check=False)
        attempt('failed to start ' + unit, systemctl,
                ('start' if adopt else 'restart') if enabled else 'stop', unit)
    if env.get('XDG_SESSION_TYPE') == 'wayland':
        attempt('Wayland locking', configure_lock, adopt)
    else:
        attempt('stop Wayland idle handler', systemctl, 'stop', 'galinia-wayland-idle.service')
    if errors:
        raise RuntimeError('; '.join(errors))


def configure_lock(adopt=False):
    # Missing PAM-enabled packages must stay visible.
    run(str(Path.home() / '.local/bin/galinia-lock'), '--check')
    current = run('xfconf-query', '-c', 'xfce4-session', '-p', '/general/LockCommand', check=False)
    command = shlex.quote(str(Path.home() / '.local/bin/galinia-lock'))
    if current.returncode == 0 and current.stdout.strip() not in ('', command):
        raise RuntimeError('Custom XFCE LockCommand retained; review it for Wayland compatibility')
    flags = ('--create', '--type', 'string') if current.returncode else ()
    run('xfconf-query', '-c', 'xfce4-session', '-p', '/general/LockCommand', *flags, '--set', command)
    systemctl('start' if adopt else 'restart', 'galinia-wayland-idle.service')


def session_pid():
    response = run('busctl', '--user', 'call', 'org.freedesktop.DBus',
                   '/org/freedesktop/DBus', 'org.freedesktop.DBus',
                   'GetConnectionUnixProcessID', 's', 'org.xfce.SessionManager').stdout.split()
    if len(response) != 2 or response[0] != 'u':
        raise RuntimeError('Cannot identify XFCE session owner')
    pid = int(response[1]); proc = Path('/proc') / str(pid)
    if proc.stat().st_uid != os.getuid() or (proc / 'comm').read_text().strip() != 'xfce4-session':
        raise RuntimeError('Unexpected XFCE session owner')
    return pid


def wait_for_exit(fd):
    select.select([fd], [], [])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true', help='refresh services without owning their lifetime (recovery/testing)')
    parser.add_argument('--adopt', action='store_true', help='attach to a running login without restarting healthy services')
    args = parser.parse_args()
    if args.once:
        start_services(os.environ, load(), adopt=args.adopt)
        return
    runtime = Path(os.environ['XDG_RUNTIME_DIR'])
    if runtime.stat().st_uid != os.getuid():
        raise RuntimeError('Runtime directory is not owned by this user')
    with (runtime / 'galinia-session.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another Galinia session owner is still running')
        pid = session_pid()
        fd = os.pidfd_open(pid)
        try:
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, lambda *_: sys.exit(0))
            try:
                start_services(os.environ, load(), adopt=args.adopt)
            except (OSError, RuntimeError, subprocess.SubprocessError) as error:
                # Keep lifetime ownership even if one optional provider is missing.
                print('Galinia session startup needs attention:', error, file=sys.stderr, flush=True)
            wait_for_exit(fd)
        finally:
            systemctl('stop', 'galinia-session.target', check=False)
            os.close(fd)


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print('Galinia session:', error, file=sys.stderr)
        raise SystemExit(1)
