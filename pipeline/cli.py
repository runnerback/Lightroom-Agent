#!/usr/bin/env python3
"""lightroom-agent: one command-line entry point for AI agents (via the skill) and for the MCP server.

  lightroom-agent doctor                         check Python deps, models, plugin, Lightroom connection
  lightroom-agent status                         is Lightroom + plugin reachable? which catalog?
  lightroom-agent catalog                        folders and collections in the catalog (with photo counts)
  lightroom-agent photos  --collection C | --folder F
  lightroom-agent cull    --collection C | --folder F [--run DIR]   technical culling + contact sheets
  lightroom-agent pick    --run DIR --names a b ... --collection NAME   ratings / flags + picks collection
  lightroom-agent collect NAME --collection C --names a b ...        small collection (e.g. proofs) from named photos
  lightroom-agent styles                         styles defined in styles/STYLES.md
  lightroom-agent apply-style STYLE --collection C [--run DIR] [...]   per-photo calibrated colour grade
  lightroom-agent rollback [STYLE] --collection C [--run DIR]         undo: to the original state, or to before STYLE
  lightroom-agent check-boxes STYLE --collection C [--run DIR]        QA sheet of the face patches used
  lightroom-agent import PATH... [--collection C]                     add files to the catalog in place
  lightroom-agent export --collection C --dest DIR [--long-edge N]    (only when the user asks for it)
  lightroom-agent install-plugin                 copy the Lightroom plugin into Lightroom's Modules folder
  lightroom-agent mcp                            run the MCP server on stdio

Long commands print progress lines and end with one line `SUMMARY {json}` that agents can parse.
Work files go to --run DIR, default: ~/Pictures/Lightroom Agent/<collection or folder name>/
"""
import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'bridge'))
sys.path.insert(0, HERE)
from lr_client import LrBridge, LrError  # noqa: E402

RUNS = os.environ.get('LIGHTROOM_AGENT_RUNS', os.path.join(os.path.expanduser('~'), 'Pictures', 'Lightroom Agent'))
PLUGIN_SRC = next((os.path.join(ROOT, 'lightroom_plugin', d) for d in sorted(os.listdir(os.path.join(ROOT, 'lightroom_plugin')))
                   if d.endswith('.lrplugin')), None)
IMAGE_EXT = ('.jpg', '.jpeg', '.tif', '.tiff', '.png', '.heic', '.dng', '.arw', '.cr2', '.cr3', '.nef', '.nrw', '.raf',
             '.orf', '.rw2', '.pef', '.srw', '.x3f', '.3fr', '.iiq', '.erf', '.mos', '.rwl')


def summary(obj):
    print('SUMMARY ' + json.dumps(obj, ensure_ascii=False), flush=True)


def slug(name):
    return re.sub(r'[\\/:*?"<>|]+', '_', name.strip().rstrip('/\\')).strip() or 'run'


def run_dir(args, key):
    d = args.run or os.path.join(RUNS, slug(os.path.basename(key.rstrip('/\\')) or key))
    if not args.run and os.path.realpath(d) == os.path.realpath(key):    # never write work files into the photo folder
        d += '-run'
    os.makedirs(d, exist_ok=True)
    return os.path.abspath(d)


def script(name, *argv):
    subprocess.run([sys.executable, '-I', os.path.join(HERE, name), *map(str, argv)], check=True)


def modules_dir():
    """Folder Lightroom Classic scans for plug-ins at start-up."""
    if platform.system() == 'Darwin':
        return os.path.expanduser('~/Library/Application Support/Adobe/Lightroom/Modules')
    if platform.system() == 'Windows':
        return os.path.join(os.environ.get('APPDATA', ''), 'Adobe', 'Lightroom', 'Modules')
    return None


def source_photos(lr, args):
    if getattr(args, 'collection', None):
        return lr.list_collection(args.collection), args.collection
    if getattr(args, 'folder', None):
        return lr.list_folder(os.path.abspath(args.folder), include_children=getattr(args, 'recursive', False)), args.folder
    sys.exit('give --collection NAME or --folder PATH')


# ---------------------------------------------------------------- commands

def cmd_doctor(args):
    ok = True

    def check(label, good, hint=''):
        nonlocal ok
        ok &= bool(good)
        print(('  ok   ' if good else '  FAIL ') + label + ('' if good or not hint else f'\n         -> {hint}'))

    print('Python', sys.version.split()[0], sys.executable)
    check('Python >= 3.10', sys.version_info >= (3, 10), 'install Python 3.10-3.14 (python.org or Homebrew)')
    for mod in ('numpy', 'cv2', 'PIL', 'mediapipe', 'mcp'):
        try:
            __import__(mod)
            check(f'module {mod}', True)
        except Exception as e:
            check(f'module {mod}', False, f'{e}; run: pip install -r requirements.txt')
    try:
        import cv2
        check('OpenCV face detector (YuNet)', hasattr(cv2, 'FaceDetectorYN'), 'needs opencv >= 4.8')
    except Exception:
        pass
    for m in ('face_detection_yunet_2023mar.onnx', 'face_landmarker.task', 'blaze_face_short_range.tflite'):
        check(f'model {m}', os.path.exists(os.path.join(ROOT, 'models', m)), 'models/ is part of the repository; re-clone it')
    try:
        import style_lib
        check(f'styles: {", ".join(style_lib.load_styles())}', True)
    except Exception as e:
        check('styles/STYLES.md', False, str(e))
    md = modules_dir()
    installed = md and PLUGIN_SRC and os.path.isdir(os.path.join(md, os.path.basename(PLUGIN_SRC)))
    print(f'  info plugin in Lightroom Modules folder: {"yes" if installed else "no"} ({md})')
    try:
        with LrBridge(timeout=10) as lr:
            r = lr.ping()
        check(f'Lightroom connection: {r.get("plugin")} {r.get("version", "")} - catalog {r.get("catalog")}', True)
    except Exception as e:
        check('Lightroom connection', False, f'{str(e).splitlines()[0]}\n            Start Lightroom Classic; if the plugin '
              'is not installed run `lightroom-agent install-plugin` and restart Lightroom (docs/install-plugin.md)')
    print('all good' if ok else 'some checks failed')
    return 0 if ok else 1


def cmd_status(args):
    with LrBridge(timeout=15) as lr:
        r = lr.ping()
    summary(r)


def cmd_catalog(args):
    with LrBridge() as lr:
        r = lr.call('catalog_info', count=True)
    print('catalog:', r['catalog'])
    print('folders:')
    for f in r['folders']:
        print('  ' + '  ' * f['depth'] + f['path'] + (f'  ({f["photos"]})' if f.get('photos') is not None else ''))
    print('collections:')
    for c in r.get('collections', []):
        print(f'  {(c["set"] + " / ") if c.get("set") else ""}{c["name"]}  ({c.get("photos")})')
    summary({'catalog': r['catalog'], 'folders': len(r['folders']), 'collections': [c['name'] for c in r.get('collections', [])]})


def cmd_photos(args):
    with LrBridge() as lr:
        photos, _ = source_photos(lr, args)
    for p in photos:
        print(f'{p["name"]:<34} {p.get("format") or "":<5} rating {p.get("rating", 0)} pick {p.get("pick", 0):>2} '
              f'{p.get("iso") or "":<9} {p.get("datetime") or ""}')
    summary({'count': len(photos), 'names': [p['name'] for p in photos][:500]})


def cmd_cull(args):
    """Previews -> analyze.py -> cull.py -> contact sheets. JPG originals are analysed directly; anything else
    (RAW, DNG, HEIC ...) is first exported by Lightroom as a 2048px JPG preview (with the user's crop)."""
    import contact_sheet
    with LrBridge() as lr:
        photos, key = source_photos(lr, args)
        photos = [p for p in photos if not p.get('virtual')]
        if not photos:
            sys.exit('no photos found')
        run = run_dir(args, key)
        prev = os.path.join(run, 'previews')
        os.makedirs(prev, exist_ok=True)
        by_stem = {}
        for p in photos:
            stem = os.path.splitext(p['name'])[0]
            by_stem.setdefault(stem, []).append(p)
        to_export, linked = [], 0
        for stem, group in by_stem.items():
            target = os.path.join(prev, stem + '.jpg')
            if os.path.exists(target):
                continue
            jpg = next((p for p in group if p['name'].lower().endswith(('.jpg', '.jpeg')) and os.path.exists(p['path'])), None)
            if jpg:
                try:
                    os.symlink(jpg['path'], target)
                except OSError:
                    shutil.copy2(jpg['path'], target)
                linked += 1
            else:
                to_export.append(group[0]['path'])
        print(f'{len(photos)} photos, {len(by_stem)} distinct; {linked} JPG originals linked, {len(to_export)} previews to export', flush=True)
        for i in range(0, len(to_export), 100):
            r = lr.export(prev, paths=to_export[i:i + 100], long_edge=2048, quality=85, sharpen_level=1)
            print(f'  exported {i + r["written"]}/{len(to_export)}', flush=True)
    json.dump({'source': key, 'by': 'collection' if args.collection else 'folder',
               'stems': {s: [p['path'] for p in g] for s, g in by_stem.items()}},
              open(os.path.join(run, 'source.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    script('analyze.py', prev, run, '--workers', args.workers)
    extra = [x for k in ('gap', 'hamming', 'keep_per_group') if getattr(args, k) is not None
             for x in ('--' + k.replace('_', '-'), getattr(args, k))]
    script('cull.py', run, *extra)
    cull = json.load(open(os.path.join(run, 'cull.json'), encoding='utf-8'))
    keeps = [{'name': p['name'], 'caption': f'score {p["score"]:.2f}' + (f' {",".join(p["tech_flags"])}' if p['tech_flags'] else ''),
              'group': p['group']} for p in cull['photos'] if p['decision'] == 'keep']
    rejects = [{'name': p['name'], 'caption': p['reason'], 'group': p['group']} for p in cull['photos'] if p['decision'] == 'reject']
    sheets_dir = os.path.join(run, 'sheets')
    shutil.rmtree(sheets_dir, ignore_errors=True)
    keep_sheets = contact_sheet.build(run, sheets_dir, keeps, cols=6, rows=4, cell=320, prefix='keep')
    reject_sheets = contact_sheet.build(run, sheets_dir, rejects, cols=6, rows=4, cell=320, prefix='reject')
    s = cull['summary']
    summary({'run': run, 'total': s['total'], 'keep': s['keep'], 'reject': s['reject'], 'burst_groups': s['groups'],
             'reject_reasons': s['reject_reasons'], 'keep_sheets': keep_sheets, 'reject_sheets': reject_sheets,
             'cull_json': os.path.join(run, 'cull.json')})


def cmd_pick(args):
    run = os.path.abspath(args.run)
    src = json.load(open(os.path.join(run, 'source.json'), encoding='utf-8'))
    cull = {os.path.splitext(p['name'])[0]: p for p in json.load(open(os.path.join(run, 'cull.json'), encoding='utf-8'))['photos']}
    names = list(args.names or [])
    if args.names_file:
        names += open(args.names_file, encoding='utf-8').read().split()
    if args.all_keeps:
        names += [s for s, p in cull.items() if p['decision'] == 'keep']
    picks = {os.path.splitext(os.path.basename(n))[0] for n in names}
    unknown = sorted(picks - src['stems'].keys())
    if unknown:
        sys.exit(f'not in this run: {", ".join(unknown)}')
    items = []
    for stem, paths in src['stems'].items():
        for path in paths:
            if stem in picks:
                items.append({'path': path, 'rating': args.rating, 'pick': 0, 'label': args.label})
            elif args.mark_others and cull.get(stem, {}).get('decision') == 'reject':
                items.append({'path': path, 'rating': 0, 'pick': -1, 'label': 'none'})
            elif args.mark_others:
                items.append({'path': path, 'rating': 1, 'pick': 0, 'label': 'none'})
    json.dump(items, open(os.path.join(run, 'lr_plan.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    pick_paths = [i['path'] for i in items if i['rating'] == args.rating and i['pick'] == 0 and
                  os.path.splitext(os.path.basename(i['path']))[0] in picks]
    result = {'picks': len(picks), 'photos_rated': len(items), 'collection': args.collection, 'dry_run': args.dry_run}
    if not args.dry_run:
        with LrBridge() as lr:
            lr.set_meta(items, history='Lightroom Agent: culling')
            if args.collection:
                lr.collection_add(args.collection, pick_paths, set_name=args.set, replace=True, show=True)
    summary(result)


def cmd_collect(args):
    """Make (or refill) a collection from named photos of another collection or folder, e.g. a 3-photo proof set."""
    with LrBridge() as lr:
        photos, _ = source_photos(lr, args)
        want = {os.path.splitext(os.path.basename(n))[0] for n in args.names}
        chosen = [p['path'] for p in photos if os.path.splitext(p['name'])[0] in want or p['name'] in args.names]
        missing = sorted(want - {os.path.splitext(os.path.basename(p))[0] for p in chosen})
        if missing:
            sys.exit(f'not found: {", ".join(missing)}')
        lr.collection_add(args.name, chosen, set_name=args.set, replace=True, show=False)
    summary({'collection': args.name, 'photos': len(chosen)})


def cmd_styles(args):
    import style_lib
    styles = style_lib.load_styles()
    for n, st in styles.items():
        w = st.get('white')
        print(f'{n}: {st.get("desc", "")}\n    skin L{st["skin"]["L"]} a{st["skin"]["a"]} b{st["skin"]["b"]}'
              + (f', white a{w["a"]} b{w["b"]}' if w else ''))
    summary({'styles': list(styles), 'doc': style_lib.STYLES_DOC})


def style_dir(args):
    import style_lib
    name = style_lib.resolve_style(style_lib.load_styles(), args.style)
    return name, os.path.join(run_dir(args, args.collection), 'style_applied', name)


def cmd_apply_style(args, rest):
    run = run_dir(args, args.collection)
    script('style_apply.py', run, os.path.join(ROOT, 'styles', 'STYLES.md'), args.style, '--collection', args.collection, *rest)


def cmd_rollback(args):
    """Without a style: back to the settings from before the first style applied with this run directory.
    With a style: back to the settings from just before that style was (first) applied."""
    import style_lib
    if args.style:
        name, d = style_dir(args)
        base = os.path.join(d, 'baseline.json')
    else:
        name, base = 'original', os.path.join(run_dir(args, args.collection), 'style_applied', 'original.json')
    if not os.path.exists(base):
        sys.exit(f'nothing to roll back: {base} does not exist (no style applied with this --run directory)')
    saved = json.load(open(base, encoding='utf-8'))
    keys = {k for st in style_lib.load_styles().values() for k in st['settings']}
    with LrBridge() as lr:
        paths = {p['path'] for p in lr.list_collection(args.collection)}
        items = [{'path': p, 'settings': {**({k: style_lib.NEUTRAL.get(k, 0) for k in keys - set(v)} if not args.style else {}), **v}}
                 for p, v in saved.items() if p in paths]
        lr.apply_develop(items=items, history='Lightroom Agent: undo style')
    summary({'rolled_back_to': 'before ' + name if args.style else 'original', 'photos': len(items), 'collection': args.collection})


def cmd_check_boxes(args):
    name, d = style_dir(args)
    script('check_boxes.py', d)
    summary({'sheet': os.path.join(d, 'boxes.jpg')})


def cmd_import(args):
    paths = []
    for p in args.paths:
        p = os.path.abspath(p)
        if os.path.isdir(p):
            paths += [os.path.join(p, f) for f in sorted(os.listdir(p)) if f.lower().endswith(IMAGE_EXT)]
        else:
            paths.append(p)
    with LrBridge() as lr:
        r = lr.call('import_photos', paths=paths, collection=args.collection, set=args.set if args.collection else None)
    summary(r)


def cmd_export(args):
    with LrBridge() as lr:
        r = lr.export(os.path.abspath(args.dest), collection=args.collection, long_edge=args.long_edge, quality=args.quality)
    summary({k: r[k] for k in ('requested', 'written', 'dest', 'seconds') if k in r})


def cmd_install_plugin(args):
    md = args.modules or modules_dir()
    if not md:
        sys.exit('Lightroom Classic runs on macOS and Windows only; pass --modules DIR to install elsewhere')
    os.makedirs(md, exist_ok=True)
    dest = os.path.join(md, os.path.basename(PLUGIN_SRC))
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    shutil.copytree(PLUGIN_SRC, dest, ignore=shutil.ignore_patterns('.DS_Store', 'DEV_ENABLE_EVAL'))
    print(f'installed {os.path.basename(PLUGIN_SRC)} -> {dest}')
    print('Restart Lightroom Classic (or File > Plug-in Manager > Reload) to load it.')
    summary({'installed': dest})


def cmd_mcp(args):
    import mcp_server
    mcp_server.main()


def main(argv=None):
    ap = argparse.ArgumentParser(prog='lightroom-agent', description=__doc__.split('\n')[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split('\n', 2)[2])
    sub = ap.add_subparsers(dest='cmd', required=True)

    def src(p):
        g = p.add_mutually_exclusive_group(required=True)
        g.add_argument('--collection')
        g.add_argument('--folder')
        p.add_argument('--recursive', action='store_true', help='with --folder: include sub-folders')

    sub.add_parser('doctor')
    sub.add_parser('status')
    sub.add_parser('catalog')
    src(sub.add_parser('photos'))
    p = sub.add_parser('cull'); src(p); p.add_argument('--run'); p.add_argument('--workers', type=int, default=max(2, (os.cpu_count() or 4) - 2))
    p.add_argument('--gap', type=float); p.add_argument('--hamming', type=int); p.add_argument('--keep-per-group', type=int)
    p = sub.add_parser('pick'); p.add_argument('--run', required=True); p.add_argument('--names', nargs='*')
    p.add_argument('--names-file'); p.add_argument('--all-keeps', action='store_true')
    p.add_argument('--collection', help='collection to create with the picks'); p.add_argument('--set', default='Lightroom Agent')
    p.add_argument('--rating', type=int, default=3); p.add_argument('--label', default='green')
    p.add_argument('--no-mark-others', dest='mark_others', action='store_false',
                   help='leave non-picks untouched (default: rejects get the reject flag, other keeps 1 star)')
    p.add_argument('--dry-run', action='store_true')
    p = sub.add_parser('collect'); p.add_argument('name'); src(p); p.add_argument('--names', nargs='+', required=True)
    p.add_argument('--set', default='Lightroom Agent')
    sub.add_parser('styles')
    for name in ('apply-style', 'rollback', 'check-boxes'):
        p = sub.add_parser(name); p.add_argument('style', nargs='?' if name == 'rollback' else None)
        p.add_argument('--collection', required=True); p.add_argument('--run')
    p = sub.add_parser('import'); p.add_argument('paths', nargs='+'); p.add_argument('--collection'); p.add_argument('--set', default='Lightroom Agent')
    p = sub.add_parser('export'); p.add_argument('--collection', required=True); p.add_argument('--dest', required=True)
    p.add_argument('--long-edge', type=int); p.add_argument('--quality', type=int, default=90)
    p = sub.add_parser('install-plugin'); p.add_argument('--modules', help='override the Lightroom Modules folder')
    sub.add_parser('mcp')

    args, rest = ap.parse_known_args(argv)
    if rest and args.cmd != 'apply-style':
        ap.error('unrecognized arguments: ' + ' '.join(rest))
    try:
        if args.cmd == 'apply-style':
            return cmd_apply_style(args, rest)   # remaining options go to style_apply.py (--iters, --max-ev, --only ...)
        return globals()['cmd_' + args.cmd.replace('-', '_')](args)
    except LrError as e:
        print(f'error: {e}', file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as e:
        print(f'error: step failed ({e})', file=sys.stderr)
        return 3


if __name__ == '__main__':
    sys.exit(main() or 0)
