# Changelog

Write changes under **Unreleased** as you go. `python3 scripts/release.py X.Y.Z` turns that section into
`X.Y.Z - <date>`, and the release workflow uses it as the highlights of the GitHub release.

## Unreleased

## 0.3.0 - 2026-11-08

### Added
- Black-and-white styles **E1_Leica_Monochrom** (long, smooth tonal range, neutral grey) and **E2_GR_IV_Monochrome**
  (hard "Solid" curve with a red-filter mix). Any style with `"ConvertToGrayscale": true` is B&W: exposure is
  calibrated on the face, white balance stays as shot, raw files switch to the Adobe Monochrome profile and get their
  colour profile back when a colour style is applied later.
- `export --preset NAME` (and `preset` on the MCP `export_photos` tool): export with one of your own Lightroom export
  presets; only the destination folder is replaced.
- `apply-style --wb-from NAME=REF`: lock a photo's white balance to a neighbour shot in the same light (for tight crops
  or deep shade with too few whites); exposure is still calibrated on its own face.
- Release automation: `scripts/release.py` and `.github/workflows/release.yml` (push a version tag such as
  `0.3.0`, get a GitHub release with the Lightroom plugin attached).

### Fixed
- Faces were missed in pale, pastel renders (style D with whites-balanced WB): the skin-colour filter is slightly wider.
- `--refine` no longer starts from a calibration borrowed from another photo.

## v0.1.1 - 2026-10-31

First public release: culling with contact sheets, picks to ratings / labels / collections, per-photo calibrated
styles A_Airy_White, B_Warm_Film, C_Natural, D_Fuji_400H, rollback, Claude Code plugin and MCP server, installer.
