# 8. Pull-based deploy with a forced-command SSH key

Date: 2026-11-10 · Status: Accepted

## Context
Every merge to `main` should reach the VPS without manual steps. A CI system that holds an SSH key to
the server is an attack surface: if the key leaks, whoever holds it gets a shell. The server is small
(2–4 GB RAM), too small to run the Maven build comfortably.

## Decision
- GitHub Actions runs all checks, builds both images and pushes them to ghcr.io, tagged with the commit
  sha and `latest`.
- The CI key is installed on the server with `command="…/scripts/deploy.sh",restrict`. It cannot open
  a shell, forward ports or run anything else. Its only input is the commit sha.
- `deploy.sh` accepts only a 40-character sha that is an ancestor of `origin/main`, checks it out from
  the public repo, then runs `compose pull` and `compose up --wait` with that image tag.
- The host key is pinned in a secret (`DEPLOY_KNOWN_HOSTS`). No `StrictHostKeyChecking=no`.
- Deploy stays disabled until the repo variable `DEPLOY_ENABLED` is `true`, so the pipeline is useful
  (checks, images) before a server exists.

## Consequences
- A leaked CI key can at most redeploy a commit that is already on `main`.
- The server runs exactly the reviewed images. Compose files and the DB schema come from the same commit.
- The deploy user is in the `docker` group, which is root-equivalent on the host. The forced command
  is the boundary. Rootless Docker would remove this, at the cost of more setup.
- Rollback = deploy an older sha from `main` (run `scripts/deploy.sh <sha>` on the server).
