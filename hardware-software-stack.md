# Hardware / Software Stack

## Hardware / hosting
- Single AWS EC2 free-tier instance (provisioned via Terraform, see `infra/`)
- Docker Compose runs web + Postgres + Redis on the one box
- Cloudflare proxy in front (DNS + TLS at the edge, Flexible mode); security group only allows 80/443 from Cloudflare ranges
- No inbound SSH: access via AWS SSM Session Manager (instance role with `AmazonSSMManagedInstanceCore`)
- Deploys: CI-gated pull via systemd timer on the box; `main` protected by a ruleset (PR + `test`/`e2e` required)

## Backend
- Python 3.13, Django 6.1 (server-rendered monolith, no API/frontend split)
- PostgreSQL (psycopg 3), Redis (django-redis), Celery
- Gunicorn + Whitenoise (static files) in prod
- Pydantic for validation

## Frontend
- **Tailwind CSS 4 + daisyUI 5** — styling (replaced Bootstrap 5)
  - Built with `pytailwindcss-extra` (`tailwindcss-extra` binary bundles daisyUI, no Node).
  - Entry `assets/input.css` -> `static/css/app.css` (gitignored). Built in Dockerfile and CI; watched by the `tailwind` compose service in dev.
- **htmx** — decided. Server returns HTML partials for dynamic UI, no JS framework or JSON API.
  - Plan: load via script tag in `templates/base.html`, add `django-htmx` for `request.htmx`.
  - CSRF: send token via `hx-headers` on `<body>`.
  - Views stay thin; partial-rendering logic lives in templates, business logic in models/services.

## Testing / CI
- pytest + pytest-django
- Cypress e2e
- CI on GitHub
