"""HTML surfaces for catalog, docs, legal, IotaDB dashboard."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.appsite import app_shell_html
from app.pages import (
    about_html,
    db_dashboard_html,
    docs_html,
    landing_html,
    privacy_html,
    stats_page_html,
    terms_html,
)

router = APIRouter()


@router.get("/", include_in_schema=False)
async def app_home():
    return HTMLResponse(app_shell_html())


@router.get("/dev", include_in_schema=False)
async def landing():
    return HTMLResponse(landing_html())


@router.get("/about", include_in_schema=False)
async def about():
    return HTMLResponse(about_html())


@router.get("/status", include_in_schema=False)
async def status_page():
    return HTMLResponse(stats_page_html())


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
