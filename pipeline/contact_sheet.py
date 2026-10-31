#!/usr/bin/env python3
"""Build labelled contact sheets from thumbnails for visual review.

Usage:
  contact_sheet.py <run_dir> <out_dir> --names a.JPG b.JPG ...      (explicit list)
  contact_sheet.py <run_dir> <out_dir> --from list.json [--key name]  (JSON list of names or of dicts)
Options: --cols 4 --rows 3 --cell 380 --label-field reason --prefix sheet
Each cell shows the thumbnail (letterboxed) and a caption: index, file number, optional extra text.
"""
import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont


def load_font(size):
    for p in ('/System/Library/Fonts/Hiragino Sans GB.ttc', '/System/Library/Fonts/STHeiti Medium.ttc',
              '/System/Library/Fonts/Helvetica.ttc', '/System/Library/Fonts/SFNS.ttf',
              '/System/Library/Fonts/Supplemental/Arial.ttf',
              'C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/arial.ttf',
              '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _fit(draw, text, font, width):
    """Shorten text from the middle (keeping the distinctive start and end of file names) to fit width pixels."""
    if draw.textlength(text, font=font) <= width:
        return text
    head, tail = text[:len(text) // 2], text[len(text) // 2:]
    while head and tail and draw.textlength(head + '…' + tail, font=font) > width:
        head, tail = head[:-1], tail[1:]
    return head + '…' + tail


def build(run_dir, out_dir, items, cols=4, rows=3, cell=380, prefix='sheet', caption_h=34, group_rows=False):
    os.makedirs(out_dir, exist_ok=True)
    thumbs = os.path.join(run_dir, 'thumbs')
    font = load_font(15)
    font_small = load_font(12)
    per = cols * rows
    if group_rows:
        # re-pack: each group starts a new row, padding the previous row with blanks
        packed, cur_group = [], None
        for it in items:
            g = it.get('group') if isinstance(it, dict) else None
            if g != cur_group and len(packed) % cols != 0:
                packed += [None] * (cols - len(packed) % cols)
            cur_group = g
            packed.append(it)
        items = packed
    sheets = []
    for si in range(0, len(items), per):
        chunk = items[si:si + per]
        W = min(cols, len(chunk)) * cell                     # a short last sheet is not padded to the full grid
        H = -(-len(chunk) // cols) * (cell + caption_h)
        sheet = Image.new('RGB', (W, H), (28, 28, 28))
        draw = ImageDraw.Draw(sheet)
        for i, it in enumerate(chunk):
            if it is None:
                continue
            name = it['name'] if isinstance(it, dict) else it
            cap2 = it.get('caption', '') if isinstance(it, dict) else ''
            r, c = divmod(i, cols)
            x0, y0 = c * cell, r * (cell + caption_h)
            tp = os.path.join(thumbs, os.path.splitext(name)[0] + '.jpg')
            try:
                im = Image.open(tp)
                im.thumbnail((cell - 6, cell - 6))
                ox = x0 + (cell - im.width) // 2
                oy = y0 + (cell - im.height) // 2
                sheet.paste(im, (ox, oy))
            except Exception as e:
                draw.text((x0 + 10, y0 + 10), f'missing {name}', fill=(255, 80, 80), font=font)
            idx = si + i + 1
            num = os.path.splitext(name)[0]
            hl = isinstance(it, dict) and it.get('highlight')
            if hl:
                draw.rectangle([x0 + 1, y0 + 1, x0 + cell - 2, y0 + cell - 2], outline=(80, 220, 120), width=4)
            label = _fit(draw, f'{num}' + ('  KEEP' if hl else ''), font, cell - 10)
            draw.text((x0 + 6, y0 + cell + 2), label, fill=(80, 220, 120) if hl else (255, 255, 255), font=font)
            if cap2:
                draw.text((x0 + 6, y0 + cell + 18), _fit(draw, cap2, font_small, cell - 10), fill=(190, 190, 190), font=font_small)
        out = os.path.join(out_dir, f'{prefix}_{si // per + 1:02d}.jpg')
        sheet.save(out, quality=82)
        sheets.append(out)
    return sheets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run_dir')
    ap.add_argument('out_dir')
    ap.add_argument('--names', nargs='*')
    ap.add_argument('--from', dest='from_file')
    ap.add_argument('--cols', type=int, default=4)
    ap.add_argument('--rows', type=int, default=3)
    ap.add_argument('--cell', type=int, default=380)
    ap.add_argument('--prefix', default='sheet')
    ap.add_argument('--group-rows', action='store_true')
    args = ap.parse_args()
    items = []
    if args.from_file:
        data = json.load(open(args.from_file, encoding='utf-8'))
        items = data if isinstance(data, list) else data.get('items', [])
    if args.names:
        items += args.names
    sheets = build(args.run_dir, args.out_dir, items, args.cols, args.rows, args.cell, args.prefix, group_rows=args.group_rows)
    print(f'{len(items)} items -> {len(sheets)} sheets in {args.out_dir}')
    for s in sheets:
        print(' ', s)


if __name__ == '__main__':
    main()
