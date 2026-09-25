describe("Player", () => {
  const titleOfRow = (i) =>
    cy.get('[data-cy="track-row"]').eq(i).find('[data-cy="track-title"]').invoke("text").then((t) => t.trim());

  beforeEach(() => {
    cy.visit("/");
  });

  it("lists the sample tracks", () => {
    cy.get('[data-cy="list-title"]').should("contain", "All tracks");
    cy.get('[data-cy="track-row"]').should("have.length", 6);
    cy.get('[data-cy="now-playing-title"]').should("contain", "Pick a track");
  });

  it("selecting a track shows it as now playing and loads its audio", () => {
    titleOfRow(1).then((title) => {
      cy.get('[data-cy="track-row"]').eq(1).click();
      cy.get('[data-cy="now-playing-title"]').should("have.text", title);
      cy.get('[data-cy="player"] audio')
        .should("have.attr", "src")
        .and("match", /\/static\/player\/audio\/.+\.mp3$/);
    });
  });

  it("next and previous step through the queue", () => {
    cy.get('[data-cy="track-row"]').eq(0).click();
    titleOfRow(1).then((second) => {
      cy.get('[data-cy="next"]').click();
      cy.get('[data-cy="now-playing-title"]').should("have.text", second);
    });
    titleOfRow(0).then((first) => {
      cy.get('[data-cy="prev"]').click();
      cy.get('[data-cy="now-playing-title"]').should("have.text", first);
    });
  });

  it("hearting a track adds it to Favourites without starting playback", () => {
    titleOfRow(2).then((title) => {
      cy.get('[data-cy="track-row"]').eq(2).find('[data-cy="fav"]').click();
      cy.get('[data-cy="track-row"]').eq(2).find('[data-cy="fav"]').should("have.attr", "data-fav", "true");
      cy.get('[data-cy="now-playing-title"]').should("contain", "Pick a track");
      cy.get('[data-cy="nav-favourites"]').click();
      cy.location("pathname").should("eq", "/favourites/");
      cy.get('[data-cy="list-title"]').should("contain", "Favourites");
      cy.get('[data-cy="track-row"]').should("have.length", 1).and("contain", title);
    });
  });

  it("search filters the list and the Queue follows it", () => {
    cy.get('[data-cy="search"]').type("komiku");
    cy.get('[data-cy="track-row"]').should("have.length", 2);
    cy.location("search").should("eq", "?q=komiku");
    cy.get('[data-cy="track-row"]').eq(1).click();
    cy.get('[data-cy="next"]').click(); // last of the filtered Queue: stays put
    cy.get('[data-cy="now-playing-artist"]').should("have.text", "Komiku");
  });

  it("shuffle keeps the current track first and unshuffle restores the order", () => {
    cy.get('[data-cy="track-row"]').eq(3).click();
    cy.window().then((win) => {
      const store = win.Alpine.store("player");
      const original = store.queue.map((t) => t.id);
      const current = store.currentId;
      cy.get('[data-cy="shuffle"]').click().should("have.attr", "aria-pressed", "true");
      cy.wrap(null).then(() => {
        expect(store.queue[0].id).to.eq(current);
        expect(store.currentId).to.eq(current);
        expect([...store.queue.map((t) => t.id)].sort()).to.deep.eq([...original].sort());
      });
      cy.get('[data-cy="shuffle"]').click().should("have.attr", "aria-pressed", "false");
      cy.wrap(null).then(() => {
        expect(store.queue.map((t) => t.id)).to.deep.eq(original);
        expect(store.currentId).to.eq(current);
      });
    });
  });

  it("remembers the track, Queue and volume across reloads (restored paused)", () => {
    titleOfRow(4).then((title) => {
      cy.get('[data-cy="track-row"]').eq(4).click();
      cy.get('[data-cy="volume"]').invoke("val", 0.3).trigger("input");
      cy.reload();
      cy.get('[data-cy="now-playing-title"]').should("have.text", title);
      cy.get('[data-cy="volume"]').should("have.value", "0.3");
      cy.get('[data-cy="player"] audio').should("have.prop", "paused", true);
      cy.window().its("Alpine").invoke("store", "player").its("queue").should("have.length", 6);
    });
  });

  it("track rows are real buttons that report the current track", () => {
    cy.get('[data-cy="track-play"]').should("have.length", 6).first().should("match", "button");
    cy.get('[data-cy="track-play"]').eq(2).focus().click();
    cy.get('[data-cy="track-play"]').eq(2).should("have.attr", "aria-current", "true");
    cy.get('[data-cy="track-play"]').eq(0).should("have.attr", "aria-current", "false");
  });

  it("a track that fails to load shows an error instead of failing silently", () => {
    cy.window().then((win) => {
      win.Alpine.store("player").playFrom(
        [{ id: 999, title: "Missing", artist: "Nobody", src: "/static/player/audio/nope.mp3", cover: "", playedUrl: "/tracks/999/played/" }],
        999,
      );
    });
    cy.get('[data-cy="player-error"]').should("be.visible").and("contain", "Couldn't load this track.");
  });

  it("playing a track reports it once and it shows up in Recently played", () => {
    cy.intercept("POST", "/tracks/*/played/").as("played");
    titleOfRow(3).then((title) => {
      cy.get('[data-cy="track-row"]').eq(3).find('[data-cy="track-play"]').click();
      cy.wait("@played").its("response.statusCode").should("eq", 204);
      cy.get('[data-cy="nav-recent"]').click();
      cy.location("pathname").should("eq", "/recent/");
      cy.get('[data-cy="track-row"]').should("have.length", 1).and("contain", title);
    });
    cy.get("@played.all").should("have.length", 1);
  });

  // Headless Electron can't decode the audio, so drive the <audio> element's events directly.
  it("starting playback in another tab pauses this one, and this tab tells the others", () => {
    cy.get('[data-cy="track-play"]').eq(0).click();
    cy.get('[data-cy="player"] audio').then(([audio]) => {
      const win = audio.ownerDocument.defaultView;
      const otherTab = new win.BroadcastChannel("pippins-player");
      const heard = [];
      otherTab.onmessage = (e) => heard.push(e.data);

      audio.dispatchEvent(new win.Event("play"));
      cy.wrap(heard).should("deep.include", { type: "playing" });

      Object.defineProperty(audio, "paused", { configurable: true, get: () => false });
      const pause = cy.stub(audio, "pause");
      cy.wrap(null).then(() => otherTab.postMessage({ type: "playing" }));
      cy.wrap(pause).should("have.been.calledOnce");
      cy.wrap(null).then(() => otherTab.close());
    });
  });

  it("nav marks the current page and moves focus to the new list's heading", () => {
    cy.get('[data-cy="nav-all"]').should("have.attr", "aria-current", "page");
    cy.get('[data-cy="nav-favourites"]').click();
    cy.get('[data-cy="list-title"]').should("contain", "Favourites").and("have.focus");
    cy.get('[data-cy="nav-favourites"]').should("have.attr", "aria-current", "page");
    cy.get('[data-cy="nav-all"]').should("not.have.attr", "aria-current");
  });

  it("hearting keeps keyboard focus on the heart", () => {
    cy.get('[data-cy="fav"]').eq(1).focus().type("{enter}");
    cy.get('[data-cy="fav"]').eq(1).should("have.attr", "data-fav", "true");
    cy.focused().should("have.attr", "data-cy", "fav").and("have.attr", "data-fav", "true");
  });

  it("search announces the new result count", () => {
    cy.get('[data-cy="search"]').type("komiku");
    cy.get('[data-cy="list-status"]').should("have.attr", "role", "status").and("have.text", "2 tracks");
  });

  it("seek and volume are available on a phone-sized screen", () => {
    cy.viewport("iphone-x");
    cy.get('[data-cy="seek"]').should("be.visible");
    cy.get('[data-cy="volume-mobile"]').should("be.visible");
  });
});

describe("Health check", () => {
  it("reports DB as ok", () => {
    cy.request("/healthz/").then((res) => {
      expect(res.status).to.eq(200);
      expect(res.body.status).to.eq("ok");
      expect(res.body.checks.database).to.eq("ok");
    });
  });
});
