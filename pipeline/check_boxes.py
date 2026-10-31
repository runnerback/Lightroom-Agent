#!/usr/bin/env python3
"""QA sheet for skin calibration: draws the patch each photo was calibrated on (red) and what detection finds now
on the current overview thumb (green), so wrong "faces" (balloons, hands) are easy to spot.
Usage: check_boxes.py <style_applied/<style> dir>   -> <dir>/boxes.jpg"""
import json, os, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import style_lib
from contact_sheet import load_font

D = sys.argv[1]
c = json.load(open(os.path.join(D, 'calib.json'), encoding='utf-8'))
font = load_font(14)


def to_upright(box):
    """Box measured on np.rot90(img, k) -> the same box in the unrotated image (normalised x0, y0, x1, y1)."""
    x0, y0, x1, y1, k = box[0], box[1], box[2], box[3], int(box[4])
    pts = [(x0, y0), (x1, y1)]
    conv = {0: lambda x, y: (x, y), 1: lambda x, y: (1 - y, x), 2: lambda x, y: (1 - x, 1 - y), 3: lambda x, y: (y, 1 - x)}[k]
    (ax, ay), (bx, by) = [conv(x, y) for x, y in pts]
    return min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)


def draw(img, box, col):
    if not box:
        return img
    h, w = img.shape[:2]
    x0, y0, x1, y1 = to_upright(box)
    cv2.rectangle(img, (int(x0 * w), int(y0 * h)), (int(x1 * w), int(y1 * h)), col, 3)
    return img


cells, moved_names = [], []
for name, v in sorted(c.items()):
    f = os.path.join(D, 'thumbs', os.path.splitext(name)[0] + '.jpg')
    new, _ = style_lib.detect_subject(f)
    old = v['hist'][-1]['box'] if v.get('hist') else None
    r = draw(draw(cv2.imread(f), old, (0, 0, 255)), new, (0, 255, 0))
    moved = (old is None) != (new is None) or bool(old and new and sum(abs(p - q) for p, q in zip(to_upright(old), to_upright(new))) > 0.08)
    if moved:
        moved_names.append(name)
    t = Image.fromarray(cv2.cvtColor(r, cv2.COLOR_BGR2RGB)); t.thumbnail((240, 240))
    cells.append((name, t, moved))
cols, W = 10, 244
sheet = Image.new('RGB', (cols * W, -(-len(cells) // cols) * (W + 20)), (25, 25, 25)); d = ImageDraw.Draw(sheet)
for i, (n, t, mv) in enumerate(cells):
    r, cc = divmod(i, cols)
    sheet.paste(t, (cc * W, r * (W + 20)))
    d.text((cc * W + 2, r * (W + 20) + W), os.path.splitext(n)[0][:16] + (' moved' if mv else ''), fill=(255, 120, 120) if mv else (220, 220, 220), font=font)
sheet.save(os.path.join(D, 'boxes.jpg'), quality=88)
print('box changed:', moved_names)
