# E2_GR_IV_Monochrome

**Look:** street black and white in the spirit of the Ricoh GR IV Monochrome: its "Solid" image control (a hard tone
curve, crisp edges) shot through the camera's built-in red contrast filter. Graphic and punchy: luminous faces, dark
skies and foliage, deep blacks, a little grain.

**Where the GR IV Monochrome look comes from** (references: Ricoh's GR IV Monochrome announcement, January 2026, as
reported by Macfilos and B&H; the GR line's long-standing high-contrast B&W modes)
- **Built-in red filter:** a red filter passes red/orange light and blocks blue/green. In the B&W mix red +35 and
  orange +25 (skin glows, blemishes soften), blue −50 and aqua −40 (skies go dark, clouds stand out), green −25
  (foliage drops away behind the subject).
- **"Solid" hard curve:** contrast +30, blacks −15 and a steep S-curve (toe 40→30, shoulder 220→234): deep blacks
  and a short, punchy mid-scale, but shadows +5 so dark clothes keep a hint of texture (a dark dress must not turn
  into a flat black shape). Highlights −40 and whites only +5 keep skies and white shirts from blowing, so faces can
  still be brought up to their target.
- **Crisp edges:** clarity +20, texture +15, a touch of dehaze (+5).
- **Grain:** light-medium grain (20, size 20, roughness 65), a nod to the camera's "Grainy" mode without going gritty.
- **Street vignette:** darker corners (−20, midpoint 35) to hold the eye on the subject.

**Good for:** street, travel and documentary; strong light and shadow; portraits in front of greenery or sky, where
the red filter separates the subject.

**Notes**
- B&W styles calibrate exposure only: faces are brought to L 64, slightly below E1 because the hard curve and the red
  filter already lift skin against its surroundings. Against a bright, near-clipping sky the highlight guard may hold
  the face a little lower. White balance stays as shot; raw files are switched to the Adobe
  Monochrome profile and get their colour profile back when a colour style is applied later.
- For a softer, more film-like variant ("Grainy"), copy this file to `~/.lightroom-agent/styles/D3_GR_Grainy.md`, lower
  contrast to +15, raise GrainAmount to 40 and GrainSize to 35.
- Under a blue sky in hard sun the red filter can turn the sky nearly black; that is the intended look.

```json
{
  "desc": "Ricoh GR IV Monochrome-style street B&W: 'Solid' hard curve with deep blacks and bright whites, built-in red filter (luminous skin, dark skies and foliage), crisp edges, light grain, dark corners",
  "skin": {"L": 64},
  "settings": {
    "ConvertToGrayscale": true,
    "GrayMixerRed": 35,
    "GrayMixerOrange": 25,
    "GrayMixerYellow": 10,
    "GrayMixerGreen": -25,
    "GrayMixerAqua": -40,
    "GrayMixerBlue": -50,
    "GrayMixerPurple": -20,
    "GrayMixerMagenta": 15,
    "Contrast2012": 30,
    "Highlights2012": -40,
    "Shadows2012": 5,
    "Whites2012": 5,
    "Blacks2012": -15,
    "Texture": 15,
    "Clarity2012": 20,
    "Dehaze": 5,
    "GrainAmount": 20,
    "GrainSize": 20,
    "GrainFrequency": 65,
    "PostCropVignetteAmount": -20,
    "PostCropVignetteMidpoint": 35,
    "PostCropVignetteFeather": 55,
    "ToneCurvePV2012": [0, 0, 40, 30, 96, 90, 160, 176, 220, 234, 255, 255]
  }
}
```
