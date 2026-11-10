from datetime import datetime

import psycopg
from domain.entities import Market, Trade
from domain.use_cases.ports import RepositoryPort
from settings import DbSettings

UPSERT_MARKET = """
INSERT INTO markets (condition_id, question, slug, end_date, closed, tag_ids, outcomes, token_ids, updated_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (condition_id) DO UPDATE SET
    question = EXCLUDED.question, slug = EXCLUDED.slug, end_date = EXCLUDED.end_date,
    closed = EXCLUDED.closed, tag_ids = EXCLUDED.tag_ids, outcomes = EXCLUDED.outcomes,
    token_ids = EXCLUDED.token_ids, updated_at = EXCLUDED.updated_at
"""

INSERT_SNAPSHOT = """
INSERT INTO market_snapshots (time, condition_id, outcome_prices, volume, volume_24h, liquidity)
VALUES (%s, %s, %s, %s, %s, %s)
"""

INSERT_TRADE = """
INSERT INTO trades (time, transaction_hash, condition_id, token_id, proxy_wallet, side, size, price, outcome)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT DO NOTHING
"""


class PostgresRepository(RepositoryPort):
    """One short connection per call: a cycle runs once a minute, and a DB restart heals by itself."""

    def __init__(self, db: DbSettings):
        self._db = db

    def _connect(self) -> psycopg.Connection[tuple[object, ...]]:
        return psycopg.connect(
            host=self._db.host, port=self._db.port, dbname=self._db.name, user=self._db.user, password=self._db.password
        )

    def save_markets(self, markets: list[Market], polled_at: datetime) -> None:
        with self._connect() as conn, conn.cursor() as cur:  # one transaction: markets and snapshots together
            cur.executemany(
                UPSERT_MARKET,
                [
                    (
                        m.condition_id,
                        m.question,
                        m.slug,
                        m.end_date,
                        m.closed,
                        list(m.tag_ids),
                        list(m.outcomes),
                        list(m.token_ids),
                        polled_at,
                    )
                    for m in markets
                ],
            )
            cur.executemany(
                INSERT_SNAPSHOT,
                [
                    (polled_at, m.condition_id, list(m.outcome_prices), m.volume, m.volume_24h, m.liquidity)
                    for m in markets
                ],
            )

    def closing_market_ids(self, end_min: datetime, end_max: datetime) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT condition_id FROM markets WHERE NOT closed AND end_date BETWEEN %s AND %s ORDER BY end_date",
                (end_min, end_max),
            ).fetchall()
        return [str(r[0]) for r in rows]

    def latest_trade_times(self, condition_ids: list[str]) -> dict[str, datetime]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT condition_id, max(time) FROM trades WHERE condition_id = ANY(%s) GROUP BY condition_id",
                (condition_ids,),
            ).fetchall()
        return {str(cid): t for cid, t in rows if isinstance(t, datetime)}

    def save_trades(self, trades: list[Trade]) -> None:
        if not trades:
            return
        with self._connect() as conn, conn.cursor() as cur:
            cur.executemany(
                INSERT_TRADE,
                [
                    (
                        t.time,
                        t.transaction_hash,
                        t.condition_id,
                        t.token_id,
                        t.proxy_wallet,
                        t.side,
                        t.size,
                        t.price,
                        t.outcome,
                    )
                    for t in trades
                ],
            )
