from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data


def test_data_summary():
    response = client.get("/data/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_orders" in data
    assert "total_revenue" in data
    assert "refund_rate" in data
    assert data["total_orders"] > 0


def test_analyze_missing_date():
    response = client.post("/analyze", json={})
    assert response.status_code == 422


def test_results_not_found():
    response = client.get("/results/nonexistent")
    assert response.status_code == 404
