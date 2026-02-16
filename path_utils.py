"""
Centralized path resolution utilities for ExerciseApp.
Handles both frozen (PyInstaller) and unfrozen (development) environments.
"""

import os
import sys


def get_app_root():
    """
    Get application root directory.
    Works in both frozen (PyInstaller .exe) and unfrozen (dev) environments.

    Returns:
        str: Absolute path to application root directory
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.abspath(__file__))


def get_data_dir():
    """
    Get writable data directory for CSV, JSON, and log files.

    In frozen builds, uses %LOCALAPPDATA%\ExerciseApp to avoid permission issues.
    In development, uses application root directory.

    Returns:
        str: Absolute path to writable data directory
    """
    if getattr(sys, 'frozen', False):
        # Use %LOCALAPPDATA%\ExerciseApp for writable data
        data_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'ExerciseApp')
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(os.path.join(data_dir, 'game_logs'), exist_ok=True)
        return data_dir
    else:
        # Use current directory in dev mode
        return get_app_root()


def get_game_asset_dir(game_folder_path):
    """
    Get game assets directory for individual game resources.

    Args:
        game_folder_path (str): Relative path to game folder (e.g., 'game_folder1/cardio')

    Returns:
        str: Absolute path to game assets directory
    """
    app_root = get_app_root()
    return os.path.join(app_root, game_folder_path)
