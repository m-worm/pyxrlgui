#!/usr/bin/env python3
"""Build a self-contained X-ray Explorer bundle, and a native installer.

    python packaging/build.py              # bundle + installer for this OS
    python packaging/build.py --no-installer
    python packaging/build.py --clean      # remove build/ and dist/ first

Produces, under ``dist/``:

    Windows   dist/X-ray Explorer/XrayExplorer.exe
              dist/installer/XrayExplorer-<version>-windows-x64-setup.exe
    macOS     dist/X-ray Explorer.app
              dist/installer/XrayExplorer-<version>-macos-<arch>.dmg
    Linux     dist/X-ray Explorer/XrayExplorer
              dist/installer/XrayExplorer-<version>-linux-x86_64.AppImage
                 (or a .tar.gz if appimagetool is unavailable)

Installers cannot be cross-compiled: PyInstaller freezes the interpreter it is
run with, so each platform's artifact must be built on that platform. Run this
script once per target OS (a CI matrix does this nicely).
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGING = ROOT / "packaging"
DIST = ROOT / "dist"
BUILD = ROOT / "build"
INSTALLER_DIR = DIST / "installer"

APP_NAME = "X-ray Explorer"
EXE_NAME = "XrayExplorer"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def log(message: str) -> None:
    print(f"\033[36m==>\033[0m {message}" if sys.stdout.isatty() else f"==> {message}",
          flush=True)


def warn(message: str) -> None:
    print(f"\033[33m !\033[0m {message}" if sys.stdout.isatty() else f" !  {message}",
          flush=True)


def run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    printable = " ".join(f'"{c}"' if " " in str(c) else str(c) for c in command)
    print(f"    {printable}", flush=True)
    return subprocess.run([str(c) for c in command], check=True, **kwargs)


def app_version() -> str:
    """Read __version__ without importing the package (avoids needing Qt here)."""
    text = (ROOT / "xrlgui" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
    return match.group(1) if match else "0.0.0"


def require_tools() -> None:
    missing = []
    for module in ("PyInstaller", "PySide6", "matplotlib", "numpy", "xraylib"):
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    if missing:
        raise SystemExit(
            "Missing build dependencies: " + ", ".join(missing) +
            "\nInstall them with:\n"
            "  pip install -r requirements.txt\n"
            "  pip install pyinstaller")


# --------------------------------------------------------------------------
# stages
# --------------------------------------------------------------------------


def clean() -> None:
    for path in (BUILD, DIST):
        if path.exists():
            log(f"removing {path.relative_to(ROOT)}")
            shutil.rmtree(path)


def make_icons() -> None:
    log("generating icons")
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    run([sys.executable, PACKAGING / "make_icon.py"], env=env)


def freeze() -> Path:
    log(f"freezing {APP_NAME} {app_version()} with PyInstaller")
    run([sys.executable, "-m", "PyInstaller",
         "--noconfirm", "--clean",
         "--distpath", DIST, "--workpath", BUILD,
         PACKAGING / "xrayexplorer.spec"])

    bundle = (DIST / f"{APP_NAME}.app") if sys.platform == "darwin" else (DIST / APP_NAME)
    if not bundle.exists():
        raise SystemExit(f"expected bundle at {bundle}, but it was not produced")
    size = sum(f.stat().st_size for f in bundle.rglob("*") if f.is_file())
    log(f"bundle ready: {bundle}  ({size / 1e6:.0f} MB)")
    return bundle


def smoke_test(bundle: Path) -> None:
    """Launch the frozen app headless to prove xraylib survived freezing."""
    if sys.platform == "darwin":
        executable = bundle / "Contents" / "MacOS" / EXE_NAME
    elif sys.platform == "win32":
        executable = bundle / f"{EXE_NAME}.exe"
    else:
        executable = bundle / EXE_NAME
    if not executable.exists():
        warn(f"no executable at {executable}; skipping smoke test")
        return

    log("smoke-testing the frozen bundle")
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["XRAYEXPLORER_SELFTEST"] = "1"
    try:
        result = subprocess.run([str(executable)], env=env, timeout=180,
                                capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        # A frozen GUI app that fails to start pops a modal error dialog and
        # waits forever, so a hang means a broken bundle, not a slow one.
        raise SystemExit(
            "smoke test timed out — the frozen app did not start.\n"
            "    Run it directly to see the error dialog:\n"
            f"    {executable}") from None
    output = (result.stdout + result.stderr).strip()
    if result.returncode == 0:
        log(f"smoke test passed — {output.splitlines()[-1] if output else 'no output'}")
    else:
        warn(f"smoke test failed (exit {result.returncode}):\n{output}")
        raise SystemExit("refusing to package a bundle that does not start")


# --------------------------------------------------------------------------
# installers
# --------------------------------------------------------------------------


def find_iscc() -> Path | None:
    candidates = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ]
    found = shutil.which("iscc") or shutil.which("ISCC")
    if found:
        candidates.insert(0, Path(found))
    return next((c for c in candidates if c.exists()), None)


def installer_windows(bundle: Path, version: str) -> Path | None:
    iscc = find_iscc()
    if iscc is None:
        warn("Inno Setup 6 not found — skipping the installer.\n"
             "    Install it from https://jrsoftware.org/isdl.php, then re-run.")
        return zip_fallback(bundle, version, "windows-x64")

    log("building the Windows installer with Inno Setup")
    INSTALLER_DIR.mkdir(parents=True, exist_ok=True)
    run([iscc,
         f"/DAppVersion={version}",
         f"/DSourceDir={bundle}",
         f"/DOutputDir={INSTALLER_DIR}",
         f"/DProjectRoot={ROOT}",
         PACKAGING / "windows" / "installer.iss"])
    produced = sorted(INSTALLER_DIR.glob("*setup.exe"))
    return produced[-1] if produced else None


def installer_macos(bundle: Path, version: str) -> Path | None:
    if not shutil.which("hdiutil"):
        warn("hdiutil not found — skipping the DMG")
        return None

    log("building the macOS disk image")
    INSTALLER_DIR.mkdir(parents=True, exist_ok=True)
    arch = platform.machine()
    dmg = INSTALLER_DIR / f"{EXE_NAME}-{version}-macos-{arch}.dmg"
    dmg.unlink(missing_ok=True)

    staging = BUILD / "dmg"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    shutil.copytree(bundle, staging / bundle.name, symlinks=True)
    # The /Applications symlink gives the familiar drag-to-install window.
    os.symlink("/Applications", staging / "Applications")
    for extra in ("LICENSE", "THIRD-PARTY-NOTICES.md"):
        if (ROOT / extra).exists():
            shutil.copy2(ROOT / extra, staging / extra)

    run(["hdiutil", "create", "-volname", APP_NAME, "-srcfolder", staging,
         "-ov", "-format", "UDZO", dmg])
    return dmg


def installer_linux(bundle: Path, version: str) -> Path | None:
    INSTALLER_DIR.mkdir(parents=True, exist_ok=True)
    appdir = BUILD / f"{EXE_NAME}.AppDir"
    if appdir.exists():
        shutil.rmtree(appdir)

    log("assembling the AppDir")
    (appdir / "usr" / "bin").mkdir(parents=True)
    for item in bundle.iterdir():
        target = appdir / "usr" / "bin" / item.name
        if item.is_dir():
            shutil.copytree(item, target, symlinks=True)
        else:
            shutil.copy2(item, target)

    desktop = (PACKAGING / "linux" / "xray-explorer.desktop").read_text(encoding="utf-8")
    (appdir / "xray-explorer.desktop").write_text(desktop, encoding="utf-8")
    icon = PACKAGING / "icon.png"
    if icon.exists():
        shutil.copy2(icon, appdir / "xray-explorer.png")

    apprun = appdir / "AppRun"
    apprun.write_text(
        '#!/bin/sh\n'
        'HERE="$(dirname "$(readlink -f "$0")")"\n'
        f'exec "$HERE/usr/bin/{EXE_NAME}" "$@"\n',
        encoding="utf-8")
    apprun.chmod(0o755)

    tool = shutil.which("appimagetool") or shutil.which("appimagetool-x86_64.AppImage")
    if tool:
        log("building the AppImage")
        arch = platform.machine()
        target = INSTALLER_DIR / f"{EXE_NAME}-{version}-linux-{arch}.AppImage"
        target.unlink(missing_ok=True)
        env = dict(os.environ, ARCH=arch)
        run([tool, appdir, target], env=env)
        target.chmod(0o755)
        return target

    warn("appimagetool not found — falling back to a .tar.gz.\n"
         "    Get it from https://github.com/AppImage/AppImageKit/releases "
         "for a single-file AppImage.")
    return tar_fallback(appdir, version, f"linux-{platform.machine()}")


def zip_fallback(bundle: Path, version: str, tag: str) -> Path:
    INSTALLER_DIR.mkdir(parents=True, exist_ok=True)
    base = INSTALLER_DIR / f"{EXE_NAME}-{version}-{tag}"
    log(f"creating {base.name}.zip")
    archive = shutil.make_archive(str(base), "zip", root_dir=bundle.parent,
                                  base_dir=bundle.name)
    return Path(archive)


def tar_fallback(source: Path, version: str, tag: str) -> Path:
    INSTALLER_DIR.mkdir(parents=True, exist_ok=True)
    target = INSTALLER_DIR / f"{EXE_NAME}-{version}-{tag}.tar.gz"
    log(f"creating {target.name}")
    with tarfile.open(target, "w:gz") as tar:
        tar.add(source, arcname=f"{EXE_NAME}-{version}")
    return target


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clean", action="store_true",
                        help="delete build/ and dist/ before building")
    parser.add_argument("--no-installer", action="store_true",
                        help="build the bundle only")
    parser.add_argument("--no-smoke-test", action="store_true",
                        help="skip launching the frozen app to verify it starts")
    args = parser.parse_args()

    require_tools()
    version = app_version()
    log(f"{APP_NAME} {version} on {platform.system()} {platform.machine()} "
        f"(Python {platform.python_version()})")

    if args.clean:
        clean()

    make_icons()
    bundle = freeze()
    if not args.no_smoke_test:
        smoke_test(bundle)

    if args.no_installer:
        log("done (bundle only)")
        return 0

    builder = {"win32": installer_windows,
               "darwin": installer_macos}.get(sys.platform, installer_linux)
    artifact = builder(bundle, version)

    print()
    log("build complete")
    print(f"    bundle:    {bundle}")
    if artifact:
        print(f"    installer: {artifact}  ({artifact.stat().st_size / 1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
