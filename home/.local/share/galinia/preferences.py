"""Validated user preferences and reversible desktop controls; no GTK dependency."""
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

DEFAULTS = {'version': 1, 'accent_mode': 'wallpaper', 'fixed_accent': '#efb579',
            'monitor_enabled': True, 'panel_size': 36, 'app_profiles': {}}
PRIORITIES = {
    'normal': ['--property=CPUWeight=100'],
    'background': ['--property=CPUWeight=20', '--property=Nice=10'],
    'interactive': ['--property=CPUWeight=200'],
}


def config_path():
    return Path(os.environ.get('XDG_CONFIG_HOME', str(Path.home() / '.config'))) / 'galinia/preferences.json'


def contrast(a, b):
    def luminance(color):
        channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
        return sum(v * w for v, w in zip(linear, (.2126, .7152, .0722)))
    light, dark = sorted((luminance(a), luminance(b)), reverse=True)
    return (light + .05) / (dark + .05)


def validate(data):
    if not isinstance(data, dict) or set(data) - set(DEFAULTS):
        raise ValueError('Unknown or malformed Galinia preferences.')
    result = copy.deepcopy(DEFAULTS)
    result.update(data)
    if type(result['version']) is not int or result['version'] != 1 or result['accent_mode'] not in ('wallpaper', 'fixed'):
        raise ValueError('Unsupported preference version or accent mode.')
    color = result['fixed_accent']
    if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        raise ValueError('Choose a six-digit accent color.')
    if contrast(color, '#242429') < 4.5:
        raise ValueError('Choose a brighter accent so text and controls remain readable.')
    result['fixed_accent'] = color.lower()
    if type(result['monitor_enabled']) is not bool or type(result['panel_size']) is not int or not 28 <= result['panel_size'] <= 48:
        raise ValueError('Panel size must be 28–48; monitor visibility must be true or false.')
    if not isinstance(result['app_profiles'], dict) or len(result['app_profiles']) > 1000:
        raise ValueError('Invalid application priority settings.')
    for key, value in result['app_profiles'].items():
        if not isinstance(key, str) or not key.endswith('.desktop') or any(c in key for c in '\n\r\x00/') or value not in PRIORITIES:
            raise ValueError('Invalid application ID or priority.')
    return result


def load(path=None):
    path = path or config_path()
    return validate(json.loads(path.read_text()) if path.exists() else {})


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.preferences-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, indent=2)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save(data, path=None):
    path = path or config_path()
    validated = validate(data)
    previous = load(path)
    if validated == previous:
        return
    atomic_write(path.with_name('preferences.previous.json'), previous)
    atomic_write(path, validated)


def apply_desktop(data, path=None, run=None):
    path = path or config_path()
    run = run or (lambda command: subprocess.run(command, check=True, capture_output=True, text=True, timeout=10))
    previous, new = load(path), validate(data)
    completed = []
    try:
        if new['panel_size'] != previous['panel_size']:
            current = run(['xfconf-query', '-c', 'xfce4-panel', '-p', '/panels/panel-1/size'])
            actual_size = int(current.stdout.strip())
            prefix = ['xfconf-query', '-c', 'xfce4-panel', '-p', '/panels/panel-1/size', '-s']
            run(prefix + [str(new['panel_size'])])
            completed.append(prefix + [str(actual_size)])
        if new['monitor_enabled'] != previous['monitor_enabled']:
            state = run(['systemctl', '--user', 'show', 'sysmon-widget.service', '--property=ActiveState', '--value']).stdout.strip()
            if state not in ('active', 'inactive', 'failed'):
                raise ValueError('Could not determine the monitor service state.')
            run(['systemctl', '--user', 'start' if new['monitor_enabled'] else 'stop', 'sysmon-widget.service'])
            completed.append(['systemctl', '--user', 'start' if state == 'active' else 'stop', 'sysmon-widget.service'])
        save(new, path)
    except Exception:
        for command in reversed(completed):
            try:
                run(command)
            except Exception as error:
                print('Galinia preference rollback needs attention:', error, file=sys.stderr)
        raise


def undo(path=None, run=None):
    path = path or config_path()
    previous = path.with_name('preferences.previous.json')
    if not previous.exists():
        raise ValueError('There is no saved change to undo.')
    desired = validate(json.loads(previous.read_text()))
    apply_desktop(desired, path, run)
    previous.unlink(missing_ok=True)


def resource_flags(app_id, data=None):
    data = load() if data is None else validate(data)
    return list(PRIORITIES[data['app_profiles'].get(app_id, 'normal')])


def apply_palette(palette, data):
    data = validate(data)
    result = dict(palette)
    if data['accent_mode'] == 'fixed':
        color = data['fixed_accent']
        rgb = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
        soft = [round(value * .82) for value in rgb]
        result.update(accent_hex=color, accent_rgb=rgb, accent_soft_rgb=soft,
                      accent_soft_hex='#' + ''.join(f'{v:02x}' for v in soft), is_mono=False)
        result['sel_fg_hex'] = '#11151d' if contrast(color, '#11151d') >= contrast(color, '#ffffff') else '#ffffff'
    return result


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'get':
        print(json.dumps(load()[sys.argv[2]]))
    else:
        print(json.dumps(load(), indent=2))
