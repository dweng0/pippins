# StackCX Assessment

Django + Postgres + Redis + Bootstrap 5, server-rendered monolith (no separate frontend/API split). Deployed to a single AWS EC2 free-tier box via Docker Compose. Cloudflare only for DNS, not hosting.

## Structure
- `config/settings/` — `base.py` (shared), `dev.py` (local), `prod.py` (EC2). Never hardcode secrets — everything comes from `.env` / environment.
- `core/` — main app. Add new features as new apps under the repo root, not by bloating `core`.
- `templates/` — `base.html` has the Bootstrap 5 shell; app templates extend it.

## Conventions
- Business logic lives in models/services, not views. Keep views thin.
- Any new dependency goes in `requirements.txt` (`pip freeze > requirements.txt` after installing).
- Write a test alongside any new view or model behavior (`pytest`, see `core/tests.py` for the pattern). Not exhaustive coverage — enough to prove the feature works and won't silently regress.
- `core/views.py:healthz` checks real DB + Redis connectivity, not just process liveness — keep that pattern for any future health/readiness endpoint.

## Commands
- `docker compose up --build` — full stack locally (web + Postgres + Redis)
- `python manage.py test` or `pytest` — run tests
- `python manage.py migrate` — apply migrations (needed after any model change)
