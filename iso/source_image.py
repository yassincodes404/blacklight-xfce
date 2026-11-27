#!/usr/bin/env python3
"""Fetch a pinned official ISO, authenticate its checksum, and inspect its layers."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parent


def run(args):
    return subprocess.run([str(a) for a in args], check=True, text=True, capture_output=True).stdout


def fetch(url, dest):
    if dest.exists():
        return
    partial = dest.with_name(dest.name + '.partial')
    with urllib.request.urlopen(url, timeout=120) as response, partial.open('wb') as output:
        shutil.copyfileobj(response, output, 1024 * 1024)
    partial.replace(dest)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    lock = json.loads((ROOT / 'source.lock.json').read_text())
    output, report = args.output.resolve(), args.report.resolve()
    output.mkdir(parents=True, exist_ok=True); report.mkdir(parents=True, exist_ok=True)
    for name in ['SHA256SUMS', 'SHA256SUMS.gpg']:
        fetch(lock['url'] + name, output / name)
    verification = subprocess.run(['gpgv', '--keyring', '/usr/share/keyrings/ubuntu-archive-keyring.gpg',
                                  str(output / 'SHA256SUMS.gpg'), str(output / 'SHA256SUMS')],
                                 check=True, capture_output=True, text=True)
    (report / 'signature.txt').write_text(verification.stderr)
    entries = {row.split()[1].lstrip('*'): row.split()[0] for row in (output / 'SHA256SUMS').read_text().splitlines() if row.strip()}
    if entries.get(lock['filename']) != lock['sha256']:
        raise ValueError('Pinned checksum does not match signed upstream metadata')
    iso = output / lock['filename']
    print('Downloading verified-source candidate:', lock['filename'], flush=True)
    fetch(lock['url'] + lock['filename'], iso)
    if digest(iso) != lock['sha256']:
        raise ValueError('ISO checksum mismatch')
    shutil.copy2(ROOT / 'source.lock.json', report / 'source.lock.json')
    for relative in ['casper', 'boot/grub/grub.cfg', '.disk/info']:
        dest = output / relative
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            run(['xorriso', '-osirrox', 'on', '-indev', iso, '-extract', '/' + relative, dest])
    shutil.copy2(output / 'casper/install-sources.yaml', report / 'install-sources.yaml')
    shutil.copy2(output / 'boot/grub/grub.cfg', report / 'grub.cfg')
    (report / 'boot-layout.txt').write_text(run(['xorriso','-indev',iso,'-report_el_torito','plain','-report_system_area','plain']))
    for layer in sorted((output / 'casper').glob('*.squashfs')):
        text = run(['unsquashfs', '-ll', layer])
        (report / (layer.name + '.files.txt')).write_text(text)
    print('Source image authenticated and layer evidence recorded.', flush=True)


if __name__ == '__main__':
    main()
