# 1. A Listener model owns all per-person state

Date: 2026-09-25
Status: Accepted

## Context

The brief has no accounts, but asks for per-person features (favourites, playlists, recently played, "remember session information"). Accounts may be added later.

Options considered:

- **Key every table on `session_key`.** Fastest now; adding accounts later means reworking every per-person table.
- **Nullable `user` + `session_key` on every table.** Accounts work later, but every query needs "user OR session" logic.
- **A `Listener` model as the single owner.** One extra table now.

## Decision

A `Listener` is created on first visit; its id is stored in the Django session. Favourites, playlists and play history reference `Listener`, never the session or a user directly. Views obtain it via one service function (`get_listener(request)`).

## Consequences

- Adding accounts later = add a nullable `user` FK to `Listener` and attach/merge on login. Per-person tables are untouched.
- An anonymous Listener is lost when their session expires or cookies are cleared (orphaned rows). Acceptable until accounts exist.
- Two simultaneous first requests from a new browser can each create a Listener; the session keeps the last, the other is an empty orphan. Harmless (no per-person rows yet), so no locking.
- Sessions must survive deploys, so they live in Postgres (#23), not an unpersisted Redis.
- Device-level state (playback position, volume) stays in the browser, not on `Listener`.
