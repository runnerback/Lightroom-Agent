# D_Fuji_400H

**Look:** an emulation of Fujicolor Pro 400H negative film, the most recognisable "Fuji colour" in Japanese portrait
photography: airy, cool, pastel.

**Where the Fuji look comes from** (references: Mastin Labs' and Presetpro's descriptions of 400H, Fujilove's digital
400H emulation)
- **Mint / cyan greens:** green hue pushed strongly toward cyan, desaturated and brightened; aqua brightened. Foliage
  turns pastel mint.
- **Cyan shadows:** colour grading adds cyan-green to the shadows (hue 185); the Calibration panel's shadow tint leans
  green.
- **Pink, not yellow, skin:** orange hue toward red and brighter, yellow desaturated; the red primary leans slightly
  magenta.
- **Pastel, low contrast, hazy:** lower contrast, curve black point 18 and white point 248; blue, purple and magenta
  desaturated and brightened.
- **Slightly cool whites:** white target b only +0.5, cooler than A/B/C, with a touch of cyan.
- Fine grain (10) for film texture, no vignette.

**Good for:** light, pastel scenes in daylight; portraits with greenery; a fresh Japanese-style look.

**Notes**
- The Calibration panel (`RedHue`, ...) shifts the base of every colour: tune this style there first, HSL second.
- With its cool white target, frames whose "whites" are really cream clothing or a beige wall come out too cool with
  grey skin. Balance those on skin with `--skin-wb NAME ...`.
- Frames with little white are balanced on skin anyway; the skin target is pink (b16), so they do not turn yellow.

```json
{
  "desc": "Fuji Pro 400H: mint/cyan greens, cyan shadows, pink clean skin, pastel low contrast, slightly cool whites",
  "skin": {"L": 70, "a": 14, "b": 16},
  "white": {"a": -0.3, "b": 0.5},
  "settings": {
    "Contrast2012": -15,
    "Highlights2012": -40,
    "Shadows2012": 25,
    "Whites2012": 0,
    "Blacks2012": 5,
    "Texture": -5,
    "Saturation": -8,
    "Vibrance": 5,
    "HueAdjustmentRed": 5,
    "HueAdjustmentOrange": -10,
    "SaturationAdjustmentOrange": -3,
    "LuminanceAdjustmentOrange": 8,
    "HueAdjustmentYellow": 10,
    "SaturationAdjustmentYellow": -25,
    "HueAdjustmentGreen": 40,
    "SaturationAdjustmentGreen": -25,
    "LuminanceAdjustmentGreen": 15,
    "HueAdjustmentAqua": -10,
    "SaturationAdjustmentAqua": -15,
    "LuminanceAdjustmentAqua": 12,
    "HueAdjustmentBlue": -10,
    "SaturationAdjustmentBlue": -20,
    "LuminanceAdjustmentBlue": 10,
    "SaturationAdjustmentPurple": -20,
    "SaturationAdjustmentMagenta": -15,
    "LuminanceAdjustmentMagenta": 8,
    "ShadowTint": -8,
    "RedHue": -6,
    "RedSaturation": 0,
    "GreenHue": -15,
    "GreenSaturation": 5,
    "BlueHue": -10,
    "BlueSaturation": 10,
    "SplitToningShadowHue": 185,
    "SplitToningShadowSaturation": 12,
    "SplitToningHighlightHue": 0,
    "SplitToningHighlightSaturation": 0,
    "SplitToningBalance": 0,
    "GrainAmount": 10,
    "GrainSize": 15,
    "GrainFrequency": 60,
    "ToneCurvePV2012": [0, 18, 64, 70, 128, 132, 192, 195, 255, 248]
  }
}
```
