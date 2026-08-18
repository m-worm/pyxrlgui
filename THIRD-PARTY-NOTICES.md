# Third-party notices

X-ray Explorer is itself under the MIT License. See `LICENSE`. A packaged build made with `packaging/build.py` is self-contained, so it redistributes the components listed below, and each of those keeps its own license.

This file is a good-faith summary written for practical use. It is not legal advice. If you ship builds commercially, have counsel confirm the Qt and LGPL obligations for your situation.

| Component | Version built against | License |
| --- | --- | --- |
| [xraylib](https://github.com/tschoonj/xraylib) | 4.2.1 | BSD 3-Clause |
| [Qt](https://www.qt.io/) through [PySide6](https://doc.qt.io/qtforpython/) and shiboken6 | 6.11 | LGPL v3, or commercial |
| [matplotlib](https://matplotlib.org/) | 3.11 | Matplotlib License, a BSD-style license derived from the PSF one |
| [NumPy](https://numpy.org/) | 2.5 | BSD 3-Clause |
| [contourpy](https://github.com/contourpy/contourpy), [kiwisolver](https://github.com/nucleic/kiwi) and [cycler](https://matplotlib.org/cycler/) | | BSD 3-Clause |
| [fonttools](https://github.com/fonttools/fonttools) and [pyparsing](https://github.com/pyparsing/pyparsing) | | MIT |
| [Pillow](https://python-pillow.org/) | 12.3 | MIT-CMU |
| [python-dateutil](https://github.com/dateutil/dateutil) | 2.9 | BSD 3-Clause or Apache-2.0 |
| [packaging](https://github.com/pypa/packaging) | | Apache-2.0 or BSD 2-Clause |
| CPython runtime | 3.12 | Python Software Foundation License |
| [PyInstaller](https://pyinstaller.org/) bootloader | 6.22 | GPL v2 or later, with the bootloader exception |

## The two components that constrain you

### Qt and PySide6, under the LGPL v3

This is the one obligation worth understanding in detail. The LGPL allows you to ship X-ray Explorer under the MIT License, or under any other license including a proprietary one, but the build must meet three conditions.

First, it must state that it uses Qt and that Qt is licensed under the LGPL v3. The About dialog and this file both do so. Second, it must allow users to replace the Qt libraries with a modified or different build of Qt. This is why `packaging/xrayexplorer.spec` produces a directory rather than a single file: Qt stays as ordinary `.dll`, `.so` and `.dylib` files next to the executable, where a user can replace them. Do not switch the specification to the one-file mode of PyInstaller without taking separate advice, because a single self-extracting binary makes that condition much harder to satisfy. Third, it must provide the LGPL v3 text and the Qt source, or a written offer of the source. The canonical source is at <https://download.qt.io/official_releases/qt/> and the license text is at <https://www.gnu.org/licenses/lgpl-3.0.html>.

Qt must not be linked statically, and its license notices must not be removed.

### PyInstaller, under the GPL v2 with an exception

PyInstaller is licensed under the GPL v2, but its bootloader carries an explicit exception that permits the resulting bundled application to be distributed under any license, including a proprietary one. Freezing this program therefore does not make it GPL.

## The permissive remainder

xraylib, NumPy, matplotlib, Pillow and the small support libraries are all under BSD, MIT or Apache-style licenses. They require attribution, which this file provides, and nothing more.

## If you cite xraylib

The xraylib authors ask that published work using their data cite their papers. The 2011 paper supersedes the 2004 original and is the one to cite for current versions.

> T. Schoonjans, A. Brunetti, B. Golosio, M. Sanchez del Rio, V. A. Sole, C. Ferrero and L. Vincze, "The xraylib library for X-ray-matter interactions. Recent developments", *Spectrochimica Acta Part B* **66** (2011) 776-784. <https://doi.org/10.1016/j.sab.2011.09.011>

> A. Brunetti, M. Sanchez del Rio, B. Golosio, A. Simionovici and A. Somogyi, "A library for X-ray matter interaction cross sections for X-ray fluorescence applications", *Spectrochimica Acta Part B* **59** (2004) 1725-1731. <https://doi.org/10.1016/j.sab.2004.03.014>

See the [xraylib wiki](https://github.com/tschoonj/xraylib/wiki) for current citation guidance.
