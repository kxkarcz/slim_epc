import pytest


def test_list_ues_initially_empty(client):
    response = client.get("/ues")

    assert response.status_code == 200
    assert response.json() == {"ues": []}


def test_get_missing_ue(client):
    response = client.get("/ues/99")

    assert response.status_code == 400
    assert response.json()["detail"] == "UE not found"


def test_detach_missing_ue(client):
    response = client.delete("/ues/99")

    assert response.status_code == 400
    assert response.json()["detail"] == "UE not found"


def test_add_duplicate_bearer(client):
    client.post("/ues", json={"ue_id": 1})
    client.post("/ues/1/bearers", json={"bearer_id": 2})

    response = client.post("/ues/1/bearers", json={"bearer_id": 2})

    assert response.status_code == 400
    assert response.json()["detail"] == "Bearer already exists"


@pytest.mark.parametrize("bearer_id", [0, 10])
def test_add_invalid_bearer_id(client, bearer_id):
    client.post("/ues", json={"ue_id": 1})

    response = client.post("/ues/1/bearers", json={"bearer_id": bearer_id})

    assert response.status_code == 422


def test_start_traffic_missing_ue(client):
    response = client.post(
        "/ues/99/bearers/9/traffic",
        json={"protocol": "tcp", "bps": 1000},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "UE not found"


def test_start_traffic_twice_returns_400(client):
    client.post("/ues", json={"ue_id": 1})
    client.post("/ues/1/bearers/9/traffic", json={"protocol": "tcp", "bps": 1000})

    response = client.post(
        "/ues/1/bearers/9/traffic",
        json={"protocol": "tcp", "bps": 1000},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Traffic already running"


def test_stop_traffic_missing_ue(client):
    response = client.delete("/ues/99/bearers/9/traffic")

    assert response.status_code == 400
    assert response.json()["detail"] == "UE not found"


def test_stop_traffic_missing_bearer(client):
    client.post("/ues", json={"ue_id": 1})

    response = client.delete("/ues/1/bearers/2/traffic")

    assert response.status_code == 400
    assert response.json()["detail"] == "Bearer not found"


def test_start_traffic_bps_response_shape_and_state(client, fake_traffic_manager):
    client.post("/ues", json={"ue_id": 1})

    response = client.post(
        "/ues/1/bearers/9/traffic",
        json={"protocol": "udp", "bps": 1234},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "traffic_started",
        "ue_id": 1,
        "bearer_id": 9,
        "target_bps": 1234,
    }
    assert fake_traffic_manager.is_running(1, 9)

    bearer = client.get("/ues/1").json()["bearers"]["9"]
    assert bearer["active"] is True
    assert bearer["protocol"] == "udp"
    assert bearer["target_bps"] == 1234


def test_delete_bearer_stops_running_traffic(client, fake_traffic_manager):
    client.post("/ues", json={"ue_id": 1})
    client.post("/ues/1/bearers", json={"bearer_id": 2})
    client.post("/ues/1/bearers/2/traffic", json={"protocol": "udp", "bps": 1000})
    assert fake_traffic_manager.is_running(1, 2)

    response = client.delete("/ues/1/bearers/2")

    assert response.status_code == 200
    assert response.json() == {"status": "bearer_deleted", "ue_id": 1, "bearer_id": 2}
    assert fake_traffic_manager.is_running(1, 2) is False
    assert "2" not in client.get("/ues/1").json()["bearers"]


def test_get_traffic_stats_before_traffic(client):
    client.post("/ues", json={"ue_id": 1})

    response = client.get("/ues/1/bearers/9/traffic")

    assert response.status_code == 200
    assert response.json() == {
        "ue_id": 1,
        "bearer_id": 9,
        "protocol": None,
        "target_bps": None,
        "tx_bps": 0,
        "rx_bps": 0,
        "duration": 0,
    }


def test_reset_clears_multiple_ues_and_stops_multiple_traffic_flows(
    client,
    fake_traffic_manager,
):
    client.post("/ues", json={"ue_id": 1})
    client.post("/ues", json={"ue_id": 2})
    client.post("/ues/1/bearers", json={"bearer_id": 2})
    client.post("/ues/1/bearers/2/traffic", json={"protocol": "udp", "bps": 1000})
    client.post("/ues/2/bearers/9/traffic", json={"protocol": "tcp", "bps": 2000})
    assert fake_traffic_manager.is_running(1, 2)
    assert fake_traffic_manager.is_running(2, 9)

    response = client.post("/reset")

    assert response.status_code == 200
    assert response.json() == {"status": "reset"}
    assert client.get("/ues").json() == {"ues": []}
    assert fake_traffic_manager.is_running(1, 2) is False
    assert fake_traffic_manager.is_running(2, 9) is False


def test_stats_for_empty_single_ue(client):
    client.post("/ues", json={"ue_id": 1})

    response = client.get("/ues/stats", params={"ue_id": 1})

    assert response.status_code == 200
    assert response.json() == {
        "scope": "ue:1",
        "ue_count": 1,
        "bearer_count": 0,
        "total_tx_bps": 0,
        "total_rx_bps": 0,
        "details": None,
    }
