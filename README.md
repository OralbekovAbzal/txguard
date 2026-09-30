# TxGuard

TxGuard is a transaction scoring service for detecting suspicious bank payments.
For every incoming payment it returns one of three decisions:

- **approve** — looks normal, let it through
- **review** — suspicious, send to a human analyst
- **block** — clearly risky, stop the payment

The service exposes a REST API (FastAPI), keeps each client's recent payment history in Redis
and stores every payment together with its decision in PostgreSQL.

## How it works

```
POST /transactions/score
        │
        ▼
  Pydantic validation ──── invalid data ──▶ 422
        │
        ▼
  client exists? ───────── no ────────────▶ 404
        │
        ▼
  rules: amount · city · velocity
        │
        ▼
  strictest decision wins
        │
        ├──▶ Redis: add payment to client history
        ├──▶ PostgreSQL: save payment + decision
        ▼
  {"decision": "approve" | "review" | "block"}
```

### Rules

| Rule | What it checks | Decision |
|---|---|---|
| **Amount** | Payment amount against limits | `> 100 000` → review, `> 500 000` → block |
| **City** | Payment city against the client's home city (from PostgreSQL) | Different city or unknown city → review |
| **Velocity** | How many payments the client made recently (from Redis) | 3 or more previous payments within 10 minutes → review |

The final decision is the **strictest** one: any `block` blocks the payment,
otherwise any `review` sends it to review, otherwise it is approved.

**Fail-safe by default.** When information is missing, the system chooses the cautious option:
a payment without a city goes to `review`, never silently approved.

All limits are settings at the top of `main.py` and can be read via `GET /settings`.

### Storage

**Redis — fast, short-lived client history for the velocity rule**

- Key per client: `history:<client_id>` — a list of payment times
- Only the last 3 entries are kept (`LTRIM`); older ones never affect the decision
- Keys expire after 10 minutes of inactivity (`EXPIRE`)

Only payment times are stored in Redis: it keeps data in memory, so it holds the minimum the rule needs.

**PostgreSQL — permanent record of clients, payments and decisions**

- `clients` — client id, name, home city
- `transactions` — every scored payment with its decision and the time it was recorded

Integrity is enforced in the database as well as in the API:
`client_id` is a foreign key to `clients`, `amount` must be non-negative,
and `decision` can only be `approve`, `review` or `block`.
Amounts are stored as `BIGINT`, never as floating-point numbers.

All SQL queries use parameters (`%s`), never string formatting, to prevent SQL injection.

## API

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health check |
| `GET` | `/settings` | Current rule limits |
| `POST` | `/transactions/score` | Score a payment and save the decision |

**Request**

```json
{
  "id": 1,
  "client_id": 1,
  "amount": 50000,
  "city": "Astana",
  "minute": 600
}
```

| Field | Type | Rules |
|---|---|---|
| `id` | int | > 0 |
| `client_id` | int | > 0, must exist in `clients` |
| `amount` | int | ≥ 0 |
| `city` | string or `null` | optional — `null` leads to `review` |
| `minute` | int | minute of the day, 0–1439 |

**Responses**

| Code | When | Body |
|---|---|---|
| `200` | Payment scored | `{"decision": "approve"}` |
| `404` | Unknown `client_id` | `{"detail": "Client not found"}` |
| `422` | Invalid data (negative amount, missing field, wrong type) | validation details |

Interactive documentation is available at `http://127.0.0.1:8000/docs` while the service is running.

## Tech stack

- Python 3.11+, FastAPI, Pydantic
- PostgreSQL 16, psycopg 3
- Redis 7
- Docker
- pytest

## Getting started

**1. Clone the repository**

```bash
git clone https://github.com/OralbekovAbzal/txguard.git
cd txguard
```

**2. Create a virtual environment and install dependencies**

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
```

**3. Start Redis and PostgreSQL**

```bash
docker run -d --name txguard-redis -p 6379:6379 redis:7
docker run -d --name txguard-postgres -e POSTGRES_USER=txguard -e POSTGRES_PASSWORD=txguard -e POSTGRES_DB=txguard -p 5432:5432 postgres:16
```

> If PostgreSQL is also installed locally, stop it first — both use port 5432.

**4. Create tables and sample clients**

```bash
docker exec -i txguard-postgres psql -U txguard -d txguard < schema.sql
```

**5. Run the service**

```bash
uvicorn api:app --reload
```

Open `http://127.0.0.1:8000/docs` and try `POST /transactions/score`.

## Tests

```bash
pytest
```

25 tests cover:

- amount limits, including exact boundary values (100 000 and 500 000)
- city rule, including unknown city
- velocity rule with prepared Redis history, including the exact 10-minute boundary
- combining rules (the strictest decision wins)
- API: validation errors (422), unknown client (404), a payment without a city,
  and velocity across several real requests

> ⚠️ Tests clear Redis (`FLUSHDB`) and the `transactions` table (`TRUNCATE`) before and after each test.
> Don't run them against data you need.

## Known limitations

This is a learning-stage version. Things that will change:

- **Time** is a minute of the day, not a real timestamp, so the velocity rule can mix up
  payments around midnight. PostgreSQL already records real time in `created_at`;
  the API will switch to timestamps.
- **Configuration**: database and Redis credentials are in the code.
  They will move to environment variables.
- **Tests share the development database.** A separate test database is planned.
- **Race condition:** the velocity check reads history and writes the new payment in separate steps,
  so two simultaneous payments from one client could both pass.
  The fix is to write and count in a single atomic Redis operation.
- **Single database connection** shared by the whole service; a connection pool is needed under load.

## Roadmap

- [x] Rule-based scoring: amount, city, velocity
- [x] Client history in Redis with trimming and TTL
- [x] REST API with FastAPI and Pydantic validation
- [x] PostgreSQL for clients, payments and decisions
- [x] Unit and API tests with pytest
- [ ] Real timestamps instead of minutes
- [ ] ML model trained on a public fraud dataset, used as an additional check
- [ ] Analyst dashboard for reviewing suspicious payments
- [ ] Docker Compose, environment variables, CI with GitHub Actions, deployment
- [ ] LLM-generated explanations of decisions for analysts
