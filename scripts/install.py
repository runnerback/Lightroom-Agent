#!/usr/bin/env python3
"""One-step installer for Lightroom Agent (macOS / Windows). Run from the cloned repository:

    python3 scripts/install.py            # everything, skills for every AI tool found on this computer
    python3 scripts/install.py --skills claude codex gemini workbuddy trae cursor
    python3 scripts/install.py --no-plugin --no-skills

1. builds the private Python environment (~/.lightroom-agent/venv) and checks it
2. puts the `lightroom-agent` command on your PATH (~/.local/bin, or ~/.lightroom-agent/bin on Windows)
3. copies the Lightroom plugin into Lightroom's Modules folder (restart Lightroom afterwards)
4. links the skill into the skills folder of each AI tool
5. prints the MCP server settings to paste into MCP-only apps
Uses only the standard library, so any Python 3.10+ can run it.
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIN = platform.system() == 'Windows'
HOME = os.path.expanduser('~')
LAUNCHER = os.path.join(ROOT, 'bin', 'lightroom-agent.cmd' if WIN else 'lightroom-agent')
SKILL = os.path.join(ROOT, 'skills', 'lightroom-agent')
# tool -> (folder that shows the tool is installed, its user-level skills folder)
TOOLS = {
    'claude': ('.claude', '.claude/skills'),
    'codex': ('.codex', '.codex/skills'),
    'gemini': ('.gemini', '.gemini/skills'),
    'workbuddy': ('.workbuddy', '.workbuddy/skills'),
    'trae': ('.trae', '.trae/skills'),
    'cursor': ('.cursor', '.cursor/skills'),
}


def step(msg):
    print(f'\n==> {msg}', flush=True)


def run(*cmd):
    return subprocess.run(list(cmd), check=False).returncode


def link(src, dst):
    if os.path.islink(dst) or os.path.isfile(dst):
        os.remove(dst)
    elif os.path.isdir(dst):
        shutil.rmtree(dst)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        os.symlink(src, dst, target_is_directory=os.path.isdir(src))
        return 'linked'
    except OSError:                       # Windows without developer mode: copy instead
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
        return 'copied (re-run the installer after updating)'


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--skills', nargs='*', choices=sorted(TOOLS), help='tools to install the skill for (default: all detected)')
    ap.add_argument('--no-skills', action='store_true')
    ap.add_argument('--no-plugin', action='store_true', help='do not copy the Lightroom plugin')
    ap.add_argument('--no-path', action='store_true', help='do not put lightroom-agent on PATH')
    a = ap.parse_args()

    step('Python environment (first run downloads Python packages, ~400 MB on disk)')
    if run(LAUNCHER, 'doctor') not in (0, 1):     # 1 = some check failed, e.g. Lightroom not running yet: fine here
        sys.exit('environment setup failed; see the messages above')

    if not a.no_path:
        step('lightroom-agent command')
        bindir = os.path.join(HOME, '.lightroom-agent', 'bin') if WIN else os.path.join(HOME, '.local', 'bin')
        os.makedirs(bindir, exist_ok=True)
        if WIN:
            shim = os.path.join(bindir, 'lightroom-agent.cmd')
            open(shim, 'w').write(f'@echo off\r\n"{LAUNCHER}" %*\r\n')
            print(f'created {shim}')
        else:
            print(f'{link(LAUNCHER, os.path.join(bindir, "lightroom-agent"))} {os.path.join(bindir, "lightroom-agent")}')
        if bindir not in os.environ.get('PATH', '').split(os.pathsep):
            print(f'NOTE: {bindir} is not on your PATH. Add it, e.g. ' +
                  (f'setx PATH "%PATH%;{bindir}"' if WIN else f'echo \'export PATH="{bindir}:$PATH"\' >> ~/.zshrc'))

    if not a.no_plugin:
        step('Lightroom Classic plugin')
        run(LAUNCHER, 'install-plugin')

    if not a.no_skills:
        step('Agent skill')
        tools = a.skills if a.skills is not None else [t for t, (marker, _) in TOOLS.items() if os.path.isdir(os.path.join(HOME, marker))]
        if not tools:
            print('no supported AI tool folders found (~/.claude, ~/.codex, ~/.gemini, ~/.workbuddy, ~/.trae, ~/.cursor);'
                  ' use --skills to choose')
        for t in tools:
            dst = os.path.join(HOME, TOOLS[t][1], 'lightroom-agent')
            print(f'{t:<10} {link(SKILL, dst)} {dst}')

    step('MCP server (for MCP-only apps: Claude Desktop, Cherry Studio, Cursor, Trae ...)')
    print('Add a stdio server named "lightroom" with:')
    print(f'  command: {LAUNCHER}\n  args:    ["mcp"]')
    print('Details for each app: docs/agents.md')
    print('\nDone. Restart Lightroom Classic, then run:  lightroom-agent doctor')


if __name__ == '__main__':
    main()
