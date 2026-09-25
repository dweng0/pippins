# 2. Sample audio ships in the repo as static files

Date: 2026-09-25
Status: Accepted

## Context

The brief supplies six sample mp3s (~29 MB with covers) and hints: "just keep the audio as part of the application rather than hosting it". We run on one free-tier EC2 box behind Cloudflare, with a 2-hour build budget.

Options considered:

- **Commit the files; serve them as static files (WhiteNoise, cached at the Cloudflare edge).** No extra service or cost. Repo and image grow by ~29 MB, and the catalogue is tied to what's baked into the image.
- **Object storage (S3 / Cloudflare R2) + upload pipeline + FileField.** The right shape at scale, but it needs credentials, a bucket and an upload path. S3 egress also costs money.
- **Git LFS.** Keeps history light, but CI, the box's pull-based deploy and GitHub LFS quota all need setup.

## Decision

Commit the mp3s under `player/static/player/audio/` (slug names, full ID3 tags). `load_tracks` builds `Track` rows from them on every deploy. `Track.audio_path` / `cover_path` are static paths, resolved through the static storage, so URLs are content-hashed and served `immutable`.

## Consequences

- Adding or changing a track = commit + deploy. No runtime uploads.
- Every clone and image carries the audio. Fine for six files; not for a real catalogue.
- Moving to object storage later: swap the two path fields for a `FileField` (or a URL field) and point `audio_url` / `cover_url` at the bucket. Views, templates and the player JS only use `audio_url` / `cover_url`, so nothing else changes. Prefer R2 (no egress fees).
