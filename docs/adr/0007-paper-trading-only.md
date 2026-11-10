# 7. Paper trading only

Date: 2026-11-10 · Status: Accepted

## Context
Collected data will be used to design and backtest insider-detection strategies, and possibly to test
them live. Real orders bring financial risk, need wallet keys on a server, and raise legal questions.

## Decision
No order placement, no wallet keys, no trading API credentials in this system. Strategies are tested
on stored data (backtest) and live as signals only (paper trading).

## Consequences
- The attack surface stays small: the system only reads public data.
- Revisiting this needs a new ADR covering key management, risk limits and legal review.
