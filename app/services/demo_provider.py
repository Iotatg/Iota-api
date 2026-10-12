"""Demo media provider.

Reads from a directory of pre-licensed audio files (one file per media_id).
The file at `storage/audio/<media_id>.mp3` is served when a client requests
`media_id`. A manifest.json file can describe additional metadata for each
id; otherwise, the file's mtime and size are used.

This is a SAFE DEFAULT that:
- never reaches the public internet,
- never extracts audio from any third-party source,
- is fully self-contained,
- is suitable for production as a reference implementation.

The interface is identical to a real provider so you can swap it out.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from app.services.media_provider import (
    MediaMetadata,
    MediaNotFoundError,
    MediaProvider,
    StreamSource,
)


class DemoProvider(MediaProvider):
    name = "demo"

    def __init__(self, audio_dir: str) -> None:
        self.audio_dir = Path(audio_dir).resolve()
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self._manifest: Dict[str, dict] = self._load_manifest()

    def _load_manifest(self) -> Dict[str, dict]:
        manifest_path = self.audio_dir / "manifest.json"
        if not manifest_path.is_file():
            return {}
        try:
            return json.loads(manifest_path.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _resolve(self, media_id: str) -> Path:
        # media_id is restricted to [a-zA-Z0-9_-] to prevent path traversal
        if not media_id or not all(c.isalnum() or c in "-_." for c in media_id):
            raise MediaNotFoundError(f"invalid media_id: {media_id!r}")
        return self.audio_dir / media_id

    def _build(self, media_id: str, file_path: Path) -> MediaMetadata:
        meta = self._manifest.get(media_id, {})
        return MediaMetadata(
            media_id=media_id,
            title=meta.get("title", media_id),
            artist=meta.get("artist"),
            duration_seconds=meta.get("duration_seconds"),
            thumbnail_url=meta.get("thumbnail_url"),
            size_bytes=file_path.stat().st_size if file_path.exists() else None,
            mime_type=meta.get("mime_type", "audio/mpeg"),
            storage_key=file_path.name,
            provider=self.name,
        )

    async def search(self, query: str, limit: int = 20) -> List[MediaMetadata]:
        q = (query or "").lower().strip()
        results: List[MediaMetadata] = []
        for path in sorted(self.audio_dir.glob("*")):
            if not path.is_file() or path.name in {"manifest.json", ".gitkeep"}:
                continue
            media_id = path.name
            meta = self._build(media_id, path)
            haystack = f"{meta.title} {meta.artist or ''}".lower()
            if q in haystack or q in media_id.lower():
                results.append(meta)
                if len(results) >= limit:
                    break
        return results

    async def get_info(self, media_id: str) -> MediaMetadata:
        path = self._resolve(media_id)
        if not path.is_file():
            raise MediaNotFoundError(media_id)
        return self._build(media_id, path)

    async def get_stream(self, media_id: str) -> StreamSource:
        path = self._resolve(media_id)
        if not path.is_file():
            raise MediaNotFoundError(media_id)
        return StreamSource(
            storage_key=path.name,
            size_bytes=path.stat().st_size,
            mime_type=self._manifest.get(media_id, {}).get("mime_type", "audio/mpeg"),
        )
