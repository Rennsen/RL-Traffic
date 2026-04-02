import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_local_register_and_login():
    email = f"user-{uuid.uuid4()}@example.com"
    payload = {"email": email, "password": "secret123", "name": "Local User"}

    register = client.post("/api/auth/register", json=payload)
    assert register.status_code == 200

    login = client.post("/api/auth/login_local", json=payload)
    assert login.status_code == 200

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == email
