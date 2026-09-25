// Pure Queue and saved-state logic: no DOM, no Alpine, so it runs under `npm run test:js`
// (player/js_tests/). The store in player.js keeps only the wiring to <audio> and the page.
// Loaded before player.js as a classic script (window.PlayerQueue); require()-able from Node.
(function (root) {
  // Shuffle keeps the current track first so playback doesn't jump; `original` is kept for unshuffle.
  function shuffle(queue, index, random = Math.random) {
    const current = queue[index];
    const rest = queue.filter((_, i) => i !== index);
    for (let i = rest.length - 1; i > 0; i--) {
      const j = Math.floor(random() * (i + 1));
      [rest[i], rest[j]] = [rest[j], rest[i]];
    }
    return { queue: current ? [current, ...rest] : rest, index: current ? 0 : -1, original: queue.slice() };
  }

  // Back to the original order, still on the same track.
  function unshuffle(original, currentId) {
    return { queue: original, index: original.findIndex((t) => t.id === currentId) };
  }

  // End of Queue is -1: playback stops (no repeat).
  function nextIndex(index, length) {
    return index < length - 1 ? index + 1 : -1;
  }

  // Like most players: after 3s, or on the first track, "previous" restarts the current track.
  function prevRestarts(index, currentTime) {
    return currentTime > 3 || index === 0;
  }

  // Whatever came out of localStorage: malformed means start fresh, out-of-range values are clamped.
  function parseSaved(raw) {
    let s;
    try {
      s = JSON.parse(raw);
    } catch {
      return null;
    }
    if (!s || !Array.isArray(s.queue)) return null;
    return {
      queue: s.queue,
      index: Number.isInteger(s.index) && s.queue[s.index] ? s.index : -1,
      position: Math.max(0, Number(s.position) || 0),
      volume: typeof s.volume === "number" ? Math.min(1, Math.max(0, s.volume)) : null,
      shuffled: !!s.shuffled,
      unshuffledQueue: Array.isArray(s.unshuffledQueue) ? s.unshuffledQueue : [],
    };
  }

  function formatTime(seconds) {
    const s = Math.floor(seconds || 0);
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  }

  const api = { shuffle, unshuffle, nextIndex, prevRestarts, parseSaved, formatTime };
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.PlayerQueue = api;
})(this);
