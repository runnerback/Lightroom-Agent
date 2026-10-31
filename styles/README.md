English | [中文](./README_CN.md)

# Styles

Every colour style is **one Markdown file** in this folder, named after the style: `A_Airy_White.md`,
`D_Fuji_400H.md`, ... The first ```` ```json ```` block in the file holds the parameters; everything else is the
description for people. To add a style, add a file; to remove one, delete its file.

- **Name** = file name without `.md`, used on the command line and as the output folder
  (`<run dir>/style_applied/<name>/`). Use `Letter_Name`: the letter alone also works (`apply-style D`) as long as it is
  unique.
- **Your own styles** go in `~/.lightroom-agent/styles/` (Windows: `%USERPROFILE%\.lightroom-agent\styles\`). Updates
  never touch that folder, and a file there with the same name as a built-in style replaces it.
  `LIGHTROOM_AGENT_STYLES` can list more folders.
- `README*.md` and files starting with `_` are not styles ([`_template.md`](./_template.md) is the starting point for
  a new one).
- Validate after editing: `lightroom-agent styles` lists every style and reports the file of any error.

## How a style is applied

A style has three parts:

| Part | Field | Role |
|---|---|---|
| Fixed look | `settings` | Lightroom develop settings written to every photo: contrast, highlights/shadows, HSL, tone curve, colour grading, calibration, grain, vignette |
| Skin target | `skin` | Target colour (Lab) of the centre of the subject's face. **Exposure** is calibrated per photo on its lightness L; when the frame has too little white, **white balance** is also calibrated on its a/b |
| White target | `white` | Target tint (Lab a/b) of near-white areas (shirts, walls, sheets, sky haze). When they cover ≥ 8 % of the frame, **white balance** is calibrated on them |

Per-photo calibration (`pipeline/style_apply.py`):

1. Write `settings`, render a 1600 px calibration JPEG through Lightroom (with your crop).
2. Detect the main face on it; measure the Lab of the central skin patch and of the near-white areas.
3. Adjust exposure (skin L → target) and white balance (whites or skin a/b → target); repeat 3–4 rounds and keep the
   closest result.
4. Deep skin tones keep their depth: the skin L target is lowered when the face is much darker than the brightest
   parts of the same frame.
5. Photos without a usable face (landscapes, architecture, backs) borrow the calibration of the nearest face photo
   taken within 30 minutes (same light); otherwise they keep the camera's exposure and white balance and only get the
   look.
6. RAW files get luminance noise reduction by ISO (≤1600: 10, ≤3200: 20, ≤6400: 30, higher: 40); JPGs and AI-Denoise
   DNGs get none.

When you switch styles, keys set by another style but not by this one are reset to neutral, so nothing of the previous
look is left. Crop, straighten and orientation are never touched.

**Why a white target:** balancing RAW files on skin alone pushes tint to about +40 to reach a rosy skin target, and
white shirts or sheets turn pink. Balancing on whites and using skin only for exposure keeps whites clean and skin
natural.

### Reading Lab values

| Channel | Meaning | Reference |
|---|---|---|
| L | lightness, 0 black – 100 white | light skin 65–72 reads bright and airy; ≈3 L is about 0.3 EV |
| a | + red/magenta, − green | skin 13–15 natural and rosy; whites above 2 start to look pink |
| b | + yellow, − blue | skin 15–22 from cool to warm; whites 1–2 clean, 4–6 creamy, above 8 visibly yellow |

The skin targets were tuned on light skin; deeper skin is handled by step 4 above.

## The built-in styles

One file each: [A_Airy_White](./A_Airy_White.md) · [B_Warm_Film](./B_Warm_Film.md) · [C_Natural](./C_Natural.md) · [D_Fuji_400H](./D_Fuji_400H.md)

| | A_Airy_White | B_Warm_Film | C_Natural | D_Fuji_400H |
|---|---|---|---|---|
| In one line | high-key, bright, clean creamy whites | warm, nostalgic film | true colour, crisp and clear | Fuji Pro 400H: airy, cool, pastel |
| Skin target L / a / b | 72 / 13 / 15 | 68 / 15 / 22 | 66 / 14 / 18 | 70 / 14 / 16 |
| White target a / b | 0.5 / 1.5 (clean) | 1.0 / 5.0 (creamy warm) | 0.5 / 2.5 (neutral, slightly warm) | −0.3 / 0.5 (slightly cool) |
| Contrast | soft | soft, lifted grey blacks | slightly punchy, solid blacks | low, lifted hazy blacks |
| Colour | low saturation, muted yellow/green | low saturation, yellow-green, muted blue, warm split tone | natural, vibrance +10 | mint/cyan greens, cyan shadows, pink skin, pastels |
| Texture | softened (texture −10, clarity −5) | film grain + light vignette | slightly crisp (texture +5, clarity +5) | fine grain, no vignette |
| Good for | bright interiors, white backdrops, weddings, high-key portraits | warm indoor light, lifestyle, golden-hour street | street, travel, documentary, landscapes, architecture | daylight portraits, pastel scenes, fresh Japanese-style look |

## Add a style

1. Copy [`_template.md`](./_template.md) (or the closest existing style) to `~/.lightroom-agent/styles/E_My_Style.md`
   — or into this folder if you want to contribute it.
2. Describe the look in the prose: what it should look like, what it suits, caveats.
3. Edit the json:
   - `desc`: one line, shown to the agent when it chooses styles.
   - `skin`: start from the closest style and adjust with "Reading Lab values". +3 L ≈ +0.3 EV.
   - `white`: clean white b≈1.5, creamy b≈5; keep a at 0.5–1 (above 2 looks pink). Omit `white` to balance on skin
     only.
   - `settings`: Lightroom develop keys (table below). Keys you leave out keep Lightroom's defaults.
4. `lightroom-agent styles` to validate.
5. Proof on 2–3 photos, then style a whole collection. Or just ask your agent: *"add a style like Kodak Portra 400"*.

**Contributing a style:** open a pull request with the `.md` file and a before/after image of 2–3 photos (no private
photos of other people without their consent). Pick the next free letter.

## Change a style

- Prose only: nothing to do.
- `settings`, `skin` or `white` changed: re-apply with calibration (not `--reuse-calib`, which keeps the old exposure /
  WB). `--refine` starts from the last calibration and converges faster.

## Common keys (`settings`)

| Key | Panel | Range | Default |
|---|---|---|---|
| `Exposure2012` | exposure (set by calibration, never in a style) | −5 – +5 | 0 |
| `Contrast2012` / `Highlights2012` / `Shadows2012` / `Whites2012` / `Blacks2012` | Basic | −100 – +100 | 0 |
| `Texture` / `Clarity2012` / `Dehaze` | Basic · Presence | −100 – +100 | 0 |
| `Vibrance` / `Saturation` | Basic · Presence | −100 – +100 | 0 |
| `HueAdjustment<Colour>` / `SaturationAdjustment<Colour>` / `LuminanceAdjustment<Colour>` | HSL; Colour = Red Orange Yellow Green Aqua Blue Purple Magenta | −100 – +100 | 0 |
| `SplitToningShadowHue` / `SplitToningHighlightHue` | Color Grading (shadow / highlight hue) | 0 – 360 | 0 |
| `SplitToningShadowSaturation` / `SplitToningHighlightSaturation` | Color Grading (saturation) | 0 – 100 | 0 |
| `SplitToningBalance` | Color Grading · Balance | −100 – +100 | 0 |
| `ShadowTint`, `RedHue` / `RedSaturation`, `GreenHue` / `GreenSaturation`, `BlueHue` / `BlueSaturation` | Calibration | −100 – +100 | 0 |
| `ToneCurvePV2012` | point curve, `[in1, out1, in2, out2, ...]`, 0–255 | — | `[0,0,255,255]` |
| `GrainAmount` / `GrainSize` / `GrainFrequency` | Effects · Grain | 0 – 100 | 0 / 25 / 50 |
| `PostCropVignetteAmount` | Effects · Post-Crop Vignetting (negative darkens) | −100 – +100 | 0 |
| `PostCropVignetteMidpoint` / `PostCropVignetteFeather` / `PostCropVignetteRoundness` | Effects · vignette shape | 0–100 / 0–100 / −100–100 | 50 / 50 / 0 |

**Never put in a style:** white balance (`Temperature`, `Tint`, `IncrementalTemperature`, `IncrementalTint`,
`WhiteBalance`), `Exposure2012`, `LuminanceSmoothing` (set per photo by calibration and the noise rule), or crop keys
(`Crop*`, `orientation`).

**Keys whose default is not 0:** when switching styles, keys set by another style are reset to a neutral value. Keys
whose Lightroom default is not 0 (e.g. `GrainSize` 25, vignette `Midpoint` 50) must be listed in `NEUTRAL` in
`pipeline/style_lib.py`; add a line there when you use a new one.

## Commands

```bash
lightroom-agent styles                                              # validate and list
lightroom-agent apply-style D --collection "Proofs"                 # JPG defaults
lightroom-agent apply-style D --collection "Picks" --max-ev 1.5 --iters 4   # RAW
lightroom-agent apply-style D --collection "Picks" --refine          # after a small style change
lightroom-agent apply-style D --collection "Picks" --refine --only IMG_0012.ARW IMG_0230.ARW
lightroom-agent apply-style D --collection "Picks" --refine --only IMG_0301.ARW --skin-wb IMG_0301.ARW
lightroom-agent apply-style D --collection "Picks" --reuse-calib     # style unchanged: re-apply saved calibration
lightroom-agent check-boxes D --collection "Picks"                  # QA: where each photo was measured
lightroom-agent rollback --collection "Picks"                       # back to before the first style
```

Output goes to `<run dir>/style_applied/<style>/`: `overview_*.jpg`, `boxes.jpg` (from `check-boxes`), `calib.json`
(per-photo calibration), `baseline.json` (settings before this style).
