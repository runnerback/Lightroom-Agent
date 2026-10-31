# X_Style_Name

<!-- Copy this file to ~/.lightroom-agent/styles/<Letter>_<Name>.md (your own styles) or to styles/ (to contribute).
     The file name is the style name. Only the first json block below is read; everything else is for people.
     Guide: styles/README.md -->

**Look:** one or two sentences: what the photos should look like.

**Characteristics**
- Tone: contrast, highlights, blacks, curve.
- Colour: which colours are pushed or muted, split toning.
- Texture: grain, clarity, vignette.

**Good for:** scenes and light this style suits.

**Notes**
- Caveats: scenes where it fails, things to check in the overview.

```json
{
  "desc": "one line the agent sees when choosing a style",
  "skin": {"L": 66, "a": 14, "b": 18},
  "white": {"a": 0.5, "b": 2.5},
  "settings": {
    "Contrast2012": 0,
    "Highlights2012": -30,
    "Shadows2012": 15,
    "Vibrance": 5,
    "ToneCurvePV2012": [0, 0, 255, 255]
  }
}
```
