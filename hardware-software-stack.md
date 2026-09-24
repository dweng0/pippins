# Hardware / Software Stack

## Hardware / hosting
- Single AWS EC2 free-tier instance (provisioned via Terraform, see `infra/`)
- Docker Compose runs web + Postgres + Redis on the one box
- Cloudflare for DNS only, not hosting

## Backend
- Python 3.13, Django 6.1 (server-rendered monolith, no API/frontend split)
- PostgreSQL (psycopg 3), Redis (django-redis), Celery
- Gunicorn + Whitenoise (static files) in prod
- Pydantic for validation

## Frontend
- Bootstrap 5 (CDN) — current styling
- **htmx** — decided. Server returns HTML partials for dynamic UI, no JS framework or JSON API.
  - Plan: load via script tag in `templates/base.html`, add `django-htmx` for `request.htmx`.
  - CSRF: send token via `hx-headers` on `<body>`.
  - Views stay thin; partial-rendering logic lives in templates, business logic in models/services.
- Styling: under discussion (Tailwind + daisyUI vs. staying on Bootstrap)

## Testing / CI
- pytest + pytest-django
- Cypress e2e
- CI on GitHub
