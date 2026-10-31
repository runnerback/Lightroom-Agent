---
name: lightroom-agent
description: Cull and colour-grade photos in Adobe Lightroom Classic on this computer. Use when the user wants to pick the best shots from a shoot (sharpness, closed eyes, duplicates, expressions), rate/flag photos or build a picks collection, apply a consistent look or colour style (e.g. airy white, warm film, natural, Fuji film) to a collection with per-photo exposure and white-balance calibration, compare or undo styles, or add a new style. Works through the Lightroom Agent plugin; never changes crops and never makes final exports unless asked.
---

# Lightroom Agent

You drive **Adobe Lightroom Classic** on the user's computer through the Lightroom Agent plugin, using the
`lightroom-agent` command. Lightroom does all rendering; you decide, run commands, look at the result sheets, and fix
problems. Answer in the user's language.

## 0. Find the command and check the setup

Use the first that works:
1. `lightroom-agent` (on PATH after `python3 scripts/install.py`)
2. `${CLAUDE_PLUGIN_ROOT}/bin/lightroom-agent` (Claude Code plugin install)
3. `<this skill's folder>/../../bin/lightroom-agent` (repository checkout; on Windows `bin\lightroom-agent.cmd`)

Run `lightroom-agent doctor` first. The first run builds a Python environment (1–3 min). If the Lightroom connection
fails: Lightroom Classic must be running with the plugin installed (`lightroom-agent install-plugin`, then restart
Lightroom; full guide: `docs/install-plugin.md` in the repository). If an MCP server named `lightroom` is connected,
you may use its tools instead of the CLI; they are the same operations.

Every long command prints progress and ends with one line `SUMMARY {json}`: read that line. Culling and styling a
whole shoot takes minutes (≈30 s per photo for styles): run them in the background when your tool allows it and poll.

## 1. Hard rules

- **Never change the user's crop, straighten or orientation.** The tools don't touch them; `apply-style` verifies it
  (`crop_changed` in SUMMARY must be empty — if not, report it immediately).
- **Final exports are the user's job** unless they explicitly ask. Small QA exports inside the run directory are fine.
- **Everything is reversible:** each style run saves a baseline. Tell the user how to undo (`rollback`).
- Before writing ratings/flags or styling many photos, say what you are about to do (collection, count, style).
- **Check quality yourself** (section 5) before saying "done". Report problems honestly, with photo names.
- Lightroom menu-only features (AI Denoise, HDR/Panorama merge, masks) cannot be automated: recommend them by name.

## 2. Find the photos

```bash
lightroom-agent catalog                         # folders + collections with counts
lightroom-agent photos --collection "Wedding picks"
lightroom-agent photos --folder "/Users/me/Pictures/2026/0501-wedding/raw"
```
Work files go to `~/Pictures/Lightroom Agent/<collection or folder>/` (override with `--run DIR`; reuse the same
`--run` for every step of one job).

## 3. Culling (choosing the best photos)

```bash
lightroom-agent cull --folder "/path/in/catalog" [--recursive]     # or --collection NAME
```
- **Subject:** with several faces the largest is the subject (`--subject main`, default). For family / baby shoots
  where the child is held by or next to adults, add `--subject child` to `cull`, `apply-style` and `check-boxes`.
- Technical pass only, writes nothing to Lightroom: face sharpness relative to neighbouring frames, closed eyes,
  exposure, burst/near-duplicate grouping (keeps the best of each burst). RAW files are previewed through Lightroom
  (with the user's crop), JPGs are read directly.
- SUMMARY gives `keep_sheets` / `reject_sheets` (contact sheets with file names and scores). **Look at the keep
  sheets** and choose like a photographer: genuine expressions (smiles, eye contact, interaction), eyes open and
  sharp, clean composition, variety of moments/angles — avoid near-identical frames. Glance at reject sheets for
  false rejects (e.g. intentional motion blur). `cull.json` has per-photo metrics if you need them.
- Agree the pick list with the user (show names, roughly how many), then:

```bash
lightroom-agent pick --run "<run dir>" --names IMG_0012 IMG_0045 ... --collection "Wedding picks"
```
Picks get 3★ + green label and go into the collection (in the "Lightroom Agent" collection set); culled rejects get
the reject flag and other keeps 1★ (`--no-mark-others` to leave them alone; `--dry-run` to preview).

## 4. Colour styles

```bash
lightroom-agent styles                          # names, descriptions, targets, files
lightroom-agent collect "Wedding proofs" --collection "Wedding picks" --names IMG_0012 IMG_0230 IMG_0301
lightroom-agent apply-style D --collection "Wedding proofs"          # letter or full name
lightroom-agent apply-style D --collection "Wedding picks" --max-ev 1.5 --iters 4   # RAW shoots
```
- Each photo is calibrated on the subject's face: exposure so the skin reaches the style's lightness (lowered
  automatically for deeper skin tones), white balance on neutral whites in the frame (sheets, clothes) or on skin.
  Photos without a usable face borrow the calibration of the nearest face photo taken within 30 min
  (`--borrow-window`); landscapes and other faceless photos with no such neighbour keep the camera's exposure / white
  balance and only get the look.
- **Proof first:** put 2–3 representative photos (different scenes/light) in a proof collection, apply 1–4 candidate
  styles, show the user the overview sheets, then style the whole collection.
- Defaults: `--max-ev 0.9 --iters 3` (JPG). For RAW use `--max-ev 1.5 --iters 4`.
- Switching style: just apply the other style (keys of the previous style are reset automatically).
- Undo: `lightroom-agent rollback --collection C` (back to before the first style of this run) or
  `lightroom-agent rollback B --collection C` (back to just before style B).
- Re-apply a previous calibration without re-measuring: `apply-style B --collection C --reuse-calib`.
- Fix a few photos: `apply-style D --collection C --refine --only IMG_1.ARW IMG_2.ARW`
  (`--skin-wb IMG_1.ARW ...` when the frame's "whites" are really cream clothes or a beige sofa and the photo came
  out too cool / skin grey).
- RAW noise reduction is set automatically by ISO; files whose name says Enhanced/Denoise (Lightroom AI Denoise
  DNGs) get none — prefer those versions when they exist.

## 5. Quality check — always, before reporting

After `apply-style`, using its SUMMARY:
1. `crop_changed` is empty.
2. **Look at every `overview_*.jpg`**: skin natural and consistent across the set, whites not pink/green/yellow,
   no washed-out or muddy frames, highlights not blown. Name the photos that look off.
3. `lightroom-agent check-boxes D --collection C` → look at `boxes.jpg`: the **red box must sit on the main
   subject's face** (not a balloon, poster, hand, or a passer-by's face). Re-calibrate wrong
   ones with `--refine --only ...`.
4. `exposure_capped`: those photos hit `--max-ev`; their face may stay a bit dark — mention it.
5. High ISO (≥ 6400): suggest Lightroom AI Denoise for photos that will be printed/enlarged.
6. Report: what was applied to how many photos, problems found and fixed, remaining caveats, how to undo, where the
   overview sheets are. No final export unless asked.

## 6. Adding or changing a style

Each style is one Markdown file: built-in ones in the repository's `styles/`, the user's own in
`~/.lightroom-agent/styles/<Letter>_<Name>.md` (survives updates; same name overrides a built-in). The first ```json
block holds the parameters, the rest documents the look. To add one, copy `styles/_template.md` or the closest style into
the user folder, adjust `skin` (L/a/b target), `white` (a/b of neutral whites, b≈1.5 clean, ≈5 creamy) and `settings`
(Lightroom develop keys: Basic, HSL, ColorGrading/SplitToning, Calibration, ToneCurvePV2012, Grain, Vignette), and
describe the look in prose. Never put white balance, exposure or crop keys in a style. Validate with
`lightroom-agent styles`, proof on 2–3 photos. Full guide: `styles/README.md`.

## 7. Other commands

```bash
lightroom-agent import /path/to/folder --collection "New shoot"     # add files in place
lightroom-agent export --collection C --dest DIR --long-edge 2048     # only when the user asks
lightroom-agent status
```

## Troubleshooting

- `cannot connect to the command port` → Lightroom closed or plugin not loaded: start Lightroom; File > Plug-in
  Manager shows "Lightroom Agent" as running; else `lightroom-agent install-plugin` and restart Lightroom.
- `handshake failed` → Lightroom menu Library > Plug-in Extras > Lightroom Agent: Restart service.
- Only one client at a time: commands queue automatically; don't run two style jobs on the same photos.
- Plugin log: `~/Library/Logs/Adobe/Lightroom/LrClassicLogs/LightroomAgent.log` (macOS).
