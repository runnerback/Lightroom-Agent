#!/usr/bin/env python3
"""MCP server (stdio) exposing Lightroom Agent to any MCP client: Claude Desktop / Code, Codex, Gemini CLI, Cursor,
WorkBuddy, Trae, Cherry Studio ... Start with `lightroom-agent mcp`.

Each tool wraps a `lightroom-agent` CLI command. Culling and style application take minutes (Lightroom renders every
photo several times), so they run as background jobs: the tool returns a job id, `job_status` reports progress and the
final summary. `view_image` returns contact sheets / overviews as images for clients that can see them.
"""
import io
import json
import os
import subprocess
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cli  # noqa: E402
from mcp.server.mcpserver import Image, MCPServer  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402
from mcp.types import ToolAnnotations  # noqa: E402

DATA = os.environ.get('LIGHTROOM_AGENT_HOME', os.path.join(os.path.expanduser('~'), '.lightroom-agent'))
JOBS = os.path.join(DATA, 'jobs')

INSTRUCTIONS = """Lightroom Agent drives Adobe Lightroom Classic on this computer (through its plugin) to cull and colour-grade photos.
Typical flow: lightroom_status -> list_catalog -> cull_photos (job) -> view_image on the keep sheets, choose the best
frames with the user -> pick_photos (ratings + picks collection) -> list_styles -> apply_style on 2-3 photos first, show
the user, then the whole collection (job) -> view_image on the overview and check_boxes sheets to check quality.
Rules: never change the user's crop/rotation (the tools don't); apply_style keeps a baseline so rollback_style can undo it;
final exports are the user's call - only use export_photos when they ask. Reply in the user's language."""

server = MCPServer('lightroom-agent', instructions=INSTRUCTIONS, version='0.1.0')
READ = ToolAnnotations(read_only_hint=True, open_world_hint=False)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False)


def _cli(*argv, timeout=600):
    """Run a short CLI command and return its SUMMARY json (or the error text)."""
    r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'cli.py'), *map(str, argv)],
                       capture_output=True, text=True, timeout=timeout)
    out = r.stdout.strip().splitlines()
    summ = next((json.loads(line[8:]) for line in reversed(out) if line.startswith('SUMMARY ')), None)
    if r.returncode != 0:
        return {'ok': False, 'error': (r.stderr.strip() or '\n'.join(out[-5:]))[-2000:]}
    return {'ok': True, **(summ or {}), 'output': '\n'.join(out[-60:]) if summ is None else None}


def _job(*argv):
    os.makedirs(JOBS, exist_ok=True)
    jid = time.strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:6]
    log = open(os.path.join(JOBS, jid + '.log'), 'w', encoding='utf-8')
    proc = subprocess.Popen([sys.executable, '-I', '-u', os.path.join(HERE, 'cli.py'), *map(str, argv)],
                            stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    json.dump({'id': jid, 'pid': proc.pid, 'argv': list(map(str, argv)), 'started': time.time()},
              open(os.path.join(JOBS, jid + '.json'), 'w', encoding='utf-8'))
    _procs[jid] = proc
    return {'ok': True, 'job_id': jid, 'hint': 'poll job_status(job_id) every 30-60 s; this takes several minutes'}


_procs = {}


def _src(collection, folder):
    if bool(collection) == bool(folder):
        raise ToolError('give exactly one of collection or folder')
    return ['--collection', collection] if collection else ['--folder', folder]


@server.tool(annotations=READ)
def lightroom_status() -> dict:
    """Check that Lightroom Classic is running with the Lightroom Agent plugin; returns version and open catalog."""
    return _cli('status', timeout=30)


@server.tool(annotations=READ)
def list_catalog() -> dict:
    """List the catalog's folders and collections with photo counts."""
    return _cli('catalog', timeout=120)


@server.tool(annotations=READ)
def list_photos(collection: str = '', folder: str = '') -> dict:
    """List photos (name, format, rating, flag, ISO, capture time) of one collection or one catalog folder path."""
    return _cli('photos', *_src(collection, folder), timeout=120)


@server.tool(annotations=WRITE)
def cull_photos(collection: str = '', folder: str = '', run_dir: str = '', subject: str = 'main') -> dict:
    """Start technical culling (job): sharpness, closed eyes, exposure, burst duplicates. Writes nothing to Lightroom.
    subject: 'main' (largest face) or 'child' (a baby/child held by or next to adults).
    Result: keep/reject contact sheets (view them with view_image) and cull.json in run_dir. Then call pick_photos."""
    return _job('cull', *_src(collection, folder), '--subject', subject, *(['--run', run_dir] if run_dir else []))


@server.tool(annotations=WRITE)
def pick_photos(run_dir: str, names: list[str], collection: str = '', mark_others: bool = True, dry_run: bool = False) -> dict:
    """Write culling decisions to Lightroom: `names` (file names or stems) get 3 stars + green label and go into
    `collection`; with mark_others, culled rejects get the reject flag and other keeps 1 star."""
    argv = ['pick', '--run', run_dir, '--names', *names] + (['--collection', collection] if collection else [])
    argv += [] if mark_others else ['--no-mark-others']
    return _cli(*argv, *(['--dry-run'] if dry_run else []), timeout=600)


@server.tool(annotations=WRITE)
def make_collection(name: str, names: list[str], from_collection: str = '', from_folder: str = '') -> dict:
    """Create/refill collection `name` with the named photos of another collection or folder (e.g. a 3-photo proof
    set to try a style on before grading the whole shoot)."""
    return _cli('collect', name, *_src(from_collection, from_folder), '--names', *names, timeout=300)


@server.tool(annotations=READ)
def list_styles() -> dict:
    """Colour styles (name, description, skin / white targets). Each style is one Markdown file: styles/<name>.md in
    the repository, or the user's own in ~/.lightroom-agent/styles/ (guide: styles/README.md)."""
    import style_lib
    return {'ok': True, 'guide': os.path.join(style_lib.STYLES_DIR, 'README.md'), 'user_styles_dir': style_lib.USER_STYLES_DIR,
            'files': style_lib.style_files(),
            'styles': {n: {'desc': s.get('desc'), 'skin': s['skin'], 'white': s.get('white')} for n, s in style_lib.load_styles().items()}}


@server.tool(annotations=WRITE)
def apply_style(style: str, collection: str, run_dir: str = '', only: list[str] | None = None, skin_wb: list[str] | None = None,
                refine: bool = False, reuse_calib: bool = False, max_ev: float = 0.9, iters: int = 3, subject: str = 'main') -> dict:
    """Start applying a style (job) to every photo of a collection, calibrating exposure and white balance per photo on
    the subject's face. style: full name or letter (A, B, C, D...). only: recalibrate just these photos (needs refine).
    skin_wb: photos whose 'whites' are really cream/beige, balanced on skin instead. reuse_calib: re-apply a previous
    calibration without re-measuring. RAW shoots usually want max_ev=1.5, iters=4. subject: 'main' (largest face) or
    'child' (a baby/child next to adults). Crops are never changed."""
    argv = ['apply-style', style, '--collection', collection, '--subject', subject] + (['--run', run_dir] if run_dir else [])
    argv += ['--max-ev', max_ev, '--iters', iters] + (['--refine'] if refine else []) + (['--reuse-calib'] if reuse_calib else [])
    argv += (['--only', *only] if only else []) + (['--skin-wb', *skin_wb] if skin_wb else [])
    return _job(*argv)


@server.tool(annotations=WRITE)
def rollback_style(collection: str, style: str = '', run_dir: str = '') -> dict:
    """Undo styles. Without style: back to the photos' original settings (before the first style of this run).
    With style: back to the settings from just before that style was applied."""
    return _cli('rollback', *([style] if style else []), '--collection', collection, *(['--run', run_dir] if run_dir else []), timeout=900)


@server.tool(annotations=READ)
def check_boxes(style: str, collection: str, run_dir: str = '', subject: str = 'main') -> dict:
    """QA: draw the face patch each photo was calibrated on (red) and today's detection (green) into boxes.jpg.
    A red box off the face means that photo was calibrated on the wrong thing - re-run apply_style with only=[...]"""
    return _cli('check-boxes', style, '--collection', collection, '--subject', subject, *(['--run', run_dir] if run_dir else []), timeout=600)


@server.tool(annotations=READ)
def job_status(job_id: str) -> dict:
    """Progress of a background job: running / done / failed, the last log lines, and the final summary when done."""
    meta_path = os.path.join(JOBS, job_id + '.json')
    if not os.path.exists(meta_path):
        return {'ok': False, 'error': f'unknown job {job_id}'}
    meta = json.load(open(meta_path, encoding='utf-8'))
    lines = open(os.path.join(JOBS, job_id + '.log'), encoding='utf-8', errors='replace').read().splitlines()
    proc = _procs.get(job_id)
    if proc is not None:
        code = proc.poll()
    else:                                   # started by an earlier server process
        try:
            os.kill(meta['pid'], 0)
            code = None
        except OSError:
            code = 0 if any(line.startswith('SUMMARY ') for line in lines) else 1
    summ = next((json.loads(line[8:]) for line in reversed(lines) if line.startswith('SUMMARY ')), None)
    state = 'running' if code is None else ('done' if code == 0 else 'failed')
    return {'ok': state != 'failed', 'state': state, 'elapsed_s': round(time.time() - meta['started']),
            'command': ' '.join(meta['argv']), 'summary': summ,
            'log_tail': [line for line in lines if not line.startswith('SUMMARY ')][-15:]}


def _allowed(path):
    """view_image only serves images produced by this tool (inside a run directory), not arbitrary files."""
    p = os.path.realpath(path)
    if p.startswith(os.path.realpath(cli.RUNS) + os.sep):
        return True
    d = os.path.dirname(p)
    for _ in range(4):
        if any(os.path.exists(os.path.join(d, m)) for m in ('source.json', 'calib.json', 'baseline.json', 'cull.json')):
            return True
        d = os.path.dirname(d)
    return False


@server.tool(annotations=READ)
def view_image(path: str, max_size: int = 1600) -> Image:
    """Return a contact sheet / overview / QA image (from a summary of the other tools) so you can look at it."""
    from PIL import Image as PILImage
    if not path.lower().endswith(('.jpg', '.jpeg', '.png')) or not os.path.isfile(path) or not _allowed(path):
        raise ToolError('only .jpg/.png images inside a Lightroom Agent run directory can be viewed')
    im = PILImage.open(path).convert('RGB')
    im.thumbnail((max_size, max_size))
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=85)
    return Image(data=buf.getvalue(), format='jpeg')


@server.tool(annotations=WRITE)
def import_photos(paths: list[str], collection: str = '') -> dict:
    """Add image files or folders to the Lightroom catalog in place (no copying), optionally into a collection."""
    return _cli('import', *paths, *(['--collection', collection] if collection else []), timeout=900)


@server.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, open_world_hint=False,
                                         title='Export photos (only when the user asks)'))
def export_photos(collection: str, dest: str, long_edge: int = 0, quality: int = 90, preset: str = '') -> dict:
    """Export a collection as JPEG into dest. Final exports are the user's decision: only call this when they ask.
    preset: title of one of the user's Lightroom export presets; when given, its size/format/naming/metadata are used
    (long_edge and quality are ignored) and only the destination is replaced by dest."""
    opts = ['--preset', preset] if preset else [*(['--long-edge', long_edge] if long_edge else []), '--quality', quality]
    return _cli('export', '--collection', collection, '--dest', dest, *opts, timeout=7200)


def main():
    server.run('stdio')


if __name__ == '__main__':
    main()
