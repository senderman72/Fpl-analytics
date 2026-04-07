"""Integration tests: /players endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_players_list(client: AsyncClient) -> None:
    resp = await client.get("/players")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert isinstance(body["data"], list)


@pytest.mark.asyncio
async def test_players_list_with_position_filter(
    client: AsyncClient,
) -> None:
    resp = await client.get("/players?position=3")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)


@pytest.mark.asyncio
async def test_players_list_with_search(
    client: AsyncClient,
) -> None:
    resp = await client.get("/players?search=salah")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_player_detail_not_found(
    client: AsyncClient,
) -> None:
    resp = await client.get("/players/999999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_compare_invalid_ids(client: AsyncClient) -> None:
    resp = await client.get("/players/compare?ids=abc")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_compare_too_few_ids(client: AsyncClient) -> None:
    resp = await client.get("/players/compare?ids=1")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_player_ids_list(client: AsyncClient) -> None:
    resp = await client.get("/players/ids")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert isinstance(body["data"], list)
