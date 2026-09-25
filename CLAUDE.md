# StackCX Assessment

Django + Postgres + Tailwind CSS 4 + daisyUI 5, server-rendered monolith (no separate frontend/API split). Deployed to a single AWS EC2 free-tier box via Docker Compose. Cloudflare proxies web traffic (TLS at the edge, SSL mode Flexible); the box only accepts 80/443 from Cloudflare ranges. No SSH port: shell access via SSM Session Manager (see `infra/README.md`). `main` is protected: changes land via PR with `test` + `e2e` green.

## Structure
- `config/settings/` — `base.py` (shared), `dev.py` (local), `prod.py` (EC2). Never hardcode secrets — everything comes from `.env` / environment.
- `core/` — main app. Add new features as new apps under the repo root, not by bloating `core`.
- `templates/` — `base.html` has the Tailwind/daisyUI shell; app templates extend it. Style with daisyUI component classes (`btn`, `card`, `alert`, ...) plus Tailwind utilities. Keep `data-cy` hooks (Cypress relies on them).
- `assets/input.css` — Tailwind entry (`@plugin "daisyui"`, `@source` template paths). Built to `static/css/app.css` (gitignored) by `tailwindcss-extra` (pip package `pytailwindcss-extra`, standalone binary, no Node). New template dirs outside `templates/`/`core/` need an `@source` line.

## Conventions
- Business logic lives in models/services, not views. Keep views thin.
- Any new dependency goes in `requirements.txt` (`pip freeze > requirements.txt` after installing).
- Write a test alongside any new view or model behavior (`pytest`, see `core/tests.py` for the pattern). Not exhaustive coverage — enough to prove the feature works and won't silently regress.
- `core/views.py:healthz` checks real DB connectivity, not just process liveness — keep that pattern for any future health/readiness endpoint.

## Commands
- `docker compose up --build` — full stack locally (web + Postgres + Tailwind watcher)
- `tailwindcss-extra -i assets/input.css -o static/css/app.css --watch` — CSS watcher when running outside Docker (compose uses `--watch=always`, since plain `--watch` exits when stdin closes)
- `python manage.py test` or `pytest` — run tests
- `python manage.py migrate` — apply migrations (needed after any model change)

## Session end
- Before finishing a session, append an entry to `JOURNAL.md` (date, what changed, decisions + why, open items/next steps). Keep it short.
