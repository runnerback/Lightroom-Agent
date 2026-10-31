# Lightroom Agent — instructions for Gemini CLI

This repository lets an AI agent cull and colour-grade photos in **Adobe Lightroom Classic** through a Lightroom
plugin. If the user asks you to work on their photos (choose the best shots, rate/flag, apply a style, undo, add a
style), read and follow **[skills/lightroom-agent/SKILL.md](skills/lightroom-agent/SKILL.md)** — it is the complete
operating guide (commands, workflow, quality checks, hard rules).

Run commands with `bin/lightroom-agent` (Windows: `bin\lightroom-agent.cmd`) from this repository, or `lightroom-agent`
if installed on PATH. Start with `bin/lightroom-agent doctor`.

If the user asks you to change this project's code:
- `lightroom_plugin/LightroomAgent.lrplugin/` — Lua plugin (Lightroom SDK, Lua 5.1); `Handlers.lua` holds the commands
  and hot-reloads with `python3 bridge/lr_client.py reload` (no Lightroom restart).
- `bridge/lr_client.py` — Python client for the plugin's localhost socket protocol (stdlib only).
- `pipeline/` — `cli.py` (entry point), `mcp_server.py`, culling (`analyze.py`, `cull.py`), styles (`style_lib.py`,
  `style_apply.py`), sheets (`contact_sheet.py`, `check_boxes.py`).
- `styles/` — one Markdown file per style (prose + one ```json block); guide in `styles/README.md`. Users' own
  styles live in `~/.lightroom-agent/styles/`.
