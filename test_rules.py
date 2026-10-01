import pytest
from main import check_amount, check_city, check_velocity, add_history, score, r
from datetime import datetime, timedelta

time = datetime.fromisoformat("2026-10-01T10:01:00+05:00")

#Тесты проверки суммы транзакции
def test_amount_small_approve():
    assert check_amount({"amount": 1000}) == "approve"

def test_amount_exactly_100000_approve():
    assert check_amount({"amount": 100000}) == "approve"

def test_amount_just_over_100000_review():
    assert check_amount({"amount": 100001}) == "review"

def test_amount_exactly_500000_review():
    assert check_amount({"amount": 500000}) == "review"

def test_amount_just_over_500000_block():
    assert check_amount({"amount": 500001}) == "block"

#Тесты проверки города
def test_city_home_city_approve():
    assert check_city({"client_id": 1,"city": "Astana"}) == "approve"

def test_city_foreign_city_review():
    assert check_city({"client_id": 1,"city": "Oskemen"}) == "review"

def test_city_unknown_client_review():
    assert check_city({"client_id": 5,"city": "Astana"}) == "review"

def test_city_unknown_client_without_city_review():
    assert check_city({"client_id": 5,"city": None}) == "review"

#Тесты проверки количество транзакций
def test_velocity_no_history_approve(clean_storage):
    assert check_velocity({"client_id": 1,"occurred_at": time}) == "approve"

def test_velocity_two_recent_transactions_approve(clean_storage):
    add_history({"client_id": 1,"occurred_at": time})
    add_history({"client_id": 1,"occurred_at": time + timedelta(minutes=1)})
    assert check_velocity({"client_id": 1,"occurred_at": time + timedelta(minutes=2)}) == "approve"

def test_velocity_three_recent_transactions_review(clean_storage):
    add_history({"client_id": 1,"occurred_at": time})
    add_history({"client_id": 1,"occurred_at": time + timedelta(minutes=1)})
    add_history({"client_id": 1,"occurred_at": time + timedelta(minutes=2)})
    assert check_velocity({"client_id": 1,"occurred_at": time + timedelta(minutes=3)}) == "review"

def test_velocity_more_than_10_approve(clean_storage):
    add_history({"client_id": 1,"occurred_at": time})
    add_history({"client_id": 1,"occurred_at": time + timedelta(minutes=2)})
    add_history({"client_id": 1,"occurred_at": time + timedelta(minutes=3)})
    assert check_velocity({"client_id": 1,"occurred_at": time + timedelta(minutes=11)}) == "approve"

def test_velocity_exactly_10_occurred_at_approve(clean_storage):
    add_history({"client_id": 1,"occurred_at": time})
    add_history({"client_id": 1,"occurred_at": time})
    add_history({"client_id": 1,"occurred_at": time})
    assert check_velocity({"client_id": 1,"occurred_at": time + timedelta(minutes=10)}) == "approve"

def test_velocity_midnight_review(clean_storage):
    midnight_time = datetime.fromisoformat("2026-10-01T23:56:00+05:00")
    add_history({"client_id": 1,"occurred_at": midnight_time})
    add_history({"client_id": 1,"occurred_at": midnight_time + timedelta(minutes=2)})
    add_history({"client_id": 1,"occurred_at": midnight_time + timedelta(minutes=4)})
    assert check_velocity({"client_id": 1,"occurred_at": midnight_time + timedelta(minutes=6)}) == "review"

def test_score_ideal_approve(clean_storage):
    assert score({"client_id": 1,"city": "Astana", "amount": 50000, "occurred_at": time}) == "approve"

def test_score_amount_over_block_limit_foreign_city_block(clean_storage):
    assert score({"client_id": 1,"city": "Pavlodar", "amount": 5000000, "occurred_at": time}) == "block"

def test_score_foreign_city_review(clean_storage):
    assert score({"client_id": 1,"city": "Semey", "amount": 50000, "occurred_at": time}) == "review"