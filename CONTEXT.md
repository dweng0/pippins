# StackCX Music Player

A web music player (Spotify-like) that plays a small fixed catalogue of sample tracks to anonymous listeners.

## Language

**Listener**:
The person using the player; the single owner of all per-person state. Anonymous until accounts exist.
_Avoid_: User, account, session (a session is how a Listener is recognised, not the Listener itself)

**Track**:
One playable song in the catalogue, with a title, artist, album and cover.
_Avoid_: Song, file, audio

**Queue**:
The ordered Tracks the player steps through, set from the list a Listener started playing from. Browsing other lists does not change it.
_Avoid_: Playlist (a Playlist is saved; the Queue is transient), play context

**Favourite**:
A Track a Listener has marked to keep.
_Avoid_: Like, saved track
