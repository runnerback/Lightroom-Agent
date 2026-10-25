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


CALIB_KEYS = ('Exposure2012', 'IncrementalTemperature', 'IncrementalTint', 'WhiteBalance')


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
    return {'L': float(L[keep].mean()), 'a': float(A[keep].mean()), 'b': float(B[keep].mean()),
            'clip_hi': float((gray >= 250).mean() * 100)}


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
    for k in (0, 1, 3, 2):
        r = im if k == 0 else np.ascontiguousarray(np.rot90(im, k))
        h, w = r.shape[:2]
        _fd.setInputSize((w, h))
        _, faces = _fd.detect(r)
        faces = [f for f in (faces if faces is not None else []) if float(f[14]) >= min_score and f[2] > 12]
        if not faces:
            continue
        big = max(f[2] * f[3] for f in faces)
        f = min((f for f in faces if f[2] * f[3] >= 0.25 * big), key=lambda f: f[2] * f[3])
        x, y, fw, fh = f[0] / w, f[1] / h, f[2] / w, f[3] / h
        cx, cy = x + fw / 2, y + fh * 0.55
        return tuple(float(v) for v in (cx - fw * 0.25, cy - fh * 0.2, cx + fw * 0.25, cy + fh * 0.2)) + (k,), float(fw)
    return None, 0


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
    """Incremental temp/tint only persist with WhiteBalance=Custom; with 'As Shot' Lightroom later resets them to 0."""
    return {'WhiteBalance': 'Custom'} if adj.get('IncrementalTemperature') or adj.get('IncrementalTint') else {'WhiteBalance': 'As Shot'}


def step(adj, meas, tgt, max_ev):
    """One proportional update. L* ~ Y^(1/3): stops = 3*log2(Lt/L), damped. Temp raises b*, tint raises a*."""
    return {
        'Exposure2012': round(max(-max_ev, min(max_ev, adj['Exposure2012'] + 0.8 * 3 * math.log2(tgt['L'] / meas['L']))), 2),
        'IncrementalTemperature': int(max(-40, min(40, adj['IncrementalTemperature'] + round(1.2 * (tgt['b'] - meas['b']))))),
        'IncrementalTint': int(max(-30, min(30, adj['IncrementalTint'] + round(1.0 * (tgt['a'] - meas['a']))))),
    }


def calibrate(lr, path, box, style, tmp, iters=3, max_ev=0.9, long_edge=800, history='Pic Agent'):
    """Apply style, then iterate exposure/WB until the skin patch hits style['skin']. Leaves the final settings applied.
    box=None: detect the face on the first export (respects the user's crop/rotation); returns (None, hist) if none found.
    Returns (adj, hist); hist[-1]['meas'] is the measurement of the final settings."""
    adj = {'Exposure2012': 0.0, 'IncrementalTemperature': 0, 'IncrementalTint': 0}
    hist = []
    for it in range(iters + 1):
        lr.apply_develop(paths=[path], settings={**style['settings'], **adj, **wb_mode(adj)}, history=history)
        f = export_one(lr, path, tmp, long_edge)
        if box is None:
            box, _ = detect_subject(f)
            if box is None:
                return None, hist
        meas = measure(f, box)
        hist.append({'adj': dict(adj), 'meas': meas, 'box': list(box)})
        if it == iters:
            break
        adj = step(adj, meas, style['skin'], max_ev)
    return adj, hist
