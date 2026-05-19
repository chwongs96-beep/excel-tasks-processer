# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Securities Reporting desktop app (one-folder build)."""

from pathlib import Path

DESKTOP_ROOT = Path(SPECPATH)
REPO_ROOT = DESKTOP_ROOT.parent

config_datas = [
    (str(REPO_ROOT / "config" / name), "config")
    for name in (
        "canonical_schema.yaml",
        "report_definitions.yaml",
        "template_mapping.yaml",
    )
]
preset_dir = REPO_ROOT / "config" / "mapping_presets"
if preset_dir.is_dir():
    config_datas.append((str(preset_dir), "config/mapping_presets"))

templates_dir = DESKTOP_ROOT / "app" / "templates"
template_datas = []
if templates_dir.is_dir():
    for path in templates_dir.glob("*.xlsx"):
        template_datas.append((str(path), "app/templates"))

a = Analysis(
    [str(DESKTOP_ROOT / "main.py")],
    pathex=[str(DESKTOP_ROOT), str(REPO_ROOT)],
    binaries=[],
    datas=config_datas + template_datas,
    hiddenimports=[
        "reporting",
        "reporting.mapping.presets",
        "reporting.validation.column_validator",
        "reporting.validation.date_validator",
        "reporting.validation.file_validator",
        "yaml",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SecuritiesReportDesktop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SecuritiesReportDesktop",
)
