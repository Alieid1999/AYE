# Telegram Service Deployment Guide (Render)

This project runs a backend service on Render (`https://market-anxk.onrender.com`) handling **Telegram order management**.

---

## 1. Render Environment Variables Setup

Go to your Render Dashboard -> Service (`market-anxk`) -> **Environment** and add:

| Key | Example Value | Description |
| :--- | :--- | :--- |
| `PORT` | `8000` | Port number used by FastAPI / Server |
| `TELEGRAM_BOT_TOKEN` | `123456789:ABCDefgh...` | Bot API token from Telegram `@BotFather` |
| `TELEGRAM_ADMIN_CHAT_ID` | `987654321` | Your personal/admin Telegram chat ID |
| `TELEGRAM_GATEWAY_API_KEY` | `your_secret_key` | Secret key (matches Settings in Dashboard) |
| `FIREBASE_API_KEY` | `AIzaSy...` | Firebase API Key |
| `FIREBASE_PROJECT_ID` | `aye-commercial-4b871` | Firebase Project ID |

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
- **Instant Status Sync**: Tapping any button in Telegram updates Firestore and refreshes the Telegram alert message.


