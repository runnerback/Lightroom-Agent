# E1_Leica_Monochrom

**Look:** black and white in the spirit of the Leica M Monochrom: a sensor without a colour filter array, known for a
long, smooth tonal range, neutral grey, deep blacks that keep their detail, and crisp micro-contrast. Quiet and
precise rather than dramatic.

**Where the Monochrom look comes from** (references: reviews of the M11 Monochrom on Fstoppers and Photography News,
Leica's own descriptions of the Monochrom line)
- **Long tonal range, smooth gradation:** no added contrast (the Adobe Monochrome profile has its own gentle S),
  highlights pulled back (−40) so bright skin, white shirts and skies roll off gently instead of clipping; shadows
  opened (+25) so dark clothes and foliage keep their texture, while the black point stays anchored (blacks −12,
  curve toe 32→27). No crushed shadows, no grey-veil blacks.
- **Panchromatic, unfiltered:** no colour filter on the sensor, so colours map to grey close to their brightness.
  The B&W mix stays near neutral, with only a small lift on red/orange (skin a little luminous) and a small dip on
  green (foliage separates from faces).
- **Neutral grey:** no toning. (Leica offers sepia / selenium / blue toning in-camera; add `SplitToning*` keys in your
  own copy if you want them.)
- **Micro-contrast:** texture +10, clarity +8 (on top of the Adobe Monochrome profile's own clarity), the "acutance" of
  Leica glass.
- **Clean files:** the Monochrom's files are almost noise-free; only a very fine grain (8) for a print-like surface.
- Slight lens vignetting (−8), soft edges.

**Good for:** portraits and everyday scenes that should look timeless and calm; soft and mixed light; anything where
the tonal detail matters more than punch.

**Notes**
- B&W styles calibrate exposure only: the subject's face is brought to L 66 (Zone VI, a classic B&W skin value). White
  balance stays as shot; raw files are switched to the Adobe Monochrome profile and get their colour profile back when
  a colour style is applied later.
- Faces that come out too bright against a white sky: lower `GrayMixerOrange` / `GrayMixerRed` in your own copy.

```json
{
  "desc": "Leica M Monochrom-style B&W: long smooth tonal range, neutral grey, deep but detailed blacks, gentle highlight roll-off, crisp micro-contrast, very fine grain",
  "skin": {"L": 66},
  "settings": {
    "ConvertToGrayscale": true,
    "GrayMixerRed": 5,
    "GrayMixerOrange": 10,
    "GrayMixerYellow": 5,
    "GrayMixerGreen": -5,
    "GrayMixerAqua": -5,
    "GrayMixerBlue": 0,
    "GrayMixerPurple": 0,
    "GrayMixerMagenta": 5,
    "Contrast2012": 0,
    "Highlights2012": -40,
    "Shadows2012": 25,
    "Whites2012": 5,
    "Blacks2012": -12,
    "Texture": 10,
    "Clarity2012": 8,
    "GrainAmount": 8,
    "GrainSize": 10,
    "GrainFrequency": 60,
    "PostCropVignetteAmount": -8,
    "PostCropVignetteMidpoint": 45,
    "PostCropVignetteFeather": 80,
    "ToneCurvePV2012": [0, 0, 32, 27, 64, 61, 128, 128, 192, 196, 255, 255]
  }
}
```
