#!/usr/bin/env python3
"""Render style proofs in Lightroom: apply each style to sample photos, calibrate exposure / WB so the subject's
skin hits the style's Lab target, export, then restore the photos' original develop settings.

Usage: style_proof.py <run_dir> <styles.json> --names JBZ04064.JPG ... [--folder <jpg dir>] [--iters 3] [--long-edge 1600]
Output: <run_dir>/style_proofs/<style>/<name>.jpg, original/<name>.jpg, calib.json, compare_*.jpg
"""
import argparse, json, os, shutil, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bridge'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lr_client import LrBridge
import style_lib
from style_lib import DEFAULTS, measure

ap = argparse.ArgumentParser()
ap.add_argument('run_dir'); ap.add_argument('styles')
ap.add_argument('--names', nargs='+', required=True)
ap.add_argument('--folder', default='/Volumes/T4/SynologyDrive/ALL-照片/2026/20261024-宝宝百天/jpg')
ap.add_argument('--iters', type=int, default=3)
ap.add_argument('--long-edge', type=int, default=1600)
ap.add_argument('--max-ev', type=float, default=0.9, help='cap on exposure push; side-lit faces would otherwise wash out the scene')
a = ap.parse_args()

styles = json.load(open(a.styles, encoding='utf-8'))
metrics = style_lib.load_metrics(a.run_dir)
out_root = os.path.abspath(os.path.join(a.run_dir, 'style_proofs'))
tmp = os.path.join(out_root, '_iter')
paths = {n: os.path.join(a.folder, n) for n in a.names}



def face_box(name):
    return style_lib.face_box(metrics[name])


def export_one(lr, name, dest, long_edge):
    return style_lib.export_one(lr, paths[name], dest, long_edge)


touched = sorted({k for s in styles.values() for k in s['settings']} | {'Exposure2012', 'IncrementalTemperature', 'IncrementalTint'})
calib = {}
with LrBridge() as lr:
    baseline = {}
    for n in a.names:
        cur = lr.get_develop(paths[n])
        baseline[n] = {k: cur.get(k, DEFAULTS.get(k, 0)) for k in touched}
    json.dump(baseline, open(os.path.join(a.run_dir, 'style_baseline.json'), 'w'), ensure_ascii=False, indent=1)
    try:
        for n in a.names:
            export_one(lr, n, os.path.join(out_root, 'original'), a.long_edge)
        for sname, st in styles.items():
            tgt = st['skin']
            calib[sname] = {}
            for n in a.names:
                box = face_box(n)
                adj = {'Exposure2012': 0.0, 'IncrementalTemperature': 0, 'IncrementalTint': 0}
                hist = []
                for it in range(a.iters + 1):
                    lr.apply_develop(paths=[paths[n]], settings={**st['settings'], **adj}, history=f'Pic Agent: 小样 {sname}')
                    final = it == a.iters or box is None
                    f = export_one(lr, n, os.path.join(out_root, sname) if final else tmp, a.long_edge if final else 800)
                    meas = measure(f, box) if box else None
                    hist.append({'adj': dict(adj), 'meas': meas})
                    if final:
                        break
                    adj = style_lib.step(adj, meas, tgt, a.max_ev)
                calib[sname][n] = hist
                last = hist[-1]['meas']
                print(sname, n, hist[-1]['adj'], last and {k: round(v, 1) for k, v in last.items()}, flush=True)
    finally:
        r = lr.apply_develop(items=[{'path': paths[n], 'settings': baseline[n]} for n in a.names], history='Pic Agent: 恢复小样前参数')
        print('restored:', r)
shutil.rmtree(tmp, ignore_errors=True)
json.dump(calib, open(os.path.join(out_root, 'calib.json'), 'w'), ensure_ascii=False, indent=1)
