# PyInstaller spec for the macOS app bundle.
# Build with:  uv run pyinstaller packaging/cligui.spec

import os
import tomllib
from pathlib import Path

project_root = Path(SPECPATH).parent
icon_assets = project_root / "packaging" / "app-icons"
with (project_root / "pyproject.toml").open("rb") as metadata:
    app_version = tomllib.load(metadata)["project"]["version"]

a = Analysis(
    [str(project_root / "src" / "cligui" / "app.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
    datas=[
        (str(icon_assets / "BetterCLI-light.png"), "."),
        (str(icon_assets / "BetterCLI-dark.png"), "."),
    ],
    hiddenimports=["keyring.backends.macOS", "keyring.backends.SecretService"],
    hookspath=[],
    runtime_hooks=[],
    # PySide6 ships far more than this app needs; dropping these keeps the
    # bundle to a sane size.
    excludes=[
        "PySide6.Qt3DCore",
        "PySide6.Qt3DRender",
        "PySide6.QtCharts",
        "PySide6.QtDataVisualization",
        "PySide6.QtMultimedia",
        "PySide6.QtMultimediaWidgets",
        "PySide6.QtQuick",
        "PySide6.QtQuick3D",
        "PySide6.QtQml",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtWebEngineQuick",
        "tkinter",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BetterCLI",
    debug=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=False,
    codesign_identity=os.environ.get("BETTERCLI_CODESIGN_IDENTITY"),
    entitlements_file=os.environ.get("BETTERCLI_ENTITLEMENTS_FILE"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="BetterCLI",
)

app = BUNDLE(
    coll,
    name="BetterCLI.app",
    icon=str(project_root / "packaging" / "BetterCLI.icns"),
    bundle_identifier=os.environ.get("BETTERCLI_BUNDLE_ID", "com.swetrasoft.BetterCLI"),
    info_plist={
        "CFBundleName": "BetterCLI",
        "CFBundleDisplayName": "BetterCLI",
        "CFBundleShortVersionString": app_version,
        "CFBundleVersion": os.environ.get("BETTERCLI_BUILD_NUMBER", "1"),
        "LSApplicationCategoryType": "public.app-category.developer-tools",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",
    },
)
