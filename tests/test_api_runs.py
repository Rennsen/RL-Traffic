from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _base_payload():
    return {
        "district_id": "downtown_core",
        "algorithm": "q_learning",
        "backend": "internal",
        "episodes": 50,
        "steps_per_episode": 60,
        "traffic_pattern": "rush_hour_ns",
        "fixed_cycle": 16,
        "service_rate": 3,
        "emergency_rate": 0.02,
        "learning_rate": 0.12,
        "discount_factor": 0.95,
        "epsilon_start": 1.0,
        "epsilon_min": 0.05,
        "epsilon_decay": 0.992,
        "switch_penalty": 1.1,
        "seed": 42,
    }


def test_run_returns_expected_keys():
    response = client.post("/api/run", json=_base_payload())
    assert response.status_code == 200
    data = response.json()

    assert "run_id" in data
    assert "created_at" in data
    assert "comparison" in data
    assert "training" in data
    assert "time_series" in data

    rl_metrics = data["comparison"]["rl"]
    assert isinstance(rl_metrics["avg_wait"], float)
    assert isinstance(rl_metrics["avg_queue"], float)


def test_run_history_endpoints():
    run_response = client.post("/api/run", json=_base_payload())
    assert run_response.status_code == 200
    run_data = run_response.json()

    list_response = client.get("/api/runs", params={"district_id": "downtown_core", "limit": 1})
    assert list_response.status_code == 200
    runs = list_response.json()["runs"]
    assert runs
    assert runs[0]["run_id"] == run_data["run_id"]

    detail_response = client.get(f"/api/runs/{run_data['run_id']}")
    assert detail_response.status_code == 200
    detail_data = detail_response.json()
    assert detail_data["run_id"] == run_data["run_id"]


def test_alerts_are_computed():
    client.post("/api/run", json=_base_payload())
    response = client.get("/api/alerts")
    assert response.status_code == 200
    alerts = response.json()["alerts"]
    for alert in alerts:
        assert "alert_id" in alert
        assert "district_id" in alert
        assert "severity" in alert


def test_anomalies_endpoint():
    client.post("/api/run", json=_base_payload())
    response = client.get("/api/anomalies")
    assert response.status_code == 200
    anomalies = response.json()["anomalies"]
    for anomaly in anomalies:
        assert "anomaly_id" in anomaly
        assert "district_id" in anomaly
