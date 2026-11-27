#!/usr/bin/env python3
"""Observe a CD-ROM boot in QEMU. Screenshots are evidence, not an automatic desktop pass."""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time


def command(stream, name, arguments=None):
    request={'execute':name}
    if arguments:request['arguments']=arguments
    stream.write((json.dumps(request)+'\n').encode());stream.flush()
    while True:
        line=stream.readline()
        if not line:raise RuntimeError('QMP connection closed')
        response=json.loads(line)
        if 'error' in response:raise RuntimeError(str(response['error']))
        if 'return' in response:return response['return']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--firmware',choices=['bios','uefi'],required=True)
    parser.add_argument('--seconds',type=int,default=180)
    args=parser.parse_args()
    if not 30<=args.seconds<=600:raise ValueError('Use a 30–600 second observation window')
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    acceleration='kvm' if os.access('/dev/kvm',os.R_OK|os.W_OK) else 'tcg'
    with tempfile.TemporaryDirectory(prefix='galinia-qmp-') as temporary:
        qmp=Path(temporary)/'socket'
        argv=['qemu-system-x86_64','-accel',acceleration,'-m','4096','-smp','2','-vga','std',
              '-display','none','-no-reboot','-boot','d','-cdrom',str(args.iso.resolve()),
              '-nic','user,model=virtio-net-pci','-serial','file:'+str(out/'serial.log'),
              '-qmp','unix:'+str(qmp)+',server=on,wait=off']
        if args.firmware=='uefi':
            vars=Path(temporary)/'VARS.fd';shutil.copyfile('/usr/share/OVMF/OVMF_VARS_4M.fd',vars)
            argv+=['-drive','if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd',
                   '-drive','if=pflash,format=raw,file='+str(vars)]
        with (out/'qemu.log').open('w') as log:
            process=subprocess.Popen(argv,stdout=log,stderr=log)
            started=time.monotonic()
            try:
                while not qmp.exists():
                    if process.poll() is not None or time.monotonic()-started>20:raise RuntimeError('QEMU did not open QMP')
                    time.sleep(.2)
                with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as sock:
                    sock.settimeout(30);sock.connect(str(qmp));stream=sock.makefile('rwb')
                    json.loads(stream.readline());command(stream,'qmp_capabilities')
                    for index in range(1,args.seconds//30+1):
                        deadline=started+index*30
                        while time.monotonic()<deadline:
                            if process.poll() is not None:raise RuntimeError('Guest exited before observation finished')
                            time.sleep(min(1,deadline-time.monotonic()))
                        from PIL import Image
                        ppm=out/f'frame-{index*30:03d}.ppm'
                        command(stream,'screendump',{'filename':str(ppm)})
                        Image.open(ppm).save(ppm.with_suffix('.png'));ppm.unlink()
                        print(f'{args.firmware}: captured {index*30}s boot observation ({acceleration})',flush=True)
                    state=command(stream,'query-status')
                    (out/'observation.json').write_text(json.dumps({'firmware':args.firmware,'accelerator':acceleration,
                        'seconds':args.seconds,'qemu_status':state,'desktop_result':'requires screenshot review',
                        'installation_tested':False,'secure_boot_tested':False},indent=2)+'\n')
                    command(stream,'quit')
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:process.wait(timeout=10)
                    except subprocess.TimeoutExpired:process.kill();process.wait()


if __name__=='__main__':main()
