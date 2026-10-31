# A_Airy_White

**Look:** Japanese-style high key. Bright overall, soft highlights, clean neutral whites, light rosy skin.

**Characteristics**
- Brightest skin target (L72), about half a stop brighter than the others.
- Highlights pulled down strongly (−45) to keep detail in white fabric; shadows +20, blacks +5: gentle contrast.
- Lower saturation with yellow, green and orange muted: few distracting colours, a creamy feel.
- Slightly less texture and clarity: smooth skin.
- Tone curve: black point lifted to 8, white point 252, a light airy haze.

**Notes**
- Pushes exposure the most. Dark scenes may hit the exposure limit (`--max-ev`, default 0.9, use 1.5 for RAW); the face
  then stays a little darker than the target.
- Back-lit faces or faces half in shadow can measure too warm: check the overview.

```json
{
  "desc": "high-key airy: soft contrast, protected highlights, desaturated creams, bright clean skin",
  "skin": {"L": 72, "a": 13, "b": 15},
  "white": {"a": 0.5, "b": 1.5},
  "settings": {
    "Contrast2012": -10,
    "Highlights2012": -45,
    "Shadows2012": 20,
    "Whites2012": 5,
    "Blacks2012": 5,
    "Texture": -10,
    "Clarity2012": -5,
    "Vibrance": 5,
    "Saturation": -8,
    "SaturationAdjustmentOrange": -8,
    "LuminanceAdjustmentOrange": 10,
    "SaturationAdjustmentYellow": -25,
    "SaturationAdjustmentGreen": -20,
    "ToneCurvePV2012": [0, 8, 64, 68, 128, 134, 192, 197, 255, 252]
  }
}
```
