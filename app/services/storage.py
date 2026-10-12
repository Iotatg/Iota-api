"""Storage backend abstraction.

Two backends:

- LocalStorage: stores audio files under STORAGE_LOCAL_PATH. Used in dev
  and tests. The Docker compose setup mounts this as a volume so audio
  persists across restarts.

- S3Storage: stores audio files in an S3-compatible bucket. Used in prod.
  If S3_CDN_BASE_URL is set, `get_redirect_url` returns CDN URLs instead
  of signed S3 URLs (cheaper, lower latency, but loses per-request auth).

Both backends implement:

- exists(key) -> bool
- size(key) -> int
- open_stream(key, start, end) -> AsyncIterator[bytes]
- public_url(key) -> str   (signed URL or local route)
- put(key, data)            (used to seed the demo provider)

CRITICAL: `open_stream` MUST NOT load the full file into memory. It opens
a file handle and yields chunks. The caller (the FastAPI route) wraps it
in a StreamingResponse.
"""
from __future__ import annotations

import abc
import os
from pathlib import Path
from typing import AsyncIterator, Optional

import aiofiles

from app.config import StorageBackend, get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class StorageError(Exception):
    pass


class ObjectNotFoundError(StorageError):
    pass


class StorageService(abc.ABC):
    @abc.abstractmethod
    async def exists(self, key: str) -> bool: ...

    @abc.abstractmethod
    async def size(self, key: str) -> int: ...

    @abc.abstractmethod
    async def open_stream(
        self, key: str, start: int = 0, end: Optional[int] = None
    ) -> AsyncIterator[bytes]: ...

    @abc.abstractmethod
    async def public_url(self, key: str, expires_in: int = 3600) -> str: ...

    @abc.abstractmethod
    async def put(self, key: str, source_path: str) -> None: ...


class LocalStorage(StorageService):
    def __init__(self, base_path: str, public_base_url: str) -> None:
        self.base = Path(base_path).resolve()
        self.base.mkdir(parents=True, exist_ok=True)
        self.public_base_url = public_base_url.rstrip("/")
        logger.info("local_storage_init", extra={"path": str(self.base)})

    def _resolve(self, key: str) -> Path:
        # Defend against path traversal: resolve and ensure it stays under base.
        candidate = (self.base / key).resolve()
        if not str(candidate).startswith(str(self.base)):
            raise StorageError(f"invalid storage key: {key!r}")
        return candidate

    async def exists(self, key: str) -> bool:
        return self._resolve(key).is_file()

    async def size(self, key: str) -> int:
        p = self._resolve(key)
        if not p.is_file():
            raise ObjectNotFoundError(key)
        return p.stat().st_size

    async def open_stream(
        self, key: str, start: int = 0, end: Optional[int] = None
    ) -> AsyncIterator[bytes]:
        p = self._resolve(key)
        if not p.is_file():
            raise ObjectNotFoundError(key)

        settings = get_settings()
        chunk_size = settings.stream_chunk_size
        # Note: end is inclusive (HTTP Range semantics)
        end_inclusive = end if end is not None else p.stat().st_size - 1
        bytes_to_read = end_inclusive - start + 1

        async with aiofiles.open(p, mode="rb") as f:
            await f.seek(start)
            remaining = bytes_to_read
            while remaining > 0:
                buf = await f.read(min(chunk_size, remaining))
                if not buf:
                    break
                remaining -= len(buf)
                yield buf

    async def public_url(self, key: str, expires_in: int = 3600) -> str:
        return f"{self.public_base_url}/storage/{key}"

    async def put(self, key: str, source_path: str) -> None:
        import shutil
        dest = self._resolve(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest)


class S3Storage(StorageService):
    """S3-compatible storage. Used when STORAGE_BACKEND=s3.

    We lazy-import boto3 so the project still starts without boto3 in
    development (it is in requirements.txt but tests can opt out).
    """

    def __init__(
        self,
        bucket: str,
        region: str,
        endpoint: Optional[str],
        access_key: str,
        secret_key: str,
        cdn_base_url: Optional[str] = None,
    ) -> None:
        import boto3
        from botocore.config import Config

        self.bucket = bucket
        self.cdn_base_url = cdn_base_url.rstrip("/") if cdn_base_url else None
        self.client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint or None,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4"),
        )
        logger.info("s3_storage_init", extra={"bucket": bucket, "endpoint": endpoint})

    async def exists(self, key: str) -> bool:
        try:
            await self._run(self.client.head_object, Bucket=self.bucket, Key=key)
            return True
        except _NotFound:
            return False

    async def size(self, key: str) -> int:
        try:
            resp = await self._run(self.client.head_object, Bucket=self.bucket, Key=key)
            return int(resp["ContentLength"])
        except _NotFound as e:
            raise ObjectNotFoundError(key) from e

    async def open_stream(
        self, key: str, start: int = 0, end: Optional[int] = None
    ) -> AsyncIterator[bytes]:
        range_header = f"bytes={start}-{end if end is not None else ''}"
        try:
            resp = await self._run(
                self.client.get_object, Bucket=self.bucket, Key=key, Range=range_header
            )
        except _NotFound as e:
            raise ObjectNotFoundError(key) from e

        body = resp["Body"]
        settings = get_settings()
        chunk_size = settings.stream_chunk_size
        try:
            while True:
                buf = body.read(chunk_size)
                if not buf:
                    break
                yield buf
        finally:
            body.close()

    async def public_url(self, key: str, expires_in: int = 3600) -> str:
        if self.cdn_base_url:
            return f"{self.cdn_base_url}/{key}"
        url = await self._run(
            self.client.generate_presigned_url,
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return url

    async def put(self, key: str, source_path: str) -> None:
        await self._run(
            self.client.upload_file, source_path, self.bucket, key
        )

    @staticmethod
    async def _run(func, *args, **kwargs):
        """Run a sync boto3 call in a thread to keep the event loop unblocked."""
        import asyncio
        return await asyncio.to_thread(func, *args, **kwargs)


class _NotFound(Exception):
    pass


def make_storage() -> StorageService:
    """Factory: build the storage backend configured by env vars."""
    settings = get_settings()
    if settings.storage_backend == StorageBackend.S3:
        if not all([
            settings.s3_bucket,
            settings.s3_access_key,
            settings.s3_secret_key,
        ]):
            raise RuntimeError(
                "S3 storage requires S3_BUCKET, S3_ACCESS_KEY, and S3_SECRET_KEY."
            )
        return S3Storage(
            bucket=settings.s3_bucket,
            region=settings.s3_region,
            endpoint=settings.s3_endpoint,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
            cdn_base_url=settings.s3_cdn_base_url,
        )
    return LocalStorage(
        base_path=settings.storage_local_path,
        public_base_url=settings.app_base_url,
    )
