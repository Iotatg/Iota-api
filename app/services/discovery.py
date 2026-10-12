"""Discovery helpers: lyrics, similar tracks, live search suggestions.

All features lean on free key-less public APIs:

- lyrics:   https://lrclib.net   (crowd-sourced lyrics, time-synced LRC)
            https://lyrics.ovh   (plain-text fallback, different corpus)
- similar:  api.deezer.com       (track similarity, Deezer catalogue)
- suggest:  Google YouTube completion endpoint (key-less autocomplete)

Everything is cached in-process with a modest TTL: these endpoints are
cheap but the upstreams are rate-limited per IP, and identical lookups
are extremely common (bot queues replay the same tracks).
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

_LRCLIB_GET = "https://lrclib.net/api/get"
_LRCLIB_SEARCH = "https://lrclib.net/api/search"
_OVH_BASE = "https://api.lyrics.ovh/v1/"
_GOOGLE_SUGGEST = "https://suggestqueries.google.com/complete/search"
_DEEZER_SEARCH = "https://api.deezer.com/search"
_DEEZER_SIMILAR = "https://api.deezer.com/track/{track_id}/similar"
_DEEZER_API = "https://api.deezer.com"
_DEEZER_CHART = "https://api.deezer.com/chart/0/{kind}"
_ITUNES_SEARCH = "https://itunes.apple.com/search"
_ITUNES_LOOKUP = "https://itunes.apple.com/lookup"
# iTunes rejects the default httpx UA with empty result sets.
_ITUNES_UA = {"User-Agent": "Mozilla/5.0 (iota-api discovery)"}

_HTTP_TIMEOUT = 12.0
_CACHE_TTL = 600.0
_CACHE_MAX = 400
# lrclib matches within this duration window are accepted from search
# results when the exact metadata lookup misses.
_DURATION_SLACK = 15


class DiscoveryNotFoundError(Exception):
    """The track could not be confidently matched upstream."""


class LyricsNotFoundError(DiscoveryNotFoundError):
    """No lyrics could be confidently matched for the track."""


class DiscoveryUnavailableError(Exception):
    """Upstream discovery service (Deezer/lrclib) is failing."""


class DiscoveryClient:
    """Thin async client over lrclib + Deezer with a tiny TTL cache."""

    def __init__(self, http: Optional[httpx.AsyncClient] = None) -> None:
        self._http = http
        self._owns_http = http is None
        self._cache: Dict[str, tuple[float, Any]] = {}

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                timeout=_HTTP_TIMEOUT,
                follow_redirects=True,
                headers={"User-Agent": "iota-api/discovery"},
            )
        return self._http

    async def aclose(self) -> None:
        if self._owns_http and self._http is not None:
            await self._http.aclose()
            self._http = None

    # ── tiny TTL cache ──────────────────────────────────────────────
    def _cache_get(self, key: str) -> Optional[Any]:
        hit = self._cache.get(key)
        if hit is None:
            return None
        stamp, value = hit
        if time.monotonic() - stamp > _CACHE_TTL:
            self._cache.pop(key, None)
            return None
        return value

    def _cache_put(self, key: str, value: Any) -> None:
        if len(self._cache) >= _CACHE_MAX:
            oldest = min(self._cache, key=lambda k: self._cache[k][0])
            self._cache.pop(oldest, None)
        self._cache[key] = (time.monotonic(), value)

    async def _get_json(
        self, url: str, params: Optional[dict] = None, headers: Optional[dict] = None
    ) -> Optional[dict]:
        """GET with tolerant 404 handling and upstream error mapping.

        Deezer-style bodies that answer HTTP 200 with ``{"error": ...}``
        are surfaced as upstream failures instead of empty successes.
        """
        http = await self._get_http()
        try:
            resp = await http.get(url, params=params, headers=headers)
        except httpx.HTTPError as exc:
            raise DiscoveryUnavailableError(f"{url} request failed: {exc}") from exc
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            raise DiscoveryUnavailableError(f"{url} returned HTTP {resp.status_code}")
        try:
            data = resp.json()
        except ValueError as exc:
            raise DiscoveryUnavailableError(f"{url} returned non-JSON body") from exc
        if isinstance(data, dict) and data.get("error"):
            msg = data["error"]
            msg = msg.get("message", str(msg)) if isinstance(msg, dict) else str(msg)
            raise DiscoveryUnavailableError(f"{url} error: {msg}")
        return data

    # ── lyrics ──────────────────────────────────────────────────────
    async def lyrics(
        self,
        title: str,
        artist: Optional[str] = None,
        album: Optional[str] = None,
        duration_seconds: Optional[int] = None,
    ) -> dict:
        """Return ``{synced, plain, title, artist}`` LRC payload.

        Tries the exact lrclib metadata lookup first, then a fuzzy
        search filtered by duration. Raises LyricsNotFoundError when
        confident matching fails on both.
        """
        title = str(title or "").strip()
        artist = str(artist).strip() if artist else None
        if not title:
            raise LyricsNotFoundError("empty title")
        cache_key = f"lyr|{title.lower()}|{(artist or '').lower()}|{duration_seconds}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        params: Dict[str, Any] = {"track_name": title}
        if artist:
            params["artist_name"] = artist
        if album:
            params["album_name"] = album
        if duration_seconds:
            params["duration"] = duration_seconds
        lrclib_down = False
        try:
            data = await self._get_json(_LRCLIB_GET, params)
        except DiscoveryUnavailableError:
            lrclib_down = True
            data = None

        if data is None or not (data.get("syncedLyrics") or data.get("plainLyrics")):
            query = " ".join(x for x in (artist, title) if x)
            try:
                results = await self._get_json(
                    _LRCLIB_SEARCH, {"q": query, "limit": 8}
                )
            except DiscoveryUnavailableError:
                lrclib_down = True
                results = None
            data = None
            for cand in results or []:
                if not (cand.get("syncedLyrics") or cand.get("plainLyrics")):
                    continue
                if duration_seconds and cand.get("duration"):
                    if abs(int(cand["duration"]) - int(duration_seconds)) > _DURATION_SLACK:
                        continue
                data = cand
                break

        if data is None:
            # lrclib missed (or is down) — lyrics.ovh keeps an
            # independent plain-text corpus; consult it before
            # reporting failure.
            ovh = await self._lyrics_ovh(title, artist, cache_key)
            if ovh is not None:
                return ovh
            if lrclib_down:
                raise DiscoveryUnavailableError(
                    f"lyrics upstream failing for {title!r}")
            raise LyricsNotFoundError(f"no lyrics for {title!r}")

        payload = {
            "title": data.get("trackName") or title,
            "artist": data.get("artistName") or artist,
            "synced": data.get("syncedLyrics") or None,
            "plain": data.get("plainLyrics") or None,
            "source": "lrclib",
        }
        self._cache_put(cache_key, payload)
        return payload

    async def _lyrics_ovh(
        self, title: str, artist: Optional[str], cache_key: str
    ) -> Optional[dict]:
        """lyrics.ovh is artist-scoped by path; without an artist name
        there is nothing to query. 404 (no match) maps to ``None`` via
        ``_get_json``; soft-fails here never mask the lrclib outcome."""
        if not artist:
            return None
        ovh_key = f"ovh|{title.lower()}|{artist.lower()}"
        cached = self._cache_get(ovh_key)
        if cached is not None:
            return cached if cached.get("plain") else None
        try:
            data = await self._get_json(f"{_OVH_BASE}{quote(artist)}/{quote(title)}")
        except DiscoveryUnavailableError:
            return None
        text = str((data or {}).get("lyrics") or "").strip()
        if not text:
            return None
        payload = {
            "title": title,
            "artist": artist,
            "synced": None,
            "plain": text,
            "source": "lyrics.ovh",
        }
        self._cache_put(ovh_key, payload)
        self._cache_put(cache_key, payload)
        return payload

    # ── similar tracks ──────────────────────────────────────────────
    async def youtube_suggest(self, query: str, limit: int = 10) -> List[str]:
        """YouTube search autocomplete via Google's public completion
        endpoint (key-less, ``client=firefox`` gives plain JSON). The
        endpoint is occasionally walled from datacenter IPs; the route
        then answers an empty list rather than failing."""
        query = str(query or "").strip()
        if not query:
            return []
        cache_key = f"sgs|{query.lower()}|{limit}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        out: List[str] = []
        try:
            data = await self._get_json(
                _GOOGLE_SUGGEST, {"client": "firefox", "ds": "yt", "q": query}
            )
            if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list):
                out = [str(s).strip() for s in data[1] if str(s).strip()]
        except DiscoveryUnavailableError:
            out = []
        out = out[:limit]
        if out:
            self._cache_put(cache_key, out)
        return out

    async def _similar_itunes(
        self, title: str, artist: Optional[str], limit: int
    ) -> List[dict]:
        """Related tracks via iTunes: rest-of-album first, then the
        artist's other songs. Key-less and reliable, unlike Deezer's
        public similarity endpoint (retired 2025)."""
        term = " ".join(x for x in (artist, title) if x)
        data = await self._get_json(
            _ITUNES_SEARCH,
            {"media": "music", "entity": "song", "term": term,
             "limit": 1, "country": "US"},
            headers=_ITUNES_UA,
        )
        tracks = (data or {}).get("results") or []
        if not tracks:
            return []
        seed = tracks[0]
        seen = {seed.get("trackId")}
        out: List[dict] = []
        album_id = seed.get("collectionId")
        if album_id:
            album = await self._get_json(
                _ITUNES_LOOKUP,
                {"id": album_id, "entity": "song", "limit": limit + 1},
                headers=_ITUNES_UA,
            )
            for item in (album or {}).get("results") or []:
                tid = item.get("trackId")
                if not tid or tid in seen:
                    continue
                seen.add(tid)
                out.append(item)
                if len(out) >= limit:
                    break
        if len(out) < limit and seed.get("artistName"):
            more = await self._get_json(
                _ITUNES_SEARCH,
                {"media": "music", "entity": "song", "attribute": "artistTerm",
                 "term": str(seed["artistName"]), "limit": limit + 2,
                 "country": "US"},
                headers=_ITUNES_UA,
            )
            for item in (more or {}).get("results") or []:
                tid = item.get("trackId")
                if not tid or tid in seen:
                    continue
                seen.add(tid)
                out.append(item)
                if len(out) >= limit:
                    break
        return self._map_itunes_batch(out, limit)

    @staticmethod
    def _map_itunes_batch(items: List[dict], limit: int) -> List[dict]:
        out: List[dict] = []
        for item in items[:limit]:
            millis = item.get("trackTimeMillis")
            art = item.get("artworkUrl100")
            out.append({
                "media_id": f"am:{item['trackId']}",
                "provider": "am",
                "title": item.get("trackName") or "",
                "artist": item.get("artistName"),
                "duration_seconds": int(millis // 1000) if millis else None,
                "thumbnail_url": (
                    art.replace("100x100bb", "300x300bb") if art else None
                ),
            })
        return out

    async def _deezer_track_id(self, title: str, artist: Optional[str]) -> Optional[str]:
        query = " ".join(x for x in (artist, title) if x)
        data = await self._get_json(_DEEZER_SEARCH, {"q": query, "limit": 3})
        for item in (data or {}).get("data") or []:
            if item.get("id"):
                return str(item["id"])
        return None

    async def similar(
        self,
        title: str,
        artist: Optional[str] = None,
        limit: int = 10,
        deezer_id: Optional[str] = None,
    ) -> List[dict]:
        """Return similar tracks (iTunes catalogue, ``am:`` ids;
        Deezer similarity kept as a fallback for Deezer-native ids)."""
        cache_key = f"sim|{deezer_id or title.strip().lower()}|{(artist or '').strip().lower()}|{limit}"
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached

        try:
            results = await self._similar_itunes(title, artist, limit)
            if results:
                self._cache_put(cache_key, results)
                return results
        except DiscoveryUnavailableError:
            if not deezer_id:
                raise

        if deezer_id:
            data = await self._get_json(
                _DEEZER_SIMILAR.format(track_id=deezer_id), {"limit": limit}
            )
            results = []
            for item in (data or {}).get("data") or []:
                results.append({
                    "media_id": f"dz:{item['id']}",
                    "provider": "dz",
                    "title": item.get("title") or item.get("title_short") or "",
                    "artist": ((item.get("artist") or {}).get("name")) or None,
                    "duration_seconds": item.get("duration"),
                    "thumbnail_url": ((item.get("album") or {}).get("cover_medium")) or None,
                })
            if results:
                self._cache_put(cache_key, results)
                return results

        raise DiscoveryNotFoundError(
            f"no similar tracks found for {title!r}"
        )

    # ── suggestions ─────────────────────────────────────────────────
    async def suggest(self, q: str, limit: int = 10) -> List[str]:
        """Top live titles for a prefix (Deezer search). Empty on any
        upstream trouble — suggestions are best-effort by nature."""
        key = f"sg|{q.strip().lower()}|{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        try:
            data = await self._get_json(_DEEZER_SEARCH, {"q": q, "limit": min(limit, 25)})
        except DiscoveryUnavailableError:
            return []
        out: List[str] = []
        seen: set = set()
        for item in (data or {}).get("data") or []:
            title = str(item.get("title") or item.get("title_short") or "").strip()
            if not title:
                continue
            norm = title.lower()
            if norm and norm not in seen:
                seen.add(norm)
                out.append(title)
            if len(out) >= limit:
                break
        self._cache_put(key, out)
        return out

    # ── Deezer catalogue: charts, radios, genres, artists, albums ────
    # Deezer's public JSON API needs no key or auth. It is used only as
    # a metadata catalogue (ids, titles, art); audio still comes from the
    # normal provider path so no Deezer stream urls leak into responses.

    async def _dz_pages(
        self,
        path: str,
        limit: int,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[dict]:
        """Walk Deezer's index/limit pagination until ``limit`` items."""
        out: List[dict] = []
        page = 25
        index = 0
        while len(out) < limit:
            query = dict(params or {})
            query.update({"index": index, "limit": min(page, limit - len(out))})
            data = await self._get_json(f"{_DEEZER_API}{path}", query)
            rows = (data or {}).get("data") if isinstance(data, dict) else None
            if not rows:
                break
            out.extend(rows)
            if len(rows) < query["limit"]:
                break
            index += len(rows)
        return out[:limit]

    async def _dz_first(self, path: str) -> dict:
        try:
            data = await self._get_json(f"{_DEEZER_API}{path}")
        except DiscoveryUnavailableError as e:
            # Deezer answers unknown objects with an in-body error that
            # _get_json surfaces as "unavailable"; for object lookups that
            # really means "no such record", so callers should 404.
            if "no data" in str(e) or "Unknown path" in str(e):
                raise DiscoveryNotFoundError(
                    f"Deezer has no record at {path!r}."
                ) from e
            raise
        if not isinstance(data, dict) or not data.get("id"):
            raise DiscoveryNotFoundError(f"Deezer has no record at {path!r}.")
        return data

    async def charts(self, kind: str, limit: int) -> List[dict]:
        """Current Deezer chart: tracks, albums, artists or playlists."""
        if kind not in _CHART_KINDS:
            raise DiscoveryNotFoundError(
                f"Unknown chart {kind!r}; expected one of {sorted(_CHART_KINDS)}."
            )
        key = f"charts:{kind}:{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        data = await self._get_json(
            _DEEZER_CHART.format(kind=kind), {"limit": limit}
        )
        rows = (data or {}).get("data") if isinstance(data, dict) else None
        if not rows:
            raise DiscoveryUnavailableError("Deezer chart is unavailable.")
        out = [self._chart_row(kind, r) for r in rows]
        self._cache_put(key, out)
        return out

    @staticmethod
    def _chart_row(kind: str, row: dict) -> dict:
        if kind == "artists":
            return {
                "id": f"dzartist:{row.get('id')}",
                "name": str(row.get("name") or ""),
                "picture": row.get("picture_xl") or row.get("picture"),
                "nb_fan": row.get("nb_fan"),
            }
        if kind in ("albums", "playlists"):
            return {
                "id": f"dz{kind[:-1]}:{row.get('id')}",
                "title": str(row.get("title") or ""),
                "art": row.get("cover_xl") or row.get("cover"),
                "artist": (row.get("artist") or {}).get("name"),
                "nb_tracks": (row.get("tracks") or {}).get("nb"),
            }
        return {
            "id": f"dztrack:{row.get('id')}",
            "title": str(row.get("title") or row.get("title_short") or ""),
            "artist": (row.get("artist") or {}).get("name"),
            "album": (row.get("album") or {}).get("title"),
            "duration_seconds": row.get("duration"),
            "art": (row.get("album") or {}).get("cover_xl"),
        }

    async def radios(self, limit: int) -> List[dict]:
        """Deezer's curated station list (unlimited, algorithmic radio)."""
        key = f"radios:{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        rows = await self._dz_pages("/radio", limit)
        out = [
            {
                "id": f"dzradio:{r.get('id')}",
                "title": str(r.get("title") or ""),
                "description": str(r.get("description") or ""),
                "picture": r.get("picture_xl") or r.get("picture"),
            }
            for r in rows
            if r.get("id")
        ]
        if not out:
            raise DiscoveryUnavailableError("Deezer radio list is unavailable.")
        self._cache_put(key, out)
        return out

    async def radio_tracks(self, radio_id: str, limit: int) -> List[dict]:
        """Track seed list for one Deezer station (id accepts dzradio:)."""
        rid = self.strip_id(radio_id)
        key = f"radio_tracks:{rid}:{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        rows = await self._dz_pages(f"/radio/{rid}/tracks", limit)
        if not rows:
            raise DiscoveryNotFoundError(f"No Deezer radio station {rid!r}.")
        out = [self._track_row(r) for r in rows]
        self._cache_put(key, out)
        return out

    async def genres(self) -> List[dict]:
        """Full Deezer genre tree (flat list, stable and tiny)."""
        key = "genres"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        data = await self._get_json(f"{_DEEZER_API}/genre")
        rows = (data or {}).get("data") if isinstance(data, dict) else None
        if not rows:
            raise DiscoveryUnavailableError("Deezer genres are unavailable.")
        out = [
            {
                "id": g.get("id"),
                "name": str(g.get("name") or ""),
                "picture": g.get("picture_big") or g.get("picture"),
            }
            for g in rows
            if g.get("id")
        ]
        self._cache_put(key, out)
        return out

    async def artist(self, value: str, limit: int) -> dict:
        """Artist by Deezer id or name, with discography + top tracks."""
        needle = self.strip_id(value)
        key = f"artist:{needle.lower()}:{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        blob = await self._resolve_artist(needle)
        aid = blob["id"]
        disc = await self._dz_pages(f"/artist/{aid}/albums", limit)
        top = await self._dz_pages(f"/artist/{aid}/top", limit)
        similar = await self._dz_pages(f"/artist/{aid}/related", 6)
        out = {
            "id": f"dzartist:{aid}",
            "name": str(blob.get("name") or ""),
            "picture": blob.get("picture_xl") or blob.get("picture"),
            "nb_fan": blob.get("nb_fan"),
            "nb_album": blob.get("nb_album"),
            "radio": bool(blob.get("radio")),
            "albums": [
                {
                    "id": f"dzalbum:{a.get('id')}",
                    "title": str(a.get("title") or ""),
                    "art": a.get("cover_xl") or a.get("cover"),
                    "release_date": a.get("release_date"),
                    "nb_tracks": (a.get("tracks") or {}).get("nb"),
                }
                for a in disc
                if a.get("id")
            ],
            "top_tracks": [self._track_row(t) for t in top],
            "similar_artists": [
                {
                    "id": f"dzartist:{r.get('id')}",
                    "name": str(r.get("name") or ""),
                    "picture": r.get("picture_xl") or r.get("picture"),
                }
                for r in similar
                if r.get("id")
            ],
        }
        self._cache_put(key, out)
        return out

    async def _resolve_artist(self, needle: str) -> dict:
        if needle.isdigit():
            try:
                return await self._dz_first(f"/artist/{needle}")
            except DiscoveryNotFoundError:
                pass
        rows = await self._dz_pages("/search/artist", 1, {"q": needle})
        if not rows:
            raise DiscoveryNotFoundError(f"No artist matches {needle!r}.")
        return rows[0]

    async def album(self, value: str, limit: int) -> dict:
        """Album by Deezer id or catalogue URL/id, with its tracklist."""
        aid = self.strip_id(value)
        if not aid.isdigit():
            rows = await self._dz_pages("/search/album", 1, {"q": aid})
            if not rows:
                raise DiscoveryNotFoundError(f"No album matches {aid!r}.")
            aid = str(rows[0].get("id"))
        key = f"album:{aid}:{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        blob = await self._dz_first(f"/album/{aid}")
        tracks = await self._dz_pages(f"/album/{aid}/tracks", limit)
        out = {
            "id": f"dzalbum:{aid}",
            "title": str(blob.get("title") or ""),
            "artist": (blob.get("artist") or {}).get("name"),
            "art": blob.get("cover_xl") or blob.get("cover"),
            "release_date": blob.get("release_date"),
            "genre": blob.get("genre"),
            "label": blob.get("label"),
            "nb_tracks": blob.get("nb_tracks"),
            "tracks": [self._track_row(t) for t in tracks],
        }
        self._cache_put(key, out)
        return out

    async def catalog_search(
        self, kind: str, query: str, limit: int
    ) -> List[dict]:
        """Deezer entity search: playlist / album / artist / radio."""
        if kind not in _CATALOG_KINDS:
            raise DiscoveryNotFoundError(
                f"Unknown search kind {kind!r}; expected {sorted(_CATALOG_KINDS)}."
            )
        key = f"cat:{kind}:{query.lower()}:{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        endpoint = _CATALOG_ENDPOINTS[kind]
        rows = await self._dz_pages(f"/search/{endpoint}", limit, {"q": query})
        if kind == "artists":
            out = [self._chart_row("artists", r) for r in rows]
        elif kind == "albums":
            out = [self._chart_row("albums", r) for r in rows]
        elif kind == "playlists":
            out = [self._chart_row("playlists", r) for r in rows]
        else:
            out = [
                {
                    "id": f"dzradio:{r.get('id')}",
                    "title": str(r.get("title") or ""),
                    "picture": r.get("picture_xl") or r.get("picture"),
                }
                for r in rows
                if r.get("id")
            ]
        self._cache_put(key, out)
        return out

    async def playlist_tracks(self, value: str, limit: int) -> dict:
        """Deezer playlist by id (bare, dzplaylist: or deezer URL)."""
        pid = self.playlist_id(value)
        key = f"pl_tracks:{pid}:{limit}"
        cached = self._cache_get(key)
        if cached is not None:
            return cached
        meta = await self._dz_first(f"/playlist/{pid}")
        rows = await self._dz_pages(f"/playlist/{pid}/tracks", limit)
        out = {
            "id": f"dzplaylist:{pid}",
            "title": str(meta.get("title") or ""),
            "description": str(meta.get("description") or ""),
            "art": meta.get("picture_xl") or meta.get("picture"),
            "creator": (meta.get("user") or {}).get("name"),
            "nb_tracks": meta.get("nb_tracks"),
            "tracks": [self._track_row(t) for t in rows if t.get("id")],
        }
        self._cache_put(key, out)
        return out

    @staticmethod
    def _track_row(row: dict) -> dict:
        return {
            "id": f"dztrack:{row.get('id')}",
            "title": str(row.get("title") or row.get("title_short") or ""),
            "artist": (row.get("artist") or {}).get("name"),
            "album": (row.get("album") or {}).get("title"),
            "duration_seconds": row.get("duration"),
            "art": (row.get("album") or {}).get("cover_big")
            or (row.get("album") or {}).get("cover"),
        }

    @staticmethod
    def strip_id(value: str) -> str:
        """Drop a dz/deezer namespace prefix and any URL wrapper."""
        v = str(value).strip()
        for prefix in ("dzradio:", "dzplaylist:", "dzartist:", "dzalbum:", "dztrack:", "dz:"):
            if v.startswith(prefix):
                return v.split(":", 1)[1]
        if "deezer.com" in v:
            v = v.rstrip("/").rsplit("/", 1)[-1]
        return v

    @classmethod
    def playlist_id(cls, value: str) -> str:
        v = cls.strip_id(value)
        for token in ("playlist/", "album/"):
            if token in v:
                v = v.rsplit(token, 1)[-1]
        return v.split("?")[0].strip()


def looks_like_deezer_playlist(value: str) -> bool:
    """True when a playlist path should be resolved through Deezer."""
    v = str(value).strip().lower()
    return v.startswith(("dz:", "dzplaylist:", "deezer:")) or "deezer.com" in v


_CHART_KINDS = frozenset({"tracks", "albums", "artists", "playlists"})
_CATALOG_KINDS = frozenset({"playlists", "albums", "artists", "radios"})
# Deezer's search paths are singular while our public kind names are not.
_CATALOG_ENDPOINTS = {
    "playlists": "playlist",
    "albums": "album",
    "artists": "artist",
    "radios": "radio",
}


def get_shared_client(request) -> "DiscoveryClient":
    """Lazily create one DiscoveryClient per app instance."""
    client = getattr(request.app.state, "discovery_client", None)
    if client is None:
        client = DiscoveryClient()
        request.app.state.discovery_client = client
    return client
