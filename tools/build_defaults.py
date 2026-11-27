#!/usr/bin/python3
"""Build the preview defaults .deb without root; does not build a bootable ISO."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import control
import install

ROOT = Path(__file__).resolve().parents[1]


def copy(source, dest, executable=False):
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
    dest.chmod(0o755 if executable else 0o644)


def stage_package(root, version):
    if not re.fullmatch(r'[0-9][A-Za-z0-9.+~]*', version):
        raise ValueError('Use a Debian version beginning with a digit.')
    source = ROOT / 'packaging/galinia-defaults'
    payload = root / 'usr/share/galinia'
    shutil.copytree(ROOT / 'home', payload / 'home', symlinks=True, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    for name in ['first-launch.json', 'retired-files.json']:
        copy(ROOT / 'config' / name, payload / 'config' / name)
    for name in ['control.py', 'install.py']:
        copy(ROOT / 'tools' / name, root / 'usr/lib/galinia' / name)
    copy(source / 'initialize-home', root / 'usr/lib/galinia/initialize-home', executable=True)
    copy(source / '45galinia-defaults', root / 'etc/X11/Xsession.d/45galinia-defaults')
    copy(source / '90-galinia.cfg', root / 'etc/default/grub.d/90-galinia.cfg')
    copy(source / 'galinia.desktop', root / 'usr/share/xsessions/galinia.desktop')
    marker = root / 'etc/skel/.config/galinia/initialize'
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(version + '\n')
    release = root / 'etc/galinia-release'
    release.write_text('NAME="Galinia OS"\nVERSION="' + version + '"\nBASE="Xubuntu 26.04"\nSTATUS="development preview"\n')
    lightdm = root / 'etc/lightdm/lightdm.conf.d/60-galinia-session.conf'
    lightdm.parent.mkdir(parents=True, exist_ok=True)
    lightdm.write_text('[Seat:*]\nuser-session=galinia\ngreeter-session=lightdm-gtk-greeter\n')
    spec = importlib.util.spec_from_file_location('stage_identity', ROOT / 'tools/stage-identity.py')
    identity = importlib.util.module_from_spec(spec); spec.loader.exec_module(identity)
    with tempfile.TemporaryDirectory(prefix='galinia-brand-') as tmp:
        staged = Path(tmp) / 'identity'
        identity.stage(staged)
        shutil.copytree(staged, root, dirs_exist_ok=True)
    documentation = root / 'usr/share/doc/galinia-defaults'
    copy(ROOT / 'LICENSE', documentation / 'copyright')
    copy(ROOT / 'NOTICE', documentation / 'NOTICE')
    shutil.copytree(ROOT / 'LICENSES', documentation / 'licenses')
    for name in ['FIRST-LAUNCH.md', 'IDENTITY.md', 'EVERYDAY.md', 'MEMORY.md', 'SHORTCUTS.md', 'ASSETS.md', 'CONTROL-CENTER.md']:
        copy(ROOT / 'docs' / name, documentation / name)
    # Let upstream packages own shared fonts/icons; avoid overwriting their files.
    dependencies = sorted(set(install.packages() + ['lightdm', 'lightdm-gtk-greeter', 'plymouth', 'grub-common',
                                                   'papirus-icon-theme', 'fonts-jetbrains-mono']))
    debian = root / 'DEBIAN'
    debian.mkdir()
    size = sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink()) // 1024
    (debian / 'control').write_text(
        f'Package: galinia-defaults\nVersion: {version}\nArchitecture: all\n'
        'Maintainer: Galinia Contributors <207205991+yassincodes404@users.noreply.github.com>\nSection: x11\nPriority: optional\n'
        f'Installed-Size: {size}\nDepends: ' + ', '.join(dependencies) + '\n'
        'Homepage: https://github.com/yassincodes404/blacklight-xfce\n'
        'Description: Galinia desktop and boot identity development preview\n'
        ' Defaults for fresh XFCE accounts, shared assets, login styling and boot\n'
        ' branding. Boot activation is performed by the ISO customization recipe.\n')
    configs = sorted('/' + str(p.relative_to(root)) for p in (root / 'etc').rglob('*') if p.is_file())
    (debian / 'conffiles').write_text('\n'.join(configs) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--version', default='0.1.0~dev')
    args = parser.parse_args()
    control.verify()
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    package = output / f'galinia-defaults_{args.version}_all.deb'
    if package.exists():
        raise ValueError('Output already exists; choose a new version/output directory.')
    with tempfile.TemporaryDirectory(prefix='galinia-package-') as tmp:
        root = Path(tmp) / 'root'; root.mkdir()
        stage_package(root, args.version)
        subprocess.run(['nice', '-n', '10', 'dpkg-deb', '--build', '--root-owner-group', '--threads-max=2', '-Zxz', str(root), str(package)], check=True)
    sha = hashlib.sha256(package.read_bytes()).hexdigest()
    package.with_suffix('.deb.sha256').write_text(sha + '  ' + package.name + '\n')
    print('Built defaults package:', package)
    print('This is a .deb preview, not a bootable ISO. See iso/README.md.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise SystemExit('Galinia package: ' + str(error)) from None
