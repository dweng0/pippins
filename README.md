# StackCX Assessment

## Local dev
```
cp .env.example .env   # fill in secrets
docker compose up --build
```
App at http://localhost:8000, health check at `/healthz/`.

## Tests
```
docker compose exec web pytest
```

## Stack
Django, PostgreSQL, Redis, Bootstrap 5 (CDN). Deployed to a single AWS EC2 free-tier instance via Docker Compose; DNS via Cloudflare.
