BLOCK_LIMIT = 500000
REVIEW_LIMIT = 100000

transactions = [
    # --- Обычные проверки: сумма и город ---
    {"id": 1, "client": "Abzal", "amount": 50000, "city": "Astana", "minute": 600},        # approve: всё нормально
    {"id": 2, "client": "Ansar", "amount": 346000, "city": "Astana", "minute": 601},       # review: сумма > 100 000
    {"id": 3, "client": "Assel", "amount": 79000, "city": "Pavlodar", "minute": 603},      # review: не свой город
    {"id": 4, "client": "Unknown", "amount": 70000, "city": None, "minute": 605},          # review: незнакомец без города
    {"id": 5, "client": "Abzal", "amount": 700000, "city": "Astana", "minute": 606},       # block: сумма > 500 000
    {"id": 6, "client": "Baurzhan", "amount": 70000, "city": "Oskemen", "minute": 610},    # approve: свой город
    {"id": 7, "client": "Kto-to", "amount": 20000, "city": "Almaty", "minute": 612},       # review: незнакомый клиент

    # --- Velocity: Baurzhan делает серию мелких платежей подряд ---
    {"id": 8, "client": "Baurzhan", "amount": 5000, "city": "Oskemen", "minute": 640},     # approve: за 10 мин 0 прошлых
    {"id": 9, "client": "Baurzhan", "amount": 5000, "city": "Oskemen", "minute": 641},     # approve: 1 прошлый
    {"id": 10, "client": "Baurzhan", "amount": 5000, "city": "Oskemen", "minute": 642},    # approve: 2 прошлых
    {"id": 11, "client": "Baurzhan", "amount": 5000, "city": "Oskemen", "minute": 643},    # review: 3 прошлых
    {"id": 12, "client": "Baurzhan", "amount": 5000, "city": "Oskemen", "minute": 645},    # review: 4 прошлых
    {"id": 13, "client": "Baurzhan", "amount": 5000, "city": "Oskemen", "minute": 710},    # approve: прошёл час, всё "остыло"

    # --- Velocity: граница "10 минут" ---
    {"id": 14, "client": "Ansar", "amount": 20000, "city": "Astana", "minute": 700},       # approve
    {"id": 15, "client": "Ansar", "amount": 20000, "city": "Astana", "minute": 705},       # approve: 1 прошлый
    {"id": 16, "client": "Ansar", "amount": 20000, "city": "Astana", "minute": 709},       # approve: 2 прошлых
    {"id": 17, "client": "Ansar", "amount": 20000, "city": "Astana", "minute": 710},       # approve: платёж в 700 ровно 10 мин назад — НЕ считается, остаётся 2

    # --- Граница суммы ---
    {"id": 18, "client": "Assel", "amount": 100000, "city": "Astana", "minute": 720},      # approve: ровно 100 000 — это не "больше"
    {"id": 19, "client": "Assel", "amount": 500000, "city": "Astana", "minute": 725},      # review: ровно 500 000 — не block, но review
]

home_cities = {
    "Abzal" : "Astana",
    "Ansar" : "Astana",
    "Assel" : "Astana",
    "Baurzhan" : "Oskemen"
}

history = {}

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

def get_history(tx: dict) -> list:
    return history.get(tx["client"],[])

def add_history(tx: dict) -> None:
    if get_history(tx) == []:
        history[tx["client"]] = [tx["minute"]]
    else:
        history[tx["client"]].append(tx["minute"])

def check_velocity(tx: dict) -> str:
    times = get_history(tx)
    if times == []:
        return "approve"

    count = 0
    for t in times:
        if t > tx["minute"] - 10:
            count+=1
    
    if count > 2:
        return "review"

    return "approve"

#Оценка транзакции по итогам двух проверок
def score(tx: dict) -> str:
    results = []
    results.append(check_amount(tx))
    results.append(check_city(tx))
    results.append(check_velocity(tx))
    if "block" in results:
        return "block"
    elif "review" in results:
        return "review"
    else:
        return "approve"

for tx in transactions:
    print(f'Платеж {tx["id"]} ({tx["client"]}, {tx["amount"]}): {score(tx)}')
    add_history(tx)
print(history)