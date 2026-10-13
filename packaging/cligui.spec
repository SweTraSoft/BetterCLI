# PyInstaller spec for the macOS app bundle.
# Build with:  uv run pyinstaller packaging/cligui.spec

from pathlib import Path

project_root = Path(SPECPATH).parent
icon_assets = project_root / "packaging" / "app-icons"

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
    bundle_identifier="dev.bettercli.app",
    info_plist={
        "CFBundleName": "BetterCLI",
        "CFBundleDisplayName": "BetterCLI",
        "CFBundleShortVersionString": "0.1.0",
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "12.0",
    },
)
