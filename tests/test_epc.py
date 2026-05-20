import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_up():
    client.post("/reset")
    yield
    client.post("/reset")



def test_add_ue():
    response = client.post("/ues", json={"ue_id": 1})
    assert response.status_code == 200

def test_invalid_ue_id():
    response = client.post("/ues", json={"ue_id": 0})
    assert response.status_code == 422
    response = client.post("/ues", json={"ue_id": 101})
    assert response.status_code == 422


