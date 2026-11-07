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
    
    cy.get('#login-password-input').type('admin123')
    cy.get('#login-btn-el').click()
    
    cy.get('#login-overlay').should('not.be.visible')
    cy.get('.main-container', { timeout: 10000 }).should('be.visible')
  })

  it('2. يختبر قسم المنتجات وإضافة لابتوب جديد', () => {
    // تسجيل الدخول
    cy.get('#login-password-input', { timeout: 10000 }).type('admin123')
    cy.get('#login-btn-el').click()

    // الانتقال للـ Products
    cy.get('li[data-tab="products"]').click()
    cy.get('#tab-title').should('contain', 'Products')

    // فتح نافذة الإضافة وتعبئتها
    cy.contains('إضافة لابتوب جديد', { timeout: 10000 }).click()
    cy.get('#edit-product-modal').should('have.class', 'active')
    
    cy.get('#edit-title').type('لابتوب فحص تجريبي Cypress')
    cy.get('#edit-price').type('1200')
    cy.get('#edit-cost-price').type('1000')
    
    // إغلاق النافذة (لن نحفظ حتى لا نمتلئ ببيانات وهمية)
    cy.get('#close-edit-modal-btn').click()
    cy.get('#edit-product-modal').should('not.have.class', 'active')
  })

  it('3. يختبر أرشيف المواقع والتقسيط (Websites)', () => {
    // تسجيل الدخول
    cy.get('#login-password-input', { timeout: 10000 }).type('admin123')
    cy.get('#login-btn-el').click()

    cy.get('li[data-tab="websites"]').click()
    cy.get('#tab-title').should('contain', 'Websites')
    
    cy.contains('Add New Website', { timeout: 10000 }).click()
    cy.get('#website-modal').should('have.class', 'active')
    cy.get('#website-modal .close-modal').click()
  })

  it('4. يختبر استجابة السيرفر لجلب الطلبات (Orders)', () => {
    // تسجيل الدخول
    cy.get('#login-password-input', { timeout: 10000 }).type('admin123')
    cy.get('#login-btn-el').click()

    cy.get('li[data-tab="orders"]').click()

    // الانتظار حتى يقوم فايربيز بجلب الطلبات بنجاح
    cy.wait('@firebaseData', { timeout: 15000 }).its('response.statusCode').should('eq', 200)
    cy.get('#orders-table-body', { timeout: 10000 }).should('be.visible')
  })

})