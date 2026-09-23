BLOCK_LIMIT = 500000
REVIEW_LIMIT = 100000

transactions = [
    {"id": 1, "client": "Abzal", "amount": 50000, "city": "Astana"},
    {"id": 2, "client": "Ansar", "amount": 346000, "city": "Astana"},
    {"id": 3, "client": "Assel", "amount": 79000, "city": "Pavlodar"},
    {"id": 4, "client": "Unknown", "amount": 70000, "city": None},
    {"id": 5, "client": "Abzal", "amount": 700000, "city": "Astana"},
    {"id": 6, "client": "Baurzhan", "amount": 70000, "city": "Oskemen"}
    ]

home_cities = {
    "Abzal" : "Astana",
    "Ansar" : "Astana",
    "Assel" : "Astana",
    "Baurzhan" : "Oskemen"
}

def check_amount(tx: dict) -> str:
    #Если сумма превышает лимит по транзакциям то блокируется
    if tx["amount"] > BLOCK_LIMIT:
        return "block"
    #Если сумма превышает лимит то идет на проверку
    elif tx["amount"] > REVIEW_LIMIT:
        return "review"
    return "approve"

def check_city(tx: dict) -> str:
    home = home_cities.get(tx["client"])
    #Если у транзакции нету города то идет на проверку
    if home is None:
        return "review"

    #Если город проживания и город в котором была сделана транзакция разная то идет на проверку
    if tx["city"] != home:
        return "review"
    
    return "approve"

#Оценка транзакции по итогам двух проверок
def score(tx: dict) -> str:
    results = []
    results.append(check_amount(tx))
    results.append(check_city(tx))
    if "block" in results:
        return "block"
    elif "review" in results:
        return "review"
    else:
        return "approve"

for tx in transactions:
    print(f'Платеж {tx["id"]} ({tx["client"]}, {tx["amount"]}): {score(tx)}')