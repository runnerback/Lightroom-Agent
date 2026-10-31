# C_Natural

**Look:** natural documentary. Colours close to reality, clear tonal separation, no effects.

**Characteristics**
- Skin target L66, the most solid of the four; whites neutral, slightly warm (b2.5).
- Contrast +5, blacks −5, linear curve: shadows keep their weight.
- Vibrance +10 without touching overall saturation: colourful scenes stay lively.
- Texture and clarity +5 each: detailed but not harsh.

**Notes**
- Blacks are not lifted; very saturated colours (neon, painted walls) may clip in one channel. That is saturation, not
  overexposure.
- No grain to hide noise: run Lightroom AI Denoise on high-ISO photos first.

```json
{
  "desc": "natural documentary: true colour, crisp but gentle, moderate highlight recovery",
  "skin": {"L": 66, "a": 14, "b": 18},
  "white": {"a": 0.5, "b": 2.5},
  "settings": {
    "Contrast2012": 5,
    "Highlights2012": -30,
    "Shadows2012": 15,
    "Whites2012": 5,
    "Blacks2012": -5,
    "Texture": 5,
    "Clarity2012": 5,
    "Vibrance": 10,
    "Saturation": 0,
    "ToneCurvePV2012": [0, 0, 255, 255]
  }
}
```
