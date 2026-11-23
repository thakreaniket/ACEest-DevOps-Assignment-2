# test_app.py
import os
import tempfile
import pytest
from ACEest_Fitness import app, init_db


@pytest.fixture
def client():
    # Create a temporary test database so we don't mess up real data
    db_fd, temp_db_path = tempfile.mkstemp(suffix=".db")
    app.config["TESTING"] = True
    app.config["DB_NAME"] = temp_db_path

    init_db(temp_db_path)

    with app.test_client() as test_client:
        yield test_client

    os.close(db_fd)
    os.unlink(temp_db_path)


def test_health_endpoint(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"


def test_login_valid_and_invalid(client):
    # Valid default admin credentials
    res_ok = client.post("/login", json={"username": "admin", "password": "admin"})
    assert res_ok.status_code == 200
    assert res_ok.get_json()["role"] == "Admin"

    # Invalid credentials
    res_bad = client.post("/login", json={"username": "admin", "password": "wrong"})
    assert res_bad.status_code == 401


def test_add_and_list_clients(client):
    res_add = client.post("/clients", json={"name": "Aarav", "age": 28, "weight": 75.5})
    assert res_add.status_code == 201

    res_list = client.get("/clients")
    assert res_list.status_code == 200
    clients = res_list.get_json()
    assert len(clients) == 1
    assert clients[0]["name"] == "Aarav"
    assert clients[0]["membership_status"] == "Active"


def test_generate_ai_program(client):
    client.post("/clients", json={"name": "Priya"})
    res = client.post("/clients/Priya/generate-program", json={})
    assert res.status_code == 200
    data = res.get_json()
    assert data["client"] == "Priya"
    assert data["program"] is not None


def test_add_and_get_workouts(client):
    client.post("/clients", json={"name": "Rohan"})
    res_post = client.post(
        "/clients/Rohan/workouts",
        json={"workout_type": "Strength", "duration_min": 45, "notes": "Bench press"},
    )
    assert res_post.status_code == 201

    res_get = client.get("/clients/Rohan/workouts")
    assert res_get.status_code == 200
    workouts = res_get.get_json()
    assert len(workouts) == 1
    assert workouts[0]["workout_type"] == "Strength"


def test_check_membership(client):
    client.post("/clients", json={"name": "Sneha"})
    res = client.get("/clients/Sneha/membership")
    assert res.status_code == 200
    assert res.get_json()["membership_status"] == "Active"