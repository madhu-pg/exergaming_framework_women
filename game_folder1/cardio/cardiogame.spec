# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['cardiogame.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('background.png', '.'),
        ('plant_stage1-removebg-preview.png', '.'),
        ('plant_stage2-removebg-preview.png', '.'),
        ('plant_stage3-removebg-preview.png', '.'),
        ('plant_stage4-removebg-preview.png', '.'),
        ('plant_stage5-removebg-preview.png', '.'),
        ('plant_stage6-removebg-preview.png', '.'),
        ('plant_stage7-removebg-preview.png', '.'),
        ('plant_stage8-removebg-preview.png', '.'),
        ('plant_stage9-removebg-preview.png', '.'),
        ('correct-156911.mp3', '.'),
    ],
    hiddenimports=[
        'cv2',
        'mediapipe',
        'mediapipe.python',
        'mediapipe.python.solutions',
        'mediapipe.python._framework_bindings',
        'numpy',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=True,      # 🔥 THIS STOPS BYTECODE SCAN
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CardioGame',
    debug=False,
    strip=False,
    upx=False,          # 🔥 OpenCV safe
    console=False,
)
