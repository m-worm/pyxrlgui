# Changelog

All notable changes to X-ray Explorer are recorded here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [semantic versioning](https://semver.org/).

## [0.1.0] - 2026-08-17

First public release.

### Added

- Nine tabs over the xraylib database: Elements, Cross sections, Emission lines, Atomic data, Compounds, Scattering, Optics, Crystals and Radionuclides.
- Interactive periodic table that can be tinted as a heat map of the K edge, Ka1, L3 edge, atomic weight, density, K fluorescence yield or mass attenuation.
- Live recomputation on every control change, with no calculate button.
- Sortable and filterable result tables, with copy to the clipboard as tab-separated text and export to CSV.
- Plot export to PNG, SVG and PDF, with log and grid toggles, pan and zoom.
- Material abstraction covering elements, chemical formulas, the 180 NIST reference materials and mixtures blended by mass.
- Light and dark themes, persisted along with the window geometry.
- Self-contained builds for Windows, macOS and Linux through `packaging/build.py`, with an Inno Setup installer, a disk image and an AppImage.
- Self-test mode, `XRAYEXPLORER_SELFTEST=1`, which computes every tab, exports a figure in three formats and checks three known xraylib values. The build refuses to package a bundle that fails it.

### Notes

- Cross sections for mixtures and the refractive index are derived in this program rather than read directly from xraylib. Both agree with the xraylib `*_CP` and `Refractive_Index_*` functions to about 1e-9 relative.
- Element coverage follows xraylib: symbols to atomic number 107, atomic weights to 103 and densities to 98.
- The macOS and Linux build paths are implemented but have not yet been exercised on those platforms.

[0.1.0]: https://github.com/m-worm/pyxrlgui/releases/tag/v0.1.0
