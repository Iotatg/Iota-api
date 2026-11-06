"""Locate the ffmpeg binary used for the merges and the mp3 transcode.

The PATH of a container can point at a build that crashes on a fragmented
mp4. The folder of a known good build wins over it when FFMPEG_LOCATION
names one.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

_CANDIDATE_FOLDERS = ("/usr/bin", "/usr/local/bin", "/bin")


def ffmpeg_binary() -> str:
    """Return the ffmpeg binary to use."""
    location = (os.environ.get("FFMPEG_LOCATION") or "").strip()
    if location:
        candidate = Path(location) / "ffmpeg"
        if candidate.is_file():
            return str(candidate)

    # The folders are checked before the PATH: a static build in
    # /usr/local/bin can crash on a fragmented mp4 while the build of the
    # distribution in /usr/bin handles it.
    for folder in _CANDIDATE_FOLDERS:
        candidate = Path(folder) / "ffmpeg"
        if candidate.is_file():
            return str(candidate)

    return shutil.which("ffmpeg") or "ffmpeg"
