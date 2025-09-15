"""PyInstaller spec for building the GUI executable on Windows."""

from __future__ import annotations

from PyInstaller.building.build_main import Analysis, COLLECT, EXE, PYZ
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = (
    ["pythoncom", "pywintypes"]
    + collect_submodules("win32com")
    + collect_submodules("win32com.client")
    + collect_submodules("win32com.gen_py")
)

analysis = Analysis(
    ["src/pdf_toolbox/gui/__main__.py"],
    hiddenimports=hiddenimports,
    pathex=[],
    binaries=[],
    datas=[],
    hooksconfig={},
)
pyz = PYZ(analysis.pure, analysis.zipped_data)
exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    name="pdf_toolbox",
    console=False,
)
coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    name="pdf_toolbox",
)
