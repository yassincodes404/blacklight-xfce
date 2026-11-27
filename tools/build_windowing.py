#!/usr/bin/env python3
"""Build an ABI-matched qualification .deb with a shared icon resolver fix.

Run on an isolated Ubuntu 26.04 amd64 builder with native development headers.
Does not install anything or replace the builder's libraries.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT=Path(__file__).resolve().parents[1]


def run(args,**kw):
    print('+',' '.join(map(str,args)),flush=True)
    return subprocess.run(list(map(str,args)),check=True,**kw)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    lock=json.loads((ROOT/'packaging/windowing/source.json').read_text())
    version=lock['ubuntu_package_version']+'galinia1'
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=True)
    result=output/('libxfce4windowing-0-0_'+version+'_amd64.deb')
    if result.exists():raise ValueError('Refusing to replace an existing package')
    with tempfile.TemporaryDirectory(prefix='galinia-windowing-') as tmp:
        work=Path(tmp);archive=work/'source.tar.bz2'
        archive.write_bytes(urllib.request.urlopen(lock['url'],timeout=60).read())
        if hashlib.sha256(archive.read_bytes()).hexdigest()!=lock['sha256']:raise ValueError('Source checksum mismatch')
        with tarfile.open(archive) as tar:tar.extractall(work,filter='data')
        source=work/('libxfce4windowing-'+lock['version'])
        private=source/'libxfce4windowing/libxfce4windowing-private.c'
        old=private.read_text();start=old.index('GDesktopAppInfo *\n_xfw_g_desktop_app_info_get(');end=old.index('\nGdkPixbuf *\n_xfw_gicon_load',start)
        private.write_text(old[:start]+(ROOT/'packaging/windowing/resolve-app.c').read_text()+'\n'+old[end:])
        run(['python3','-m','unittest','discover','-s','tests','-p','test_icon_resolver.py','-v'],cwd=ROOT)
        run(['./configure','--prefix=/usr','--libdir=/usr/lib/x86_64-linux-gnu','--enable-x11','--enable-wayland','--disable-introspection','--disable-gtk-doc'],cwd=source)
        run(['make','-j2'],cwd=source)
        # Keep the distro's complete package layout, dependencies, triggers and license.
        download=work/'official';download.mkdir()
        run(['apt-get','download','libxfce4windowing-0-0='+lock['ubuntu_package_version']],cwd=download)
        original=list(download.glob('*.deb'))
        if len(original)!=1:raise ValueError('Expected one original distribution package')
        package=work/'package';run(['dpkg-deb','--raw-extract',original[0],package])
        library=source/'libxfce4windowing/.libs/libxfce4windowing-0.so.0.0.0'
        target=package/'usr/lib/x86_64-linux-gnu/libxfce4windowing-0.so.0.0.0'
        if not library.is_file() or not target.is_file():raise ValueError('Unexpected shared-library layout')
        shutil.copy2(library,target);run(['strip','--strip-unneeded',target])
        control=package/'DEBIAN/control';text=control.read_text()
        text=re.sub(r'^Version:.*$', 'Version: '+version,text,flags=re.M)
        oldmaint=re.search(r'^Maintainer: (.*)$',text,re.M).group(1)
        text=re.sub(r'^(Original-Maintainer|Origin):.*\n?', '', text, flags=re.M)
        text=re.sub(r'^Maintainer:.*$','Maintainer: Galinia Contributors <207205991+yassincodes404@users.noreply.github.com>\nOriginal-Maintainer: '+oldmaint,text,flags=re.M)
        control.write_text(text+'\nOrigin: Galinia\n')
        doc=package/'usr/share/doc/libxfce4windowing-0-0/galinia-resolver';doc.mkdir(parents=True)
        for name in ['source.json','resolve-app.c']:shutil.copy2(ROOT/'packaging/windowing'/name,doc/name)
        sums=[]
        for p in sorted(package.rglob('*')):
            if p.is_file() and not p.is_symlink() and not p.is_relative_to(package/'DEBIAN'):
                sums.append(hashlib.md5(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(package)))
        (package/'DEBIAN/md5sums').write_text('\n'.join(sums)+'\n')
        run(['dpkg-deb','--build','--root-owner-group',package,result])
    result.with_suffix('.deb.sha256').write_text(hashlib.sha256(result.read_bytes()).hexdigest()+'  '+result.name+'\n')
    print('Built qualification package:',result)


if __name__=='__main__':main()
