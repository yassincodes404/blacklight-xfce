#!/usr/bin/env python3
"""Read-only inspection, safe staging and allowlisted capture for Blacklight XFCE."""
import argparse, ast, hashlib, json, os, shutil, subprocess, tarfile
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT = Path(__file__).resolve().parents[1]

def fresh(path):
    path=path.expanduser().resolve()
    if path == Path.home() or (path.exists() and any(path.iterdir())):
        raise SystemExit('Choose a new or empty staging directory, never your live home.')
    path.mkdir(parents=True,exist_ok=True)
    return path

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def verify():
    failures=[]
    expected=json.loads((ROOT/'manifests/content.sha256.json').read_text())
    payloads = {str(p.relative_to(ROOT)) for d in ['home', 'assets', 'optional'] for p in (ROOT/d).rglob('*') if p.is_file() or p.is_symlink()}
    failures.extend('untracked payload: '+rel for rel in sorted(payloads-set(expected)))
    for rel,value in expected.items():
        path=ROOT/rel
        actual=('symlink:'+os.readlink(path)) if path.is_symlink() else digest(path) if path.is_file() else 'MISSING'
        if actual != value:failures.append(rel)
    for path in (ROOT/'home').rglob('*'):
        if path.is_symlink():
            if not path.exists():failures.append('broken alias: '+str(path.relative_to(ROOT)))
            continue
        if not path.is_file():continue
        if path.suffix=='.py':ast.parse(path.read_text(),filename=str(path))
        elif path.suffix=='.xml':ET.parse(path)
        elif path.suffix=='.json':json.loads(path.read_text())
        if path.name in ['cookies.sqlite','key4.db','logins.json','rclone.conf','known_hosts','authorized_keys']:
            failures.append('private data: '+str(path.relative_to(ROOT)))
    shortcuts=ET.parse(ROOT/'home/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-keyboard-shortcuts.xml')
    seen={}
    for node in shortcuts.findall("./property[@name='xfwm4']/property[@name='custom']/property"):
        action=node.get('value','')
        if action.endswith('_key'):
            if action in seen:failures.append('duplicate XFWM action: '+action)
            seen[action]=node.get('name')
    if failures:raise SystemExit('Verification failed:\n'+'\n'.join(failures))
    print(f'PASS: {len(expected)} tracked payloads verified; Python/XML/JSON parse; no private runtime files.')

def render(args):
    target=args.target_home.expanduser()
    if not target.is_absolute() or any(c in str(target) for c in '\n\r\x00"\\$`'):
        raise SystemExit('Target home must be absolute and contain no control, quote, backslash, dollar or backtick characters.')
    wallpaper=args.wallpaper.expanduser() if args.wallpaper else target/'.local/share/backgrounds/Galinia/galinia-dusk.png'
    if not wallpaper.is_absolute() or any(c in str(wallpaper) for c in '\n\r\x00'):
        raise SystemExit('Wallpaper must be an absolute single-line path.')
    out=fresh(args.output)
    shutil.copytree(ROOT/'home',out,dirs_exist_ok=True,symlinks=True)
    for archive in sorted((ROOT/'assets').glob('*.tar.xz')):
        with tarfile.open(archive) as tar:tar.extractall(out,filter='data')
    for path in out.rglob('*'):
        if not path.is_file() or path.is_symlink():continue
        try:text=path.read_text()
        except UnicodeDecodeError:continue
        if '@HOME@' not in text:continue
        if path.suffix=='.xml':
            tree=ET.ElementTree(ET.fromstring(text))
            for node in tree.iter():
                for key,value in list(node.attrib.items()):
                    node.set(key,value.replace('@HOME@',str(target)))
            tree.write(path,encoding='UTF-8',xml_declaration=True)
        elif path.suffix=='.json':
            # Replace inside decoded strings, preserving JSON escaping.
            def replace(value):
                if isinstance(value,str):return value.replace('@HOME@',str(target))
                if isinstance(value,list):return [replace(v) for v in value]
                if isinstance(value,dict):return {k:replace(v) for k,v in value.items()}
                return value
            path.write_text(json.dumps(replace(json.loads(text)),indent=2)+'\n')
        else:path.write_text(text.replace('@HOME@',str(target)))
    # Monitor connectors are discovered by the session daemon, not copied from the owner.
    shared=out/'.config/blacklight-rice/wallpaper'
    shared.write_text(str(wallpaper)+'\n')
    print(f'Staged home: {out}\nNo live settings changed. Read docs/RESTORE.md before copying anything.')

def capture(args):
    out=fresh(args.output);home=args.source_home.expanduser().resolve()
    for rel in json.loads((ROOT/'config/managed-files.json').read_text()):
        source=home/rel
        if not source.is_file():continue
        text=source.read_text()
        if source.suffix=='.xml':
            root=ET.fromstring(text)
            for parent in root.iter():
                for child in list(parent):
                    if child.get('name') in ['known-items','known-legacy-items','known-players','persistent-players','last','last-settings-migration-version']:
                        parent.remove(child)
            ET.indent(root);text=ET.tostring(root,encoding='unicode')+'\n'
        text=text.replace(str(home),'@HOME@')
        dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text)
    print(f'Allowlisted text configuration captured to {out}. Review the diff; assets and secrets were not copied.')

def doctor():
    for name in ['xfconf-query','xfce4-panel','xfwm4','xfdesktop','python3','gtk-update-icon-cache','systemctl','xcursorgen']:
        print(f'{name:24} {shutil.which(name) or "MISSING"}')
    print('Session:',os.environ.get('XDG_SESSION_TYPE','unknown'))
    print('DISPLAY:',os.environ.get('DISPLAY','unset'))
    print('Optional NVIDIA metrics:',bool(shutil.which('nvidia-smi')))
    print('External artwork and inherited cursor roles: see docs/ASSETS.md')

def main():
    p=argparse.ArgumentParser(description=__doc__);commands=p.add_subparsers(dest='command',required=True)
    commands.add_parser('verify');commands.add_parser('doctor')
    r=commands.add_parser('render');r.add_argument('--output',type=Path,required=True);r.add_argument('--target-home',type=Path,default=Path.home());r.add_argument('--monitor',help=argparse.SUPPRESS);r.add_argument('--wallpaper',type=Path)
    c=commands.add_parser('capture');c.add_argument('--output',type=Path,required=True);c.add_argument('--source-home',type=Path,default=Path.home())
    a=p.parse_args()
    if a.command=='verify':verify()
    elif a.command=='doctor':doctor()
    elif a.command=='render':render(a)
    else:capture(a)

if __name__=='__main__':main()
