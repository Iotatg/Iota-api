"""Discovery endpoints: lyrics, similar tracks and catalogue browse.

GET /lyrics/{media_id}          -> LRC payload for any provider's track
GET /similar/{media_id}         -> related tracks (Deezer similarity)
GET /charts /radios /genres     -> Deezer catalogue browse (key required)
GET /artists/{name} /albums/{id}-> artist discography / album tracklist
GET /entity?kind=...            -> playlist/album/artist/radio search
GET /playlists/{id}             -> YouTube PL, or Deezer PL via dz: prefix
GET /transcript/{media_id}      -> YouTube captions (yt-dlp, key required)

Metadata endpoints resolve the track's metadata through the provider
registry first, so provider-neutral ids (yt:, dz:, sp:, am:, ...) all work.

Every route below needs an API key, use ``POST /api/v1/keys/anonymous``
to mint a sandbox key for the public demo.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth.api_key import require_api_key
from app.dependencies import get_provider
from app.models.api_key import APIKey
from app.services.discovery import (
    DiscoveryNotFoundError,
    DiscoveryUnavailableError,
    get_shared_client as _get_client,
    looks_like_deezer_playlist,
)
from app.services.media_provider import (
    MediaNotFoundError,
    MediaProvider,
    ProviderUnavailableError,
)
from app.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/lyrics/{media_id}")
async def get_lyrics(
    media_id: str,
    request: Request,
    provider: MediaProvider = Depends(get_provider),
    api_key: APIKey = Depends(require_api_key),
):
    try:
        meta = await provider.get_info(media_id)
    except MediaNotFoundError:
        raise HTTPException(status_code=404, detail={
            "error": "media_not_found",
            "detail": f"No media with id {media_id!r}.",
        })
    except ProviderUnavailableError as e:
        raise HTTPException(status_code=503, detail={
            "error": "provider_unavailable", "detail": str(e),
        })

    disc = _get_client(request)
    try:
        payload = await disc.lyrics(
            meta.title, meta.artist, None, meta.duration_seconds
        )
    except DiscoveryNotFoundError:
        raise HTTPException(status_code=404, detail={
            "error": "lyrics_not_found",
            "detail": f"No lyrics matched {meta.title!r}.",
        })
    except DiscoveryUnavailableError as e:
        raise HTTPException(status_code=502, detail={
            "error": "lyrics_upstream_error",
            "detail": f"Lyrics sources are unavailable for {meta.title!r}: {e}",
        })
    payload["media_id"] = media_id
    return {"success": True, **payload}


@router.get("/similar/{media_id}")
async def get_similar(
    media_id: str,
    request: Request,
    limit: int = Query(10, ge=1, le=20),
    provider: MediaProvider = Depends(get_provider),
    api_key: APIKey = Depends(require_api_key),
):
    try:
        meta = await provider.get_info(media_id)
    except MediaNotFoundError:
        raise HTTPException(status_code=404, detail={
            "error": "media_not_found",
            "detail": f"No media with id {media_id!r}.",
        })
    except ProviderUnavailableError as e:
        raise HTTPException(status_code=503, detail={
            "error": "provider_unavailable", "detail": str(e),
        })

    disc = _get_client(request)
    deezer_id = meta.media_id.split(":", 1)[1] if meta.provider == "dz" else None
    try:
        results = await disc.similar(
            meta.title, meta.artist, limit=limit, deezer_id=deezer_id
        )
    except DiscoveryNotFoundError:
        raise HTTPException(status_code=404, detail={
            "error": "similar_not_found",
            "detail": f"No similar tracks matched {meta.title!r}.",
        })
    except DiscoveryUnavailableError as e:
        raise HTTPException(status_code=502, detail={
            "error": "similar_upstream_error", "detail": str(e),
        })
    return {
        "success": True,
        "media_id": media_id,
        "title": meta.title,
        "artist": meta.artist,
        "count": len(results),
        "results": results,
    }


def _youtube_provider(provider: MediaProvider):
    """The YouTube provider inside the registry (or the provider itself
    when a bare YouTubeProvider was injected in tests)."""
    providers = getattr(provider, "providers", None)
    if providers is not None:
        return providers.get("yt")
    return provider if getattr(provider, "name", "") == "yt" else None


@router.get("/suggest")
async def suggest(
    request: Request,
    q: str = Query(..., min_length=1, max_length=200, description="Partial query"),
    limit: int = Query(10, ge=1, le=25),
    api_key: APIKey = Depends(require_api_key),
):
    """YouTube search autocomplete (Google's key-less completion
    endpoint). Answers an empty list when the endpoint walled us."""
    disc = _get_client(request)
    suggestions = await disc.youtube_suggest(q, limit=limit)
    return {
        "success": True,
        "query": q,
        "count": len(suggestions),
        "suggestions": suggestions,
    }


@router.get("/trending")
async def trending(
    request: Request,
    limit: int = Query(25, ge=1, le=50),
    provider: MediaProvider = Depends(get_provider),
    api_key: APIKey = Depends(require_api_key),
):
    """YouTube's trending feed via yt-dlp flat extraction. Answers []
    while the feed is unreachable or our IP is bot-blocked."""
    yt = _youtube_provider(provider)
    results = await yt.trending(limit=limit) if yt is not None else []
    return {
        "success": True,
        "count": len(results),
        "results": [
            {
                "media_id": f"yt:{m.media_id}",
                "title": m.title,
                "artist": m.artist,
                "duration_seconds": m.duration_seconds,
                "thumbnail_url": m.thumbnail_url,
                "views": m.views,
            }
            for m in results
        ],
    }


@router.get("/playlists/{playlist_id}")
async def playlist(
    request: Request,
    playlist_id: str,
    limit: int = Query(50, ge=1, le=200),
    provider: MediaProvider = Depends(get_provider),
    api_key: APIKey = Depends(require_api_key),
):
    """Contents of a playlist: YouTube (id/URL) or Deezer (dz:/URL) —
    flat and fast, with per-video view counts on the YouTube side.
    Mixes/Radio ids (RD…) may return few items."""
    pid = playlist_id.strip()
    if looks_like_deezer_playlist(pid):
        disc = _get_client(request)
        try:
            payload = await disc.playlist_tracks(pid, limit=limit)
        except DiscoveryNotFoundError:
            raise HTTPException(status_code=404, detail={
                "error": "playlist_not_found",
                "detail": f"Unknown Deezer playlist {playlist_id!r}.",
            })
        except DiscoveryUnavailableError as e:
            raise HTTPException(status_code=502, detail={
                "error": "playlist_upstream_error", "detail": str(e),
            })
        return {"success": True, "source": "deezer", **payload}
    yt = _youtube_provider(provider)
    if yt is None:
        raise HTTPException(status_code=503, detail={
            "error": "provider_unavailable", "detail": "no youtube provider",
        })
    if "list=" in pid:
        pid = pid.split("list=", 1)[1].split("&", 1)[0]
    try:
        title, entries = await yt.get_playlist(pid, limit=limit)
    except MediaNotFoundError:
        raise HTTPException(status_code=404, detail={
            "error": "playlist_not_found",
            "detail": f"Unknown, empty or private playlist {playlist_id!r}.",
        })
    except ProviderUnavailableError as e:
        raise HTTPException(status_code=503, detail={
            "error": "provider_unavailable", "detail": str(e),
        })
    return {
        "success": True,
        "playlist_id": pid,
        "title": title,
        "count": len(entries),
        "results": [
            {
                "media_id": f"yt:{m.media_id}",
                "title": m.title,
                "artist": m.artist,
                "duration_seconds": m.duration_seconds,
                "thumbnail_url": m.thumbnail_url,
                "views": m.views,
            }
            for m in entries
        ],
    }


def _map_browse_error(exc: Exception, what: str) -> HTTPException:
    if isinstance(exc, DiscoveryNotFoundError):
        return HTTPException(status_code=404, detail={
            "error": f"{what}_not_found", "detail": str(exc),
        })
    return HTTPException(status_code=502, detail={
        "error": f"{what}_upstream_error", "detail": str(exc),
    })


@router.get("/charts")
async def charts(
    request: Request,
    kind: str = Query("tracks", description="tracks|albums|artists|playlists"),
    limit: int = Query(20, ge=1, le=50),
    api_key: APIKey = Depends(require_api_key),
):
    """Live global music chart (Deezer catalogue, key-less upstream)."""
    disc = _get_client(request)
    try:
        rows = await disc.charts(kind, limit=limit)
    except (DiscoveryNotFoundError, DiscoveryUnavailableError) as e:
        raise _map_browse_error(e, "chart")
    return {"success": True, "kind": kind, "count": len(rows), "results": rows}


@router.get("/radios")
async def radios(
    request: Request,
    limit: int = Query(25, ge=1, le=100),
    api_key: APIKey = Depends(require_api_key),
):
    """Curated radio stations; feed one to /radios/{id} for endless tracks."""
    disc = _get_client(request)
    try:
        rows = await disc.radios(limit=limit)
    except (DiscoveryNotFoundError, DiscoveryUnavailableError) as e:
        raise _map_browse_error(e, "radio")
    return {"success": True, "count": len(rows), "results": rows}


@router.get("/radios/{radio_id}")
async def radio_tracks(
    request: Request,
    radio_id: str,
    limit: int = Query(25, ge=1, le=100),
    api_key: APIKey = Depends(require_api_key),
):
    """Seed tracks for a station (dzradio:<id> or bare id) — queue filler
    for autoplay; ids are streamable dz: tracks."""
    disc = _get_client(request)
    try:
        rows = await disc.radio_tracks(radio_id, limit=limit)
    except (DiscoveryNotFoundError, DiscoveryUnavailableError) as e:
        raise _map_browse_error(e, "radio")
    return {"success": True, "radio_id": radio_id,
            "count": len(rows), "results": rows}


@router.get("/genres")
async def genres(
    request: Request,
    api_key: APIKey = Depends(require_api_key),
):
    """The full genre tree; names double as /entity playlists queries."""
    disc = _get_client(request)
    try:
        rows = await disc.genres()
    except (DiscoveryNotFoundError, DiscoveryUnavailableError) as e:
        raise _map_browse_error(e, "genre")
    return {"success": True, "count": len(rows), "results": rows}


@router.get("/artists/{name}")
async def artist(
    request: Request,
    name: str,
    limit: int = Query(10, ge=1, le=50),
    api_key: APIKey = Depends(require_api_key),
):
    """Artist (Deezer id or name): profile, discography, top tracks,
    similar artists."""
    disc = _get_client(request)
    try:
        payload = await disc.artist(name, limit=limit)
    except (DiscoveryNotFoundError, DiscoveryUnavailableError) as e:
        raise _map_browse_error(e, "artist")
    return {"success": True, **payload}


@router.get("/albums/{album_id}")
async def album(
    request: Request,
    album_id: str,
    limit: int = Query(50, ge=1, le=200),
    api_key: APIKey = Depends(require_api_key),
):
    """One album with its full tracklist (Deezer id, dzalbum: or URL)."""
    disc = _get_client(request)
    try:
        payload = await disc.album(album_id, limit=limit)
    except (DiscoveryNotFoundError, DiscoveryUnavailableError) as e:
        raise _map_browse_error(e, "album")
    return {"success": True, **payload}


@router.get("/entity")
async def entity_search(
    request: Request,
    kind: str = Query(..., description="playlists|albums|artists|radios"),
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(10, ge=1, le=50),
    api_key: APIKey = Depends(require_api_key),
):
    """Catalog search beyond tracks: mood playlists, albums, artists,
    stations (Deezer corpus)."""
    disc = _get_client(request)
    try:
        rows = await disc.catalog_search(kind, q, limit=limit)
    except (DiscoveryNotFoundError, DiscoveryUnavailableError) as e:
        raise _map_browse_error(e, "search")
    return {"success": True, "kind": kind, "query": q,
            "count": len(rows), "results": rows}


@router.get("/transcript/{media_id}")
async def transcript(
    request: Request,
    media_id: str,
    lang: str = Query("en", description="Subtitle language code"),
    provider: MediaProvider = Depends(get_provider),
    api_key: APIKey = Depends(require_api_key),
):
    """Captions (explicit preferred, auto-generated fallback) for a
    YouTube video as timed segments + plain text. Key-less."""
    yt = _youtube_provider(provider)
    if yt is None:
        raise HTTPException(status_code=503, detail={
            "error": "provider_unavailable", "detail": "no youtube provider",
        })
    try:
        payload = await yt.get_transcript(media_id, language=lang)
    except MediaNotFoundError:
        raise HTTPException(status_code=404, detail={
            "error": "transcript_not_found",
            "detail": f"No {lang!r} captions for {media_id!r}.",
        })
    except ProviderUnavailableError as e:
        raise HTTPException(status_code=503, detail={
            "error": "transcript_unavailable", "detail": str(e),
        })
    return {"success": True, **payload}
