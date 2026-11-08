#!/usr/bin/env python3
"""Release helper (stdlib only).

Tags are plain versions without a "v": 0.3.0, 0.4.0-beta.1.

  python3 scripts/release.py 0.3.0            set 0.3.0 in every version file and stamp CHANGELOG (no git);
                                              then commit, `git tag 0.3.0`, `git push origin main 0.3.0`
  python3 scripts/release.py 0.3.0 --tag      ... and commit "release: 0.3.0" and tag 0.3.0
  python3 scripts/release.py 0.3.0 --push     ... and push the commit and the tag
  python3 scripts/release.py 0.3.0 --dry-run  show what would change
Pushing the tag makes GitHub Actions publish the release (.github/workflows/release.yml).

Used by CI:
  python3 scripts/release.py --check 0.3.0    tag == every version file; Python / Lua syntax; styles parse
  python3 scripts/release.py --notes 0.3.0    release notes (CHANGELOG section + commits + install) on stdout
"""
import argparse
import datetime
import glob
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = 'Runnerback/lightroom-agent'
SEMVER = re.compile(r'^(\d+)\.(\d+)\.(\d+)(-[0-9A-Za-z.-]+)?$')
PLUGIN = 'lightroom_plugin/LightroomAgent.lrplugin'

# file -> (regex with one group around the version, how to write a version)
VERSION_FILES = {
    '.claude-plugin/plugin.json': (r'("version":\s*")([^"]+)(")', lambda v: v),
    f'{PLUGIN}/Server.lua': (r"(VERSION = ')([^']+)(')", lambda v: v),
    'pipeline/mcp_server.py': (r"(version=')([^']+)(')", lambda v: v),
    f'{PLUGIN}/Info.lua': (r'(VERSION = \{ )(major = \d+, minor = \d+, revision = \d+)(, build = \d+ \})',
                           lambda v: 'major = {}, minor = {}, revision = {}'.format(*SEMVER.match(v).groups()[:3])),
}


def git(*args, check=True):
    return subprocess.run(['git', *args], cwd=ROOT, check=check, capture_output=True, text=True).stdout.strip()


def read(rel):
    return open(os.path.join(ROOT, rel), encoding='utf-8').read()


def current_versions():
    out = {}
    for rel, (pat, _) in VERSION_FILES.items():
        m = re.search(pat, read(rel))
        if not m:
            sys.exit(f'{rel}: version not found')
        v = m.group(2)
        if rel.endswith('Info.lua'):
            v = '{}.{}.{}'.format(*re.findall(r'\d+', v))
        out[rel] = v
    return out


def bump(version, dry):
    for rel, (pat, fmt) in VERSION_FILES.items():
        text = read(rel)
        new = re.sub(pat, lambda m: m.group(1) + fmt(version) + m.group(3), text, count=1)
        print(f'  {rel}: {"unchanged" if new == text else "-> " + version}')
        if not dry and new != text:
            open(os.path.join(ROOT, rel), 'w', encoding='utf-8').write(new)


def stamp_changelog(version, dry):
    """'## Unreleased' becomes '## <version> - <date>' with a fresh empty Unreleased section above it."""
    path = os.path.join(ROOT, 'CHANGELOG.md')
    if not os.path.exists(path):
        print('  CHANGELOG.md: none')
        return
    text = read('CHANGELOG.md')
    if re.search(rf'^## v?{re.escape(version)}\b', text, re.M):
        print(f'  CHANGELOG.md: already has a {version} section')
        return
    if '## Unreleased' not in text:
        print('  CHANGELOG.md: no "## Unreleased" section')
        return
    today = datetime.date.today().isoformat()
    new = text.replace('## Unreleased', f'## Unreleased\n\n## {version} - {today}', 1)
    print(f'  CHANGELOG.md: Unreleased -> {version} - {today}')
    if not dry:
        open(path, 'w', encoding='utf-8').write(new)


def changelog_section(version):
    path = os.path.join(ROOT, 'CHANGELOG.md')
    if not os.path.exists(path):
        return ''
    m = re.search(rf'^## v?{re.escape(version)}\b[^\n]*\n(.*?)(?=^## |\Z)', read('CHANGELOG.md'), re.S | re.M)
    return m.group(1).strip() if m else ''


def check(tag):
    version = tag.lstrip('v')
    if not SEMVER.match(version):
        sys.exit(f'{tag}: not a MAJOR.MINOR.PATCH tag')
    errors = []
    base = SEMVER.match(version).group(0).split('-')[0]
    for rel, v in current_versions().items():
        want = base if rel.endswith('Info.lua') else version
        if v != want:
            errors.append(f'{rel}: version {v}, tag says {want}')
    for f in glob.glob(os.path.join(ROOT, 'pipeline', '*.py')) + glob.glob(os.path.join(ROOT, 'bridge', '*.py')) + \
            glob.glob(os.path.join(ROOT, 'scripts', '*.py')):
        try:
            compile(open(f, encoding='utf-8').read(), f, 'exec')
        except SyntaxError as e:
            errors.append(f'{os.path.relpath(f, ROOT)}:{e.lineno}: {e.msg}')
    luac = shutil.which('luac5.1') or shutil.which('luac')
    for f in glob.glob(os.path.join(ROOT, PLUGIN, '*.lua')):
        if luac:
            r = subprocess.run([luac, '-p', f], capture_output=True, text=True)
            if r.returncode:
                errors.append(r.stderr.strip())
    if not luac:
        print('note: luac not found, Lua syntax not checked')
    forbidden = {'Exposure2012', 'IncrementalTemperature', 'IncrementalTint', 'Temperature', 'Tint', 'WhiteBalance',
                 'LuminanceSmoothing', 'orientation'}
    for f in sorted(glob.glob(os.path.join(ROOT, 'styles', '*.md'))):
        name = os.path.basename(f)
        if name.startswith('_') or name.upper().startswith('README'):
            continue
        m = re.search(r'^```json\n(.*?)^```', open(f, encoding='utf-8').read(), re.S | re.M)
        try:
            st = json.loads(m.group(1)) if m else None
        except json.JSONDecodeError as e:
            errors.append(f'styles/{name}: bad JSON: {e}')
            continue
        if not st or 'skin' not in st or 'settings' not in st or 'L' not in st['skin']:
            errors.append(f'styles/{name}: needs skin.L and settings')
        elif bad := [k for k in st['settings'] if k in forbidden or k.startswith('Crop')]:
            errors.append(f'styles/{name}: {", ".join(bad)} must not be in a style')
    if errors:
        sys.exit('release check failed:\n  ' + '\n  '.join(errors))
    print(f'release check ok: {tag}')


def notes(tag):
    version = tag.lstrip('v')
    prev = git('describe', '--tags', '--abbrev=0', '--match', '[0-9]*', '--match', 'v[0-9]*', f'{tag}^', check=False)
    rng = f'{prev}..{tag}' if prev else tag
    commits = '\n'.join('- ' + line.strip() for line in
                        git('log', '--no-merges', '--pretty=format:%s (%h)', rng, check=False).splitlines())
    out = []
    section = changelog_section(version)
    if section:
        out += ['## Highlights', '', section, '']
    out += ['## Install / update', '',
            '```bash',
            f'git clone https://github.com/{REPO}.git   # or: git pull',
            'cd lightroom-agent && python3 scripts/install.py',
            '```',
            f'Claude Code: `/plugin marketplace add {REPO}` (update: `/plugin update lightroom-agent`). '
            f'The Lightroom plugin alone is attached below as `LightroomAgent.lrplugin-{tag}.zip` '
            '(unzip, then File > Plug-in Manager > Add). Restart Lightroom Classic after updating.', '']
    if commits:
        out += ['## Commits', '', commits, '']
    if prev:
        out += [f'**Full changelog:** https://github.com/{REPO}/compare/{prev}...{tag}']
    print('\n'.join(out))


def release(version, tag_it, push, dry):
    if not SEMVER.match(version):
        sys.exit(f'{version}: use MAJOR.MINOR.PATCH, e.g. 0.3.0')
    tag = version
    tag_it = tag_it or push
    if tag_it and not dry and git('status', '--porcelain'):
        sys.exit('working tree not clean: commit or stash first')
    branch = git('rev-parse', '--abbrev-ref', 'HEAD')
    if branch != 'main':
        print(f'warning: on branch {branch}, not main')
    exists = ('locally' if git('tag', '--list', tag) else
              'on origin' if git('ls-remote', '--tags', 'origin', f'refs/tags/{tag}', check=False) else '')
    if exists:
        if tag_it:
            sys.exit(f'tag {tag} already exists {exists}')
        print(f'warning: tag {tag} already exists {exists}')
    print(f'current: {current_versions()}')
    print(f'{"would bump" if dry else "bumping"} to {version}:')
    bump(version, dry)
    stamp_changelog(version, dry)
    if dry:
        return
    if not tag_it:
        print(f'next: commit, then  git tag {tag} && git push origin {branch} {tag}')
        return
    git('add', '-A')
    git('commit', '-m', f'release: {tag}')
    git('tag', '-a', tag, '-m', tag)
    print(f'committed and tagged {tag}')
    if push:
        git('push', 'origin', branch)
        git('push', 'origin', tag)
        print(f'pushed: GitHub Actions now publishes https://github.com/{REPO}/releases/tag/{tag}')
    else:
        print(f'next: git push origin {branch} && git push origin {tag}')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('version', nargs='?', help='new version, e.g. 0.3.0')
    ap.add_argument('--tag', action='store_true', help='also commit and tag')
    ap.add_argument('--push', action='store_true', help='also commit, tag and push')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--check', metavar='TAG')
    ap.add_argument('--notes', metavar='TAG')
    a = ap.parse_args()
    if a.check:
        check(a.check)
    elif a.notes:
        notes(a.notes)
    elif a.version:
        release(a.version.lstrip('v'), a.tag, a.push, a.dry_run)
    else:
        ap.print_help()


if __name__ == '__main__':
    main()
