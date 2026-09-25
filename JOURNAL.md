# Journal

## 2026-09-24 — Styling: Bootstrap -> Tailwind + daisyUI, htmx decided

**Done**
- Replaced Bootstrap 5 CDN with Tailwind CSS 4.3 + daisyUI 5.6, built by `pytailwindcss-extra` (standalone binary that bundles daisyUI; no Node in the image).
- `assets/input.css` is the entry; output `static/css/app.css` is gitignored and built in the Dockerfile (before `collectstatic`), in the CI e2e job, and by a `tailwind` watch service in `docker-compose.yml`.
- Restyled `base.html`, `home.html`, `task_list.html`; `data-cy` hooks kept so Cypress specs are untouched.
- Added `hardware-software-stack.md`; noted htmx as decided (not wired up yet).
- CLAUDE.md now tells future sessions to update this journal at session end.

**Decisions / why**
- Standalone CLI over Node build: Cypress already pulls in Node for dev, but prod image stays small and Python-only. Research (daisyUI "Tailwind without Node" docs, pytailwindcss-extra, django-tailwind-cli) showed this is the supported no-Node path.
- Built CSS not committed: avoids noisy diffs; every build path generates it.
- Watcher disabled in prod via `profiles: ["dev-only"]` in `docker-compose.prod.yml`, so EC2 doesn't run it.
- Source lives in `assets/`, not `static/`, so collectstatic doesn't ship it.

**Gotchas**
- First run downloads the Tailwind binary from GitHub (flaky; retry). On Linux with `/tmp` on a different filesystem than `~/.cache`, the move fails with `Invalid cross-device link`; fix with `TMPDIR=$HOME/.cache/pytailwindcss-extra/tmp`.
- Tailwind v4 `--watch` exits when stdin closes, so the detached compose service needs `--watch=always` (otherwise `tailwind` exits 0 right after one build).
- Tailwind only emits classes it finds in scanned files; new template dirs need an `@source` line.

**State at end of session**
- Verified: 7 pytest tests pass; Docker image builds and collects `css/app.css`; `docker compose up -d --build` serves `/`, `/healthz/` and `/static/css/app.css` with 200.
- Not verified: visual look of the restyled pages in a browser, Cypress run, CI run on GitHub.
- Nothing committed yet (all changes are in the working tree). The compose stack was left running.
- Initial "can't reach localhost" was just `web`/`tailwind` never having been started; the watcher exiting was a real bug (fixed above).

**Next**
- Add htmx (`django-htmx`, script tag in base.html, CSRF via `hx-headers`) + a test for a partial view.
- Consider daisyUI theme switching / dark mode.
- Check the CI e2e run on GitHub after pushing.

## 2026-09-24 (evening) — Infra hardening, Cloudflare proxy, SSM

**Done**
- Stopped tracking `infra/tfplan` (plan files embed variable values); `infra/tfplan` + `*.tfplan` gitignored.
- Security review of `infra/`. Found and fixed: `aws_ami` `most_recent` would have replaced the instance (and wiped Postgres on the root volume) on the next `apply` — `ignore_changes` now includes `ami`.
- PR #1 (merged + applied): SSM Session Manager replaces SSH (port 22 closed, `allowed_ssh_cidr` removed); ports 80/443 accept only Cloudflare edge ranges; IMDSv2 with hop limit 1 (verified containers can't reach IMDS); `instance_id` / `ssm_command` outputs.
- `main` protected by a ruleset: no force-push/deletion, PR required, `test` + `e2e` required.
- Cloudflare record proxied; site serves via Cloudflare, raw IP no longer answers.

**Decisions / why**
- SSM over SSH: no inbound port, IAM-controlled, no dependence on a home IP. SSH/scp still tunnel over SSM.
- Cloudflare Flexible for now (no TLS listener on the box yet); Full (strict) with an origin cert later.
- No separate EBS data volume for Postgres (yet): backups instead; data volume is the next step before real data.
- Hop limit 1: once the instance has a role, containers must not reach its credentials.

**Next**
- Phase 2 rebuild: encrypted root EBS + account default encryption; `user_data` compose plugin with pinned SHA-256 and `dnf-automatic`; then termination protection.
- CI-built images on GHCR (decide public package vs pull token).
- Redis roles (sessions → `cached_db` at minimum); `pg_dump` → S3 backups.
- htmx; daisyUI dark mode; Celery only if needed.

## 2026-09-25 — Assessment part 2: music player, slice 1

**Done**
- Read the part 2 brief (build a Spotify-like player in 2h) and worked out the plan through Q&A. Plan captured as issues #3–#23; domain terms in `CONTEXT.md` (Listener, Track, Queue, Favourite); ADR-0001 (a Listener model owns per-person state so accounts can attach later).
- Research agents checked WhiteNoise Range support, htmx + Alpine pitfalls, the custom theme and animations, and Sendspin. Findings are posted on the issues.
- Slice 1 (PR #24): `player` app, `Track` catalogue + `load_tracks`, `Listener`, track list, Alpine player (play/pause, prev/next, volume, seek, Queue), "Pippins" daisyUI theme, first animations, Task demo removed. pytest 11/11, Cypress 4/4 locally.
- Repo renamed to `dweng0/pippins`; `deploy.sh` updated to match.

**Decisions / why**
- One `<audio>` element + an Alpine store; htmx only swaps `#main` (`hx-history-elt`), so navigation never stops playback.
- Audio is committed static, served by WhiteNoise with Range/206 and cached by Cloudflare, following the brief's "keep audio in the app" hint. Sendspin was rejected for core (pre-RC1, needs a separate WS service, spec requires `ws://` behind HTTPS).
- gthread workers: a streaming mp3 holds a thread, not a worker. Cache TTL is 1 day for now; hashed names + immutable caching come later (#22).
- Original filenames kept for now (2 files have no tags, so the filename is their metadata). Revisit in #22.

**Next**
- Merge #24 once green. The box runs its own copy of `deploy.sh`, so reinstall it there after merge.
- #23 drop Redis (sessions to Postgres; Redis has no volume, so every deploy wipes Listeners).
- #14 favourites, #11 persistence, #12 search, #13 shuffle, #15 recent, #20 Media Session, #21 multi-tab.
- Nit: clicking a row scrolls the page slightly. Fill in the README audio measurements after deploy.

## 2026-09-25 (afternoon) — Slices 2+, review fixes, mascot

**Done** (branch `slices`, stacked on `player` / PR #24; one commit per slice)
- #23 Redis dropped: sessions in Postgres, LocMem cache, healthz DB-only, redis/celery out of compose, CI and requirements.
- #14 favourites (htmx heart, `/favourites/`), #12 search (htmx, rows-only swap, `?q=`), #15 recently played (`Play` rows, `/recent/`), #13 shuffle, #11 localStorage persistence (restored paused), #20 Media Session, #21 one tab plays at a time (`BroadcastChannel`).
- #22 audio renamed to slugs; ID3 tags written into the 2 untagged files. #19 Sendspin design note in README.
- Mascot: the Mooch bunny wearing headphones (`core/static/core/pippins.svg`), used as logo and favicon.
- PR #24 review fixes: hashed static names (manifest storage) so CSS/JS/audio are immutable and never stale after a deploy; prod static path tested (collectstatic, 206/416); Dockerfile no longer ignores collectstatic failures; `load_catalogue` logs and skips unreadable files; `base.html` is now the site shell only and `player/layout.html` owns the player; ADR-0002 (audio as static files); vocabulary fixes; keyboard-accessible track rows; seek on mobile; scrubbing doesn't fight timeupdate; audio error messages.
- pytest 29/29, Cypress 11/11 locally; Docker image builds.

**Decisions / why**
- Tests use plain static storage (autouse fixture); one fixture runs the real manifest + WhiteNoise path. Manifest storage can't resolve names without collectstatic, and `manifest_strict=False` doesn't help (it still hashes from disk).
- `infra/user_data.sh.tftpl` still says Redis in a comment: editing user_data would force the instance to be replaced.
- The first-request Listener race is left as is (it only creates a harmless empty orphan); documented in ADR-0001.

**Next**
- Push and merge (the slices go through #24, or a follow-up PR). The first deploy after this drops all sessions once (Redis → DB). Run `docker compose ... up -d --remove-orphans` so the old redis container goes away. The box's `deploy.sh` still needs the repo-rename patch (see HANDOFF).
- #18 playlists on branch `playlists` (unfinished, as the brief allows).
- Load test audio on the box (README "Measuring it"). This was review item 10, and can't be done locally.

## 2026-09-25 (late afternoon) — Audio measurements, box check

**Done**
- Measured audio delivery on the live site (edge from a home connection, origin on the box via SSM). Results table in README replaces the "to do" placeholder: `206`/`416` correct, `immutable` 10-year cache, MISS then HIT at the edge, origin p50 TTFB 2.5 ms under 20 concurrent range requests.
- Checked the box: `deploy.sh` has the repo rename and `curl -L`, auto-deploy runs every 2 min and is on `358b1c7`, no redis container left.
- Row-click scroll nit: not reproducible after rows became real `<button>`s (#25). Closed as fixed.

**Decisions / why**
- Measured with parallel `curl` instead of `oha`: `oha` isn't on either machine, and installing tools on the prod box just for this isn't worth it.
- The "Redis roles" item under earlier Next lists is obsolete: Redis was dropped in #23.

**Next**
- Stop the AMI's built-in ECS agent on the box (it's not used and restarts on a loop), and fix it in `user_data`/AMI choice on the Phase 2 rebuild.
- Local dev: after pulling #22, run `load_tracks` (old filenames 404) and `docker compose up -d --remove-orphans` (stale local redis).
- Submission email; #18 playlists; infra backlog (Phase 2 rebuild, GHCR, backups, Full strict TLS).

## 2026-09-25 (evening) — Multi-persona review fixes (PR on `review-fixes`)

**Done** (one commit per slice)
- Played endpoint / growth: page views no longer create a Listener or session (first write does); repeat of the latest Play within 30s dropped; history capped at 200 Plays per Listener; bad track ids 404 before a Listener exists; `prune_listeners` (clearsessions + Listeners older than `SESSION_COOKIE_AGE`) runs on each deploy; composite `(listener, -played_at)` index.
- `is_fav` only from `with_favourite_flag`. Boot `collectstatic` dropped (test guards that every extractable cover is committed). `DummyCache` instead of per-worker LocMem.
- A11y: heart keeps focus (stable id, htmx restores it), nav `aria-current="page"` + focus to the new heading, search spinner + `role=status` count.
- JS: pure Queue logic in `queue.js`, 9 `node --test` tests in CI. Cypress now covers Recently played (POST once, shows up) and cross-tab pause/broadcast; both verified by mutating the code.
- pytest 39, node 9, Cypress 16 locally.

**Decisions / why**
- No real rate limiter: no shared cache (and adding one for this is heavier than the risk). The endpoint only writes to the caller's own Listener, so forging pollutes only your own history; dedupe + cap bound the storage.
- Prune by `created_at` works because nothing re-saves the session after `get_listener`; noted in ADR-0001 to revisit with accounts.

**Next**
- Headless Electron can't decode any of the mp3s ("Couldn't load this track." on every row); check whether that's just Electron or a real-browser issue with the 48 kHz file too.
