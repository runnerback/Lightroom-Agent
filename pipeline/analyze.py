#!/usr/bin/env python3
"""Phase 1 of culling: per-photo technical metrics, read-only.

For every JPG in a folder:
  * decode at 1/4 scale (fast JPEG draft mode), honour EXIF orientation
  * global + face-region sharpness (variance of Laplacian)
  * exposure stats (mean luma, clipped highlights %, crushed shadows %, face luma)
  * largest face (MediaPipe), eye-aspect-ratio per eye (FaceMesh) -> eyes open/closed
  * 16x16 dHash + capture time for burst / near-duplicate grouping
  * 800px thumbnail for contact sheets
Writes <out>/metrics.jsonl and <out>/thumbs/<name>.jpg.

Usage: analyze.py <folder> <out_dir> [--workers 8] [--limit N]
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context

import numpy as np

# per-process globals (initialised in _init)
_fd = None
_fm = None
_cv2 = None
_Image = None
_ImageOps = None


MODELS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models')


def _init():
    global _fd, _fm, _cv2, _Image, _ImageOps
    os.environ.setdefault('GLOG_minloglevel', '2')
    import cv2
    from PIL import Image, ImageOps
    _cv2, _Image, _ImageOps = cv2, Image, ImageOps
    # face detection: OpenCV YuNet (robust across face sizes)
    _fd = cv2.FaceDetectorYN.create(os.path.join(MODELS, 'face_detection_yunet_2023mar.onnx'), '', (320, 320),
                                    score_threshold=0.6, nms_threshold=0.3, top_k=50)
    # landmarks + blendshapes: MediaPipe Tasks FaceLandmarker
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions
    from mediapipe.tasks.python import vision
    opts = vision.FaceLandmarkerOptions(base_options=BaseOptions(model_asset_path=os.path.join(MODELS, 'face_landmarker.task')),
                                        running_mode=vision.RunningMode.IMAGE, num_faces=1,
                                        min_face_detection_confidence=0.4, output_face_blendshapes=True)
    _fm = (mp, vision.FaceLandmarker.create_from_options(opts))


def _detect_faces_once(rgb, min_score=0.7):
    """All faces via YuNet as (x0,y0,x1,y1,score), largest first. Half-size pass first (fast),
    full quarter-res pass only if nothing was found (small faces)."""
    h, w = rgb.shape[:2]
    bgr = _cv2.cvtColor(rgb, _cv2.COLOR_RGB2BGR)
    for scale in (0.5, 1.0):
        img = bgr if scale == 1.0 else _cv2.resize(bgr, (int(w * scale), int(h * scale)), interpolation=_cv2.INTER_AREA)
        _fd.setInputSize((img.shape[1], img.shape[0]))
        _, faces = _fd.detect(img)
        out = []
        if faces is not None:
            for f in faces:
                if float(f[14]) < min_score:
                    continue
                x, y, fw, fh = f[0] / scale, f[1] / scale, f[2] / scale, f[3] / scale
                x0, y0 = max(0, int(x)), max(0, int(y))
                x1, y1 = min(w, int(x + fw)), min(h, int(y + fh))
                # faces under MIN_FACE of the frame width are passers-by (street, crowds): judge the frame without them
                if x1 - x0 > 8 and y1 - y0 > 8 and (x1 - x0) / w >= MIN_FACE:
                    out.append((x0, y0, x1, y1, float(f[14])))
        if out:
            out.sort(key=lambda r: -(r[2] - r[0]) * (r[3] - r[1]))
            return out[:4]
    return []


def _detect_faces(rgb):
    """Try the upright image first, then rotated copies (people lying down, rotated frames).
    Returns (faces, rotated_rgb, rotation_degrees)."""
    for k in (0, 1, 3, 2):            # 0, 90, 270, 180 degrees
        r = rgb if k == 0 else np.ascontiguousarray(np.rot90(rgb, k))
        faces = _detect_faces_once(r)
        if faces:
            return faces, r, 90 * k
    return [], rgb, 0


def _face_metrics(rgb, gray, box):
    """Sharpness, luma, landmarks-based eye/smile metrics for one face box."""
    h, w = gray.shape[:2]
    x0, y0, x1, y1, score = box
    fw, fh = x1 - x0, y1 - y0
    m = {'x': x0 / w, 'y': y0 / h, 'w': fw / w, 'h': fh / h, 'score': score,
         'cx': (x0 + x1) / 2 / w, 'cy': (y0 + y1) / 2 / h, 'frac': fw * fh / (w * h)}
    fg = gray[y0:y1, x0:x1]
    m['sharp'] = _lapvar(fg)
    m['sharp_n'] = _sharp_norm(fg)
    m['luma'] = float(fg.mean())
    pad = int(0.6 * max(fw, fh))
    cx0, cy0 = max(0, x0 - pad), max(0, y0 - pad)
    cx1, cy1 = min(w, x1 + pad), min(h, y1 + pad)
    crop = np.ascontiguousarray(rgb[cy0:cy1, cx0:cx1])
    if crop.shape[0] < 256 or crop.shape[1] < 256:
        k = 256 / max(1, min(crop.shape[0], crop.shape[1]))
        crop = np.ascontiguousarray(_cv2.resize(crop, (int(crop.shape[1] * k), int(crop.shape[0] * k)), interpolation=_cv2.INTER_CUBIC))
    mp, lmk = _fm
    mres = lmk.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=crop))
    if mres.face_landmarks:
        lm = mres.face_landmarks[0]
        ch, cw = crop.shape[:2]
        pts = [(l.x * cw, l.y * ch) for l in lm]
        m['ear_l'] = _ear(pts, LEFT_EYE)
        m['ear_r'] = _ear(pts, RIGHT_EYE)
        nx = pts[1][0]; lx = pts[234][0]; rx = pts[454][0]
        m['yaw'] = float((nx - (lx + rx) / 2) / max(1.0, abs(rx - lx)))
        if mres.face_blendshapes:
            bs = {b.category_name: b.score for b in mres.face_blendshapes[0]}
            m['blink_l'] = float(bs.get('eyeBlinkLeft', 0))
            m['blink_r'] = float(bs.get('eyeBlinkRight', 0))
            m['smile'] = float(max(bs.get('mouthSmileLeft', 0), bs.get('mouthSmileRight', 0)))
            m['mouth_open'] = float(bs.get('jawOpen', 0))
    return m


SUBJECT = os.environ.get('LIGHTROOM_AGENT_SUBJECT', 'main')
MIN_FACE = 0.04     # same as style_lib.MIN_FACE


def _pick_subject(faces):
    """'main' (default): the largest face. 'child': a baby/child next to adults is normally the smaller head, so take
    the smallest face that is still at least 25% of the largest (ignores tiny false hits)."""
    if not faces:
        return None
    if SUBJECT != 'child':
        return max(range(len(faces)), key=lambda i: faces[i]['frac'])
    big = max(f['frac'] for f in faces)
    cands = [i for i, f in enumerate(faces) if f['frac'] >= 0.25 * big]
    return min(cands, key=lambda i: faces[i]['frac'])


LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]


def _ear(pts, idx):
    p = [np.array(pts[i]) for i in idx]
    v1 = np.linalg.norm(p[1] - p[5])
    v2 = np.linalg.norm(p[2] - p[4])
    h = np.linalg.norm(p[0] - p[3])
    return float((v1 + v2) / (2.0 * h)) if h > 0 else 0.0


def _lapvar(gray):
    return float(_cv2.Laplacian(gray, _cv2.CV_64F).var())


def _sharp_norm(gray, width=256):
    """Laplacian variance on a fixed-width, lightly blurred copy: comparable across face sizes,
    and much less inflated by high-ISO noise than the raw value."""
    h, w = gray.shape[:2]
    if w < 8 or h < 8:
        return 0.0
    k = width / w
    g = _cv2.resize(gray, (width, max(8, int(h * k))), interpolation=_cv2.INTER_AREA)
    g = _cv2.GaussianBlur(g, (3, 3), 0)
    return float(_cv2.Laplacian(g, _cv2.CV_64F).var())


def _dhash(gray, size=16):
    small = _cv2.resize(gray, (size + 1, size), interpolation=_cv2.INTER_AREA)
    diff = small[:, 1:] > small[:, :-1]
    return ''.join('%x' % int(''.join('1' if b else '0' for b in row[i:i + 4]), 2)
                   for row in diff for i in range(0, size, 4))


def _exif(img):
    out = {}
    try:
        ex = img.getexif()
        ifd = ex.get_ifd(0x8769)
        dt = ifd.get(0x9003) or ex.get(0x0132)
        sub = ifd.get(0x9291)
        out['datetime'] = str(dt) if dt else None
        out['subsec'] = str(sub) if sub else None
        out['iso'] = ifd.get(0x8827)
        et = ifd.get(0x829A)
        out['shutter'] = float(et) if et else None
        fn = ifd.get(0x829D)
        out['aperture'] = float(fn) if fn else None
        fl = ifd.get(0x920A)
        out['focal'] = float(fl) if fl else None
    except Exception:
        pass
    return out


def analyze_one(path, thumb_dir):
    t0 = time.time()
    name = os.path.basename(path)
    rec = {'name': name, 'path': path}
    try:
        img = _Image.open(path)
        rec.update(_exif(img))
        full_w, full_h = img.size
        img.draft('RGB', (full_w // 4, full_h // 4))
        img = img.convert('RGB')
        img = _ImageOps.exif_transpose(img)
        w, h = img.size
        rec['w'], rec['h'] = w * 4, h * 4
        rec['portrait'] = h > w
        rgb = np.asarray(img)
        gray = _cv2.cvtColor(rgb, _cv2.COLOR_RGB2GRAY)

        # exposure
        rec['luma_mean'] = float(gray.mean())
        rec['clip_hi'] = float((gray >= 250).mean() * 100)
        rec['clip_lo'] = float((gray <= 5).mean() * 100)
        rec['sharp_global'] = _lapvar(gray)
        rec['sharp_global_n'] = _sharp_norm(gray, 1024)
        rec['dhash'] = _dhash(gray)

        # faces: metrics for every face, then pick the subject
        boxes, rgb_r, rot = _detect_faces(rgb)
        gray_r = gray if rot == 0 else np.ascontiguousarray(np.rot90(gray, rot // 90))
        faces = [_face_metrics(rgb_r, gray_r, b) for b in boxes]
        rec['n_faces'] = len(faces)
        rec['face_rot'] = rot
        rec['faces'] = faces
        rec['face'] = None
        rec['ear_l'] = rec['ear_r'] = rec['blink_l'] = rec['blink_r'] = None
        si = _pick_subject(faces)
        if si is not None:
            f = faces[si]
            rec['subject'] = si
            rec['face'] = {k: f[k] for k in ('x', 'y', 'w', 'h', 'score', 'cx', 'cy')}
            rec['face_frac'] = f['frac']
            rec['face_sharp'] = f['sharp']
            rec['face_sharp_n'] = f['sharp_n']
            rec['face_luma'] = f['luma']
            for k in ('ear_l', 'ear_r', 'blink_l', 'blink_r', 'yaw', 'smile', 'mouth_open'):
                if k in f:
                    rec[k] = f[k]
        # thumbnail (long edge 800)
        tw = 800 if w >= h else int(800 * w / h)
        th = int(800 * h / w) if w >= h else 800
        tpath = os.path.join(thumb_dir, os.path.splitext(name)[0] + '.jpg')
        if not os.path.exists(tpath):
            img.resize((tw, th), _Image.LANCZOS).save(tpath, quality=85, optimize=True)
        rec['ok'] = True
    except Exception as e:  # keep going, record failure
        rec['ok'] = False
        rec['error'] = f'{type(e).__name__}: {e}'
    rec['secs'] = round(time.time() - t0, 2)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('out')
    ap.add_argument('--workers', type=int, default=8)
    ap.add_argument('--limit', type=int)
    args = ap.parse_args()
    files = sorted(f for f in os.listdir(args.folder) if f.lower().endswith(('.jpg', '.jpeg')))
    if args.limit:
        files = files[:args.limit]
    thumb_dir = os.path.join(args.out, 'thumbs')
    os.makedirs(thumb_dir, exist_ok=True)
    out_path = os.path.join(args.out, 'metrics.jsonl')
    done = set()
    if os.path.exists(out_path):
        with open(out_path, encoding='utf-8') as f:
            for line in f:
                try:
                    r = json.loads(line)
                    if r.get('ok'):
                        done.add(r['name'])
                except Exception:
                    pass
    todo = [f for f in files if f not in done]
    print(f'{len(files)} files, {len(done)} already done, {len(todo)} to analyze, {args.workers} workers', flush=True)
    t0 = time.time()
    n = 0
    with open(out_path, 'a', encoding='utf-8') as out, \
            ProcessPoolExecutor(max_workers=args.workers, mp_context=get_context('spawn'), initializer=_init) as ex:
        futs = {ex.submit(analyze_one, os.path.join(args.folder, f), thumb_dir): f for f in todo}
        for fut in as_completed(futs):
            rec = fut.result()
            out.write(json.dumps(rec, ensure_ascii=False) + '\n')
            out.flush()
            n += 1
            if n % 50 == 0 or n == len(todo):
                el = time.time() - t0
                print(f'  {n}/{len(todo)}  {el:.0f}s elapsed, {el / n:.2f}s/photo', flush=True)
    print('done ->', out_path)


if __name__ == '__main__':
    main()
