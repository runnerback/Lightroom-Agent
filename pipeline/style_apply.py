#!/usr/bin/env python3
"""Apply one style to every photo of a Lightroom collection, with per-photo skin calibration of exposure / WB.
Photos without a measurable subject face inherit the calibration of the nearest calibrated photo in time
(same scene and light). Settings stay applied; the previous values are saved for rollback.

Usage: style_apply.py <run_dir> <styles/STYLES.md> <style> [--collection 百天-精选] [--iters 3] [--max-ev 0.9] [--reuse-calib]
       style_apply.py <run_dir> --rollback <style_applied/baseline.json>
Output: <run_dir>/style_applied/<style>/{baseline.json, calib.json, thumbs/, overview_*.jpg}
"""
import argparse, json, os, re, shutil, subprocess, sys
from datetime import datetime
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(here), 'bridge'))
sys.path.insert(0, here)
from lr_client import LrBridge
import style_lib
from style_lib import DEFAULTS, CALIB_KEYS

ap = argparse.ArgumentParser()
ap.add_argument('run_dir'); ap.add_argument('styles', nargs='?', default=style_lib.STYLES_DOC); ap.add_argument('style', nargs='?')
ap.add_argument('--collection', default='百天-精选')
ap.add_argument('--iters', type=int, default=3)
ap.add_argument('--max-ev', type=float, default=0.9)
ap.add_argument('--calib-edge', type=int, default=1600, help='long edge of calibration exports (face detection runs on them)')
ap.add_argument('--rollback')
ap.add_argument('--reuse-calib', action='store_true', help='re-apply adjustments from an existing calib.json instead of recalibrating')
ap.add_argument('--refine', action='store_true', help='recalibrate, starting from the adjustments in an existing calib.json')
ap.add_argument('--only', nargs='*', help='with --refine: recalibrate just these photo names, keep the rest of calib.json')
ap.add_argument('--skin-wb', nargs='*', default=[], help='balance WB on skin for these photos even when they have white areas '
                '(whites that are really cream clothes / beige sofa pull the whole frame too cool)')
a = ap.parse_args()

if a.rollback:
    base = json.load(open(a.rollback, encoding='utf-8'))
    with LrBridge() as lr:
        print(lr.apply_develop(items=[{'path': p, 'settings': s} for p, s in base.items()], history='Pic Agent: 撤销风格'))
    sys.exit(0)

styles = style_lib.load_styles(a.styles)
style = dict(styles[a.style], settings=style_lib.style_settings(styles, a.style))
metrics = style_lib.load_metrics(a.run_dir)
out = os.path.abspath(os.path.join(a.run_dir, 'style_applied', a.style))
tmp, thumbs = os.path.join(out, '_iter'), os.path.join(out, 'thumbs')
touched = sorted(set(style['settings']) | set(CALIB_KEYS))


def metrics_for(name):
    """metrics.jsonl is keyed by the analysed JPG name; map ARW / DNG (e.g. 'JBZ04736-已增强-降噪.dng') onto it."""
    m = re.match(r'([A-Za-z]+\d+)', name)
    return metrics.get(m.group(1) + '.JPG') if m else None


def noise_reduction(p, develop):
    """Luminance NR for raw files by ISO; none for JPGs or for files already run through AI Denoise."""
    if develop.get('Temperature') is None or '降噪' in p['name'] or 'Enhanced' in p['name']:
        return {}
    iso = int(re.sub(r'\D', '', str(p.get('iso') or '0')) or 0)
    return {'LuminanceSmoothing': 10 if iso <= 1600 else 20 if iso <= 3200 else 30 if iso <= 6400 else 40}


def when(m):
    return datetime.strptime(m['datetime'], '%Y:%m:%d %H:%M:%S').timestamp() + int(m.get('subsec') or 0) / 10 ** len(m.get('subsec') or '0')


with LrBridge() as lr:
    photos = sorted(lr.list_collection(a.collection), key=lambda p: p['name'])
    print(f'{len(photos)} photos in {a.collection}', flush=True)
    os.makedirs(out, exist_ok=True)
    baseline = {}
    for p in photos:
        cur = lr.get_develop(p['path'])
        baseline[p['path']] = {k: v for k in touched if (v := cur.get(k, DEFAULTS.get(k, 0))) is not None}
        p['develop'] = cur
    CROP = ('CropLeft', 'CropTop', 'CropRight', 'CropBottom', 'CropAngle', 'orientation')
    crops = {p['path']: {k: lr.get_develop(p['path']).get(k) for k in CROP} for p in photos}
    bpath = os.path.join(out, 'baseline.json')
    if not os.path.exists(bpath):          # keep the first, pre-style baseline across re-runs
        json.dump(baseline, open(bpath, 'w'), ensure_ascii=False, indent=1)

    calib, pending = {}, []
    cpath = os.path.join(out, 'calib.json')
    prev_calib = json.load(open(cpath, encoding='utf-8')) if (a.refine or a.only) and os.path.exists(cpath) else {}
    if a.reuse_calib:
        calib = json.load(open(os.path.join(out, 'calib.json'), encoding='utf-8'))
        for p in photos:
            adj, extra = calib[p['name']]['adj'], calib[p['name']].get('extra', {})
            lr.apply_develop(paths=[p['path']], settings={**style['settings'], **extra, **adj, **style_lib.wb_mode(adj)}, history=f'Pic Agent: 风格 {a.style}')
        photos_to_calibrate = []
    elif a.only:
        calib = {k: v for k, v in prev_calib.items() if k not in a.only}
        photos_to_calibrate = [p for p in photos if p['name'] in a.only]
    else:
        photos_to_calibrate = photos
    # Faces are detected on the calibration exports themselves, so the user's crop / straighten is respected.
    for p in photos_to_calibrate:
        extra = noise_reduction(p, p['develop'])
        # Without a previous calibration start from the saved pre-style baseline (camera as-shot WB), not from
        # whatever an earlier run left applied.
        start = prev_calib[p['name']]['adj'] if p['name'] in prev_calib else style_lib.initial_adj(
            {**p['develop'], **json.load(open(bpath, encoding='utf-8')).get(p['path'], {})})
        st = {k: v for k, v in style.items() if k != 'white'} if p['name'] in a.skin_wb else style
        adj, hist = style_lib.calibrate(lr, p['path'], None, st, tmp, a.iters, a.max_ev, a.calib_edge, f'Pic Agent: 风格 {a.style}',
                                        start=start, extra=extra)
        if adj is None:
            pending.append(p); continue
        calib[p['name']] = {'adj': adj, 'extra': extra, 'meas': hist[-1]['meas'], 'hist': hist, 'source': 'face',
                            'wb_on': 'skin' if st is not style else 'auto'}
        print(p['name'], 'face', style_lib.adj_text(adj), extra, {k: round(v, 1) for k, v in hist[-1]['meas'].items()}, flush=True)

    # No usable face: borrow from the nearest calibrated frame in time.
    for p in pending:
        t = when(metrics_for(p['name'])) if metrics_for(p['name']) else 0
        donor = min((n for n in calib if metrics_for(n)), key=lambda n: abs(when(metrics_for(n)) - t))
        adj, extra = calib[donor]['adj'], noise_reduction(p, p['develop'])
        lr.apply_develop(paths=[p['path']], settings={**style['settings'], **extra, **adj, **style_lib.wb_mode(adj)}, history=f'Pic Agent: 风格 {a.style}')
        calib[p['name']] = {'adj': adj, 'extra': extra, 'source': 'from ' + donor}
        print(p['name'], 'from', donor, style_lib.adj_text(adj), flush=True)

    json.dump(calib, open(os.path.join(out, 'calib.json'), 'w'), ensure_ascii=False, indent=1)
    for p in photos:
        p.pop('develop', None)
    changed = [p['name'] for p in photos if {k: lr.get_develop(p['path']).get(k) for k in CROP} != crops[p['path']]]
    print('crop/orientation changed on:', changed or 'none', flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(thumbs, ignore_errors=True)
    r = lr.export(thumbs, paths=[p['path'] for p in photos], long_edge=800, quality=85, sharpen_level=1)
    print('overview export:', r['written'], 'files', flush=True)

items = [{'name': p['name'], 'caption': ('' if calib[p['name']]['source'] == 'face' else '借 ') +
          style_lib.adj_text(calib[p['name']]['adj'])}
         for p in photos]
json.dump(items, open(os.path.join(out, 'overview.json'), 'w'), ensure_ascii=False)
subprocess.run([sys.executable, '-I', os.path.join(here, 'contact_sheet.py'), out, out, '--from', os.path.join(out, 'overview.json'),
                '--cols', '7', '--rows', '4', '--cell', '300', '--prefix', 'overview'], check=True)
