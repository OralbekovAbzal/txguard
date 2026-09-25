# TxGuard

TxGuard is a transaction scoring service for detecting suspicious bank payments.
For every incoming payment it returns one of three decisions:

- **approve** — looks normal, let it through
- **review** — suspicious, send to a human analyst
- **block** — clearly risky, stop the payment

This is the first version: a console app with rule-based checks and client history stored in Redis.
It is the foundation for an API service with an ML model (see [Roadmap](#roadmap)).

## How it works

Each payment goes through three independent rules:

| Rule | What it checks | Decision |
|---|---|---|
| **Amount** | Payment amount against limits | `> 100 000` → review, `> 500 000` → block |
| **City** | Payment city against the client's home city | Different city → review |
| **Velocity** | How many payments the client made recently | 3 or more previous payments within 10 minutes → review |

The final decision is the **strictest** one: if any rule says `block`, the payment is blocked;
otherwise if any rule says `review`, it goes to review; otherwise it is approved.

**Fail-safe by default.** When the system lacks information, it chooses the cautious option:
an unknown client or a payment without a city is sent to `review`, never silently approved.

### Payment history in Redis

The velocity rule needs to remember each client's recent payments. History is kept in Redis,
not in program memory, so it survives restarts and can be shared by several service instances.

- Key per client: `history:<client>` (a Redis list of payment times)
- Only the last 3 entries are kept (`LTRIM`) — older ones never affect the decision
- Keys expire after 10 minutes of inactivity (`EXPIRE`), so inactive clients don't take up memory

Storage access is isolated in two functions (`get_history`, `add_history`),
so the rules don't know or care where the history is stored.

All limits (amounts, velocity window, history size, TTL) are settings at the top of `main.py`.

## Tech stack

- Python 3.11+
- Redis 7 (via Docker)
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

**3. Start Redis**

```bash
docker run -d --name txguard-redis -p 6379:6379 redis:7
```

**4. Run**

```bash
python main.py
```

The script processes a set of sample payments and prints a decision for each one.

## Tests

```bash
pytest
```

17 tests cover:

- amount limits, including exact boundary values (100 000 and 500 000)
- city rule, including unknown clients and missing city
- velocity rule with prepared Redis history, including the exact 10-minute boundary
- combining rules in `score` (the strictest decision wins)

> ⚠️ Tests clear the Redis database (`FLUSHDB`) before and after each test.
> Don't run them against a Redis instance with data you need.

## Known limitations

This version is intentionally simple. Things that will change:

- **Time** is a plain number of minutes, not a real timestamp.
- **Client data** (home cities) is hardcoded instead of stored in a database.
- **Race condition:** the velocity check reads history and writes the new payment in separate steps.
  Two simultaneous payments from one client could both pass. The fix is to write and count
  in a single atomic Redis operation.

## Roadmap

- [x] Rule-based scoring: amount, city, velocity
- [x] Client history in Redis with trimming and TTL
- [x] Unit tests with pytest
- [ ] REST API with FastAPI (`POST /transactions/score`)
- [ ] PostgreSQL for transactions, clients and decisions
- [ ] ML model trained on a public fraud dataset, used as an additional check
- [ ] Analyst dashboard for reviewing suspicious payments
- [ ] Docker Compose, CI with GitHub Actions, deployment
- [ ] LLM-generated explanations of decisions for analysts
