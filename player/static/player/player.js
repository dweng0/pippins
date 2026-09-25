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

    get current() {
      return this.queue[this.index] || null;
    },
    get currentId() {
      return this.current ? this.current.id : null;
    },

    bind(audio) {
      this.audio = audio;
      audio.volume = this.volume;
      audio.addEventListener("play", () => (this.playing = true));
      audio.addEventListener("pause", () => (this.playing = false));
      audio.addEventListener("ended", () => this.next());
      audio.addEventListener("timeupdate", () => (this.currentTime = audio.currentTime));
      audio.addEventListener("loadedmetadata", () => (this.duration = audio.duration));
    },

    // Clicking a track snapshots the list it was in as the Queue; later browsing doesn't change it.
    playFrom(list, id) {
      this.queue = list.slice();
      this.load(this.queue.findIndex((t) => t.id === id), true);
    },

    load(i, autoplay) {
      if (i < 0 || i >= this.queue.length) return;
      this.index = i;
      this.currentTime = 0;
      this.duration = this.current.duration || 0;
      this.audio.src = this.current.src;
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

    seek(seconds) {
      this.audio.currentTime = Number(seconds);
    },

    setVolume(v) {
      this.volume = Number(v);
      this.audio.volume = this.volume;
    },

    fmt(seconds) {
      const s = Math.floor(seconds || 0);
      return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
    },
  });
});

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
