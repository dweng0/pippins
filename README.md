# Pippins — StackCX Assessment

A Spotify-like music player: Django server-rendered pages, htmx for navigation, Alpine.js for the in-browser player. Live at https://pippins.run.

## Local dev
```
cp .env.example .env   # fill in secrets
docker compose up --build
docker compose exec web python manage.py load_tracks   # load the sample mp3s
```
App at http://localhost:8000, health check at `/healthz/`.

## Tests
```
docker compose exec web pytest
CYPRESS_BASE_URL=http://localhost:8000 npx cypress run
```

## Stack
Django, PostgreSQL, Redis, Tailwind CSS 4 + daisyUI 5 (built with the standalone `tailwindcss-extra` CLI, no Node), htmx (django-htmx), Alpine.js. Deployed to a single AWS EC2 free-tier instance via Docker Compose; Cloudflare in front.

Domain terms are in `CONTEXT.md`; decisions in `docs/adr/`.

## Audio delivery

The sample mp3s ship inside the app as static files (`player/static/player/audio/`), served by WhiteNoise and cached at the Cloudflare edge.

```
Browser <audio> ──Range──► Cloudflare edge ──(miss only)──► EC2: gunicorn gthread → WhiteNoise
                            HIT: 206 from edge                  200 via sendfile / 206 chunked
```

- **Seeking** relies on HTTP Range: WhiteNoise answers `206 Partial Content` (tested in `player/tests.py`). `whitenoise.runserver_nostatic` gives dev the same behaviour.
- **Concurrency at origin:** gunicorn `gthread`, 2 workers × 4 threads, so a long download holds a thread rather than a whole worker. Only edge cache misses reach the box.
- **Caching:** `WHITENOISE_MAX_AGE` is 1 day (filenames aren't content-hashed, so not `immutable`). Cache hits also keep AWS egress, and therefore cost, at zero.
- **Tracks are ~320 kbps** (≈40 KB/s real-time); browsers buffer ahead, so a play is roughly one 3–7 MB fetch plus small range fetches on seek.

### Known limitations / next steps
- Hashed filenames (`ManifestStaticFilesStorage`) + 1-year immutable caching (#8, #22).
- Cold-cache stampede: many simultaneous misses at one PoP can all reach origin (8 threads).
- At real scale, move audio to object storage with free egress (e.g. Cloudflare R2) so the box serves none of it.
- Cloudflare free-plan terms around serving large media volumes should be checked before any real traffic.

### Measuring it (to do)
```
# edge cache: expect 206, cf-cache-status MISS then HIT, Age increasing
URL='https://pippins.run/static/player/audio/Komiku%20-%20Bad%20Guys%20HQ.mp3'
curl -s -o /dev/null -D - -H 'Range: bytes=0-1023' "$URL" | grep -iE 'HTTP/|cf-cache-status|age|content-range'
curl -s -o /dev/null -w 'ttfb=%{time_starttransfer}s total=%{time_total}s\n' "$URL"   # run twice: miss vs hit

# throughput: edge vs origin (origin only reachable from Cloudflare ranges, so run the origin test on the box via SSM)
oha -z 20s -c 20 "$URL"
oha -z 20s -c 20 'http://localhost/static/player/audio/Komiku%20-%20Bad%20Guys%20HQ.mp3'
```
Results table goes here (req/s, p50/p99 TTFB, MB/s; edge vs origin).
