"""Typed HTTP client for the official FPL API."""

from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import get_settings

settings = get_settings()

BASE_URL = settings.fpl_api_base_url

_fpl_retry = retry(
    retry=retry_if_exception_type(
        (httpx.HTTPStatusError, httpx.TimeoutException, OSError),
    ),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)


def _raise_retryable(resp: httpx.Response) -> None:
    """Raise for server errors and 429; let other 4xx fail fast."""
    if resp.status_code == 429 or resp.status_code >= 500:
        resp.raise_for_status()


@_fpl_retry
async def fetch_bootstrap() -> dict[str, Any]:
    """Fetch /bootstrap-static/ — teams, players, gameweeks, game settings."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/bootstrap-static/", timeout=30)
        _raise_retryable(resp)
        resp.raise_for_status()
        return resp.json()


@_fpl_retry
async def fetch_fixtures() -> list[dict[str, Any]]:
    """Fetch /fixtures/ — all fixtures for the season."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/fixtures/", timeout=30)
        _raise_retryable(resp)
        resp.raise_for_status()
        return resp.json()


@_fpl_retry
async def fetch_live_gw(gw: int) -> dict[str, Any]:
    """Fetch /event/{gw}/live/ — live scores for a gameweek."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/event/{gw}/live/", timeout=30)
        _raise_retryable(resp)
        resp.raise_for_status()
        return resp.json()


@_fpl_retry
async def fetch_player_summary(player_id: int) -> dict[str, Any]:
    """Fetch /element-summary/{id}/ — per-player GW history + fixtures."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/element-summary/{player_id}/", timeout=30
        )
        _raise_retryable(resp)
        resp.raise_for_status()
        return resp.json()


@_fpl_retry
async def fetch_manager_info(manager_id: int) -> dict[str, Any]:
    """Fetch /entry/{manager_id}/ — manager profile, rank, points."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/entry/{manager_id}/", timeout=30)
        _raise_retryable(resp)
        resp.raise_for_status()
        return resp.json()


@_fpl_retry
async def fetch_manager_picks(manager_id: int, gw: int) -> dict[str, Any]:
    """Fetch /entry/{manager_id}/event/{gw}/picks/ — squad picks for a GW."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{BASE_URL}/entry/{manager_id}/event/{gw}/picks/",
            timeout=30,
        )
        _raise_retryable(resp)
        resp.raise_for_status()
        return resp.json()
