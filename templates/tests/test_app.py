def test_index_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Hyperlocal Hub" in response.data

def test_api_alerts(client, test_db):
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.get_json()
    assert "results" in data
