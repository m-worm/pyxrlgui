# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for X-ray Explorer.

Builds a *onedir* bundle on every platform. onedir is deliberate: Qt ships
under the LGPL, which requires that users be able to replace the Qt libraries
with their own build. Keeping them as ordinary shared libraries next to the
executable satisfies that; a onefile bundle would not, as clearly.

Invoked through ``packaging/build.py``, which also generates the icons.
"""

import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent          # noqa: F821 - SPECPATH is injected by PyInstaller
sys.path.insert(0, str(ROOT))

APP_NAME = "X-ray Explorer"
EXE_NAME = "XrayExplorer"
BUNDLE_ID = "org.xraylib.xrayexplorer"

icon_map = {
    "win32": ROOT / "packaging" / "icon.ico",
    "darwin": ROOT / "packaging" / "icon.icns",
}
icon_file = icon_map.get(sys.platform, ROOT / "packaging" / "icon.png")
icon = str(icon_file) if icon_file.exists() else None

hiddenimports = [
    # xraylib's SWIG wrapper picks between "from . import _xraylib" and
    # "import _xraylib" at runtime, which static analysis cannot follow.
    "xraylib", "_xraylib",
    # matplotlib loads output backends by name when savefig() sees the file
    # extension, so nothing imports these statically. Without them "Save
    # image..." fails for SVG and PDF in the frozen build.
    "matplotlib.backends.backend_agg",
    "matplotlib.backends.backend_svg",
    "matplotlib.backends.backend_pdf",
    "matplotlib.backends.backend_ps",
]

# Qt modules and dev tooling this app never touches. Dropping them roughly
# halves the bundle.
excludes = [
    "tkinter", "PyQt5", "PyQt6", "PySide2",
    "IPython", "jupyter", "notebook", "pytest", "sphinx", "setuptools",
    "pandas", "scipy", "xraydb", "yaml",
    # NOTE: do not exclude PIL. matplotlib imports it unconditionally, and
    # dropping it makes the frozen app die at startup with "Failed to execute
    # script". It costs ~11 MB; that is the price.
    # No networking anywhere in the app. Dropping QtNetwork also drops the
    # bundled OpenSSL libraries. ~11 MB.
    "PySide6.QtNetwork",
    "PySide6.Qt3DAnimation", "PySide6.Qt3DCore", "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput", "PySide6.Qt3DLogic", "PySide6.Qt3DRender",
    "PySide6.QtBluetooth", "PySide6.QtCharts", "PySide6.QtDataVisualization",
    "PySide6.QtDesigner", "PySide6.QtGraphs", "PySide6.QtGraphsWidgets",
    "PySide6.QtHelp", "PySide6.QtHttpServer", "PySide6.QtLocation",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtNfc",
    "PySide6.QtNetworkAuth", "PySide6.QtPositioning", "PySide6.QtQml",
    "PySide6.QtQuick", "PySide6.QtQuick3D", "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets", "PySide6.QtRemoteObjects", "PySide6.QtScxml",
    "PySide6.QtSensors", "PySide6.QtSerialBus", "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio", "PySide6.QtSql", "PySide6.QtStateMachine",
    "PySide6.QtTest", "PySide6.QtTextToSpeech", "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebEngineWidgets", "PySide6.QtWebSockets", "PySide6.QtWebView",
]

a = Analysis(                                             # noqa: F821
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "LICENSE"), "."),
        (str(ROOT / "THIRD-PARTY-NOTICES.md"), "."),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)                                         # noqa: F821

exe = EXE(                                                # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=EXE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # GUI app: no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)

coll = COLLECT(                                           # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_NAME,
)

if sys.platform == "darwin":
    app = BUNDLE(                                         # noqa: F821
        coll,
        name=f"{APP_NAME}.app",
        icon=icon,
        bundle_identifier=BUNDLE_ID,
        info_plist={
            "CFBundleName": APP_NAME,
            "CFBundleDisplayName": APP_NAME,
            "NSHighResolutionCapable": True,
            "LSMinimumSystemVersion": "11.0",
            "NSHumanReadableCopyright":
                "Copyright (c) 2026 Matthew Wormington. MIT licensed. Bundles Qt under the LGPLv3.",
        },
    )
