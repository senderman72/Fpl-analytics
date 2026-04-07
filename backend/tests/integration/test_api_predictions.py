"""Integration tests: /predictions endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_predictions_upcoming(client: AsyncClient) -> None:
    resp = await client.get("/predictions/upcoming")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body


@pytest.mark.asyncio
async def test_predictions_accuracy(client: AsyncClient) -> None:
    resp = await client.get("/predictions/accuracy")
    assert resp.status_code == 200
