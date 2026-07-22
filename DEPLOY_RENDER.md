# Unified Telegram & WhatsApp Service Deployment Guide (Render)

This project runs a unified backend service on Render (`https://market-anxk.onrender.com`) handling **Telegram order management** and **WhatsApp messaging & channel posting**.

---

## 1. Render Environment Variables Setup

Go to your Render Dashboard -> Service (`market-anxk`) -> **Environment** and add:

| Key | Example Value | Description |
| :--- | :--- | :--- |
| `PORT` | `8000` | Port number used by Express server |
| `TELEGRAM_BOT_TOKEN` | `123456789:ABCDefgh...` | Bot API token from Telegram `@BotFather` |
| `TELEGRAM_ADMIN_CHAT_ID` | `987654321` | Your personal/admin Telegram chat ID |
| `TELEGRAM_GATEWAY_API_KEY` | `your_secret_key` | Secret key (matches Settings in Dashboard) |
| `FIREBASE_API_KEY` | `AIzaSy...` | Firebase API Key |
| `FIREBASE_PROJECT_ID` | `aye-commercial-4b871` | Firebase Project ID |
| `WHATSAPP_PAIRING_NUMBER` | `9613XXXXXX` | (Optional) Your phone number to pair WhatsApp via code |

---

## 2. Features Included in `https://market-anxk.onrender.com`

### 🤖 Telegram Order Management
- **Instant Alerts**: When an order is placed, an alert is sent to Telegram with customer details and item list.
- **Interactive Action Buttons**:
  - `Pending 🟡`
  - `Shipped 🔵`
  - `Delivered 🟢`
  - `Cancelled 🔴`
  - `View Order Details 👁️`
- **Instant Status Sync**: Tapping any button in Telegram updates Firestore, refreshes the Telegram alert message, and automatically notifies the customer on WhatsApp!

### 🟢 WhatsApp Integration
- **Registration / OTP / Verification Messages**: Endpoints `/send-message` and `/send-bulk-message`.
- **WhatsApp Channel Posting**: Endpoints `/post-product` and `/sync-product` post items/offers directly to your WhatsApp Channel.
- **Automatic Session Backup**: WhatsApp session keys are saved directly in Firestore (`whatsapp_session`), so logging in stays active across Render restarts.
- **QR Code via Telegram**: Login QR codes are automatically forwarded to your Telegram Admin chat, or accessible via `/qr-code`.

---

## 3. Store Dashboard Settings

In your Store Dashboard (`store_dashboard.html`) -> **Settings** -> **Gateways**:
- **Telegram API URL**: `https://market-anxk.onrender.com/send-telegram`
- **Telegram Gateway API Key**: (Same as `TELEGRAM_GATEWAY_API_KEY`)
- **WhatsApp Bot API URL**: `https://market-anxk.onrender.com`
- **WhatsApp Bulk Message API URL**: `https://market-anxk.onrender.com`
