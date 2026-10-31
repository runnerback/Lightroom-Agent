#!/usr/bin/env python3
"""Apply one style to every photo of a Lightroom collection, with per-photo skin calibration of exposure / WB.
Photos without a measurable subject face inherit the calibration of the nearest calibrated photo in time
(same scene and light). Settings stay applied; the previous values are saved for rollback.
Crop, straighten and orientation are never touched.

Usage: style_apply.py <run_dir> <styles/STYLES.md> <style> --collection <name> [--iters 3] [--max-ev 0.9] [--reuse-calib]
       style_apply.py <run_dir> --rollback <style_applied/<style>/baseline.json | style_applied/original.json>
<style> is the full name from STYLES.md or its letter (A, B, C, D ...).
Output: <run_dir>/style_applied/<style>/{baseline.json, calib.json, summary.json, thumbs/, overview_*.jpg}
"""
import argparse, json, os, re, shutil, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(here), 'bridge'))
sys.path.insert(0, here)
from lr_client import LrBridge
import style_lib
from style_lib import DEFAULTS, CALIB_KEYS

ap = argparse.ArgumentParser()
ap.add_argument('run_dir'); ap.add_argument('styles', nargs='?', default=style_lib.STYLES_DOC); ap.add_argument('style', nargs='?')
ap.add_argument('--collection', help='Lightroom collection whose photos get the style')
ap.add_argument('--iters', type=int, default=3)
ap.add_argument('--max-ev', type=float, default=0.9)
ap.add_argument('--calib-edge', type=int, default=1600, help='long edge of calibration exports (face detection runs on them)')
ap.add_argument('--rollback')
ap.add_argument('--reuse-calib', action='store_true', help='re-apply adjustments from an existing calib.json instead of recalibrating')
ap.add_argument('--refine', action='store_true', help='recalibrate, starting from the adjustments in an existing calib.json')
ap.add_argument('--only', nargs='*', help='with --refine: recalibrate just these photo names, keep the rest of calib.json')
ap.add_argument('--skin-wb', nargs='*', default=[], help='balance WB on skin for these photos even when they have white areas '
                '(whites that are really cream clothes / beige sofa pull the whole frame too cool)')
ap.add_argument('--no-overview', action='store_true', help='skip the 800px overview export and contact sheets')
a = ap.parse_args()

if a.rollback:
    base = json.load(open(a.rollback, encoding='utf-8'))
    with LrBridge() as lr:
        print(lr.apply_develop(items=[{'path': p, 'settings': s} for p, s in base.items()], history='Lightroom Agent: undo style'))
    sys.exit(0)
if not (a.style and a.collection):
    ap.error('style and --collection are required (or --rollback)')

styles = style_lib.load_styles(a.styles)
a.style = style_lib.resolve_style(styles, a.style)
style = dict(styles[a.style], settings=style_lib.style_settings(styles, a.style))
out = os.path.abspath(os.path.join(a.run_dir, 'style_applied', a.style))
tmp, thumbs = os.path.join(out, '_iter'), os.path.join(out, 'thumbs')
touched = sorted(set(style['settings']) | set(CALIB_KEYS))
history = f'Lightroom Agent: style {a.style}'


def noise_reduction(p, develop):
    """Luminance NR for raw files by ISO; none for JPGs or for files already run through AI Denoise."""
    if not develop.get('Temperature') or re.search(r'enhanced|denoise|降噪', p['name'], re.I):
        return {}
    iso = p.get('iso_value') or int(re.sub(r'\D', '', str(p.get('iso') or '0')) or 0)
    return {'LuminanceSmoothing': 10 if iso <= 1600 else 20 if iso <= 3200 else 30 if iso <= 6400 else 40}


with LrBridge() as lr:
    photos = sorted(lr.list_collection(a.collection), key=lambda p: p['name'])
    if not photos:
        sys.exit(f'collection {a.collection!r} is empty or does not exist')
    print(f'{len(photos)} photos in {a.collection}', flush=True)
    os.makedirs(out, exist_ok=True)
    baseline = {}
    for p in photos:
        cur = lr.get_develop(p['path'])
        baseline[p['path']] = {k: v for k in touched if (v := cur.get(k, DEFAULTS.get(k, 0))) is not None}
        p['develop'] = cur
    CROP = ('CropLeft', 'CropTop', 'CropRight', 'CropBottom', 'CropAngle', 'orientation')
    crops = {p['path']: {k: p['develop'].get(k) for k in CROP} for p in photos}
    bpath = os.path.join(out, 'baseline.json')
    if os.path.exists(bpath):              # keep the first, pre-style baseline across re-runs; add photos new since then
        saved = json.load(open(bpath, encoding='utf-8'))
        baseline = {**baseline, **saved}
    json.dump(baseline, open(bpath, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # original.json: the state before the FIRST style applied in this run directory, used by `rollback` without a style.
    # (Each style's baseline.json is the state just before that style, i.e. possibly another style's look.)
    opath = os.path.join(os.path.dirname(out), 'original.json')
    original = json.load(open(opath, encoding='utf-8')) if os.path.exists(opath) else None
    if original is None:
        older = sorted((os.path.join(os.path.dirname(out), d, 'baseline.json') for d in os.listdir(os.path.dirname(out))),
                       key=lambda f: os.path.getmtime(f) if os.path.exists(f) else 1e18)
        original = json.load(open(older[0], encoding='utf-8')) if older and os.path.exists(older[0]) else {}
    for path, vals in baseline.items():   # photos new to this run, or keys of styles added since
        original[path] = {**vals, **original.get(path, {})}
    json.dump(original, open(opath, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

    calib, pending = {}, []
    cpath = os.path.join(out, 'calib.json')
    prev_calib = json.load(open(cpath, encoding='utf-8')) if (a.refine or a.only or a.reuse_calib) and os.path.exists(cpath) else {}
    if a.reuse_calib:
        calib = prev_calib
        for p in photos:
            if p['name'] not in calib:
                sys.exit(f'{p["name"]} has no saved calibration; run without --reuse-calib')
            adj, extra = calib[p['name']]['adj'], calib[p['name']].get('extra', {})
            lr.apply_develop(paths=[p['path']], settings={**style['settings'], **extra, **adj, **style_lib.wb_mode(adj)}, history=history)
        photos_to_calibrate = []
    elif a.only:
        calib = {k: v for k, v in prev_calib.items() if k not in a.only}
        photos_to_calibrate = [p for p in photos if p['name'] in a.only]
        unknown = set(a.only) - {p['name'] for p in photos}
        if unknown:
            sys.exit(f'not in {a.collection}: {", ".join(sorted(unknown))}')
    else:
        photos_to_calibrate = photos
    # Faces are detected on the calibration exports themselves, so the user's crop / straighten is respected.
    for p in photos_to_calibrate:
        extra = noise_reduction(p, p['develop'])
        # Without a previous calibration start from the saved pre-style baseline (camera as-shot WB), not from
        # whatever an earlier run left applied.
        start = prev_calib[p['name']]['adj'] if p['name'] in prev_calib else style_lib.initial_adj({**p['develop'], **baseline[p['path']]})
        st = {k: v for k, v in style.items() if k != 'white'} if p['name'] in a.skin_wb else style
        adj, hist = style_lib.calibrate(lr, p['path'], None, st, tmp, a.iters, a.max_ev, a.calib_edge, history, start=start, extra=extra)
        if adj is None:
            pending.append(p); continue
        calib[p['name']] = {'adj': adj, 'extra': extra, 'meas': hist[-1]['meas'], 'hist': hist, 'source': 'face',
                            'wb_on': 'skin' if st is not style else 'auto', 'time': p.get('time')}
        print(p['name'], 'face', style_lib.adj_text(adj), extra, {k: round(v, 1) for k, v in hist[-1]['meas'].items()}, flush=True)

    # No usable face: borrow from the nearest calibrated frame in time (same scene, same light).
    # With no calibrated frame at all, keep the camera's exposure / white balance and only apply the look.
    donors = [n for n, v in calib.items() if v.get('source') == 'face' and v.get('time') is not None]
    for p in pending:
        extra = noise_reduction(p, p['develop'])
        if donors and p.get('time') is not None:
            donor = min(donors, key=lambda n: abs(calib[n]['time'] - p['time']))
            adj, source = calib[donor]['adj'], 'from ' + donor
        else:
            adj, source = style_lib.initial_adj({**p['develop'], **baseline[p['path']]}), 'no face'
        lr.apply_develop(paths=[p['path']], settings={**style['settings'], **extra, **adj, **style_lib.wb_mode(adj)}, history=history)
        calib[p['name']] = {'adj': adj, 'extra': extra, 'source': source, 'time': p.get('time')}
        print(p['name'], source, style_lib.adj_text(adj), flush=True)

    json.dump(calib, open(cpath, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    changed = [p['name'] for p in photos if {k: lr.get_develop(p['path']).get(k) for k in CROP} != crops[p['path']]]
    print('crop/orientation changed on:', changed or 'none', flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    if not a.no_overview:
        shutil.rmtree(thumbs, ignore_errors=True)
        r = lr.export(thumbs, paths=[p['path'] for p in photos], long_edge=800, quality=85, sharpen_level=1)
        print('overview export:', r['written'], 'files', flush=True)

sheets = []
if not a.no_overview:
    items = [{'name': p['name'], 'caption': ('' if calib[p['name']]['source'] == 'face' else '≈ ') +
              style_lib.adj_text(calib[p['name']]['adj'])} for p in photos]
    json.dump(items, open(os.path.join(out, 'overview.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    subprocess.run([sys.executable, '-I', os.path.join(here, 'contact_sheet.py'), out, out, '--from', os.path.join(out, 'overview.json'),
                    '--cols', '7', '--rows', '4', '--cell', '300', '--prefix', 'overview'], check=True)
    sheets = sorted(os.path.join(out, f) for f in os.listdir(out) if f.startswith('overview_') and f.endswith('.jpg'))
summary = {
    'style': a.style, 'collection': a.collection, 'photos': len(photos),
    'calibrated_on_face': sum(1 for v in calib.values() if v['source'] == 'face'),
    'borrowed': sorted(n for n, v in calib.items() if v['source'].startswith('from ')),
    'no_face': sorted(n for n, v in calib.items() if v['source'] == 'no face'),
    'exposure_capped': sorted(n for n, v in calib.items() if abs(v['adj']['Exposure2012']) >= a.max_ev - 1e-6),
    'crop_changed': changed, 'overview': sheets, 'baseline': bpath, 'dir': out,
}
json.dump(summary, open(os.path.join(out, 'summary.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('SUMMARY', json.dumps(summary, ensure_ascii=False), flush=True)
