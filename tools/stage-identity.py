#!/usr/bin/python3
"""Stage system branding without changing /etc, boot configuration or initramfs."""
import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def stage(output):
    from control import fresh
    import gi
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import GdkPixbuf
    output = fresh(output)
    # All destinations are relative to the staging root.
    theme = output / 'usr/share/plymouth/themes/galinia'
    shutil.copytree(ROOT / 'optional/plymouth/galinia', theme)
    logo = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(ROOT / 'docs/logo.svg'), 96, 96, True)
    logo.savev(str(theme / 'logo.png'), 'png', [], [])
    targets = {
        'optional/lightdm/Galinia-Greeter': 'usr/share/themes/Galinia-Greeter',
        'optional/lightdm/90-galinia.conf': 'etc/lightdm/lightdm-gtk-greeter.conf.d/90-galinia.conf',
        'home/.local/share/backgrounds/Galinia/galinia-dusk.png': 'usr/share/backgrounds/galinia-dusk.png',
        'docs/logo.svg': 'usr/share/pixmaps/galinia.svg',
    }
    for source, target in targets.items():
        dest = output / target
        dest.parent.mkdir(parents=True, exist_ok=True)
        if (ROOT / source).is_dir():
            shutil.copytree(ROOT / source, dest)
        else:
            shutil.copyfile(ROOT / source, dest)
    print(f'Staged Galinia system identity: {output}\nNo system settings changed. Read docs/IDENTITY.md before installing.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    stage(parser.parse_args().output)
