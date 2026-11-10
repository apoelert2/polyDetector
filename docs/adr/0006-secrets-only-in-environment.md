# 6. Secrets only in the environment, enforced by tests

Date: 2026-11-10 · Status: Accepted

## Context
The repo is public, and the stack runs on a VPS. The first compose file had default passwords
for RabbitMQ and the DB, and published all ports on every interface. Those defaults are in git
history.

## Decision
- Credentials only come from `.env` (gitignored). `.env.example` holds placeholders.
- Compose uses `${VAR:?}`: no defaults, startup fails if a secret is missing. Services fail fast too.
- Ports are bound to `127.0.0.1` only. Remote access goes through an SSH tunnel.
- Passwords never reach logs: `Config.toString()` masks them, the Python settings use `repr=False`.
  Both are unit-tested.
- `tests/test_no_secrets.py` scans every tracked file for values from the local `.env`, hard-coded
  credentials, private keys and IP addresses, and includes a self-check that the patterns fire.

## Consequences
- Passwords that appeared in history must be rotated before deployment, since history is public.
- The scanner is heuristic. It complements, but does not replace, a dedicated tool like gitleaks in CI.
