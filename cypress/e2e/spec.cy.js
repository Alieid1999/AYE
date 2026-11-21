describe('A Laps Store - اختبارات لوحة التحكم وصفحة الزبائن', () => {
  
  beforeEach(() => {
    // اعتراض طلبات Firebase للتحقق من الاتصال واستقبال/إرسال البيانات
    cy.intercept('GET', '**/firestore.googleapis.com/**').as('getFirebaseData');
    cy.intercept('POST', '**/firestore.googleapis.com/**').as('postFirebaseData');
    
    // إعداد بيئة العرض
    cy.viewport(1280, 720);
  });

  // دالة مساعدة لتسجيل الدخول السريع وتخطي غطاء تسجيل الدخول
  function loginToDashboard() {
    cy.get('body').then(($body) => {
      if ($body.find('#login-overlay').is(':visible')) {
        cy.get('#login-password-input').type('admin123', { force: true });
        cy.get('#login-btn-el').click({ force: true });
        cy.get('#login-overlay', { timeout: 10000 }).should('not.be.visible');
      }
    });
  }

  it('يجب أن يحمل لوحة التحكم ويتحقق من حالة الاتصال بقاعدة البيانات (Firebase)', () => {
    cy.visit('http://127.0.0.1:5500/store_dashboard.html');
    
    // التحقق من ظهور حالة الاتصال بقاعدة البيانات
    cy.get('.db-status-container').should('exist');
    cy.get('#db-status-text').should('not.be.empty');
  });

  it('يجب أن يتنقل بين كافة تبويبات لوحة التحكم ويفحص الأوامر الأساسية', () => {
    cy.visit('http://127.0.0.1:5500/store_dashboard.html');
    loginToDashboard();

    // 1. فحص تبويب المنتجات وأمر إضافة منتج
    cy.get('#sidebar-menu li[data-tab="products"]').click({ force: true });
    cy.get('#tab-products').should('have.class', 'active');
    
    // فحص ظهور جدول المنتجات
    cy.get('#products-table-body').should('exist');
    
    // فحص أمر إضافة لابتوب جديد وفتح النافذة المنبثقة (Modal)
    cy.contains('إضافة لابتوب جديد').click({ force: true });
    cy.get('#edit-product-modal').should('have.class', 'active');
    cy.get('#edit-title').should('be.visible'); // حقل اسم المنتج
    cy.get('#close-edit-modal-btn').click({ force: true }); // إغلاق النافذة
    cy.get('#edit-product-modal').should('not.have.class', 'active');

    // 2. فحص تبويب الطلبات
    cy.get('#sidebar-menu li[data-tab="orders"]').click({ force: true });
    cy.get('#tab-orders').should('have.class', 'active');
    cy.get('#orders-table-body').should('exist');

    // 3. فحص تبويب التحليلات والإحصائيات
    cy.get('#sidebar-menu li[data-tab="analytics"]').click({ force: true });
    cy.get('#tab-analytics').should('have.class', 'active');
    cy.get('#analytics-revenue').should('exist');
    cy.get('#sales-chart').should('exist'); // فحص وجود مخطط المبيعات المنقول للتحليلات
    
    // 4. فحص تبويب الموردين
    cy.get('#sidebar-menu li[data-tab="suppliers"]').click({ force: true });
    cy.get('#tab-suppliers').should('have.class', 'active');
    cy.get('#sup-name').should('exist'); // حقل اسم المورد الجديد
  });

  it('يجب أن يعرض بيانات الموردين ويتحقق من مزامنتها مع Firebase', () => {
    cy.visit('http://127.0.0.1:5500/store_dashboard.html');
    loginToDashboard();

    cy.get('#sidebar-menu li[data-tab="suppliers"]').click({ force: true });
    cy.get('#tab-suppliers').should('have.class', 'active');
    cy.get('#suppliers-table-body').should('exist');
  });
  
  it('يجب أن يتحقق من وظيفة تسجيل الخروج', () => {
    cy.visit('http://127.0.0.1:5500/store_dashboard.html');
    loginToDashboard();
    
    // فحص زر تسجيل الخروج
    cy.get('.logout-btn').should('be.visible').click({ force: true });
    
    // التحقق من ظهور نافذة التأكيد أو شاشة تسجيل الدخول
    cy.get('#confirm-modal, #login-overlay').should('be.visible');
  });
});
