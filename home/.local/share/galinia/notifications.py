"""Typed access to XFCE notification preferences; no private configuration copy."""
# key: (Xfconf type, upstream default, accepted range or choices)
SETTINGS = {
    'do-not-disturb': ('bool', False, None),
    'gauge-ignores-dnd': ('bool', True, None),
    'notify-location': ('string', 'top-right', ('top-right', 'top-left', 'bottom-right', 'bottom-left', 'top-center', 'bottom-center')),
    'show-notifications-on': ('string', 'active-monitor', ('active-monitor', 'primary-monitor', 'all-monitors')),
    'expire-timeout-enabled': ('bool', True, None),
    'expire-timeout': ('int', 10, (1, 120)),
    'expire-timeout-allow-override': ('bool', True, None),
    'mute-sounds': ('bool', False, None),
    'do-fadeout': ('bool', True, None),
    'do-slideout': ('bool', False, None),
    'notification-log': ('bool', False, None),
    'log-max-size-enabled': ('bool', True, None),
    'log-max-size': ('uint', 1000, (10, 10000)),
}


def validate(key, value):
    kind, _, limits = SETTINGS[key]
    if kind == 'bool':
        valid = type(value) is bool
    elif kind in ('int', 'uint'):
        valid = type(value) is int and limits[0] <= value <= limits[1]
    else:
        valid = value in limits and isinstance(value, str)
    if not valid:
        raise ValueError('Invalid notification setting: ' + key)
    return value


class Settings:
    def __init__(self, channel):
        self.channel = channel

    def read(self, key):
        kind, default, _ = SETTINGS[key]
        return getattr(self.channel, 'get_' + kind)('/' + key, default)

    def write(self, key, value):
        value = validate(key, value)
        # Bound future history before enabling logging; never clear existing data.
        if key == 'notification-log' and value:
            self.write('log-max-size-enabled', True)
        kind = SETTINGS[key][0]
        if not getattr(self.channel, 'set_' + kind)('/' + key, value):
            raise RuntimeError('XFCE refused to save ' + key)


def theme_css(palette):
    """Small native GTK theme; uses the desktop accent without backdrop blur."""
    accent = palette['accent_hex']
    return f'''/* Galinia notification theme, generated with the desktop palette. */
#XfceNotifyWindow {{
    background-image: none;
    background-color: #151b24;
    color: #eef2f7;
    border: 1px solid #354052;
    border-left: 3px solid {accent};
    border-radius: 12px;
    padding: 14px;
    font-family: "Noto Sans", sans-serif;
    font-size: 13px;
}}
#XfceNotifyWindow label, #XfceNotifyWindow image {{ color: #eef2f7; }}
#XfceNotifyWindow label#summary {{ font-weight: bold; font-size: 14px; }}
#XfceNotifyWindow label#body {{ color: #cbd3df; }}
#XfceNotifyWindow button {{
    background-image: none;
    background-color: #232d3c;
    color: #eef2f7;
    border: 1px solid #43516a;
    border-radius: 7px;
    box-shadow: none;
    padding: 6px 10px;
}}
#XfceNotifyWindow button:hover {{ background-color: #344258; }}
#XfceNotifyWindow button:focus {{ border-color: {accent}; }}
#XfceNotifyWindow progressbar trough {{ background-color: #354052; border-radius: 4px; }}
#XfceNotifyWindow progressbar progress {{ background-color: {accent}; border-radius: 4px; }}
'''
