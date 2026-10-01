import redis
import psycopg
from datetime import datetime, timezone, timedelta

BLOCK_LIMIT = 500000
REVIEW_LIMIT = 100000

VELOCITY_WINDOW_SEC = 600
VELOCITY_LIMIT = 3
HISTORY_TTL = 600

r = redis.Redis(host = "localhost", port = 6379, decode_responses = True)

conn = psycopg.connect("host=localhost port=5432 dbname=txguard user=txguard password=txguard")

"""transactions = [
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
]"""

def save_transaction(tx: dict, dec: str) -> None:
    with conn.cursor() as cur:
        cur.execute("insert into transactions (client_id,city,decision,occurred_at,amount) values (%s,%s,%s,%s,%s)",(tx["client_id"],tx["city"],dec,tx["occurred_at"],tx["amount"]))
        conn.commit()

def client_exists(client_id: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("select name from clients where id=%s",(client_id,))
        name = cur.fetchone()
        return name is not None

def check_amount(tx: dict) -> str:
    #Если сумма превышает лимит по транзакциям то блокируется
    if tx["amount"] > BLOCK_LIMIT:
        return "block"
    
    #Если сумма превышает лимит то идет на проверку
    elif tx["amount"] > REVIEW_LIMIT:
        return "review"
    return "approve"

def get_home_city(client_id: int) -> str | None:
    with conn.cursor() as cur:
        cur.execute("select home_city from clients where id=%s",(client_id,))
        home_city = cur.fetchone()
        if home_city is None:
            return None
        else:
            return home_city[0]

def check_city(tx: dict) -> str:
    home = get_home_city(tx["client_id"])
    #Если у транзакции нету города то идет на проверку
    if home is None:
        return "review"

    #Если город проживания и город в котором была сделана транзакция разная то идет на проверку
    if tx["city"] != home:
        return "review"
    
    return "approve"

def get_history(tx: dict) -> list:
    historyStr = r.lrange(history_key(tx),0,-1)

    historyInt = []
    for h in historyStr:
        historyInt.append(int(h))

    return historyInt

def add_history(tx: dict) -> None:
    r.rpush(history_key(tx),timestamp_to_sec(tx["occurred_at"]))
    r.ltrim(history_key(tx),-VELOCITY_LIMIT,-1)
    r.expire(history_key(tx),HISTORY_TTL)

def history_key(tx: dict) -> str:
    return f"history:{tx['client_id']}"

def timestamp_to_sec(ts: datetime) -> int:
    return int(ts.timestamp())

def check_velocity(tx: dict) -> str:
    times = get_history(tx)

    count = 0
    for t in times:
        if t > timestamp_to_sec(tx["occurred_at"]) - VELOCITY_WINDOW_SEC:
            count+=1
    
    if count >= VELOCITY_LIMIT:
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