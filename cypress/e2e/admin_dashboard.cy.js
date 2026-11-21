describe('فحص لوحة تحكم الإدارة (الموظفين والمنتجات)', () => {
  
  beforeEach(() => {
    // مراقبة اتصال Firebase في الخلفية
    cy.intercept('POST', 'https://firestore.googleapis.com/**').as('firebaseData')
    
    // فتح صفحة لوحة التحكم
    cy.visit('http://127.0.0.1:5500/store_dashboard.html')
  })

  it('1. يختبر نظام حماية الدخول (Admin Login)', () => {
    // إعطاء مهلة لظهور شاشة الدخول
    cy.get('#login-overlay', { timeout: 10000 }).should('be.visible')
    
    cy.get('#login-password-input').type('admin123', { force: true })
    cy.get('#login-btn-el').click({ force: true })
    
    cy.get('#login-overlay').should('not.be.visible')
    cy.get('.main-container', { timeout: 10000 }).should('be.visible')
  })

  it('2. يختبر قسم المنتجات وإضافة لابتوب جديد', () => {
    // تسجيل الدخول
    cy.get('#login-password-input', { timeout: 10000 }).type('admin123', { force: true })
    cy.get('#login-btn-el').click({ force: true })
    cy.get('#login-overlay').should('not.be.visible')

    // الانتقال للـ Products
    cy.get('li[data-tab="products"]').click({ force: true })
    cy.get('#tab-title').should('contain', 'Products')

    // فتح نافذة الإضافة وتعبئتها
    cy.contains('إضافة لابتوب جديد', { timeout: 10000 }).click({ force: true })
    cy.get('#edit-product-modal').should('have.class', 'active')
    
    cy.get('#edit-title').type('لابتوب فحص تجريبي Cypress', { force: true })
    cy.get('#edit-price').type('1200', { force: true })
    cy.get('#edit-cost-price').type('1000', { force: true })
    
    // إغلاق النافذة
    cy.get('#close-edit-modal-btn').click({ force: true })
    cy.get('#edit-product-modal').should('not.have.class', 'active')
  })

  it('3. يختبر قسم الموردين (Suppliers) وقسم التحليلات (Analytics)', () => {
    // تسجيل الدخول
    cy.get('#login-password-input', { timeout: 10000 }).type('admin123', { force: true })
    cy.get('#login-btn-el').click({ force: true })
    cy.get('#login-overlay').should('not.be.visible')

    cy.get('li[data-tab="suppliers"]').click({ force: true })
    cy.get('#tab-title').should('contain', 'Suppliers')
    
    cy.get('li[data-tab="analytics"]').click({ force: true })
    cy.get('#tab-title').should('contain', 'Analytics')
    cy.get('#sales-chart').should('exist')
  })

  it('4. يختبر استجابة السيرفر لجلب الطلبات (Orders)', () => {
    // تسجيل الدخول
    cy.get('#login-password-input', { timeout: 10000 }).type('admin123', { force: true })
    cy.get('#login-btn-el').click({ force: true })
    cy.get('#login-overlay').should('not.be.visible')

    cy.get('li[data-tab="orders"]').click({ force: true })
    cy.get('#orders-table-body', { timeout: 10000 }).should('exist')
  })

})
