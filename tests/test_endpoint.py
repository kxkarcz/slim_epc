import pytest

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
