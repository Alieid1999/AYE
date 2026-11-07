describe('الفحص الشامل لمتجر AYE (واجهة الزبائن)', () => {

  function addFirstAvailableProductToCart(searchForProduct = false) {
    cy.get('.product-card', { timeout: 15000 })
      .should('have.length.greaterThan', 0)
      .first()
      .find('.product-title')
      .invoke('text')
      .then((title) => {
        const productTitle = title.trim()
        expect(productTitle).not.to.be.empty

        if (searchForProduct) {
          cy.get('#search-input').clear().type(productTitle)
        }

        return cy.get('.product-card', { timeout: 15000 })
          .first()
          .find('.add-to-cart-btn')
          .should('be.enabled')
          .click({ force: true })
      })
  }
  
  beforeEach(() => {
    cy.intercept('POST', 'https://firestore.googleapis.com/**').as('firebaseRequest')
    cy.visit('http://127.0.0.1:5500/index.html', {
      onBeforeLoad(window) {
        window.localStorage.removeItem('store_cart')
      },
    })

    // 1. ننتظر اتصال قاعدة البيانات
    cy.wait('@firebaseRequest', { timeout: 15000 })
    
    // 2. ننتظر حتى تختفي صناديق التحميل الرمادية (دليل على ظهور المنتجات الحقيقية)
    cy.get('.skeleton-card', { timeout: 15000 }).should('not.exist')
  })

  it('1. يتأكد من تحميل الموقع الأساسي واتصال Firebase', () => {
    cy.contains('ITech').should('be.visible')
  })

  it('2. يختبر مربع البحث وإضافة منتج إلى السلة', () => {
    addFirstAvailableProductToCart(true)
    
    // التأكد من أن العداد الرقمي للسلة أصبح 1
    cy.get('#cart-badge').should('contain', '1').and('be.visible')
  })

  it('3. يختبر فتح السلة وتعبئة نموذج إتمام الطلب (Checkout)', () => {
    // إضافة منتج للسلة
    addFirstAvailableProductToCart()
    
    // فتح سلة المشتريات
    cy.get('#open-cart-btn').click()
    cy.get('#cart-modal').should('have.class', 'active')
    
    // تعبئة بيانات الزبون
    cy.get('#cust-name').type('علي عيد')
    cy.get('#cust-address').type('بيروت، لبنان - شارع المتجر')
    cy.get('#submit-order-btn').should('not.be.disabled').and('be.visible')
  })

  it('4. يختبر نافذة تصميم المواقع وحاسبة الأقساط', () => {
    cy.get('#open-web-services-btn').click()
    cy.get('#web-services-modal').should('have.class', 'active')
    
    cy.get('#user-web-type').select('550')
    cy.get('#user-web-plan').select('6')
    cy.get('#public-calc-total').should('not.be.empty')
  })

})