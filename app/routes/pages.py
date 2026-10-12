"""HTML surfaces for catalog, docs, legal, IotaDB dashboard."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.pages import db_dashboard_html, docs_html, landing_html, privacy_html, terms_html

router = APIRouter()


@router.get("/", include_in_schema=False)
async def landing():
    return HTMLResponse(landing_html())


@router.get("/docs", include_in_schema=False)
async def custom_docs():
    return HTMLResponse(docs_html())


@router.get("/privacy", include_in_schema=False)
async def privacy():
    return HTMLResponse(privacy_html())


@router.get("/terms", include_in_schema=False)
async def terms():
    return HTMLResponse(terms_html())


@router.get("/db", include_in_schema=False)
async def db_home():
    return HTMLResponse(db_dashboard_html())
