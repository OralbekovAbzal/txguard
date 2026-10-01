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
  Pydantic validation ──── invalid data / time without timezone ──▶ 422
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
        ├──▶ Redis: add payment time to client history
        ├──▶ PostgreSQL: save payment + decision
        ▼
  {"decision": "approve" | "review" | "block"}
```

### Rules

| Rule         | What it checks                                                | Decision                                                      |
| ------------ | ------------------------------------------------------------- | ------------------------------------------------------------- |
| **Amount**   | Payment amount against limits                                 | `> 100 000` → review, `> 500 000` → block                     |
| **City**     | Payment city against the client's home city (from PostgreSQL) | Different city or unknown city → review                       |
| **Velocity** | How many payments the client made recently (from Redis)       | 3 or more previous payments in the last 10 minutes → review   |

The final decision is the **strictest** one: any `block` blocks the payment,
otherwise any `review` sends it to review, otherwise it is approved.

**Fail-safe by default.** When information is missing, the system chooses the cautious option:
a payment without a city goes to `review`, never silently approved.

All limits are settings at the top of `main.py` and can be read via `GET /settings`.

### Time

Every payment carries the moment it happened as an ISO 8601 timestamp **with a timezone**:

```
2026-10-01T12:00:00+05:00
```

- A timestamp without a timezone (`2026-10-01T12:00:00`) is rejected with `422`, because it does not identify a single moment.
- Different offsets are fine: `12:00+05:00` and `07:00Z` are the same moment and are treated as the same.
- Rules use the payment's own time (`occurred_at`), not the time the server received it.
- The velocity window is exclusive at its lower edge: a payment made exactly 10 minutes earlier no longer counts.
- Midnight is not special: payments at 23:58 and 00:02 are 4 minutes apart.

### Storage

**Redis — fast, short-lived client history for the velocity rule**

- Key per client: `history:<client_id>` — a list of payment times as Unix seconds
- Only the last 3 entries are kept (`RPUSH` + `LTRIM`); older ones never affect the decision
- Keys expire after 10 minutes of inactivity (`EXPIRE`)

Only payment times are stored in Redis: it keeps data in memory, so it holds the minimum the rule needs.

**PostgreSQL — permanent record of clients, payments and decisions**

- `clients` — client id, name, home city
- `transactions` — every scored payment with its decision, `occurred_at` (when the payment happened, from the request)
  and `created_at` (when the service recorded it)

Integrity is enforced in the database as well as in the API: `client_id` is a foreign key to `clients`,
`amount` must be non-negative, and `decision` can only be `approve`, `review` or `block`.
Amounts are stored as `BIGINT`, never as floating-point numbers. Times are stored as `TIMESTAMPTZ`.

All SQL queries use parameters (`%s`), never string formatting, to prevent SQL injection.

## API

| Method | Endpoint              | Description                           |
| ------ | --------------------- | ------------------------------------- |
| `GET`  | `/health`             | Service health check                  |
| `GET`  | `/settings`           | Current rule limits                   |
| `POST` | `/transactions/score` | Score a payment and save the decision |

**Request**

```json
{
  "id": 1,
  "client_id": 1,
  "amount": 50000,
  "city": "Astana",
  "occurred_at": "2026-10-01T12:00:00+05:00"
}
```

| Field         | Type             | Rules                                                        |
| ------------- | ---------------- | ------------------------------------------------------------ |
| `id`          | int              | > 0                                                          |
| `client_id`   | int              | > 0, must exist in `clients`                                 |
| `amount`      | int              | ≥ 0                                                          |
| `city`        | string or `null` | optional — `null` leads to `review`                          |
| `occurred_at` | datetime         | ISO 8601 with timezone, e.g. `2026-10-01T12:00:00+05:00`     |

**Responses**

| Code  | When                                                                             | Body                             |
| ----- | -------------------------------------------------------------------------------- | -------------------------------- |
| `200` | Payment scored                                                                   | `{"decision": "approve"}`        |
| `404` | Unknown `client_id`                                                              | `{"detail": "Client not found"}` |
| `422` | Invalid data (negative amount, missing field, wrong type, time without timezone) | validation details               |

Interactive documentation is available at `http://127.0.0.1:8000/docs` while the service is running.

## Tech stack

- Python 3.11+, FastAPI, Pydantic
- PostgreSQL 16, psycopg 3
- Redis 7
- Docker
- pytest

## Getting started

**1. Clone the repository**

```
git clone https://github.com/OralbekovAbzal/txguard.git
cd txguard
```

**2. Create a virtual environment and install dependencies**

```
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -r requirements.txt
```

**3. Start Redis and PostgreSQL**

```
docker run -d --name txguard-redis -p 6379:6379 redis:7
docker run -d --name txguard-postgres -e POSTGRES_USER=txguard -e POSTGRES_PASSWORD=txguard -e POSTGRES_DB=txguard -p 5432:5432 postgres:16
```
> If PostgreSQL is also installed locally, stop it first — both use port 5432.

**4. Create tables and sample clients**

```
docker exec -i txguard-postgres psql -U txguard -d txguard < schema.sql
```

**5. Run the service**

```
uvicorn api:app --reload
```

Open `http://127.0.0.1:8000/docs` and try `POST /transactions/score`.

## Tests

```
pytest
```

27 tests cover:

- amount limits, including exact boundary values (100 000 and 500 000)
- city rule, including unknown client and missing city
- velocity rule with prepared Redis history, including the exact 10-minute boundary and a series of payments crossing midnight
- combining rules (the strictest decision wins)
- API: validation errors (negative amount, invalid or missing `client_id`, time without timezone),
a payment without a city, and velocity across several real requests

> ⚠️ Tests clear Redis (`FLUSHDB`) and the `transactions` table (`TRUNCATE`) before and after each test.
> Don't run them against data you need.

## Known limitations

This is a learning-stage version. Things that will change:

- **Configuration**: database and Redis credentials are in the code.
They will move to environment variables.
- **Tests share the development database.** A separate test database is planned.
- **Race condition:** the velocity check reads history and writes the new payment in separate steps,
so two simultaneous payments from one client could both pass.
The fix is to write and count in a single atomic Redis operation.
- **Out-of-order payments:** Redis keeps the last 3 payments in the order they arrive, not in the order they happened,
so a late-arriving payment can be miscounted. A sorted set keyed by time would fix this.
- **No check for timestamps far in the future:** a client can send any `occurred_at`.
The API should reject times too far ahead of the server clock.
- **Single database connection** shared by the whole service; a connection pool is needed under load.

## Roadmap

- [x] Rule-based scoring: amount, city, velocity
- [x] Client history in Redis with trimming and TTL
- [x] REST API with FastAPI and Pydantic validation
- [x] PostgreSQL for clients, payments and decisions
- [x] Unit and API tests with pytest
- [x] Real timestamps instead of minutes
- [ ] ML model trained on a public fraud dataset, used as an additional check
- [ ] Analyst dashboard for reviewing suspicious payments
- [ ] Docker Compose, environment variables, CI with GitHub Actions, deployment
- [ ] LLM-generated explanations of decisions for analysts
