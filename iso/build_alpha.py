#!/usr/bin/env python3
"""Build an unqualified alpha on an isolated root-capable Linux image builder.

Preserves the two source layers, customizing installed and live roots separately,
then reconstructs their delta including deletions. Never run on an owner rootfs.
"""
import argparse
from contextlib import contextmanager, ExitStack
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import urllib.request

HERE = Path(__file__).resolve().parent


def run(*args, **kwargs):
    print('+', ' '.join(map(str,args)), flush=True)
    return subprocess.run(list(map(str,args)), check=True, **kwargs)


@contextmanager
def mounted(arguments, dest):
    dest.mkdir(parents=True, exist_ok=True)
    run('mount', *arguments, dest)
    try:
        yield dest
    finally:
        run('umount', '-R', dest)


def manifest(root):
    return subprocess.check_output(['chroot',str(root),'dpkg-query','-W','-f=${Package} ${Version}\n'],text=True)


def prepare_browser_repo(root):
    # The pinned minimal source has no Firefox payload. Use the same maintained
    # native Mozilla package route as the reference machine, with scoped trust.
    fingerprint='35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3'
    with urllib.request.urlopen('https://packages.mozilla.org/apt/repo-signing-key.gpg',timeout=60) as response:
        key=response.read()
    keyring=root/'etc/apt/keyrings/packages.mozilla.org.asc';keyring.parent.mkdir(parents=True,exist_ok=True);keyring.write_bytes(key)
    with tempfile.TemporaryDirectory(prefix='galinia-public-key-') as home:
        listing=subprocess.check_output(['gpg','--homedir',home,'--batch','--show-keys','--with-colons',str(keyring)],text=True)
    fingerprints=[row.split(':')[9] for row in listing.splitlines() if row.startswith('fpr:')]
    if not fingerprints or fingerprints[0]!=fingerprint:
        raise ValueError('Mozilla APT signing key fingerprint mismatch')
    (root/'etc/apt/sources.list.d/galinia-mozilla.sources').write_text(
        'Types: deb\nURIs: https://packages.mozilla.org/apt\nSuites: mozilla\nComponents: main\n'
        'Signed-By: /etc/apt/keyrings/packages.mozilla.org.asc\n')
    (root/'etc/apt/preferences.d/galinia-firefox').write_text(
        'Package: firefox firefox-l10n-*\nPin: origin packages.mozilla.org\nPin-Priority: 1000\n')


def customize(root, package, media):
    prepare_browser_repo(root)
    if (root/'etc/casper.conf').is_file():
        with (root/'etc/casper.conf').open('a') as stream:
            stream.write('\nexport USERNAME="galinia"\nexport USERFULLNAME="Galinia live session"\nexport HOST="galinia"\nexport FLAVOUR="Galinia"\n')
    policy = root / 'usr/sbin/policy-rc.d'
    if policy.exists():
        raise ValueError('Unexpected service policy in original image')
    resolv = root / 'etc/resolv.conf'
    saved = root / 'etc/resolv.conf.galinia-build-original'
    if resolv.exists() or resolv.is_symlink():
        resolv.rename(saved)
    shutil.copyfile('/etc/resolv.conf',resolv)
    policy.write_text('#!/bin/sh\nexit 101\n');policy.chmod(0o755)
    shutil.copy2(package,root/'tmp/galinia-defaults.deb')
    shutil.copy2(HERE/'customize.sh',root/'tmp/galinia-customize.sh')
    try:
        with ExitStack() as stack:
            stack.enter_context(mounted(['--bind',media],root/'cdrom'))
            for name in ['dev','sys']:
                stack.enter_context(mounted(['--rbind','/'+name],root/name))
                run('mount','--make-rslave',root/name)
            stack.enter_context(mounted(['-t','proc','proc'],root/'proc'))
            run('chroot',root,'/usr/bin/env','DEBIAN_FRONTEND=noninteractive','GALINIA_IMAGE_BUILD=1',
                'sh','/tmp/galinia-customize.sh','/tmp/galinia-defaults.deb')
    finally:
        policy.unlink(missing_ok=True)
        resolv.unlink(missing_ok=True)
        if saved.exists() or saved.is_symlink():
            saved.rename(resolv)
        (root/'tmp/galinia-defaults.deb').unlink(missing_ok=True)
        (root/'tmp/galinia-customize.sh').unlink(missing_ok=True)
    run('chroot',root,'apt-get','clean')
    if not (root/'usr/lib/firefox/firefox').is_file():
        raise ValueError('The native Firefox payload is missing; a transitional package is insufficient')
    (root/'etc/machine-id').write_text('')
    (root/'var/lib/systemd/random-seed').unlink(missing_ok=True)
    for key in (root/'etc/ssh').glob('ssh_host_*'):
        key.unlink()
    for log in (root/'var/log').rglob('*'):
        if log.is_file() and not log.is_symlink():
            log.write_bytes(b'')


def whiteouts(base, live, delta):
    # Only topmost deleted paths need a whiteout; do not follow symlinks.
    for directory, dirs, files in os.walk(base, followlinks=False):
        relative = Path(directory).relative_to(base)
        for name in dirs[:] + files:
            rel = relative/name
            other = live/rel
            if not other.exists() and not other.is_symlink():
                if name in dirs:
                    dirs.remove(name)
                target=delta/rel
                target.parent.mkdir(parents=True,exist_ok=True)
                os.mknod(target, stat.S_IFCHR | 0o000, os.makedev(0,0))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--package',type=Path,required=True)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--phase',choices=['all','prepare','installed','live','finish'],default='all')
    args=parser.parse_args()
    if os.geteuid()!=0 or os.environ.get('GALINIA_IMAGE_BUILD')!='1':
        raise ValueError('Requires GALINIA_IMAGE_BUILD=1 on an isolated root-capable image builder')
    source,work,out=args.source.resolve(),args.work.resolve(),args.output.resolve()
    if args.phase in ('all','prepare') and work.exists():
        raise ValueError('Use a new empty work path')
    if args.phase not in ('all','prepare') and not (work/'.prepared').is_file():
        raise ValueError('Prepare this image before continuing')
    lock=json.loads((HERE/'source.lock.json').read_text())
    iso=source/lock['filename']
    from source_image import digest
    if digest(iso)!=lock['sha256']:
        raise ValueError('Unverified source image')
    if set(p.name for p in (source/'casper').glob('*.squashfs')) != {'minimal.squashfs','minimal.live.squashfs'}:
        raise ValueError('Only the pinned two-layer minimal image is supported')
    out.mkdir(parents=True,exist_ok=True)
    casper=work/'casper';base,live=work/'base',work/'live'
    if args.phase in ('all','prepare'):
        work.mkdir();shutil.copytree(source/'casper',casper)
        for root in [base,live]:root.mkdir()
        with mounted(['-o','loop,ro',source/'casper/minimal.squashfs'],work/'source-base') as oldbase:
            with mounted(['-o','loop,ro',source/'casper/minimal.live.squashfs'],work/'source-live') as oldlive:
                with mounted(['-t','overlay','overlay','-o',f'lowerdir={oldlive}:{oldbase}'],work/'source-merged') as merged:
                    run('rsync','-aHAX',str(oldbase)+'/',str(base)+'/')
                    run('rsync','-aHAX',str(merged)+'/',str(live)+'/')
        (work/'.prepared').write_text(digest(args.package))
        if args.phase=='prepare':return
    if (work/'.prepared').read_text()!=digest(args.package):
        raise ValueError('Defaults package changed after preparation')
    for phase,root in [('installed',base),('live',live)]:
        if args.phase not in ('all',phase):continue
        marker=work/('.'+phase)
        if marker.exists():raise ValueError('This phase already completed; do not apply twice')
        with mounted(['-o','loop,ro',iso],work/'source-media') as media:
            customize(root,args.package.resolve(),media)
        marker.write_text('complete\n')
    if args.phase in ('installed','live'):return
    if not all((work/('.'+phase)).is_file() for phase in ['installed','live']):
        raise ValueError('Both installed and live root customization must succeed before packing')
    # Match the signed source kernel byte-for-byte, not just by its version text.
    original_kernel_hash=digest(casper/'vmlinuz')
    kernels=[path for path in (live/'boot').glob('vmlinuz-*') if path.is_file() and digest(path)==original_kernel_hash]
    if len(kernels)!=1:
        raise ValueError('Cannot identify the installed kernel matching the signed source payload')
    kernel_version=kernels[0].name.removeprefix('vmlinuz-')
    initrd=live/('boot/initrd.img-'+kernel_version)
    if not initrd.is_file():
        raise ValueError('No rebuilt initramfs matching the original signed live kernel')
    shutil.copy2(initrd,casper/'initrd')
    base_manifest,live_manifest=manifest(base),manifest(live)
    (casper/'minimal.manifest').write_text(base_manifest)
    (casper/'minimal.manifest.full').write_text(base_manifest)
    (casper/'minimal.live.manifest.full').write_text(live_manifest)
    base_entries=set(base_manifest.splitlines())
    (casper/'minimal.live.manifest').write_text('\n'.join(x for x in live_manifest.splitlines() if x not in base_entries)+'\n')
    delta=work/'delta';delta.mkdir()
    run('rsync','-aHAXc','--compare-dest='+str(base),str(live)+'/',str(delta)+'/')
    whiteouts(base,live,delta)
    # Whiteout creation changes parent directory mtimes. Restore all directory
    # metadata without deleting the new tombstones before validating the merge.
    run('rsync','-aHAXc','--compare-dest='+str(base),str(live)+'/',str(delta)+'/')
    with mounted(['-t','overlay','overlay','-o',f'lowerdir={delta}:{base}'],work/'verify-live') as rebuilt:
        differences=subprocess.check_output(['rsync','-aHAXcn','--delete','--itemize-changes',str(live)+'/',str(rebuilt)+'/'],text=True)
        unexpected=[line for line in differences.splitlines() if not line.endswith(' ./')]
        if unexpected:raise ValueError('Reconstructed live layer differs: '+repr(unexpected[:20]))
    for root,name in [(base,'minimal'),(delta,'minimal.live')]:
        target=casper/(name+'.squashfs');target.unlink()
        run('mksquashfs',root,target,'-noappend','-comp','zstd','-Xcompression-level','10','-processors','2','-no-progress')
        size=subprocess.check_output(['du','-sx','--block-size=1',str(root)],text=True).split()[0]
        (casper/(name+'.size')).write_text(size+'\n')
    import yaml
    sources=yaml.safe_load((casper/'install-sources.yaml').read_text())
    sources['sources'][0]['name']['en']='Galinia OS Alpha'
    sources['sources'][0]['description']['en']='Galinia XFCE desktop development alpha.'
    sources['sources'][0]['size']=int((casper/'minimal.size').read_text())
    (casper/'install-sources.yaml').write_text(yaml.safe_dump(sources,sort_keys=False))
    grub=work/'grub.cfg';grub.write_text((source/'boot/grub/grub.cfg').read_text().replace('Try or Install Xubuntu','Try or install Galinia OS Alpha').replace('Xubuntu (safe graphics)','Galinia OS Alpha (safe graphics)').replace('set timeout=30','set timeout=5'))
    info=work/'info';info.write_text('Galinia OS 0.1 Alpha amd64 - development image\n')
    # Rebuild media integrity metadata for replaced paths, retaining unchanged upstream entries.
    md5=work/'md5sum.txt'
    run('xorriso','-osirrox','on','-indev',iso,'-extract','/md5sum.txt',md5)
    rows=[row for row in md5.read_text().splitlines() if not any('/'+part in row.split()[-1] for part in ['casper/','boot/grub/grub.cfg','.disk/info','md5sum.txt','boot.catalog'])]
    for file in sorted(casper.rglob('*'))+[grub,info]:
        if not file.is_file():continue
        name='./casper/'+str(file.relative_to(casper)) if file.is_relative_to(casper) else './boot/grub/grub.cfg' if file==grub else './.disk/info'
        h=hashlib.md5()
        with file.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
        rows.append(h.hexdigest()+'  '+name)
    md5.write_text('\n'.join(rows)+'\n')
    result=out/'galinia-0.1-alpha1-amd64.iso'
    if result.exists():raise ValueError('Refusing to overwrite an existing ISO')
    run('xorriso','-indev',iso,'-outdev',result,'-boot_image','any','replay','-volid','GALINIA_ALPHA',
        '-map',casper,'/casper','-map',grub,'/boot/grub/grub.cfg','-map',info,'/.disk/info','-map',md5,'/md5sum.txt','-commit')
    (out/'SHA256SUMS').write_text(digest(result)+'  '+result.name+'\n')
    (out/'build.json').write_text(json.dumps({'status':'unqualified-development','source':lock,
        'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'browser_repository':'https://packages.mozilla.org/apt',
        'browser_key_fingerprint':'35BAA0B33E9EB396F59CA838C0BA5CE6DC6315A3',
        'iso_sha256':digest(result),'package_sha256':digest(args.package),'base_manifest_sha256':digest(casper/'minimal.manifest'),
        'pending':['functional boot review','offline-browser','installation','hardware','updates','recovery']},indent=2)+'\n')
    shutil.copy2(casper/'minimal.manifest',out/'packages.manifest')


if __name__=='__main__':
    main()
