describe("Task list", () => {
  it("loads the page", () => {
    cy.visit("/");
    cy.contains("h1", "Tasks");
  });

  it("adds a task and shows it in the list", () => {
    const title = `Cypress task ${Date.now()}`;

    cy.visit("/");
    cy.get('[data-cy="task-input"]').type(title);
    cy.get('[data-cy="task-submit"]').click();

    cy.get('[data-cy="task-list"]').should("contain", title);
  });

  it("rejects a blank task with a validation error", () => {
    cy.visit("/");
    cy.get('[data-cy="task-input"]').type("   ");
    cy.get('[data-cy="task-submit"]').click();

    cy.get('[data-cy="task-error"]').should("be.visible");
  });
});

describe("Health check", () => {
  it("reports DB and cache as ok", () => {
    cy.request("/healthz/").then((res) => {
      expect(res.status).to.eq(200);
      expect(res.body.status).to.eq("ok");
      expect(res.body.checks.database).to.eq("ok");
      expect(res.body.checks.cache).to.eq("ok");
    });
  });
});
