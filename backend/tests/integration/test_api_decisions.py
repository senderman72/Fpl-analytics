"""Integration tests: /decisions endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_buy_candidates(client: AsyncClient) -> None:
    resp = await client.get("/decisions/buys")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert isinstance(body["data"], list)


@pytest.mark.asyncio
async def test_captain_picks(client: AsyncClient) -> None:
    resp = await client.get("/decisions/captains")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_chip_strategy(client: AsyncClient) -> None:
    resp = await client.get("/decisions/chips")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_differentials(client: AsyncClient) -> None:
    resp = await client.get("/decisions/differentials")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_price_changes(client: AsyncClient) -> None:
    resp = await client.get("/decisions/price-changes")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_overnight_changes(client: AsyncClient) -> None:
    resp = await client.get("/decisions/overnight-changes")
    assert resp.status_code == 200
