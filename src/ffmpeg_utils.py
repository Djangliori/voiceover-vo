"""
FFmpeg utility functions
Handles ffmpeg path resolution across different environments
"""

import os
import shutil
from pathlib import Path


def get_ffmpeg_path():
    """
    Get the path to ffmpeg executable.
    Tries multiple locations to ensure it works on Windows, Linux, and Railway.

    Returns:
        str: Path to ffmpeg executable
    """
    # Try Nix path first (Railway deployment)
    nix_path = '/nix/var/nix/profiles/default/bin/ffmpeg'
    if os.path.exists(nix_path):
        return nix_path

    # Try explicit Windows installation paths
    windows_paths = [
        'C:/ffmpeg/bin/ffmpeg.exe',
        'C:\\ffmpeg\\bin\\ffmpeg.exe',
        os.path.expanduser('~/ffmpeg/bin/ffmpeg.exe'),
    ]

    for path in windows_paths:
        if os.path.exists(path):
            return path

    # Try using shutil.which (checks system PATH)
    ffmpeg_which = shutil.which('ffmpeg')
    if ffmpeg_which:
        return ffmpeg_which

    # Try common Linux locations
    linux_paths = [
        '/usr/bin/ffmpeg',
        '/usr/local/bin/ffmpeg',
    ]

    for path in linux_paths:
        if os.path.exists(path):
            return path

    # Last resort: just return 'ffmpeg' and hope it's in PATH
    # If this doesn't work, user needs to install ffmpeg or add to PATH
    return 'ffmpeg'


def get_ffprobe_path():
    """
    Get the path to ffprobe executable.
    Tries multiple locations to ensure it works on Windows, Linux, and Railway.

    Returns:
        str: Path to ffprobe executable
    """
    # Try Nix path first (Railway deployment)
    nix_path = '/nix/var/nix/profiles/default/bin/ffprobe'
    if os.path.exists(nix_path):
        return nix_path

    # Try explicit Windows installation paths
    windows_paths = [
        'C:/ffmpeg/bin/ffprobe.exe',
        'C:\\ffmpeg\\bin\\ffprobe.exe',
        os.path.expanduser('~/ffmpeg/bin/ffprobe.exe'),
    ]

    for path in windows_paths:
        if os.path.exists(path):
            return path

    # Try using shutil.which (checks system PATH)
    ffprobe_which = shutil.which('ffprobe')
    if ffprobe_which:
        return ffprobe_which

    # Try common Linux locations
    linux_paths = [
        '/usr/bin/ffprobe',
        '/usr/local/bin/ffprobe',
    ]

    for path in linux_paths:
        if os.path.exists(path):
            return path

    # Last resort
    return 'ffprobe'
