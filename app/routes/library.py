"""User library API: playlists, favourites, history, queue,
top tracks, ratings, tags and an overview — all scoped to the
authenticated API key (the key acts as the user).

Every endpoint is rate limited like /search. Display fields are
denormalized onto each row so listings never re-call a provider;
the provider is only consulted to fill in missing fields when a
caller adds a bare ``media_id``.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.api_key import require_api_key
from app.config import get_settings
from app.database import get_session
from app.dependencies import get_provider, get_rate_limiter
from app.models.api_key import APIKey
from app.schemas.library import (
    FavouriteCheck,
    FavouriteOut,
    HistoryOut,
    HistoryRecord,
    ImportRequest,
    LibraryOverview,
    PlaylistCreate,
    PlaylistDetail,
    PlaylistOut,
    PlaylistTrackOut,
    PlaylistUpdate,
    QueueOut,
    RatingOut,
    RatingRequest,
    ReorderRequest,
    TagAdd,
    TopTrack,
    TrackAdd,
    TrackTagOut,
)
from app.services.library import LibraryService
from app.services.media_provider import MediaProvider
from app.services.playlist_import import PlaylistImportError
from app.utils.rate_limit import RateLimiter

router = APIRouter()


def _service(
    session: AsyncSession, provider: Optional[MediaProvider] = None
) -> LibraryService:
    settings = get_settings()
    return LibraryService(
        session,
        provider,
        settings.spotify_client_id,
        settings.spotify_client_secret,
    )


async def _check_rate(
    api_key: APIKey, rate_limiter: RateLimiter
) -> None:
    rl = await rate_limiter.check(
        api_key.id, api_key.rate_per_minute, api_key.daily_limit
    )
    if not rl.allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "detail": rl.reason,
                "retry_after_seconds": rl.retry_after_seconds,
                "limit_type": (
                    "per_minute" if rl.remaining_minute == 0 else "daily"
                ),
            },
            headers={"Retry-After": str(rl.retry_after_seconds)},
        )


def _not_found(msg: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"error": "not_found", "detail": msg},
    )


# ── playlists ───────────────────────────────────────────────


@router.post(
    "/api/v1/library/playlists",
    response_model=PlaylistOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_playlist(
    payload: PlaylistCreate,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> PlaylistOut:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    pl = await svc.create_playlist(
        api_key.id, payload.name, payload.description, payload.is_public
    )
    return pl  # type: ignore[return-value]


@router.get("/api/v1/library/playlists", response_model=List[PlaylistOut])
async def list_playlists(
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> List[PlaylistOut]:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    return await svc.list_playlists(api_key.id)  # type: ignore[return-value]


@router.get(
    "/api/v1/library/playlists/{playlist_id}", response_model=PlaylistDetail
)
async def get_playlist(
    playlist_id: int,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> PlaylistDetail:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    pl = await svc.get_playlist(api_key.id, playlist_id)
    if pl is None:
        raise _not_found("playlist not found")
    return pl  # type: ignore[return-value]


@router.patch(
    "/api/v1/library/playlists/{playlist_id}", response_model=PlaylistOut
)
async def update_playlist(
    playlist_id: int,
    payload: PlaylistUpdate,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> PlaylistOut:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    pl = await svc.update_playlist(
        api_key.id,
        playlist_id,
        payload.name,
        payload.description,
        payload.is_public,
    )
    if pl is None:
        raise _not_found("playlist not found")
    return pl  # type: ignore[return-value]


@router.delete("/api/v1/library/playlists/{playlist_id}")
async def delete_playlist(
    playlist_id: int,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> dict:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    if not await svc.delete_playlist(api_key.id, playlist_id):
        raise _not_found("playlist not found")
    return {"ok": True}


@router.post(
    "/api/v1/library/playlists/{playlist_id}/tracks",
    response_model=PlaylistTrackOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_playlist_track(
    playlist_id: int,
    payload: TrackAdd,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    provider: MediaProvider = Depends(get_provider),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> PlaylistTrackOut:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session, provider)
    track = await svc.add_track(
        api_key.id,
        playlist_id,
        payload.media_id,
        payload.title,
        payload.artist,
        payload.duration_seconds,
        payload.thumbnail_url,
    )
    if track is None:
        raise _not_found("playlist not found")
    return track  # type: ignore[return-value]


@router.delete("/api/v1/library/playlists/{playlist_id}/tracks/{track_id}")
async def remove_playlist_track(
    playlist_id: int,
    track_id: int,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> dict:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    if not await svc.remove_track(api_key.id, playlist_id, track_id):
        raise _not_found("track not found in playlist")
    return {"ok": True}


@router.post("/api/v1/library/playlists/{playlist_id}/tracks/reorder")
async def reorder_playlist_tracks(
    playlist_id: int,
    payload: ReorderRequest,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> dict:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    try:
        ok = await svc.reorder_tracks(api_key.id, playlist_id, payload.ids)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_order", "detail": str(e)},
        )
    if not ok:
        raise _not_found("playlist not found")
    return {"ok": True}


# ── playlist import ─────────────────────────────────────────


@router.post(
    "/api/v1/library/import",
    response_model=PlaylistDetail,
    status_code=status.HTTP_201_CREATED,
)
async def import_playlist(
    payload: ImportRequest,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    provider: MediaProvider = Depends(get_provider),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> PlaylistDetail:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session, provider)
    try:
        pl = await svc.import_playlist(api_key.id, payload.url, payload.name)
    except PlaylistImportError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "import_failed", "detail": str(e)},
        )
    detail = await svc.get_playlist(api_key.id, pl.id)
    return detail  # type: ignore[return-value]


# ── favourites ──────────────────────────────────────────────


@router.post(
    "/api/v1/library/favourites",
    response_model=FavouriteOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_favourite(
    payload: TrackAdd,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    provider: MediaProvider = Depends(get_provider),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> FavouriteOut:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session, provider)
    fav = await svc.add_favourite(
        api_key.id,
        payload.media_id,
        payload.title,
        payload.artist,
        payload.duration_seconds,
        payload.thumbnail_url,
    )
    return fav  # type: ignore[return-value]


@router.get("/api/v1/library/favourites", response_model=List[FavouriteOut])
async def list_favourites(
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> List[FavouriteOut]:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    return await svc.list_favourites(api_key.id)  # type: ignore[return-value]


@router.get("/api/v1/library/favourites/check", response_model=FavouriteCheck)
async def check_favourite(
    media_id: str = Query(..., min_length=1, max_length=512),
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> FavouriteCheck:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    is_fav = await svc.is_favourite(api_key.id, media_id)
    return FavouriteCheck(media_id=media_id, is_favourite=is_fav)


@router.delete("/api/v1/library/favourites/{media_id}")
async def remove_favourite(
    media_id: str,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> dict:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    if not await svc.remove_favourite(api_key.id, media_id):
        raise _not_found("favourite not found")
    return {"ok": True}


# ── history ─────────────────────────────────────────────────


@router.post(
    "/api/v1/library/history",
    response_model=HistoryOut,
    status_code=status.HTTP_201_CREATED,
)
async def record_play(
    payload: HistoryRecord,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    provider: MediaProvider = Depends(get_provider),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> HistoryOut:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session, provider)
    entry = await svc.record_play(
        api_key.id,
        payload.media_id,
        payload.title,
        payload.artist,
        payload.duration_seconds,
    )
    return entry  # type: ignore[return-value]


@router.get("/api/v1/library/history", response_model=List[HistoryOut])
async def list_history(
    limit: int = Query(200, ge=1, le=1000),
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> List[HistoryOut]:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    return await svc.list_history(api_key.id, limit)  # type: ignore[return-value]


@router.delete("/api/v1/library/history")
async def clear_history(
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> dict:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    cleared = await svc.clear_history(api_key.id)
    return {"ok": True, "cleared": cleared}


# ── queue ───────────────────────────────────────────────────


@router.post(
    "/api/v1/library/queue",
    response_model=QueueOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_to_queue(
    payload: TrackAdd,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    provider: MediaProvider = Depends(get_provider),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> QueueOut:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session, provider)
    item = await svc.add_to_queue(
        api_key.id,
        payload.media_id,
        payload.title,
        payload.artist,
        payload.duration_seconds,
    )
    return item  # type: ignore[return-value]


@router.get("/api/v1/library/queue", response_model=List[QueueOut])
async def list_queue(
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> List[QueueOut]:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    return await svc.list_queue(api_key.id)  # type: ignore[return-value]


@router.delete("/api/v1/library/queue/{item_id}")
async def remove_from_queue(
    item_id: int,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> dict:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    if not await svc.remove_from_queue(api_key.id, item_id):
        raise _not_found("queue item not found")
    return {"ok": True}


@router.delete("/api/v1/library/queue")
async def clear_queue(
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> dict:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    cleared = await svc.clear_queue(api_key.id)
    return {"ok": True, "cleared": cleared}


@router.post("/api/v1/library/queue/reorder")
async def reorder_queue(
    payload: ReorderRequest,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> dict:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    try:
        await svc.reorder_queue(api_key.id, payload.ids)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_order", "detail": str(e)},
        )
    return {"ok": True}


# ── top tracks ──────────────────────────────────────────────


@router.get("/api/v1/library/top-tracks", response_model=List[TopTrack])
async def top_tracks(
    limit: int = Query(10, ge=1, le=100),
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> List[TopTrack]:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    return await svc.top_tracks(api_key.id, limit)  # type: ignore[return-value]


# ── ratings ─────────────────────────────────────────────────


@router.put(
    "/api/v1/library/ratings/{media_id}", response_model=RatingOut
)
async def rate_track(
    media_id: str,
    payload: RatingRequest,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> RatingOut:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    rating = await svc.rate_track(api_key.id, media_id, payload.rating)
    return rating  # type: ignore[return-value]


@router.get("/api/v1/library/ratings/{media_id}", response_model=RatingOut)
async def get_rating(
    media_id: str,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> RatingOut:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    rating = await svc.get_rating(api_key.id, media_id)
    if rating is None:
        raise _not_found("rating not found")
    return rating  # type: ignore[return-value]


@router.delete("/api/v1/library/ratings/{media_id}")
async def remove_rating(
    media_id: str,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> dict:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    if not await svc.remove_rating(api_key.id, media_id):
        raise _not_found("rating not found")
    return {"ok": True}


# ── tags ────────────────────────────────────────────────────


@router.post(
    "/api/v1/library/tags",
    response_model=TrackTagOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_tag(
    payload: TagAdd,
    media_id: str = Query(..., min_length=1, max_length=512),
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> TrackTagOut:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    tag = await svc.add_tag(api_key.id, media_id, payload.tag)
    return tag  # type: ignore[return-value]


@router.delete("/api/v1/library/tags/{media_id}/{tag}")
async def remove_tag(
    media_id: str,
    tag: str,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> dict:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    if not await svc.remove_tag(api_key.id, media_id, tag):
        raise _not_found("tag not found")
    return {"ok": True}


@router.get("/api/v1/library/media/{media_id}/tags", response_model=List[str])
async def list_media_tags(
    media_id: str,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> List[str]:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    return await svc.list_tags(api_key.id, media_id)


@router.get("/api/v1/library/tags/{tag}", response_model=List[TrackTagOut])
async def tracks_by_tag(
    tag: str,
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> List[TrackTagOut]:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    return await svc.tracks_by_tag(api_key.id, tag)  # type: ignore[return-value]


@router.get("/api/v1/library/tags", response_model=List[str])
async def all_tags(
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> List[str]:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    return await svc.all_tags(api_key.id)


# ── overview ────────────────────────────────────────────────


@router.get("/api/v1/library/overview", response_model=LibraryOverview)
async def library_overview(
    api_key: APIKey = Depends(require_api_key),
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> LibraryOverview:
    await _check_rate(api_key, rate_limiter)
    svc = _service(session)
    counts = await svc.overview(api_key.id)
    return LibraryOverview(**counts)
