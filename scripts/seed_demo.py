"""Seed the demo audio directory with synthetic MP3 files.

This generates a few tiny but VALID MP3 files (silent, ~1 second each)
so that the demo provider has something to stream out of the box. These
are generated programmatically using only the standard library — no
external tools required.

USAGE:
    python scripts/seed_demo.py [output_dir]

The default output_dir is ./storage/audio (relative to project root).
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path


def make_silent_mp3(target_bytes: int = 50_000) -> bytes:
    """Build a minimal valid MP3 file (MPEG-1 Layer III, mono, 32 kbps).

    This is a SILENT MP3 — useful for testing streaming mechanics without
    shipping real audio. The bitstream is technically conformant but the
    output is silence. Don't use this for music — it's a stub.

    The file is padded out to ~target_bytes by repeating frames, so Range
    requests can be exercised meaningfully on the live service.

    Structure:
    - ID3v2.3 header (10 bytes) + 0-byte tag
    - N MPEG-1 Layer III frames of 144 bytes each
    """
    id3_header = b"ID3" + bytes([3, 0, 0, 0, 0, 0, 0, 0])
    frame_header = bytes([
        0xFF, 0xFB, 0x10, 0xC4,
    ])
    frame_data = b"\x00" * 140
    frame = frame_header + frame_data

    n_frames = max(1, (target_bytes - len(id3_header)) // len(frame))
    return id3_header + frame * n_frames


def main() -> int:
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("storage/audio")
    out_dir.mkdir(parents=True, exist_ok=True)

    samples = [
        ("sample-001.mp3", 50_000, {"title": "Sample One", "artist": "Test Artist", "duration_seconds": 60}),
        ("sample-002.mp3", 30_000, {"title": "Sample Two", "artist": "Other Artist", "duration_seconds": 30}),
        ("sample-003.mp3", 80_000, {"title": "Sample Three", "artist": "Test Artist", "duration_seconds": 120}),
    ]
    manifest: dict[str, dict] = {}
    for filename, size, meta in samples:
        path = out_dir / filename
        if not path.exists() or path.stat().st_size < size:
            path.write_bytes(make_silent_mp3(target_bytes=size))
        manifest[filename] = meta

    import json
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"Seeded {len(samples)} files into {out_dir}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
