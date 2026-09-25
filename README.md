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
Django, PostgreSQL, Tailwind CSS 4 + daisyUI 5 (built with the standalone `tailwindcss-extra` CLI, no Node), htmx (django-htmx), Alpine.js. Deployed to a single AWS EC2 free-tier instance via Docker Compose; Cloudflare in front.

Domain terms are in `CONTEXT.md`; decisions in `docs/adr/`.

## Audio delivery

The sample mp3s ship inside the app as static files (`player/static/player/audio/`), served by WhiteNoise and cached at the Cloudflare edge.

```
Browser <audio> ──Range──► Cloudflare edge ──(miss only)──► EC2: gunicorn gthread → WhiteNoise
                            HIT: 206 from edge                  200 via sendfile / 206 chunked
```

- **Seeking** relies on HTTP Range: WhiteNoise answers `206 Partial Content` (tested in `player/tests.py`). `whitenoise.runserver_nostatic` gives dev the same behaviour.
- **Concurrency at origin:** gunicorn `gthread`, 2 workers × 4 threads, so a long download holds a thread rather than a whole worker. Only edge cache misses reach the box.
- **Caching:** static names are content-hashed (`CompressedManifestStaticFilesStorage`), so audio, CSS and JS are served `immutable` for a year and a deploy can't leave stale CSS/JS at the edge. Cache hits also keep AWS egress, and therefore cost, at zero. Tested on the prod path (collectstatic + WhiteNoise, no finders) in `player/tests.py`.
- **Tracks are ~320 kbps** (≈40 KB/s real-time); browsers buffer ahead, so a play is roughly one 3–7 MB fetch plus small range fetches on seek.

### Known limitations / next steps
- Cold-cache stampede: many simultaneous misses at one PoP can all reach origin (8 threads).
- At real scale, move audio to object storage with free egress (e.g. Cloudflare R2) so the box serves none of it.
- Cloudflare free-plan terms around serving large media volumes should be checked before any real traffic.

### Measuring it (to do)
```
# edge cache: expect 206, cf-cache-status MISS then HIT, Age increasing
URL='https://pippins.run/static/player/audio/komiku-bad-guys-hq.mp3'
curl -s -o /dev/null -D - -H 'Range: bytes=0-1023' "$URL" | grep -iE 'HTTP/|cf-cache-status|age|content-range'
curl -s -o /dev/null -w 'ttfb=%{time_starttransfer}s total=%{time_total}s\n' "$URL"   # run twice: miss vs hit

# throughput: edge vs origin (origin only reachable from Cloudflare ranges, so run the origin test on the box via SSM)
oha -z 20s -c 20 "$URL"
oha -z 20s -c 20 'http://localhost/static/player/audio/komiku-bad-guys-hq.mp3'
```
Results table goes here (req/s, p50/p99 TTFB, MB/s; edge vs origin).

## Design note: synced multi-device playback (Sendspin, #19)

Investigated, deliberately not built. Same-browser tabs already hand off (only one plays at a time, via `BroadcastChannel`); syncing across devices is the next step up.

- **What it would take:** [Sendspin](https://www.sendspin-audio.com/) clients hold a WebSocket to a server that sends a clock and timestamped audio, so every device plays the same sample at the same moment.
- **Why not now:**
  - SDKs are pre-RC1, so the API is still moving.
  - Needs a separate long-lived async WebSocket service. That's a second process on a 1 GB box, and it doesn't fit gunicorn's sync workers.
  - The spec expects plain `ws://` on the LAN. From a page served over HTTPS (Cloudflare) the browser blocks that as mixed content, so it would need `wss://` through Cloudflare and a server-side relay.
  - It's aimed at speakers on one network, not browsers on the internet.
- **If revisited:** Django Channels (or a small separate asyncio service) behind `wss://`. Start with "follow this Listener": a second device mirrors track + position using server timestamps, which is good enough without sample-accurate sync. Keep device state on the device (ADR-0001).
