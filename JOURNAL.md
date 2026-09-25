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
