# PyInstaller spec file for Patient Charting App
# Ensure folders "templates", "entry_data", and "output_data" are included

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('templates/chart_template.txt', 'templates'),
        ('entry_data', 'entry_data'),
        ('output_data', 'output_data')
    ],
    hiddenimports=['jinja2', 'flask'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PatientChartingApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True  # Set to False if you prefer a windowless app
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PatientChartingApp'
)
