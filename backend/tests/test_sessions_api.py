async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_get_status_no_session(client):
    response = await client.get("/api/v1/sessions/status")
    assert response.status_code == 200
    data = response.json()
    assert data["connected"] is False
    assert data["session"] is None
