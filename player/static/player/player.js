// Device-level state (Queue, position, volume) lives in localStorage, not on the Listener (ADR-0001).
// Bump the key if the stored shape changes.
const STORAGE_KEY = "pippins.player.v1";

function readSaved() {
  try {
    return PlayerQueue.parseSaved(localStorage.getItem(STORAGE_KEY));
  } catch {
    return null; // storage disabled (private mode): start fresh
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
// Queue rules live in queue.js (unit-tested); this is the wiring to <audio>, storage and other tabs.
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
    channel: null,
    scrubbing: false,
    scrubTime: 0,
    error: "",

    get current() {
      return this.queue[this.index] || null;
    },
    get shownTime() {
      return this.scrubbing ? this.scrubTime : this.currentTime;
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
        if (this.channel) this.channel.postMessage({ type: "playing" });
      });
      audio.addEventListener("pause", () => {
        this.playing = false;
        this.save();
      });
      audio.addEventListener("ended", () => this.next());
      audio.addEventListener("playing", () => (this.error = ""));
      audio.addEventListener("error", () => {
        if (!this.current) return;
        this.playing = false;
        this.error = "Couldn't load this track.";
      });
      audio.addEventListener("timeupdate", () => {
        this.currentTime = audio.currentTime;
        if (Date.now() - this.lastSavedAt > 2000) this.save();
      });
      audio.addEventListener("loadedmetadata", () => (this.duration = audio.duration));
      window.addEventListener("pagehide", () => this.save());
      this.bindMediaSession();
      this.bindOtherTabs();
      this.restore();
    },

    // Same browser, several tabs: starting playback in one pauses the others.
    bindOtherTabs() {
      if (!("BroadcastChannel" in window)) return;
      this.channel = new BroadcastChannel("pippins-player");
      this.channel.onmessage = (e) => {
        if (e.data && e.data.type === "playing" && !this.audio.paused) this.audio.pause();
      };
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
      if (!s) return;
      if (s.volume !== null) this.audio.volume = this.volume = s.volume; // not setVolume: it would save a half-restored state
      this.shuffled = s.shuffled;
      this.unshuffledQueue = s.unshuffledQueue;
      this.queue = s.queue;
      if (s.index < 0) return;
      this.load(s.index, false);
      if (s.position > 0) {
        this.currentTime = s.position;
        this.audio.addEventListener("loadedmetadata", () => (this.audio.currentTime = s.position), { once: true });
      }
    },

    // Clicking a track snapshots the list it was in as the Queue; later browsing doesn't change it.
    playFrom(list, id) {
      this.queue = list.slice();
      this.index = this.queue.findIndex((t) => t.id === id);
      if (this.shuffled) this.shuffle();
      this.load(this.index, true);
    },

    toggleShuffle() {
      this.shuffled = !this.shuffled;
      if (this.shuffled) this.shuffle();
      else this.unshuffle();
      this.save();
    },

    shuffle() {
      const s = PlayerQueue.shuffle(this.queue, this.index);
      this.queue = s.queue;
      this.index = s.index;
      this.unshuffledQueue = s.original;
    },

    unshuffle() {
      if (!this.unshuffledQueue.length) return;
      const u = PlayerQueue.unshuffle(this.unshuffledQueue, this.currentId);
      this.queue = u.queue;
      this.index = u.index;
      this.unshuffledQueue = [];
    },

    load(i, autoplay) {
      if (i < 0 || i >= this.queue.length) return;
      this.index = i;
      this.currentTime = 0;
      this.playReported = false;
      this.error = "";
      this.duration = this.current.duration || 0;
      this.audio.src = this.current.src;
      this.updateMediaSession();
      this.save();
      if (autoplay) this.play();
    },

    play() {
      this.audio.play().catch((err) => {
        this.playing = false;
        if (err.name === "NotAllowedError") this.error = "Press play to start."; // autoplay blocked
        else if (err.name === "NotSupportedError") this.error = "Couldn't load this track."; // 404 / bad file
        else if (err.name !== "AbortError") this.error = "Playback failed."; // AbortError: src changed mid-start
      });
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

    next() {
      const i = PlayerQueue.nextIndex(this.index, this.queue.length);
      if (i >= 0) this.load(i, true);
      else this.audio.pause();
    },

    prev() {
      if (!this.current) return;
      if (PlayerQueue.prevRestarts(this.index, this.audio.currentTime)) this.audio.currentTime = 0;
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

    scrub(seconds) {
      this.scrubbing = true;
      this.scrubTime = Number(seconds);
    },

    endScrub(seconds) {
      this.seek(seconds);
      this.currentTime = Number(seconds);
      this.scrubbing = false;
    },

    setVolume(v) {
      this.volume = Number(v);
      if (this.audio) this.audio.volume = this.volume;
      this.save();
    },

    fmt(seconds) {
      return PlayerQueue.formatTime(seconds);
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

// The sidebar isn't re-rendered by htmx nav, so its highlight (and aria-current) follows the URL here.
function markActiveNav() {
  document.querySelectorAll("[data-nav]").forEach((a) => {
    const active = a.pathname === location.pathname;
    a.classList.toggle("menu-active", active);
    a.classList.toggle("btn-active", active);
    if (active) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  });
}
document.addEventListener("DOMContentLoaded", markActiveNav);
document.addEventListener("htmx:pushedIntoHistory", markActiveNav);
document.addEventListener("htmx:historyRestore", markActiveNav);

document.addEventListener("htmx:afterSettle", (e) => {
  const target = e.detail.target;
  // Nav swapped #main: without this, focus stays on the nav link and nothing says the page changed.
  if (target.id === "main") {
    const heading = target.querySelector('[data-cy="list-title"]');
    if (heading) heading.focus({ preventScroll: true });
  }
  // Search swapped the rows: announce the new count ("2 tracks").
  if (target.id === "track-rows") {
    const status = document.getElementById("list-status");
    const count = target.querySelector('[data-cy="track-count"]');
    if (status && count) status.textContent = count.textContent;
  }
});
