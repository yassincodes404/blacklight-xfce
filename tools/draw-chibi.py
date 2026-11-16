#!/usr/bin/env python3
"""Render the original pointer art into a chosen output folder; never edits the desktop."""
from pathlib import Path
from PIL import Image, ImageDraw
import argparse, subprocess
ink = '#15111d'
outline = '#eee5ff'
accent = '#c5a8fb'
hair = '#a58ad6'
shadow = '#6d5498'
skin = '#fff1ed'

def draw_pointer(kind, size):
    im = Image.new('RGBA', (128,128))
    d = ImageDraw.Draw(im)
    def poly(coords, fill, edge=None):
        d.polygon([(x*4,y*4) for x,y in coords], fill=fill, outline=edge, width=4)
    def box(bounds, fill):
        d.rectangle(tuple(x*4 for x in bounds), fill=fill)
    # An arrow or raised glove defines the hotspot independently of the face.
    if kind == 'left_ptr':
        poly([(2,2),(3,20),(7,15),(11,22),(14,20),(10,13),(17,13)], outline, ink)
        poly([(3,4),(13,12),(8,12),(4,17)], accent)
    else:
        poly([(9,3),(12,3),(13,5),(13,12),(15,10),(19,11),(22,15),(20,22),(12,22),(7,15),(9,13),(11,15),(9,6)], outline, ink)
        poly([(10,5),(11,5),(12,14),(15,12),(19,13),(20,16),(18,20),(13,20),(9,15),(12,17)], accent)
    # Chibi mascot, with a light silhouette so it reads on dark surfaces.
    poly([(12,22),(12,15),(14,11),(18,12),(20,10),(24,12),(27,11),(30,16),(30,23),(27,27),(24,29),(18,29),(14,27)], outline)
    poly([(13,22),(13,16),(15,12),(18,14),(20,11),(24,14),(27,12),(29,17),(29,23),(26,27),(23,28),(18,28),(15,26)], hair, ink)
    poly([(14,18),(18,16),(24,16),(28,18),(27,24),(24,27),(18,27),(15,24)], skin, ink)
    poly([(14,19),(14,16),(16,13),(19,15),(21,12),(24,15),(27,13),(28,17),(28,20),(25,18),(23,20),(22,16),(19,19),(18,17)], hair, ink)
    poly([(25,20),(28,18),(28,23),(26,26)], shadow)
    box((17,21,18,23),ink)
    box((23,21,24,23),ink)
    box((17,21,17,21),outline)
    box((23,21,23,21),outline)
    box((15,24,16,24),'#ef9ebd')
    box((25,24,26,24),'#ef9ebd')
    box((20,25,21,25),ink)
    return im.resize((size,size), Image.Resampling.LANCZOS)


def draw_loading(kind, size, frame):
    """Draw a small amber orbit with an outlined, moving leading edge."""
    im = Image.new('RGBA', (128, 128))
    if kind == 'left_ptr_watch':
        im.alpha_composite(draw_pointer('left_ptr', 100))
        center, radius = (103, 101), 15
    else:
        center, radius = (64, 64), 35
    x, y = center
    bounds = (x - radius, y - radius, x + radius, y + radius)
    d = ImageDraw.Draw(im)
    angle = frame * 30
    d.ellipse((x - radius - 7, y - radius - 7, x + radius + 7, y + radius + 7),
              fill='#211720', outline=ink, width=3)
    d.ellipse(bounds, outline='#875751', width=3)
    d.arc(bounds, start=angle, end=angle + 135, fill='#d47d59', width=5)
    d.arc(bounds, start=angle + 95, end=angle + 153, fill='#ffc788', width=6)
    return im.resize((size, size), Image.Resampling.LANCZOS)


def write_loading(output):
    for kind, hotspot in [('wait', (16, 16)), ('left_ptr_watch', (2, 2))]:
        lines = []
        for size in (24, 28, 32, 36, 48, 64):
            for frame in range(12):
                name = f'{kind}-{size}-{frame}.png'
                draw_loading(kind, size, frame).save(output / name)
                lines.append(f'{size} {round(hotspot[0]*size/32)} {round(hotspot[1]*size/32)} {name} 55')
        config = output / f'{kind}.conf'
        config.write_text('\n'.join(lines) + '\n')
        subprocess.run(['xcursorgen', config.name, kind], cwd=output, check=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    for kind,hotspot in [('left_ptr',(2,2)),('hand2',(10,3))]:
        lines=[]
        for size in (24,28,32,36,48,64):
            name=f'{kind}-{size}.png';draw_pointer(kind,size).save(args.output/name)
            lines.append(f'{size} {round(hotspot[0]*size/32)} {round(hotspot[1]*size/32)} {name}')
        conf=args.output/f'{kind}.conf';conf.write_text('\n'.join(lines)+'\n')
        subprocess.run(['xcursorgen',conf.name,kind],cwd=args.output,check=True)
    write_loading(args.output)


if __name__=='__main__':main()
