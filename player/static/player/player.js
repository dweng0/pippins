// Device-level state (Queue, position, volume) lives in localStorage, not on the Listener (ADR-0001).
// Bump the key if the stored shape changes.
const STORAGE_KEY = "pippins.player.v1";

function readSaved() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY));
  } catch {
    return null; // storage disabled (private mode) or corrupt: start fresh
  }
}

function writeSaved(state) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // quota / disabled storage: persistence is best effort
  }
}

// Global player store: owns the single <audio> element and the Queue (see CONTEXT.md).
// Loaded before Alpine so the store exists when Alpine initialises.
document.addEventListener("alpine:init", () => {
  Alpine.store("player", {
    audio: null,
    queue: [],
    index: -1,
    playing: false,
    currentTime: 0,
    duration: 0,
    volume: 0.8,
    playReported: false,
    shuffled: false,
    unshuffledQueue: [],
    lastSavedAt: 0,

    get current() {
      return this.queue[this.index] || null;
    },
    get currentId() {
      return this.current ? this.current.id : null;
    },

    bind(audio) {
      this.audio = audio;
      audio.volume = this.volume;
      audio.addEventListener("play", () => {
        this.playing = true;
        this.reportPlay();
      });
      audio.addEventListener("pause", () => {
        this.playing = false;
        this.save();
      });
      audio.addEventListener("ended", () => this.next());
      audio.addEventListener("timeupdate", () => {
        this.currentTime = audio.currentTime;
        if (Date.now() - this.lastSavedAt > 2000) this.save();
      });
      audio.addEventListener("loadedmetadata", () => (this.duration = audio.duration));
      window.addEventListener("pagehide", () => this.save());
      this.bindMediaSession();
      this.restore();
    },

    // OS lock screen / notification metadata and hardware media keys.
    bindMediaSession() {
      if (!("mediaSession" in navigator)) return;
      const handlers = {
        play: () => this.play(),
        pause: () => this.audio.pause(),
        previoustrack: () => this.prev(),
        nexttrack: () => this.next(),
        seekto: (e) => this.seek(e.seekTime),
      };
      for (const [action, handler] of Object.entries(handlers)) {
        try {
          navigator.mediaSession.setActionHandler(action, handler);
        } catch {
          // action not supported by this browser
        }
      }
    },

    updateMediaSession() {
      if (!("mediaSession" in navigator) || !this.current) return;
      const t = this.current;
      navigator.mediaSession.metadata = new MediaMetadata({
        title: t.title,
        artist: t.artist,
        album: t.album,
        artwork: [{ src: new URL(t.cover, location.href).href, sizes: "512x512" }],
      });
    },

    save() {
      this.lastSavedAt = Date.now();
      writeSaved({
        queue: this.queue,
        index: this.index,
        position: this.audio ? this.audio.currentTime : 0,
        volume: this.volume,
        shuffled: this.shuffled,
        unshuffledQueue: this.unshuffledQueue,
      });
    },

    // Restores paused: browsers block autoplay without a user gesture.
    restore() {
      const s = readSaved();
      if (!s || !Array.isArray(s.queue)) return;
      if (typeof s.volume === "number") this.setVolume(s.volume);
      this.shuffled = !!s.shuffled;
      this.unshuffledQueue = Array.isArray(s.unshuffledQueue) ? s.unshuffledQueue : [];
      this.queue = s.queue;
      if (!this.queue[s.index]) return;
      this.load(s.index, false);
      const position = Number(s.position) || 0;
      if (position > 0) {
        this.currentTime = position;
        this.audio.addEventListener("loadedmetadata", () => (this.audio.currentTime = position), { once: true });
      }
    },

    // Clicking a track snapshots the list it was in as the Queue; later browsing doesn't change it.
    playFrom(list, id) {
      this.queue = list.slice();
      this.index = this.queue.findIndex((t) => t.id === id);
      if (this.shuffled) this.shuffle();
      this.load(this.index, true);
    },

    // Shuffle reorders the Queue with the current track first; unshuffle restores the original order.
    toggleShuffle() {
      this.shuffled = !this.shuffled;
      if (this.shuffled) this.shuffle();
      else this.unshuffle();
      this.save();
    },

    shuffle() {
      this.unshuffledQueue = this.queue.slice();
      const rest = this.queue.filter((_, i) => i !== this.index);
      for (let i = rest.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [rest[i], rest[j]] = [rest[j], rest[i]];
      }
      const current = this.queue[this.index];
      this.queue = current ? [current, ...rest] : rest;
      this.index = current ? 0 : -1;
    },

    unshuffle() {
      if (!this.unshuffledQueue.length) return;
      const id = this.currentId;
      this.queue = this.unshuffledQueue;
      this.unshuffledQueue = [];
      this.index = this.queue.findIndex((t) => t.id === id);
    },

    load(i, autoplay) {
      if (i < 0 || i >= this.queue.length) return;
      this.index = i;
      this.currentTime = 0;
      this.playReported = false;
      this.duration = this.current.duration || 0;
      this.audio.src = this.current.src;
      this.updateMediaSession();
      this.save();
      if (autoplay) this.play();
    },

    play() {
      this.audio.play().catch(() => (this.playing = false));
    },

    toggle() {
      if (!this.current) {
        const el = document.getElementById("list-data");
        const list = el ? JSON.parse(el.textContent) : [];
        if (list.length) this.playFrom(list, list[0].id);
        return;
      }
      this.audio.paused ? this.play() : this.audio.pause();
    },

    // End of Queue stops playback (no repeat).
    next() {
      if (this.index < this.queue.length - 1) this.load(this.index + 1, true);
      else this.audio.pause();
    },

    // Like most players: after 3s, "previous" restarts the current track.
    prev() {
      if (!this.current) return;
      if (this.audio.currentTime > 3 || this.index === 0) this.audio.currentTime = 0;
      else this.load(this.index - 1, true);
    },

    // Once per loaded track, on first actual playback: feeds Recently played (fire and forget).
    reportPlay() {
      if (this.playReported || !this.current) return;
      this.playReported = true;
      fetch(this.current.playedUrl, { method: "POST", headers: { "X-CSRFToken": csrfToken() } }).catch(() => {});
    },

    seek(seconds) {
      this.audio.currentTime = Number(seconds);
    },

    setVolume(v) {
      this.volume = Number(v);
      if (this.audio) this.audio.volume = this.volume;
      this.save();
    },

    fmt(seconds) {
      const s = Math.floor(seconds || 0);
      return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
    },
  });
});

function csrfToken() {
  try {
    return JSON.parse(document.body.getAttribute("hx-headers"))["X-CSRFToken"];
  } catch {
    return "";
  }
}

// The sidebar isn't re-rendered by htmx nav, so its highlight follows the URL here.
function markActiveNav() {
  document.querySelectorAll("[data-nav]").forEach((a) => {
    const active = a.pathname === location.pathname;
    a.classList.toggle("menu-active", active);
    a.classList.toggle("btn-active", active);
  });
}
document.addEventListener("DOMContentLoaded", markActiveNav);
document.addEventListener("htmx:pushedIntoHistory", markActiveNav);
document.addEventListener("htmx:historyRestore", markActiveNav);
