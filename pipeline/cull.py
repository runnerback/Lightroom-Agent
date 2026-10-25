#!/usr/bin/env python3
"""Phase 1b: turn metrics.jsonl into burst groups, quality scores and a proposed decision per photo.

Decisions (nothing is written to Lightroom here):
  reject  - technically unusable: subject face clearly out of focus relative to its neighbours,
            eyes firmly shut, blown out, or a weaker near-duplicate inside a burst
  keep    - passes technical checks (candidate for 1 star)
Each record carries 'reason' so the proposal can be audited on contact sheets.

Sharpness is judged RELATIVE to the photo's time neighbourhood (same scene, same ISO, same face
size), using the noise-normalised metric, so dim ISO-3200 frames and tiny faces are not punished.

Usage: cull.py <run_dir> [--gap 3] [--hamming 20] [--keep-per-group 1]
Writes <run_dir>/cull.json  {summary:{...}, photos:[...]}
"""
import argparse
import json
import math
import os
from datetime import datetime


def hamming(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count('1')


def ts(rec):
    dt = rec.get('datetime')
    if not dt:
        return None
    try:
        t = datetime.strptime(dt, '%Y:%m:%d %H:%M:%S').timestamp()
    except ValueError:
        return None
    sub = rec.get('subsec')
    if sub and sub.strip().isdigit():
        t += int(sub.strip()) / (10 ** len(sub.strip()))
    return t


def median(v):
    v = sorted(v)
    return v[len(v) // 2] if v else None


def neighbourhood_median(recs, i, key, radius, same_face):
    """Median of `key` over up to `radius` neighbours on each side that share the face/no-face state."""
    vals = []
    me = recs[i]
    for j in range(max(0, i - radius), min(len(recs), i + radius + 1)):
        r = recs[j]
        if bool(r.get('face')) != same_face:
            continue
        if r.get(key) is not None:
            vals.append(r[key])
    return median(vals)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run_dir')
    ap.add_argument('--gap', type=float, default=3.0, help='max seconds between burst neighbours')
    ap.add_argument('--hamming', type=int, default=20, help='max dHash distance (of 256 bits) for duplicates')
    ap.add_argument('--keep-per-group', type=int, default=1)
    ap.add_argument('--radius', type=int, default=10, help='neighbourhood (frames each side) for relative sharpness')
    ap.add_argument('--oof', type=float, default=0.40, help='sharpness ratio below which the face is out of focus')
    ap.add_argument('--soft', type=float, default=0.65, help='sharpness ratio below which the face is soft')
    ap.add_argument('--blink-shut', type=float, default=0.65, help='both eyes blink score above this = shut')
    ap.add_argument('--ear-shut', type=float, default=0.14, help='and both eye aspect ratios below this')
    args = ap.parse_args()

    recs = [json.loads(l) for l in open(os.path.join(args.run_dir, 'metrics.jsonl'), encoding='utf-8')]
    recs = [r for r in recs if r.get('ok')]
    for r in recs:
        r['t'] = ts(r)
    recs.sort(key=lambda r: (r['t'] or 0, r['name']))

    # ---------------- per-photo technical verdict
    for i, r in enumerate(recs):
        reasons, soft = [], []
        score = 0.0
        has_face = bool(r.get('face'))
        if has_face:
            ref = neighbourhood_median(recs, i, 'face_sharp_n', args.radius, True) or r['face_sharp_n']
            ratio = r['face_sharp_n'] / ref if ref else 1.0
            r['sharp_ratio'] = round(ratio, 3)
            score += math.log2(max(0.05, ratio)) * 1.5
            if ratio < args.oof:
                reasons.append('face-out-of-focus')
            elif ratio < args.soft:
                soft.append('face-soft')
                score -= 0.3
            score += min(0.5, r.get('face_frac', 0) * 10)
            bl, br = r.get('blink_l'), r.get('blink_r')
            el, er = r.get('ear_l'), r.get('ear_r')
            if bl is not None and br is not None:
                bmin = min(bl, br)
                if bmin >= args.blink_shut and el is not None and er is not None and max(el, er) <= args.ear_shut:
                    reasons.append('eyes-shut')
                elif bmin >= 0.5:
                    soft.append('eyes-narrow')
                    score -= 0.5
                else:
                    score += 0.4 * (1 - bmin)
                r['blink_min'] = round(bmin, 3)
            if r.get('smile'):
                score += min(0.6, r['smile'])
            fl = r.get('face_luma')
            if fl is not None:
                if fl > 238:
                    reasons.append('face-blown')
                elif fl < 40:
                    soft.append('face-dark')
                    score -= 0.4
                score -= abs(fl - 150) / 300
        else:
            ref = neighbourhood_median(recs, i, 'sharp_global_n', args.radius, False) or r['sharp_global_n']
            ratio = r['sharp_global_n'] / ref if ref else 1.0
            r['sharp_ratio'] = round(ratio, 3)
            score += math.log2(max(0.05, ratio)) * 1.0 - 0.3
            if ratio < args.oof:
                soft.append('soft')
                score -= 0.5
        if r.get('clip_hi', 0) > 35:
            reasons.append('highlights-clipped')
        if r.get('shutter') and r['shutter'] > 1 / 100 and ('face-soft' in soft or 'face-out-of-focus' in reasons):
            soft.append('slow-shutter')
        r['score'] = round(score, 3)
        r['tech_flags'] = reasons + soft
        r['decision'] = 'reject' if reasons else 'keep'
        r['reason'] = ','.join(reasons + soft) if (reasons or soft) else 'ok'

    # ---------------- burst / near-duplicate groups (time-adjacent + visually similar)
    gid = 0
    prev = None
    for r in recs:
        new_group = True
        if prev is not None and r['t'] and prev['t']:
            close = (r['t'] - prev['t']) <= args.gap
            similar = hamming(r['dhash'], prev['dhash']) <= args.hamming
            new_group = not (close and similar)
        if new_group:
            gid += 1
        r['group'] = gid
        prev = r
    groups = {}
    for r in recs:
        groups.setdefault(r['group'], []).append(r)
    for g, members in groups.items():
        keep = [m for m in members if m['decision'] == 'keep']
        keep.sort(key=lambda m: -m['score'])
        for i, m in enumerate(keep):
            m['group_rank'] = i + 1
            if i >= args.keep_per_group:
                m['decision'] = 'reject'
                m['reason'] = f'dupe-of-{keep[0]["name"]}' + ('' if m['reason'] == 'ok' else ',' + m['reason'])
        for m in members:
            m['group_size'] = len(members)

    n_keep = sum(1 for r in recs if r['decision'] == 'keep')
    reasons = {}
    for r in recs:
        if r['decision'] == 'reject':
            key = r['reason'].split(',')[0]
            key = 'dupe' if key.startswith('dupe-of-') else key
            reasons[key] = reasons.get(key, 0) + 1
    sizes = {}
    for members in groups.values():
        sizes[len(members)] = sizes.get(len(members), 0) + 1
    summary = {'total': len(recs), 'keep': n_keep, 'reject': len(recs) - n_keep, 'groups': len(groups),
               'group_size_hist': dict(sorted(sizes.items())), 'reject_reasons': reasons,
               'with_face': sum(1 for r in recs if r.get('face')),
               'eyes_measured': sum(1 for r in recs if r.get('blink_l') is not None),
               'soft_flags': {k: sum(1 for r in recs if k in r['tech_flags']) for k in ('face-soft', 'eyes-narrow', 'soft', 'face-dark', 'slow-shutter')},
               'params': vars(args)}
    with open(os.path.join(args.run_dir, 'cull.json'), 'w', encoding='utf-8') as f:
        json.dump({'summary': summary, 'photos': recs}, f, ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
