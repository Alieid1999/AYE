# ITech Project Guidelines & Mandatory Rules

All AI assistants and contributors MUST strictly follow the rules defined in [PROJECT_RULES.md](file:///c:/Users/Ali/Desktop/AYE/PROJECT_RULES.md) and [SYSTEM_SPECS.md](file:///c:/Users/Ali/Desktop/AYE/SYSTEM_SPECS.md).

## Mandatory Core Directives:
1. **System Name:** Always use **ITech**.
2. **Visual Design & Assets:**
   - NO decorative illustrations, graphics, or animations.
   - ONLY real product images.
   - Absolutely NO placeholders (text or images) in code.
   - Supported languages ONLY: Arabic, English, French (ar, en, fr).
   - Fully compliant PWA.
3. **Performance:** Ultra-fast product load times without long loaders.
4. **Authentication:**
   - Customers: browse and purchase directly without logging in.
   - Admin & Editors: login via **Username** and password ONLY (mapped internally to `@itech.local` for Firebase Auth, email never visible).
   - Logout: clears entire session, localStorage, and browser cache, then redirect prevents back navigation.
5. **QA Verification:** Every button (Add, Edit, Delete, Archive, Submit Order, Status change) and input MUST be verified and functionally connected to Firebase before delivery.
