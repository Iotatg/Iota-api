"""Tiny WAV bytes so demo catalog tracks are playable without licensed audio."""
from __future__ import annotations

import math
import struct
import zlib


def demo_wav_bytes(video_id: str, seconds: float = 2.0, sample_rate: int = 8000) -> bytes:
    seed = zlib.crc32(video_id.encode("utf-8")) & 0xFFFFFFFF
    n = int(sample_rate * seconds)
    freq = 220 + (seed % 400)
    samples = bytearray()
    for i in range(n):
        t = i / sample_rate
        val = int(8000 * math.sin(2 * math.pi * freq * t))
        samples.extend(struct.pack("<h", val))
    data = bytes(samples)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(data),
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        sample_rate * 2,
        2,
        16,
        b"data",
        len(data),
    )
    return header + data
