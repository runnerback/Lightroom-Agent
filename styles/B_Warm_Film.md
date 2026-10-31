# B_Warm_Film

**Look:** warm, nostalgic film. Faded blacks, restrained colour, fine grain and a faint vignette.

**Characteristics**
- Warmest skin target (b22) and creamy whites (b5): a few hundred kelvin warmer than A.
- Blacks clearly lifted (Blacks +10, curve black point 22), white point 245: the faded film look.
- Greens shifted toward yellow and desaturated (−30), blues desaturated (−20): bright props and signs stay calm.
- Split toning: a little warm orange in shadows and highlights (hue 35/45, saturation 8/10).
- Grain 12, vignette −8; the grain is fine and even at 100 % and hides some high-ISO noise.

**Notes**
- Grain is added at render time: invisible in small previews, visible when enlarged or printed.
- Not for photos whose colours must match reality (product, clothing, food).

```json
{
  "desc": "warm film: faded blacks, muted greens, warm split-tone, light grain and vignette",
  "skin": {"L": 68, "a": 15, "b": 22},
  "white": {"a": 1.0, "b": 5.0},
  "settings": {
    "Contrast2012": -15,
    "Highlights2012": -35,
    "Shadows2012": 15,
    "Whites2012": -5,
    "Blacks2012": 10,
    "Saturation": -12,
    "Vibrance": 6,
    "Texture": -5,
    "HueAdjustmentGreen": 15,
    "SaturationAdjustmentGreen": -30,
    "SaturationAdjustmentYellow": -10,
    "SaturationAdjustmentBlue": -20,
    "SplitToningShadowHue": 35,
    "SplitToningShadowSaturation": 8,
    "SplitToningHighlightHue": 45,
    "SplitToningHighlightSaturation": 10,
    "SplitToningBalance": 0,
    "GrainAmount": 12,
    "GrainSize": 20,
    "GrainFrequency": 50,
    "PostCropVignetteAmount": -8,
    "PostCropVignetteMidpoint": 50,
    "PostCropVignetteFeather": 70,
    "ToneCurvePV2012": [0, 22, 60, 64, 128, 130, 200, 203, 255, 245]
  }
}
```
