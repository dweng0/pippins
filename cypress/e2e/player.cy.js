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
