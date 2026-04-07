"""Integration tests: /gameweeks and /fixtures endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_gameweeks_list(client: AsyncClient) -> None:
    resp = await client.get("/gameweeks")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list) or "data" in body


@pytest.mark.asyncio
async def test_fixtures_list(client: AsyncClient) -> None:
    resp = await client.get("/fixtures")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list) or "data" in body


@pytest.mark.asyncio
async def test_fixtures_filter_by_gw(client: AsyncClient) -> None:
    resp = await client.get("/fixtures?gameweek_id=1")
    assert resp.status_code == 200
