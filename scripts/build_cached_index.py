"""Build the cached-track index shipped in the image.

Source of truth is the upstream catalog JSON (catbox-hosted renditions
only). Output is deduplicated, sanitized, and host-allowlisted so the
runtime loader can trust it without re-validation round-trips.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ALLOWED_HOST = "files.catbox.moe"
PATH_RE = re.compile(r"^/[A-Za-z0-9 _-]{4,32}\.(mp3|m4a|mp4)$", re.IGNORECASE)

_AUDIO_EXTS = ("mp3", "m4a")
_PRIORITY = {"mp3": 0, "m4a": 1, "mp4": 2}


def _entry(raw: dict) -> dict | None:
    vid = str(raw.get("video_id", "")).strip()
    url = str(raw.get("stream_url", "")).strip()
    title = str(raw.get("title", "")).strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid) or not title:
        return None
    if not url.startswith(f"https://{ALLOWED_HOST}"):
        return None
    rest = url[len(f"https://{ALLOWED_HOST}"):]
    if not PATH_RE.fullmatch(rest):
        return None
    ext = rest.rsplit(".", 1)[1].lower()
    mime = "video/mp4" if ext == "mp4" else "audio/mp4" if ext == "m4a" else "audio/mpeg"
    return {
        "id": vid,
        "title": title[:180],
        "url": f"https://{ALLOWED_HOST}{rest}",
        "mime": mime,
        "ext": ext,
    }


def build(src: Path) -> list[dict]:
    raw_items = json.loads(src.read_text(encoding="utf-8"))
    best: dict[str, dict] = {}
    for raw in raw_items:
        entry = _entry(raw)
        if entry is None:
            continue
        current = best.get(entry["id"])
        if current is None or _PRIORITY[entry["ext"]] < _PRIORITY[current["ext"]]:
            best[entry["id"]] = entry
    return sorted(best.values(), key=lambda e: e["id"])


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/songs.json")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("data/cached_tracks.json")
    entries = build(src)
    out.write_text(json.dumps(entries, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {len(entries)} cached tracks to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
