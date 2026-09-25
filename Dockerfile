FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Build Tailwind + daisyUI CSS (standalone binary, no Node) before collectstatic
RUN tailwindcss-extra -i assets/input.css -o static/css/app.css --minify

# Build-time only values: prod settings need them to import. Fails the build if collectstatic fails.
RUN DJANGO_SECRET_KEY=build-only DJANGO_ALLOWED_HOSTS=localhost \
    python manage.py collectstatic --noinput --settings=config.settings.prod

EXPOSE 8000

# gthread: a streaming mp3 holds a thread, not a whole worker
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--worker-class", "gthread", "--threads", "4"]
