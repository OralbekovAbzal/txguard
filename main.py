BLOCK_LIMIT = 500000
REVIEW_LIMIT = 100000

transactions = [
    {"id": 1, "client": "Abzal", "amount": 50000, "city": "Astana"},
    {"id": 2, "client": "Ansar", "amount": 346000, "city": "Astana"},
    {"id": 3, "client": "Assel", "amount": 79000, "city": "Pavlodar"},
    {"id": 4, "client": "Baurzhan", "amount": 70000, "city": "Oskemen"},
    {"id": 5, "client": "Abzal", "amount": 700000, "city": "Astana"}
    ]

def check_amount(tr: dict) -> str:
    if tr["amount"] > BLOCK_LIMIT:
        return "block"
    elif tr["amount"] > REVIEW_LIMIT:
        return "review"
    return "approve"

for t in transactions:
    print(f'Платеж {t["id"]} ({t["client"]}, {t["amount"]}): {check_amount(t)}')