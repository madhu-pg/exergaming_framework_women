# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for ExerciseApp
Bundles Python exercise game with OpenCV, MediaPipe, and pygame
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os

block_cipher = None

# Collect MediaPipe model files (pose detection models ~70MB)
datas = collect_data_files('mediapipe', include_py_files=False)

# Add application assets
datas += [
    ('images', 'images'),  # 17 launcher UI images
    ('app_icon.ico', '.'),  # Application icon
    ('game_folder1', 'game_folder1'),  # Cardio exercises
    ('game_folder2', 'game_folder2'),  # Stretch exercises
    ('game_folder3', 'game_folder3'),  # Bending exercises
    ('game_folder4', 'game_folder4'),  # Marching exercises
    ('game_folder5', 'game_folder5'),  # Squat exercises
    ('game_folder6', 'game_folder6'),  # Twist exercises
]

# Collect game modules (ensure all game scripts are included)
hiddenimports = [
    'cv2',
    'mediapipe',
    'mediapipe.python',
    'mediapipe.python.solutions',
    'mediapipe.python._framework_bindings',
    'mediapipe.calculators',
    'mediapipe.modules',
    'mediapipe.tasks',
    'numpy',
    'pygame',
    'PIL',
    'PIL._tkinter_finder',
]

# Add all game modules dynamically
for folder in ['game_folder1', 'game_folder2', 'game_folder3',
               'game_folder4', 'game_folder5', 'game_folder6']:
    if os.path.exists(folder):
        for variant in os.listdir(folder):
            variant_path = os.path.join(folder, variant)
            if os.path.isdir(variant_path) and not variant.startswith('venv'):
                try:
                    hiddenimports.extend(collect_submodules(f'{folder}.{variant}'))
                except Exception:
                    pass  # Skip if module collection fails

a = Analysis(
    ['launcher_all_pages.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 'matplotlib',  # Actually IS used by games! Don't exclude
        'scipy',       # Not used
        'pandas',      # Not used
        'tkinter',     # Not used (pygame only)
        'IPython',     # Not used
        'notebook',    # Not used
        'jupyter',     # Not used
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # ONEDIR mode (creates folder with exe + dependencies)
    name='ExerciseApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # Disable UPX compression (incompatible with OpenCV)
    console=True,  # Enable console temporarily for debugging
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ExerciseApp',
)
