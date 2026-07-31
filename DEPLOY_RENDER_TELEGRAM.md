# Deploy Telegram Gateway on Render

This project now includes a ready blueprint file: `render.yaml`.

## 1) Push the latest code

Make sure these files are committed and pushed:
- `telegram_gateway.py`
- `requirements.txt`
- `render.yaml`

## 2) Create the service from Blueprint

1. Open Render dashboard.
2. Click **New +** -> **Blueprint**.
3. Select your GitHub repository.
4. Render will detect `render.yaml` and create service `aye-telegram-gateway`.

## 3) Set environment variables on Render

Open service -> **Environment** and set:
- `TELEGRAM_API_ID`
- `TELEGRAM_API_HASH`
- `TELEGRAM_SESSION`
- `TELEGRAM_GATEWAY_API_KEY`
- `TELEGRAM_ADMIN_CHAT_ID` (optional but recommended)
- `WHATSAPP_GATEWAY_URL` (optional)

Note:
- Do not leave `TELEGRAM_SESSION` empty on Render.
- Generate it once locally, then paste it as env var.

## 4) Generate TELEGRAM_SESSION locally

Run locally once:

```powershell
python telegram_gateway.py
```

After login, create the StringSession and copy it to Render as `TELEGRAM_SESSION`.

If you already use a StringSession, reuse the same value.

## 5) Point dashboard/storefront to Render URL

In dashboard settings, set:
- `telegram_api_url` = `https://<your-render-service>.onrender.com/send-telegram`
- `telegram_api_key` = same value as `TELEGRAM_GATEWAY_API_KEY`

## 6) Verify

Health check:

```text
https://<your-render-service>.onrender.com/status
```

Expected JSON includes `status: online`.

## 7) Telegram bot pairing reminder

Open Telegram and send `/start` to your admin bot at least once.
This ensures admin chat linking and enables order notifications with action buttons.
