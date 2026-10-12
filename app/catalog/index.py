"""In-memory inverted token index for the public songs catalog.

Search never hits Postgres. Tokens are lowercased alphanumerics.
Ranking: exact video_id, title prefix, all-tokens, then partial token overlap.
"""
from __future__ import annotations

import json
import random
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Optional

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall((text or "").lower())


class SongIndex:
    def __init__(self, songs: Iterable[dict[str, Any]] | None = None) -> None:
        self._songs: list[dict[str, Any]] = []
        self._by_id: dict[str, dict[str, Any]] = {}
        self._inverted: dict[str, set[int]] = defaultdict(set)
        self._prefix: dict[str, list[str]] = defaultdict(list)
        if songs:
            self.load(list(songs))

    def load(self, songs: list[dict[str, Any]]) -> None:
        self._songs = []
        self._by_id = {}
        self._inverted = defaultdict(set)
        self._prefix = defaultdict(list)
        seen: set[str] = set()
        for song in songs:
            vid = str(song.get("video_id") or "").strip()
            if not vid or vid in seen:
                continue
            seen.add(vid)
            record = {
                "video_id": vid,
                "title": song.get("title") or vid,
                "artist": song.get("artist") or "",
                "stream_url": song.get("stream_url") or f"/api/file/{vid}",
                "source": song.get("source") or "iota_cloud",
                "thumbnail": song.get("thumbnail") or "/static/thumbs/default.svg",
                "duration_seconds": int(song.get("duration_seconds") or 0),
                "tags": list(song.get("tags") or []),
            }
            idx = len(self._songs)
            self._songs.append(record)
            self._by_id[vid] = record
            blob = " ".join(
                [
                    record["title"],
                    record["artist"],
                    " ".join(record["tags"]),
                ]
            )
            tokens = tokenize(blob)
            for tok in set(tokens):
                self._inverted[tok].add(idx)
                for n in range(1, min(len(tok), 12) + 1):
                    pref = tok[:n]
                    if record["title"] not in self._prefix[pref]:
                        self._prefix[pref].append(record["title"])

    @classmethod
    def from_json_path(cls, path: str | Path) -> "SongIndex":
        p = Path(path)
        if not p.is_file():
            return cls([])
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            data = []
        return cls(data)

    def __len__(self) -> int:
        return len(self._songs)

    def get(self, video_id: str) -> Optional[dict[str, Any]]:
        return self._by_id.get(video_id)

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        clean = (query or "").strip()
        if not clean:
            return []
        limit = max(1, min(int(limit), 50))
        q_lower = clean.lower()
        if q_lower in self._by_id:
            return [self._by_id[q_lower]]
        tokens = tokenize(clean)
        if not tokens:
            return []

        scored: dict[int, int] = {}
        for tok in tokens:
            for idx in self._inverted.get(tok, ()):
                scored[idx] = scored.get(idx, 0) + 3
            for pref_tok, ids in self._inverted.items():
                if pref_tok.startswith(tok) and pref_tok != tok:
                    for idx in ids:
                        scored[idx] = scored.get(idx, 0) + 1

        ranked: list[tuple[int, int, str, int]] = []
        for idx, score in scored.items():
            song = self._songs[idx]
            title_l = song["title"].lower()
            artist_l = song["artist"].lower()
            hay = f"{title_l} {artist_l}"
            all_tokens = all(t in hay for t in tokens)
            rank = 50 - score
            if len(tokens) == 1 and q_lower == title_l:
                rank = 0
            elif len(tokens) == 1 and title_l.startswith(q_lower):
                rank = 1
            elif len(tokens) == 1 and q_lower in hay:
                rank = 2
            elif all_tokens:
                rank = 3
            ranked.append((rank, -score, song["video_id"], idx))

        ranked.sort()
        out: list[dict[str, Any]] = []
        for _, _, _, idx in ranked[:limit]:
            out.append(self._songs[idx])
        return out

    def random(self, limit: int = 10) -> list[dict[str, Any]]:
        if not self._songs:
            return []
        k = min(max(1, int(limit)), len(self._songs), 50)
        return random.sample(self._songs, k)

    def page(self, page: int = 1, limit: int = 50) -> dict[str, Any]:
        page = max(1, int(page))
        limit = max(1, min(int(limit), 100))
        total = len(self._songs)
        total_pages = max(1, (total + limit - 1) // limit) if total else 1
        start = (page - 1) * limit
        results = self._songs[start : start + limit]
        return {
            "page": page,
            "limit": limit,
            "total_songs": total,
            "total_pages": total_pages,
            "results": results,
        }

    def stats(self) -> dict[str, Any]:
        iota = sum(1 for s in self._songs if s.get("source") == "iota_cloud")
        return {
            "total_songs": len(self._songs),
            "iota_cloud_songs": iota,
            "other_songs": len(self._songs) - iota,
        }

    def suggest(self, query: str, limit: int = 8) -> list[str]:
        tokens = tokenize(query or "")
        if not tokens:
            return []
        pref = tokens[-1]
        titles = self._prefix.get(pref, [])
        out: list[str] = []
        for t in titles:
            if t not in out:
                out.append(t)
            if len(out) >= limit:
                break
        return out

    def trending(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._songs[: max(1, min(int(limit), 50))]
