"""Shared helpers for style proofing / applying: skin-patch measurement and closed-loop exposure/WB calibration."""
import json
import math
import os

import cv2
import numpy as np

# Defaults for keys a style may touch that get_develop omits when unset.
DEFAULTS = {'ToneCurvePV2012': [0, 0, 255, 255]}
# Neutral values for keys whose Lightroom default is not 0.
NEUTRAL = {'ToneCurvePV2012': [0, 0, 255, 255], 'GrainSize': 25, 'GrainFrequency': 50,
           'PostCropVignetteMidpoint': 50, 'PostCropVignetteFeather': 50, 'PostCropVignetteRoundness': 0}


def style_settings(styles, name):
    """Settings for one style, with every key that *another* style sets reset to neutral, so switching styles
    never leaves leftovers (e.g. A's orange HSL under B)."""
    others = {k for s in styles.values() for k in s['settings']} - set(styles[name]['settings'])
    return {**{k: NEUTRAL.get(k, 0) for k in sorted(others)}, **styles[name]['settings']}


CALIB_KEYS = ('Exposure2012', 'IncrementalTemperature', 'IncrementalTint', 'Temperature', 'Tint', 'WhiteBalance', 'LuminanceSmoothing')


def load_metrics(run_dir):
    metrics = {}
    for line in open(os.path.join(run_dir, 'metrics.jsonl'), encoding='utf-8'):
        m = json.loads(line)
        metrics[m['name']] = m
    return metrics


def face_box(m):
    """Central skin patch of the subject face, normalised to the oriented image (x0, y0, x1, y1), plus face width."""
    s = m.get('subject')
    if not isinstance(s, int) or not m.get('faces') or m.get('face_rot', 0) != 0:
        return None
    f = m['faces'][s]
    cx, cy = f['x'] + f['w'] / 2, f['y'] + f['h'] * 0.55
    return cx - f['w'] * 0.25, cy - f['h'] * 0.2, cx + f['w'] * 0.25, cy + f['h'] * 0.2


def measure(path, box):
    """Skin Lab stats inside box (x0, y0, x1, y1[, rot_k]); rot_k = np.rot90 turns applied before measuring."""
    im = cv2.imread(path)
    if len(box) > 4 and box[4]:
        im = np.ascontiguousarray(np.rot90(im, box[4]))
    h, w = im.shape[:2]
    lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB).astype(np.float32)
    x0, y0, x1, y1 = int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)
    p = lab[y0:y1, x0:x1].reshape(-1, 3)
    L, A, B = p[:, 0] * 100 / 255, p[:, 1] - 128, p[:, 2] - 128
    keep = (L > np.percentile(L, 10)) & (L < np.percentile(L, 95))   # drop eyes / nostrils / speculars
    gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    out = {'L': float(L[keep].mean()), 'a': float(A[keep].mean()), 'b': float(B[keep].mean()),
           'clip_hi': float((gray >= 250).mean() * 100)}
    # Near-neutral bright areas (bedding, blankets, clothes): their cast is what the eye judges white balance by.
    full = lab.reshape(-1, 3)
    fl, fa, fb = full[:, 0] * 100 / 255, full[:, 1] - 128, full[:, 2] - 128
    wm = (fl > 78) & (fl < 97) & (np.hypot(fa, fb) < 15)
    out['wfrac'] = float(wm.mean() * 100)
    if wm.any():
        out['wa'], out['wb'] = float(fa[wm].mean()), float(fb[wm].mean())
    return out


_fd = None


def detect_subject(path, min_score=0.7):
    """Find the baby's face in an exported (cropped) image with YuNet, trying 0/90/270/180 degree turns.
    Subject = smallest face that is at least 25% of the largest (same rule as analyze.py).
    Returns the central skin patch (x0, y0, x1, y1, rot_k) normalised to the turned image, and the face width fraction."""
    global _fd
    if _fd is None:
        model = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models', 'face_detection_yunet_2023mar.onnx')
        _fd = cv2.FaceDetectorYN.create(model, '', (320, 320), score_threshold=0.6, nms_threshold=0.3, top_k=50)
    im = cv2.imread(path)
    # Detect at ~800px: YuNet misses very large faces, and at 1600px it also cut faces in half and scored hands
    # (04819, 04827) as faces. Boxes are normalised, so the scale does not matter downstream.
    if max(im.shape[:2]) > 1000:
        k0 = 800 / max(im.shape[:2])
        im = cv2.resize(im, (int(im.shape[1] * k0), int(im.shape[0] * k0)), interpolation=cv2.INTER_AREA)
    cands = []                                   # (score, area_frac, k, face, w, h) across all four turns
    for k in (0, 1, 3, 2):
        r = im if k == 0 else np.ascontiguousarray(np.rot90(im, k))
        h, w = r.shape[:2]
        _fd.setInputSize((w, h))
        _, faces = _fd.detect(r)
        lab = cv2.cvtColor(r, cv2.COLOR_BGR2LAB).astype(np.float32)
        for f in (faces if faces is not None else []):
            if float(f[14]) < min_score or f[2] <= 12:
                continue
            # Balloons and plush toys have cartoon faces that YuNet happily detects; keep only skin-coloured ones.
            x0, y0 = int(f[0] + f[2] * 0.25), int(f[1] + f[3] * 0.35)
            x1, y1 = int(f[0] + f[2] * 0.75), int(f[1] + f[3] * 0.75)
            p = lab[max(0, y0):y1, max(0, x0):x1].reshape(-1, 3)
            if len(p) == 0:
                continue
            fa, fb = np.median(p[:, 1]) - 128, np.median(p[:, 2]) - 128
            if not (3 < fa < 35 and 3 < fb < 40 and 0.25 < fb / max(fa, 0.1) < 4):
                continue
            cands.append((float(f[14]), f[2] * f[3] / (w * h), k, f, w, h))
    if not cands:
        return None, 0
    # The same face shows up in several turns, and arms/hands give weak false hits: keep the confident ones,
    # then take the smallest face that is still >= 25% of the largest (baby next to an adult).
    top = max(c[0] for c in cands)
    cands = [c for c in cands if c[0] >= top - 0.12]
    big = max(c[1] for c in cands)
    _, _, k, f, w, h = min((c for c in cands if c[1] >= 0.25 * big), key=lambda c: (c[1], -c[0]))
    x, y, fw, fh = f[0] / w, f[1] / h, f[2] / w, f[3] / h
    cx, cy = x + fw / 2, y + fh * 0.55
    return tuple(float(v) for v in (cx - fw * 0.25, cy - fh * 0.2, cx + fw * 0.25, cy + fh * 0.2)) + (k,), float(fw)


def export_one(lr, path, dest, long_edge):
    """Export one photo and return its file. The bridge's `files` lists everything recently written to dest, which
    can include other photos exported moments earlier, so pick by name and remove any stale copy first."""
    dest = os.path.abspath(dest)          # Lightroom rejects relative destinations
    os.makedirs(dest, exist_ok=True)
    stem = os.path.splitext(os.path.basename(path))[0].lower()
    for f in os.listdir(dest):
        if os.path.splitext(f)[0].lower() == stem:
            os.remove(os.path.join(dest, f))
    files = lr.export(dest, paths=[path], long_edge=long_edge, quality=90, sharpen_level=1, timeout=180)['files']
    match = [f for f in files if os.path.splitext(os.path.basename(f))[0].lower() == stem]
    if len(match) != 1:
        raise RuntimeError(f'export of {path} produced {files}')
    return match[0]


def wb_mode(adj):
    """WB offsets only persist with WhiteBalance=Custom; with 'As Shot' Lightroom later resets them."""
    if 'Temperature' in adj:                     # raw: absolute Kelvin / tint are always explicit
        return {'WhiteBalance': 'Custom'}
    return {'WhiteBalance': 'Custom'} if adj.get('IncrementalTemperature') or adj.get('IncrementalTint') else {'WhiteBalance': 'As Shot'}


def initial_adj(develop):
    """Starting point for calibration. Raw files (ARW/DNG) carry absolute Temperature/Tint; JPGs only incremental offsets."""
    if develop.get('Temperature') is not None:
        return {'Exposure2012': 0.0, 'Temperature': int(develop['Temperature']), 'Tint': int(develop.get('Tint') or 0)}
    return {'Exposure2012': 0.0, 'IncrementalTemperature': 0, 'IncrementalTint': 0}


def adj_text(adj):
    if 'Temperature' in adj:
        return 'EV {:+.2f} {}K t{:+d}'.format(adj['Exposure2012'], adj['Temperature'], adj['Tint'])
    return 'EV {Exposure2012:+.2f} T {IncrementalTemperature:+d} t {IncrementalTint:+d}'.format(**adj)


# WB axes: (adj key, Lab channel it drives, to/from a linear control variable, default gain per unit, clamp).
# Raw temperature is controlled in log2(Kelvin) so the gain is roughly constant across the range.
_AXES = {
    'IncrementalTemperature': ('b', lambda v: v, lambda x: int(round(x)), 1 / 1.2, (-40, 40)),
    'IncrementalTint': ('a', lambda v: v, lambda x: int(round(x)), 1.0, (-30, 30)),
    'Temperature': ('b', math.log2, lambda x: int(round(2 ** x / 10) * 10), 40.0, (math.log2(2500), math.log2(12000))),
    'Tint': ('a', lambda v: v, lambda x: int(round(x)), 0.4, (-60, 80)),
}


MIN_WHITE = 8.0     # % of frame that must be near-white before WB is balanced on whites instead of skin


def _wb_view(style, meas):
    """(target, measurement) dicts in the space WB is solved in: white areas when the style defines a white target and
    the frame has enough of them, else skin."""
    if style.get('white') and meas.get('wfrac', 0) >= MIN_WHITE and 'wa' in meas:
        return {'a': style['white']['a'], 'b': style['white']['b']}, {'a': meas['wa'], 'b': meas['wb']}, 'white'
    return style['skin'], meas, 'skin'


def step(adj, meas, tgt, max_ev, prev=None, style=None):
    """One update toward the skin target. Exposure: L* ~ Y^(1/3) -> stops = 3*log2(Lt/L), damped.
    WB: Newton step per axis, using the gain measured between the last two iterations (secant) when it is sane,
    else a default gain; damped to avoid overshoot."""
    new = {'Exposure2012': round(max(-max_ev, min(max_ev, adj['Exposure2012'] + 0.8 * 3 * math.log2(tgt['L'] / meas['L']))), 2)}
    if style is not None:
        tgt, wmeas, mode = _wb_view(style, meas)
        pmeas = _wb_view(style, prev['meas'])[1] if prev is not None and _wb_view(style, prev['meas'])[2] == mode else None
        meas = wmeas
        prev = {'adj': prev['adj'], 'meas': pmeas} if pmeas is not None else None
    for key, (ch, fwd, back, g0, (lo, hi)) in _AXES.items():
        if key not in adj:
            continue
        x = fwd(adj[key])
        g = g0
        if prev is not None and abs(x - fwd(prev['adj'][key])) > 1e-6:
            gs = (meas[ch] - prev['meas'][ch]) / (x - fwd(prev['adj'][key]))
            if 0.25 * g0 < gs < 4 * g0:          # same sign and plausible size
                g = gs
        new[key] = back(max(lo, min(hi, x + 0.85 * (tgt[ch] - meas[ch]) / g)))
    return new


def calibrate(lr, path, box, style, tmp, iters=3, max_ev=0.9, long_edge=800, history='Pic Agent', start=None, extra=None):
    """Apply style, then iterate exposure/WB until the skin patch hits style['skin']. Leaves the final settings applied.
    box=None: detect the face on the first export (respects the user's crop/rotation); returns (None, hist) if none found.
    start: initial adj (see initial_adj); extra: per-photo settings merged over the style (e.g. noise reduction).
    Returns (adj, hist); hist[-1]['meas'] is the measurement of the final settings."""
    adj = dict(start or {'Exposure2012': 0.0, 'IncrementalTemperature': 0, 'IncrementalTint': 0})
    hist = []
    for it in range(iters + 1):
        lr.apply_develop(paths=[path], settings={**style['settings'], **(extra or {}), **adj, **wb_mode(adj)}, history=history)
        f = export_one(lr, path, tmp, long_edge)
        if box is None:
            box, _ = detect_subject(f)
            if box is None:
                return None, hist
        meas = measure(f, box)
        hist.append({'adj': dict(adj), 'meas': meas, 'box': list(box)})
        if it == iters:
            break
        adj = step(adj, meas, style['skin'], max_ev, hist[-2] if len(hist) > 1 else None, style)
    return adj, hist
