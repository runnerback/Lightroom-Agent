#!/usr/bin/env python3
"""Lightroom Agent <-> Lightroom Classic bridge client (stdlib only).

Talks to the "Lightroom Agent" Lightroom plugin over two localhost TCP ports:
commands go in on 50111 (one JSON object per line), responses come back on 50112.

Library use:
    from lr_client import LrBridge
    with LrBridge(timeout=args.timeout) as lr:
        print(lr.ping())
        photos = lr.list_folder('/Users/me/Pictures/2026/shoot/jpg')
        lr.set_meta([{'path': p['path'], 'rating': 3} for p in photos[:5]])

CLI use:
    python3 lr_client.py ping
    python3 lr_client.py list-folder "/Users/me/Pictures/shoot" --out photos.json
    python3 lr_client.py set-meta --paths a.JPG b.JPG --rating 3 --label green
    python3 lr_client.py export /tmp/out --folder "/Users/me/Pictures/shoot" --min-rating 3 --long-edge 2048
"""
import argparse
try:
    import fcntl
except ImportError:          # Windows
    fcntl = None
    import msvcrt
import json
import os
import socket
import sys
import time
import uuid

HOST = '127.0.0.1'
PORT_IN = 50111
PORT_OUT = 50112


class LrError(RuntimeError):
    pass


class LrBridge:
    """One client at a time: a file lock serialises concurrent scripts, and the connection
    order (commands port first, then responses port) lets the plugin recycle its response
    socket for us. A ping handshake confirms the response channel really is ours."""

    LOCK_PATH = os.path.expanduser('~/.lightroom_agent_bridge.lock')

    def __init__(self, host=HOST, port_in=PORT_IN, port_out=PORT_OUT, timeout=600, lock=True):
        self.host, self.port_in, self.port_out = host, port_in, port_out
        self.timeout = timeout
        self.inp = self.out = self.rf = None
        self._lock = None
        if lock:
            self._lock = open(self.LOCK_PATH, 'w')
            self._flock(True)   # wait for any other bridge client to finish
        try:
            self._connect_in()
        except LrError as e:
            self.close()
            raise LrError(f'{e}\nIs Lightroom Classic running with the Lightroom Agent plugin installed and enabled? '
                          '(File > Plug-in Manager; see docs/install-plugin.md)') from e
        time.sleep(0.3)  # let the plugin notice the new command client and recycle its response socket
        self._connect_out()
        self._handshake()

    def _flock(self, on):
        if fcntl:
            fcntl.flock(self._lock, fcntl.LOCK_EX if on else fcntl.LOCK_UN)
        else:
            self._lock.seek(0)
            msvcrt.locking(self._lock.fileno(), msvcrt.LK_LOCK if on else msvcrt.LK_UNLCK, 1)

    def _connect_out(self):
        last = None
        for _ in range(10):
            try:
                if self.rf:
                    self.rf.close()
                if self.out:
                    self.out.close()
                self.out = socket.create_connection((self.host, self.port_out), timeout=5)
                self.out.settimeout(self.timeout)
                self.rf = self.out.makefile('r', encoding='utf-8', newline='\n')
                return
            except OSError as e:
                last = e
                time.sleep(0.3)
        raise LrError(f'cannot connect to the response port {self.port_out}: {last}')

    def _connect_in(self):
        last = None
        for _ in range(10):
            try:
                if self.inp:
                    self.inp.close()
                self.inp = socket.create_connection((self.host, self.port_in), timeout=5)
                return
            except OSError as e:
                last = e
                time.sleep(0.5)
        raise LrError(f'cannot connect to the command port {self.port_in}: {last}')

    def _handshake(self):
        """Ping until a pong proves both channels are ours. Survives the plugin recycling
        its sockets or being reloaded while we connect."""
        for attempt in range(6):
            try:
                rid = self._send('ping', {})
                resp = self._read_until(rid, timeout=3)
            except (OSError, LrError):
                resp = None
            if resp is not None:
                self.lightroom = resp.get('lightroom')
                self.catalog = resp.get('catalog')
                return
            time.sleep(0.5)
            if attempt >= 1:
                self._connect_in()          # command channel may have been dropped too
                time.sleep(0.3)
            self._connect_out()
        self.close()
        raise LrError('handshake with the Lightroom plugin failed: no response. In Lightroom choose '
                      'Library > Plug-in Extras > Lightroom Agent: Restart service, then retry.')

    def close(self):
        for s in (self.rf, self.inp, self.out):
            try:
                if s:
                    s.close()
            except Exception:
                pass
        self.rf = self.inp = self.out = None
        if self._lock:
            try:
                self._flock(False)
                self._lock.close()
            except Exception:
                pass
            self._lock = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # ------------------------------------------------------------ core
    def _send(self, cmd, params):
        rid = uuid.uuid4().hex[:8]
        line = json.dumps({'id': rid, 'cmd': cmd, 'params': params}, ensure_ascii=False)
        if '\n' in line:
            raise LrError('newline in request payload')
        try:
            self.inp.sendall((line + '\n').encode('utf-8'))
        except OSError as e:
            raise LrError(f'command channel closed ({e}); the plugin may have just been reloaded, retry') from e
        return rid

    def _read_until(self, rid, timeout):
        """Read response lines until one carries `rid`. Returns its result, or None on timeout."""
        self.out.settimeout(timeout)
        while True:
            try:
                raw = self.rf.readline()
            except socket.timeout:
                return None
            if not raw:
                raise LrError('Lightroom closed the response connection')
            raw = raw.strip()
            if not raw:
                continue
            try:
                resp = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if resp.get('id') != rid:
                continue  # response to an older request; ignore
            if not resp.get('ok'):
                raise LrError(resp.get('error', 'unknown error'))
            return resp.get('result')

    def call(self, cmd, timeout=None, **params):
        rid = self._send(cmd, params)
        result = self._read_until(rid, timeout or self.timeout)
        if result is None:
            raise LrError(f'{cmd} did not return within {timeout or self.timeout}s')
        return result

    @staticmethod
    def _chunks(seq, n):
        for i in range(0, len(seq), n):
            yield seq[i:i + n]

    @staticmethod
    def _merge(acc, r):
        for k, v in (r or {}).items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                acc[k] = acc.get(k, 0) + v
            elif isinstance(v, list):
                acc.setdefault(k, []).extend(v)
            else:
                acc[k] = v
        return acc

    # ------------------------------------------------------------ read
    def ping(self):
        return self.call('ping')

    def status(self):
        return self.call('_status')

    def reload_handlers(self):
        """Hot-reload Handlers.lua inside Lightroom (no plugin reload needed)."""
        return self.call('_reload')

    def eval(self, code):
        """Run a Lua snippet inside Lightroom; returns the list of returned values."""
        return self.call('eval', code=code)['values']

    def catalog_info(self, count=False):
        return self.call('catalog_info', count=count)

    def list_folder(self, path, include_children=False):
        return self.call('list_folder', path=path, include_children=include_children)['photos']

    def list_collection(self, name):
        return self.call('list_collection', name=name)['photos']

    def get_meta(self, paths):
        return self.call('get_meta', paths=list(paths))['photos']

    def collection_delete(self, name):
        return self.call('collection_delete', name=name)

    def get_selection(self):
        return self.call('get_selection')['photos']

    def get_develop(self, path):
        return self.call('get_develop', path=path)['settings']

    # ------------------------------------------------------------ UI
    def select(self, paths):
        return self.call('select', paths=list(paths))

    def show_folder(self, path):
        return self.call('show_folder', path=path)

    def show_collection(self, name):
        return self.call('show_collection', name=name)

    # ------------------------------------------------------------ write
    def set_meta(self, items, chunk=150, history=None):
        """items: [{'path': ..., 'rating': 0-5, 'pick': -1/0/1, 'label': 'red|yellow|green|blue|purple|none', 'title':..., 'caption':...}]"""
        acc = {}
        for part in self._chunks(list(items), chunk):
            self._merge(acc, self.call('set_meta', items=part, history=history))
        return acc

    def add_keywords(self, items, chunk=150):
        """items: [{'path': ..., 'keywords': ['a', 'b']}]"""
        acc = {}
        for part in self._chunks(list(items), chunk):
            self._merge(acc, self.call('add_keywords', items=part))
        return acc

    def collection_add(self, name, paths, set_name='Pic Agent', replace=False, show=False):
        return self.call('collection_add', name=name, paths=list(paths), set=set_name, replace=replace, show=show)

    def apply_develop(self, items=None, paths=None, settings=None, history=None, chunk=50):
        """Apply develop settings. Either paths + settings (same for all), or items=[{'path':..., 'settings':{...}}]
        with optional shared `settings` merged underneath each item's own."""
        if items is None:
            items = [{'path': p} for p in (paths or [])]
        acc = {}
        for part in self._chunks(list(items), chunk):
            self._merge(acc, self.call('apply_develop', items=part, settings=settings or {}, history=history, timeout=900))
        return acc

    def export(self, dest, paths=None, collection=None, folder=None, selection=False, filter=None, timeout=3600, **opts):
        """opts: format=JPEG|TIFF|PSD|DNG|ORIGINAL, quality=90, long_edge=None, color_space=sRGB|AdobeRGB|ProPhotoRGB|DisplayP3,
        bit_depth, sharpen=True, sharpen_media=screen|matte|glossy, sharpen_level=1-3, metadata=all|allExceptCameraInfo|copyrightOnly,
        keep_location=False, tokens='{{image_name}}', custom_text, collision=overwrite|skip|rename, raw_settings={...}"""
        params = dict(dest=dest, filter=filter, **opts)
        if paths is not None:
            params['paths'] = list(paths)
        elif collection:
            params['collection'] = collection
        elif folder:
            params['folder'] = folder
        elif selection:
            params['selection'] = True
        return self.call('export', timeout=timeout, **params)


# ---------------------------------------------------------------- CLI
def _load_items(args):
    if getattr(args, 'from_file', None):
        with open(args.from_file, encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, list) else data.get('photos') or data.get('items')
    return [{'path': p} for p in (args.paths or [])]


def _print(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def main(argv=None):
    ap = argparse.ArgumentParser(description='Pic Agent Lightroom bridge client')
    ap.add_argument('--timeout', type=int, default=600, help='seconds to wait for a response (default 600)')
    sub = ap.add_subparsers(dest='cmd', required=True)

    sub.add_parser('ping')
    sub.add_parser('status')
    sub.add_parser('reload')
    p = sub.add_parser('eval'); p.add_argument('code', help='Lua code; may use cat, json, H, cache, log, import')
    p = sub.add_parser('catalog-info'); p.add_argument('--count', action='store_true')
    p = sub.add_parser('list-folder'); p.add_argument('path'); p.add_argument('--children', action='store_true'); p.add_argument('--out')
    p = sub.add_parser('list-collection'); p.add_argument('name'); p.add_argument('--out')
    p = sub.add_parser('selection'); p.add_argument('--out')
    p = sub.add_parser('get-develop'); p.add_argument('path')
    p = sub.add_parser('get-meta'); p.add_argument('paths', nargs='+')
    p = sub.add_parser('collection-delete'); p.add_argument('name')
    p = sub.add_parser('select'); p.add_argument('paths', nargs='+')
    p = sub.add_parser('show-folder'); p.add_argument('path')
    p = sub.add_parser('show-collection'); p.add_argument('name')

    p = sub.add_parser('set-meta', help='set rating/pick/label on photos')
    p.add_argument('--from', dest='from_file', help='JSON list of {path, rating, pick, label}')
    p.add_argument('--paths', nargs='*')
    p.add_argument('--rating', type=int); p.add_argument('--pick', type=int); p.add_argument('--label')

    p = sub.add_parser('keywords'); p.add_argument('--from', dest='from_file'); p.add_argument('--paths', nargs='*'); p.add_argument('--add', nargs='*', default=[])

    p = sub.add_parser('collection'); p.add_argument('name'); p.add_argument('--from', dest='from_file'); p.add_argument('--paths', nargs='*')
    p.add_argument('--set', default='Pic Agent'); p.add_argument('--replace', action='store_true'); p.add_argument('--show', action='store_true')

    p = sub.add_parser('apply-develop'); p.add_argument('--from', dest='from_file', help='JSON list of {path, settings}')
    p.add_argument('--paths', nargs='*'); p.add_argument('--settings', help='JSON object applied to all'); p.add_argument('--history')

    p = sub.add_parser('export'); p.add_argument('dest')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--paths', nargs='+'); g.add_argument('--from', dest='from_file'); g.add_argument('--folder'); g.add_argument('--collection'); g.add_argument('--selection', action='store_true')
    p.add_argument('--min-rating', type=int); p.add_argument('--pick', type=int); p.add_argument('--label')
    p.add_argument('--format', default='JPEG'); p.add_argument('--quality', type=int, default=90); p.add_argument('--long-edge', type=int)
    p.add_argument('--color-space', default='sRGB'); p.add_argument('--no-sharpen', action='store_true'); p.add_argument('--tokens'); p.add_argument('--collision', default='overwrite')

    args = ap.parse_args(argv)
    with LrBridge() as lr:
        if args.cmd == 'ping':
            _print(lr.ping())
        elif args.cmd == 'status':
            _print(lr.status())
        elif args.cmd == 'reload':
            _print(lr.reload_handlers())
        elif args.cmd == 'eval':
            _print(lr.eval(args.code))
        elif args.cmd == 'catalog-info':
            _print(lr.catalog_info(count=args.count))
        elif args.cmd in ('list-folder', 'list-collection', 'selection'):
            if args.cmd == 'list-folder':
                photos = lr.list_folder(args.path, include_children=args.children)
            elif args.cmd == 'list-collection':
                photos = lr.list_collection(args.name)
            else:
                photos = lr.get_selection()
            if args.out:
                with open(args.out, 'w', encoding='utf-8') as f:
                    json.dump(photos, f, ensure_ascii=False, indent=1)
                print(f'{len(photos)} photos -> {args.out}')
            else:
                _print(photos)
        elif args.cmd == 'get-develop':
            _print(lr.get_develop(args.path))
        elif args.cmd == 'get-meta':
            _print(lr.get_meta(args.paths))
        elif args.cmd == 'collection-delete':
            _print(lr.collection_delete(args.name))
        elif args.cmd == 'select':
            _print(lr.select(args.paths))
        elif args.cmd == 'show-folder':
            _print(lr.show_folder(args.path))
        elif args.cmd == 'show-collection':
            _print(lr.show_collection(args.name))
        elif args.cmd == 'set-meta':
            items = _load_items(args)
            for it in items:
                if args.rating is not None: it['rating'] = args.rating
                if args.pick is not None: it['pick'] = args.pick
                if args.label is not None: it['label'] = args.label
            _print(lr.set_meta(items))
        elif args.cmd == 'keywords':
            items = _load_items(args)
            for it in items:
                it.setdefault('keywords', list(args.add))
            _print(lr.add_keywords(items))
        elif args.cmd == 'collection':
            items = _load_items(args)
            _print(lr.collection_add(args.name, [it['path'] for it in items], set_name=args.set, replace=args.replace, show=args.show))
        elif args.cmd == 'apply-develop':
            settings = json.loads(args.settings) if args.settings else None
            items = _load_items(args) if (args.from_file or args.paths) else None
            _print(lr.apply_develop(items=items, settings=settings, history=args.history))
        elif args.cmd == 'export':
            flt = {}
            if args.min_rating is not None: flt['min_rating'] = args.min_rating
            if args.pick is not None: flt['pick'] = args.pick
            if args.label: flt['label'] = args.label
            paths = None
            if args.paths or args.from_file:
                paths = [it['path'] for it in _load_items(args)]
            _print(lr.export(args.dest, paths=paths, folder=args.folder, collection=args.collection, selection=args.selection,
                             filter=flt or None, format=args.format, quality=args.quality, long_edge=args.long_edge,
                             color_space=args.color_space, sharpen=not args.no_sharpen, tokens=args.tokens, collision=args.collision))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except LrError as e:
        print(f'error: {e}', file=sys.stderr)
        sys.exit(2)
