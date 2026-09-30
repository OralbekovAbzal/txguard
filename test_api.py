from fastapi.testclient import TestClient
from api import app
from main import BLOCK_LIMIT

client = TestClient(app)
tx_test = {"id": 1, "client_id": 1, "amount": 50000, "city": "Astana", "minute": 600}

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_settings():
    response = client.get("/settings")
    assert response.status_code == 200
    assert response.json()["block_limit"] == BLOCK_LIMIT

def test_score_normal_tx_approve(clean_storage):
    response = client.post("/transactions/score",json=tx_test)
    assert response.status_code == 200
    assert response.json() == {'decision': 'approve'}

def test_score_negative_amount_reject(clean_storage):
    tx_negative_amount = dict(tx_test)
    tx_negative_amount["amount"] = -500000
    response = client.post("/transactions/score",json=tx_negative_amount)
    assert response.status_code == 422

def test_score_client_id_zero_reject(clean_storage):
    tx_zero_client = dict(tx_test)
    tx_zero_client["client_id"] = 0
    response = client.post("/transactions/score",json=tx_zero_client)
    assert response.status_code == 422

def test_score_without_client_reject(clean_storage):
    tx_without_client = dict(tx_test)
    tx_without_client.pop("client_id")
    response = client.post("/transactions/score",json=tx_without_client)
    assert response.status_code == 422

def test_score_empty_city_review(clean_storage):
    tx_empty_city = dict(tx_test)
    tx_empty_city["city"] = None
    response = client.post("/transactions/score",json=tx_empty_city)
    assert response.status_code == 200
    assert response.json() == {"decision": "review"}

def test_score_four_same_transactions_review(clean_storage):
    for _ in range(3):
        response = client.post("/transactions/score",json=tx_test)
        assert response.status_code == 200
        assert response.json() == {"decision": "approve"}
    response = client.post("/transactions/score",json=tx_test)
    assert response.status_code == 200
    assert response.json() == {"decision": "review"}