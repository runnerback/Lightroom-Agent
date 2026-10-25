#!/usr/bin/env python3
"""Apply one style to every photo of a Lightroom collection, with per-photo skin calibration of exposure / WB.
Photos without a measurable subject face inherit the calibration of the nearest calibrated photo in time
(same scene and light). Settings stay applied; the previous values are saved for rollback.

Usage: style_apply.py <run_dir> <styles.json> <style> [--collection 百天-精选] [--iters 3] [--max-ev 0.9] [--reuse-calib]
       style_apply.py <run_dir> --rollback <style_applied/baseline.json>
Output: <run_dir>/style_applied/<style>/{baseline.json, calib.json, thumbs/, overview_*.jpg}
"""
import argparse, json, os, shutil, subprocess, sys
from datetime import datetime
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(here), 'bridge'))
sys.path.insert(0, here)
from lr_client import LrBridge
import style_lib
from style_lib import DEFAULTS, CALIB_KEYS

ap = argparse.ArgumentParser()
ap.add_argument('run_dir'); ap.add_argument('styles', nargs='?'); ap.add_argument('style', nargs='?')
ap.add_argument('--collection', default='百天-精选')
ap.add_argument('--iters', type=int, default=3)
ap.add_argument('--max-ev', type=float, default=0.9)
ap.add_argument('--calib-edge', type=int, default=1600, help='long edge of calibration exports (face detection runs on them)')
ap.add_argument('--rollback')
ap.add_argument('--reuse-calib', action='store_true', help='re-apply adjustments from an existing calib.json instead of recalibrating')
a = ap.parse_args()

if a.rollback:
    base = json.load(open(a.rollback, encoding='utf-8'))
    with LrBridge() as lr:
        print(lr.apply_develop(items=[{'path': p, 'settings': s} for p, s in base.items()], history='Pic Agent: 撤销风格'))
    sys.exit(0)

styles = json.load(open(a.styles, encoding='utf-8'))
style = dict(styles[a.style], settings=style_lib.style_settings(styles, a.style))
metrics = style_lib.load_metrics(a.run_dir)
out = os.path.abspath(os.path.join(a.run_dir, 'style_applied', a.style))
tmp, thumbs = os.path.join(out, '_iter'), os.path.join(out, 'thumbs')
touched = sorted(set(style['settings']) | set(CALIB_KEYS))


def when(m):
    return datetime.strptime(m['datetime'], '%Y:%m:%d %H:%M:%S').timestamp() + int(m.get('subsec') or 0) / 10 ** len(m.get('subsec') or '0')


with LrBridge() as lr:
    photos = sorted(lr.list_collection(a.collection), key=lambda p: p['name'])
    print(f'{len(photos)} photos in {a.collection}', flush=True)
    os.makedirs(out, exist_ok=True)
    baseline = {}
    for p in photos:
        cur = lr.get_develop(p['path'])
        baseline[p['path']] = {k: cur.get(k, DEFAULTS.get(k, 0)) for k in touched}
    CROP = ('CropLeft', 'CropTop', 'CropRight', 'CropBottom', 'CropAngle', 'orientation')
    crops = {p['path']: {k: lr.get_develop(p['path']).get(k) for k in CROP} for p in photos}
    bpath = os.path.join(out, 'baseline.json')
    if not os.path.exists(bpath):          # keep the first, pre-style baseline across re-runs
        json.dump(baseline, open(bpath, 'w'), ensure_ascii=False, indent=1)

    calib, pending = {}, []
    if a.reuse_calib:
        calib = json.load(open(os.path.join(out, 'calib.json'), encoding='utf-8'))
        for p in photos:
            adj = calib[p['name']]['adj']
            lr.apply_develop(paths=[p['path']], settings={**style['settings'], **adj, **style_lib.wb_mode(adj)}, history=f'Pic Agent: 风格 {a.style}')
        photos_to_calibrate = []
    else:
        photos_to_calibrate = photos
    # Faces are detected on the calibration exports themselves, so the user's crop / straighten is respected.
    for p in photos_to_calibrate:
        adj, hist = style_lib.calibrate(lr, p['path'], None, style, tmp, a.iters, a.max_ev, a.calib_edge, f'Pic Agent: 风格 {a.style}')
        if adj is None:
            pending.append(p); continue
        calib[p['name']] = {'adj': adj, 'meas': hist[-1]['meas'], 'hist': hist, 'source': 'face'}
        print(p['name'], 'face', adj, {k: round(v, 1) for k, v in hist[-1]['meas'].items()}, flush=True)

    # No usable face: borrow from the nearest calibrated frame in time.
    for p in pending:
        t = when(metrics[p['name']]) if p['name'] in metrics else 0
        donor = min(calib, key=lambda n: abs(when(metrics[n]) - t))
        adj = calib[donor]['adj']
        lr.apply_develop(paths=[p['path']], settings={**style['settings'], **adj, **style_lib.wb_mode(adj)}, history=f'Pic Agent: 风格 {a.style}')
        calib[p['name']] = {'adj': adj, 'source': 'from ' + donor}
        print(p['name'], 'from', donor, adj, flush=True)

    json.dump(calib, open(os.path.join(out, 'calib.json'), 'w'), ensure_ascii=False, indent=1)
    changed = [p['name'] for p in photos if {k: lr.get_develop(p['path']).get(k) for k in CROP} != crops[p['path']]]
    print('crop/orientation changed on:', changed or 'none', flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(thumbs, ignore_errors=True)
    r = lr.export(thumbs, paths=[p['path'] for p in photos], long_edge=800, quality=85, sharpen_level=1)
    print('overview export:', r['written'], 'files', flush=True)

items = [{'name': p['name'], 'caption': ('' if calib[p['name']]['source'] == 'face' else '借 ') +
          'EV {Exposure2012:+.2f} T {IncrementalTemperature:+d} t {IncrementalTint:+d}'.format(**calib[p['name']]['adj'])}
         for p in photos]
json.dump(items, open(os.path.join(out, 'overview.json'), 'w'), ensure_ascii=False)
subprocess.run([sys.executable, '-I', os.path.join(here, 'contact_sheet.py'), out, out, '--from', os.path.join(out, 'overview.json'),
                '--cols', '7', '--rows', '4', '--cell', '300', '--prefix', 'overview'], check=True)
