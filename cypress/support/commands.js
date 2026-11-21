// ***********************************************
// Custom Cypress Commands
// ***********************************************

Cypress.Commands.add('loginAdmin', (password = 'admin123') => {
  cy.get('body').then(($body) => {
    if ($body.find('#login-overlay').is(':visible')) {
      cy.get('#login-password-input').type(password, { force: true });
      cy.get('#login-btn-el').click({ force: true });
      cy.get('#login-overlay', { timeout: 10000 }).should('not.be.visible');
    }
  });
});
