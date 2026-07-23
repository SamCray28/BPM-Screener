import pytest


@pytest.mark.asyncio
async def test_scanner_top_returns_list(client):
    response = await client.get("/scanner/top")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_scanner_ticker_404_when_not_ranked(client):
    response = await client.get("/scanner/ticker/NOPE_NOT_A_SYMBOL")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_research_all_returns_cards(client):
    response = await client.get("/research")
    assert response.status_code == 200
    cards = response.json()
    assert len(cards) > 0
    names = {c["metric_name"] for c in cards}
    assert "Behavioral Opportunity Score" in names


@pytest.mark.asyncio
async def test_research_one_404_for_unknown_metric(client):
    response = await client.get("/research/Not A Real Metric")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_statistics_returns_shape(client):
    response = await client.get("/statistics")
    assert response.status_code == 200
    body = response.json()
    assert "universe_size" in body
