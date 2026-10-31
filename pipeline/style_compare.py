#!/usr/bin/env python3
"""Side-by-side sheet of style proofs: one row per photo, columns = original + each style dir in style_proofs/.
Usage: style_compare.py <run_dir> [--cell 640] [--per-sheet 3]"""
import argparse, os
from PIL import Image, ImageDraw
from contact_sheet import load_font

ap = argparse.ArgumentParser()
ap.add_argument('run_dir'); ap.add_argument('--cell', type=int, default=640); ap.add_argument('--per-sheet', type=int, default=3)
a = ap.parse_args()
root = os.path.join(a.run_dir, 'style_proofs')
cols = ['original'] + sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d)) and d[0] not in '_.' and d != 'original')
names = sorted(os.listdir(os.path.join(root, 'original')))
font, cap = load_font(26), 44
for si in range(0, len(names), a.per_sheet):
    chunk = names[si:si + a.per_sheet]
    sheet = Image.new('RGB', (len(cols) * a.cell, cap + len(chunk) * a.cell), (24, 24, 24))
    d = ImageDraw.Draw(sheet)
    for c, col in enumerate(cols):
        d.text((c * a.cell + 12, 8), 'original' if col == 'original' else col, fill=(235, 235, 235), font=font)
        for r, n in enumerate(chunk):
            im = Image.open(os.path.join(root, col, n)); im.thumbnail((a.cell - 8, a.cell - 8))
            sheet.paste(im, (c * a.cell + (a.cell - im.width) // 2, cap + r * a.cell + (a.cell - im.height) // 2))
    out = os.path.join(root, f'compare_{si // a.per_sheet + 1:02d}.jpg')
    sheet.save(out, quality=90); print(out)
