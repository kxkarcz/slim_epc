from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import epc.api as api
from epc.models import BearerConfig, UEState
from main import app

# --- FakeRepo ---

@pytest.fixture
def fake_repo():
    ues = {}

    def list_ues():
        return iter(sorted(ues))

    def ue_exists(ue_id):
        return ue_id in ues

    def get_ue(ue_id):
        if not ue_exists(ue_id):
            raise ValueError("UE not found")
        return ues[ue_id].model_copy(deep=True)

    def save_ue(state):
        ues[state.ue_id] = state.model_copy(deep=True)

    def attach_ue(ue_id):
        if ue_exists(ue_id):
            raise ValueError("UE already attached")
        state = UEState(ue_id=ue_id)
        state.bearers[9] = BearerConfig(bearer_id=9)
        save_ue(state)

    def detach_ue(ue_id):
        if not ue_exists(ue_id):
            raise ValueError("UE not found")
        del ues[ue_id]

    def add_bearer(ue_id, bearer_id):
        state = get_ue(ue_id)
        if bearer_id in state.bearers:
            raise ValueError("Bearer already exists")
        state.bearers[bearer_id] = BearerConfig(bearer_id=bearer_id)
        save_ue(state)

    def update_bearer(ue_id, bearer):
        state = get_ue(ue_id)
        state.bearers[bearer.bearer_id] = bearer
        save_ue(state)

    def update_stats(ue_id, stats):
        state = get_ue(ue_id)
        state.stats[stats.bearer_id] = stats
        save_ue(state)

    def reset_all():
        ues.clear()

    def delete_bearer(ue_id, bearer_id):
        if bearer_id == 9:
            raise ValueError("Cannot remove default bearer")
        state = get_ue(ue_id)
        if bearer_id not in state.bearers:
            raise ValueError("Bearer not found")
        state.bearers.pop(bearer_id)
        state.stats.pop(bearer_id, None)
        save_ue(state)

    return SimpleNamespace(
        list_ues=list_ues,
        ue_exists=ue_exists,
        get_ue=get_ue,
        save_ue=save_ue,
        attach_ue=attach_ue,
        detach_ue=detach_ue,
        add_bearer=add_bearer,
        update_bearer=update_bearer,
        update_stats=update_stats,
        reset_all=reset_all,
        delete_bearer=delete_bearer,
    )

# --- FakeTraffic ---

@pytest.fixture
def fake_traffic_manager():
    running = set()

    def start(ue_id, bearer):
        key = (ue_id, bearer.bearer_id)
        if key in running:
            raise ValueError("Traffic already running")
        if not bearer.target_bps or not bearer.protocol:
            raise ValueError("Bearer not configured for traffic")
        running.add(key)

    def stop(ue_id, bearer_id):
        running.discard((ue_id, bearer_id))

    def stop_all():
        running.clear()

    def is_running(ue_id, bearer_id):
        return (ue_id, bearer_id) in running

    return SimpleNamespace(
        start=start,
        stop=stop,
        stop_all=stop_all,
        is_running=is_running,
    )

# --- Client ---

@pytest.fixture
def client(fake_repo, fake_traffic_manager, monkeypatch):
    app.dependency_overrides[api.get_repo] = lambda: fake_repo
    monkeypatch.setattr(api, "get_traffic_manager", lambda repo: fake_traffic_manager)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

# --- Endpoint tests ---

def test_root(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "EPC Simulator running"}


def test_attach_ue(client):
    response = client.post("/ues", json={"ue_id": 1})

    assert response.status_code == 200
    assert response.json() == {"status": "attached", "ue_id": 1}


def test_list_ues(client):
    client.post("/ues", json={"ue_id": 5})
    client.post("/ues", json={"ue_id": 2})

    response = client.get("/ues")

    assert response.status_code == 200
    assert response.json() == {"ues": [2, 5]}


def test_get_ue(client):
    client.post("/ues", json={"ue_id": 1})

    response = client.get("/ues/1")
    body = response.json()

    assert response.status_code == 200
    assert body["ue_id"] == 1
    assert body["bearers"]["9"]["bearer_id"] == 9


def test_detach_ue(client):
    client.post("/ues", json={"ue_id": 1})

    response = client.delete("/ues/1")

    assert response.status_code == 200
    assert response.json() == {"status": "detached", "ue_id": 1}
    assert client.get("/ues").json() == {"ues": []}


@pytest.mark.parametrize("ue_id", [0, 101])
def test_attach_invalid_ue(client, ue_id):
    response = client.post("/ues", json={"ue_id": ue_id})

    assert response.status_code == 422


def test_attach_same_ue_twice(client):
    client.post("/ues", json={"ue_id": 5})

    response = client.post("/ues", json={"ue_id": 5})

    assert response.status_code == 400
    assert response.json()["detail"] == "UE already attached"


def test_add_bearer(client):
    client.post("/ues", json={"ue_id": 1})

    response = client.post("/ues/1/bearers", json={"bearer_id": 2})

    assert response.status_code == 200
    assert response.json() == {"status": "bearer_added", "ue_id": 1, "bearer_id": 2}
    assert "2" in client.get("/ues/1").json()["bearers"]


def test_delete_bearer(client):
    client.post("/ues", json={"ue_id": 1})
    client.post("/ues/1/bearers", json={"bearer_id": 2})

    response = client.delete("/ues/1/bearers/2")

    assert response.status_code == 200
    assert response.json() == {"status": "bearer_deleted", "ue_id": 1, "bearer_id": 2}


def test_delete_default_bearer(client):
    client.post("/ues", json={"ue_id": 1})

    response = client.delete("/ues/1/bearers/9")

    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot remove default bearer"


def test_add_bearer_missing_ue(client):
    response = client.post("/ues/99/bearers", json={"bearer_id": 2})

    assert response.status_code == 400
    assert response.json()["detail"] == "UE not found"


def test_delete_missing_bearer(client):
    client.post("/ues", json={"ue_id": 1})

    response = client.delete("/ues/1/bearers/2")

    assert response.status_code == 400
    assert response.json()["detail"] == "Bearer not found"


def test_start_traffic(client, fake_traffic_manager):
    client.post("/ues", json={"ue_id": 1})

    response = client.post(
        "/ues/1/bearers/9/traffic",
        json={"protocol": "tcp", "kbps": 12.5},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "traffic_started",
        "ue_id": 1,
        "bearer_id": 9,
        "target_bps": 12500,
    }
    assert fake_traffic_manager.is_running(1, 9)


def test_get_traffic_stats(client):
    client.post("/ues", json={"ue_id": 1})
    client.post("/ues/1/bearers/9/traffic", json={"protocol": "tcp", "kbps": 12.5})

    response = client.get("/ues/1/bearers/9/traffic")
    body = response.json()

    assert response.status_code == 200
    assert body["ue_id"] == 1
    assert body["bearer_id"] == 9
    assert body["protocol"] == "tcp"
    assert body["target_bps"] == 12500
    assert body["tx_bps"] >= 0
    assert body["rx_bps"] >= 0
    assert body["duration"] >= 0


def test_stop_traffic(client, fake_traffic_manager):
    client.post("/ues", json={"ue_id": 1})
    client.post("/ues/1/bearers/9/traffic", json={"protocol": "tcp", "bps": 1000})

    response = client.delete("/ues/1/bearers/9/traffic")

    assert response.status_code == 200
    assert response.json() == {"status": "traffic_stopped", "ue_id": 1, "bearer_id": 9}
    assert fake_traffic_manager.is_running(1, 9) is False
    assert client.get("/ues/1").json()["bearers"]["9"]["active"] is False


def test_start_traffic_without_speed(client):
    client.post("/ues", json={"ue_id": 1})

    response = client.post("/ues/1/bearers/9/traffic", json={"protocol": "udp"})

    assert response.status_code == 422


def test_start_traffic_with_too_many_speeds(client):
    client.post("/ues", json={"ue_id": 1})

    response = client.post(
        "/ues/1/bearers/9/traffic",
        json={"protocol": "udp", "Mbps": 1, "kbps": 1},
    )

    assert response.status_code == 422


def test_start_traffic_missing_bearer(client):
    client.post("/ues", json={"ue_id": 1})

    response = client.post(
        "/ues/1/bearers/2/traffic",
        json={"protocol": "udp", "bps": 1000},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Bearer not found"


def test_all_stats(client):
    client.post("/ues", json={"ue_id": 1})
    client.post("/ues", json={"ue_id": 2})

    response = client.get("/ues/stats", params={"include_details": True})

    assert response.status_code == 200
    assert response.json() == {
        "scope": "all",
        "ue_count": 2,
        "bearer_count": 0,
        "total_tx_bps": 0,
        "total_rx_bps": 0,
        "details": {},
    }


def test_stats_for_one_ue(client):
    client.post("/ues", json={"ue_id": 2})
    client.post("/ues/2/bearers", json={"bearer_id": 3})
    client.post("/ues/2/bearers/3/traffic", json={"protocol": "udp", "bps": 1000})
    client.delete("/ues/2/bearers/3/traffic")

    response = client.get("/ues/stats", params={"ue_id": 2})
    body = response.json()

    assert response.status_code == 200
    assert body["scope"] == "ue:2"
    assert body["ue_count"] == 1
    assert body["bearer_count"] == 1
    assert body["total_tx_bps"] >= 0
    assert body["total_rx_bps"] >= 0
    assert body["details"] is None


def test_stats_missing_ue(client):
    response = client.get("/ues/stats", params={"ue_id": 99})

    assert response.status_code == 400
    assert response.json()["detail"] == "UE not found"


def test_reset(client, fake_traffic_manager):
    client.post("/ues", json={"ue_id": 1})
    client.post("/ues/1/bearers/9/traffic", json={"protocol": "tcp", "bps": 1000})
    assert fake_traffic_manager.is_running(1, 9)

    response = client.post("/reset")

    assert response.status_code == 200
    assert response.json() == {"status": "reset"}
    assert client.get("/ues").json() == {"ues": []}
    assert fake_traffic_manager.is_running(1, 9) is False
