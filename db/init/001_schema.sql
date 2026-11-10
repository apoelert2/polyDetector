-- Runs once, on the first start with an empty volume (postgres entrypoint).
-- shortcut: no migration tool; schema changes after first deploy need a manual ALTER or a fresh volume.

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Current state per market, written by the poller (Gamma API).
CREATE TABLE markets (
    condition_id text PRIMARY KEY,
    question     text        NOT NULL,
    slug         text,
    end_date     timestamptz,
    closed       boolean     NOT NULL,
    tag_ids      integer[]   NOT NULL DEFAULT '{}',
    outcomes     text[]      NOT NULL,
    token_ids    text[]      NOT NULL,
    updated_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX markets_end_date_idx ON markets (end_date) WHERE NOT closed;

-- Price/volume history per poll cycle (one row per market per poll).
CREATE TABLE market_snapshots (
    time           timestamptz        NOT NULL,
    condition_id   text               NOT NULL,
    outcome_prices double precision[] NOT NULL,
    volume         double precision,
    volume_24h     double precision,
    liquidity      double precision
);
SELECT create_hypertable('market_snapshots', 'time');
CREATE INDEX ON market_snapshots (condition_id, time DESC);

-- Every WebSocket event as received (book, price_change, last_trade_price, ...).
-- Raw payload is kept so later backtests can re-derive anything.
CREATE TABLE ws_events (
    time        timestamptz NOT NULL,  -- event time from Polymarket
    received_at timestamptz NOT NULL,  -- our clock, to measure feed latency
    event_type  text        NOT NULL,
    market      text,
    asset_id    text,
    payload     jsonb       NOT NULL
);
-- 1-day chunks: compression only touches chunks that ended more than the policy age ago,
-- so with the default 7-day chunks nothing would be compressed for about 8 days.
SELECT create_hypertable('ws_events', 'time', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX ON ws_events (market, time DESC);
ALTER TABLE ws_events SET (timescaledb.compress, timescaledb.compress_segmentby = 'market');
SELECT add_compression_policy('ws_events', INTERVAL '1 day');

-- Trades with wallet, from the Data API. transaction_hash joins with ws_events (last_trade_price).
CREATE TABLE trades (
    time             timestamptz      NOT NULL,
    transaction_hash text             NOT NULL,
    condition_id     text             NOT NULL,
    token_id         text             NOT NULL,
    proxy_wallet     text             NOT NULL,
    side             text             NOT NULL,
    size             double precision NOT NULL,
    price            double precision NOT NULL,
    outcome          text,
    -- shortcut: two identical fills (same wallet, token, side, size, price) in one tx collapse into one row.
    UNIQUE (transaction_hash, token_id, proxy_wallet, side, size, price, time)
);
SELECT create_hypertable('trades', 'time');
CREATE INDEX ON trades (condition_id, time DESC);
CREATE INDEX ON trades (proxy_wallet, time DESC);

-- Volume spikes found live by the ws-subscriber.
CREATE TABLE spikes (
    time              timestamptz      NOT NULL,
    asset_id          text             NOT NULL,
    market            text,
    window_notional   double precision NOT NULL,
    baseline_notional double precision NOT NULL
);
SELECT create_hypertable('spikes', 'time');
