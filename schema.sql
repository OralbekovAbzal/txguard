-- TxGuard database schema
-- Creates tables and sample clients.
-- Run once on an empty database:
--   docker exec -i txguard-postgres psql -U txguard -d txguard < schema.sql

-- Clients of the bank
CREATE TABLE clients (
    id        SERIAL PRIMARY KEY,
    name      TEXT NOT NULL,
    home_city TEXT NOT NULL
);

-- Every scored payment with its decision
CREATE TABLE transactions (
    id          BIGSERIAL PRIMARY KEY,
    client_id   INTEGER NOT NULL REFERENCES clients(id),
    amount      BIGINT NOT NULL,
    city        TEXT,
    occurred_at TIMESTAMPTZ NOT NULL,                -- when the payment happened (from the request)
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),  -- when TxGuard saved it
    decision    TEXT NOT NULL,

    CONSTRAINT amount_positive CHECK (amount >= 0),
    CONSTRAINT decision_types  CHECK (decision IN ('approve', 'review', 'block'))
);

-- Sample clients (tests expect these ids: 1 = Abzal, ..., 4 = Baurzhan)
INSERT INTO clients (name, home_city) VALUES
    ('Abzal',    'Astana'),
    ('Ansar',    'Astana'),
    ('Assel',    'Astana'),
    ('Baurzhan', 'Oskemen');
