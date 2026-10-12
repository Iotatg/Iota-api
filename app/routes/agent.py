"""Agent discovery files: llms.txt, robots, sitemap."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, Response

router = APIRouter()

LLMS = """# Iota API

> Public songs catalog and IotaDB JSON + object storage.

Catalog (no key):
- GET /api/search?q=&limit=
- GET /api/song/{video_id}
- GET /api/random
- GET /api/file/{video_id}

IotaDB (X-API-Key: iota_live_... or sandbox):
- POST /api/v1/db/{collection}/insert
- POST /api/v1/db/{collection}/find
- POST /api/v1/storage/upload
"""


@router.get("/llms.txt", include_in_schema=False)
async def llms_txt():
    return PlainTextResponse(LLMS)


@router.get("/robots.txt", include_in_schema=False)
async def robots():
    return PlainTextResponse("User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n")


@router.get("/sitemap.xml", include_in_schema=False)
async def sitemap():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>/</loc></url>
  <url><loc>/docs</loc></url>
  <url><loc>/db</loc></url>
  <url><loc>/api/stats</loc></url>
</urlset>
"""
    return Response(content=xml, media_type="application/xml")
