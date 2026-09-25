from main import check_city,check_amount

def test_amount_small_approve():
    assert check_amount({"amount":1000}) == "approve"

def test_amount_exactly_100000_approve():
    assert check_amount({"amount":100000}) == "approve"

def test_amount_small_review():
    assert check_amount({"amount":100001}) == "review"

def test_amount_exactly_review():
    assert check_amount({"amount":500000}) == "review"

def test_amount_block():
    assert check_amount({"amount":500001}) == "block"

def test_city_home_city_approve():
    assert check_city({"client": "Abzal","city": "Astana"}) == "approve"

def test_city_foreign_city_review():
    assert check_city({"client": "Abzal","city": "Oskemen"}) == "review"

def test_city_unknown_client_review():
    assert check_city({"client": "Aday","city": "Astana"}) == "review"

def test_city_unknown_client_without_city_review():
    assert check_city({"client": "Aday","city": None}) == "review"