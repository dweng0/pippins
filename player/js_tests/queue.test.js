// Unit tests for the pure Queue logic in player/static/player/queue.js. Run: npm run test:js
const test = require("node:test");
const assert = require("node:assert/strict");
const Q = require("../static/player/queue.js");

const tracks = (n) => Array.from({ length: n }, (_, i) => ({ id: i + 1 }));
const ids = (queue) => queue.map((t) => t.id);

test("shuffle puts the current track first and keeps every track once", () => {
  const queue = tracks(6);
  const s = Q.shuffle(queue, 3);
  assert.equal(s.queue[0].id, 4);
  assert.equal(s.index, 0);
  assert.deepEqual([...ids(s.queue)].sort(), [1, 2, 3, 4, 5, 6]);
  assert.deepEqual(ids(s.original), [1, 2, 3, 4, 5, 6]);
  assert.deepEqual(ids(queue), [1, 2, 3, 4, 5, 6], "input not mutated");
});

test("shuffle uses the random source (Fisher-Yates over the rest)", () => {
  const s = Q.shuffle(tracks(4), 0, () => 0); // always swap with the first of the rest
  assert.deepEqual(ids(s.queue), [1, 3, 4, 2]);
});

test("shuffle with nothing playing has no current track", () => {
  const s = Q.shuffle(tracks(3), -1, () => 0);
  assert.equal(s.index, -1);
  assert.equal(s.queue.length, 3);
});

test("unshuffle restores the original order and stays on the same track", () => {
  const s = Q.shuffle(tracks(5), 2);
  const u = Q.unshuffle(s.original, 3);
  assert.deepEqual(ids(u.queue), [1, 2, 3, 4, 5]);
  assert.equal(u.index, 2);
});

test("next stops at the end of the Queue (no repeat)", () => {
  assert.equal(Q.nextIndex(0, 3), 1);
  assert.equal(Q.nextIndex(2, 3), -1);
  assert.equal(Q.nextIndex(-1, 0), -1);
});

test("previous restarts after 3s or on the first track, otherwise goes back", () => {
  assert.equal(Q.prevRestarts(2, 3.5), true);
  assert.equal(Q.prevRestarts(0, 1), true);
  assert.equal(Q.prevRestarts(2, 1), false);
});

test("parseSaved rejects missing or corrupt state", () => {
  for (const raw of [null, "", "not json", "{}", '{"queue": "nope"}', "42"]) {
    assert.equal(Q.parseSaved(raw), null, raw);
  }
});

test("parseSaved keeps good state and clamps bad values", () => {
  const raw = JSON.stringify({ queue: tracks(2), index: 1, position: 12.5, volume: 0.3, shuffled: 1, unshuffledQueue: tracks(2) });
  assert.deepEqual(Q.parseSaved(raw), {
    queue: tracks(2),
    index: 1,
    position: 12.5,
    volume: 0.3,
    shuffled: true,
    unshuffledQueue: tracks(2),
  });

  const bad = Q.parseSaved(JSON.stringify({ queue: tracks(2), index: 7, position: -4, volume: 9, unshuffledQueue: "x" }));
  assert.equal(bad.index, -1);
  assert.equal(bad.position, 0);
  assert.equal(bad.volume, 1);
  assert.equal(bad.shuffled, false);
  assert.deepEqual(bad.unshuffledQueue, []);
  assert.equal(Q.parseSaved(JSON.stringify({ queue: [] })).volume, null);
});

test("formatTime renders m:ss", () => {
  assert.equal(Q.formatTime(132.4), "2:12");
  assert.equal(Q.formatTime(59), "0:59");
  assert.equal(Q.formatTime(undefined), "0:00");
});
