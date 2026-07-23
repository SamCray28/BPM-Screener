import pytest


@pytest.mark.asyncio
async def test_accepts_valid_payload(client, valid_payload):
    response = await client.post("/webhook/telemetry", json=valid_payload)
    assert response.status_code == 201
    assert response.json()["status"] == "accepted"


@pytest.mark.asyncio
async def test_rejects_wrong_webhook_secret(client, valid_payload):
    payload = {**valid_payload, "event_id": "TEST:EVENT:SEC-1", "webhook_secret": "wrong"}
    response = await client.post("/webhook/telemetry", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_duplicate_event_id_is_idempotent(client, valid_payload):
    payload = {**valid_payload, "event_id": "TEST:EVENT:DUP-1"}
    first = await client.post("/webhook/telemetry", json=payload)
    assert first.status_code == 201
    second = await client.post("/webhook/telemetry", json=payload)
    assert second.status_code == 200
    assert second.json()["status"] == "duplicate"


@pytest.mark.asyncio
async def test_rejects_bar_close_before_open(client, valid_payload):
    payload = {**valid_payload, "event_id": "TEST:EVENT:BAD-TIME", "bar_open_time": 5000, "bar_close_time": 1000}
    response = await client.post("/webhook/telemetry", json=payload)
    assert response.status_code == 422
