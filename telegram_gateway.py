#!/usr/bin/env python3
"""
AYE Store — Telegram Telethon FastAPI Gateway
This script runs a local API server (on port 8000) that allows your storefront
and admin dashboard to send free verification codes (OTPs) and custom notifications
directly from your personal Telegram account.

How to get API ID & API Hash:
1. Log in to your Telegram account at https://my.telegram.org/
2. Go to 'API development tools'.
3. Create a new application (fill in random details).
4. Copy your 'App api_id' and 'App api_hash' and paste them below.

How to start:
1. Install requirements:
   pip install fastapi uvicorn telethon
2. Edit API_ID and API_HASH below (or set TELEGRAM_API_ID / TELEGRAM_API_HASH env vars).
3. Set TELEGRAM_GATEWAY_API_KEY to a strong secret and use the same value in the admin dashboard.
4. Run the script:
   python telegram_gateway.py
5. The first time you run it, it will ask for your phone number and the code
   sent to you by Telegram to log you in and save your session.
"""

from fastapi import FastAPI, HTTPException, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from telethon import TelegramClient
from telethon.sessions import StringSession
import uvicorn
import os
import sys
import base64
import json
import urllib.request
import urllib.parse
from typing import Optional
import time
import tempfile
import telebot
from telebot import types
import threading
import requests

# Reconfigure stdout/stderr to UTF-8 to prevent UnicodeEncodeError on Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ==========================================
# ⚙️ TELEGRAM CREDENTIALS
# ==========================================
API_ID_ENV = os.environ.get('TELEGRAM_API_ID')
API_HASH_ENV = os.environ.get('TELEGRAM_API_HASH')
SESSION_STRING = os.environ.get('TELEGRAM_SESSION')
GATEWAY_API_KEY = os.environ.get('TELEGRAM_GATEWAY_API_KEY', '')
WHATSAPP_GATEWAY_URL = os.environ.get('WHATSAPP_GATEWAY_URL', '')  # e.g. https://your-whatsapp-bot.onrender.com

API_ID = int(API_ID_ENV) if API_ID_ENV else 32658899          # <-- Replace with your api_id (Integer)
API_HASH = API_HASH_ENV if API_HASH_ENV else '2ed2353e5f72146c5e053cd4730e442b' # <-- Replace with your api_hash (String)


# Telethon client initialization using StringSession or local Session File
if SESSION_STRING:
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
else:
    client = TelegramClient('telegram_gateway_session', API_ID, API_HASH)

app = FastAPI(title="AYE Store Telegram SMS Gateway")

# ----------------------------------------------------
# ⚙️ FIREBASE CONFIGURATION & CLIENT
# ----------------------------------------------------
FIREBASE_API_KEY = "AIzaSyDSIsmOtYSuQe7Y8XsUwfstc8UNQw2ykkM"
FIREBASE_PROJECT_ID = "aye-commercial-4b871"

class FirebaseFirestoreClient:
    def __init__(self, api_key, project_id):
        self.api_key = api_key
        self.project_id = project_id
        self._id_token = None
        self._token_expiry = 0
        self.session = requests.Session()

    def _authenticate(self):
        """Perform anonymous authentication to get ID token"""
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={self.api_key}"
        try:
            resp = self.session.post(url, json={"returnSecureToken": True}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            self._id_token = data["idToken"]
            expires_in = int(data.get("expiresIn", 3600))
            self._token_expiry = time.time() + expires_in - 60
            return self._id_token
        except Exception as e:
            print(f"Firebase Authentication Failed: {e}")
            raise

    @property
    def id_token(self):
        if not self._id_token or time.time() > self._token_expiry:
            self._authenticate()
        return self._id_token

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.id_token}",
            "Content-Type": "application/json"
        }

    def _parse_value(self, val):
        if "stringValue" in val:
            return val["stringValue"]
        elif "doubleValue" in val:
            return float(val["doubleValue"])
        elif "integerValue" in val:
            return int(val["integerValue"])
        elif "booleanValue" in val:
            return val["booleanValue"]
        elif "mapValue" in val:
            return {k: self._parse_value(v) for k, v in val["mapValue"].get("fields", {}).items()}
        elif "arrayValue" in val:
            return [self._parse_value(v) for v in val["arrayValue"].get("values", [])]
        return None

    def _parse_document(self, doc_data):
        fields = doc_data.get("fields", {})
        name = doc_data.get("name", "")
        doc_id = name.split("/")[-1] if name else ""
        parsed = {"id": doc_id}
        for k, v in fields.items():
            parsed[k] = self._parse_value(v)
        return parsed

    def get_orders(self, status_filter=None):
        """Fetch orders from Firestore collection, optionally filtering by status"""
        url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents:runQuery"
        
        structured_query = {
            "from": [{"collectionId": "orders"}],
            "orderBy": [
                {
                    "field": {"fieldPath": "createdAt"},
                    "direction": "DESCENDING"
                }
            ],
            "limit": 100
        }

        if status_filter:
            structured_query["where"] = {
                "fieldFilter": {
                    "field": {"fieldPath": "status"},
                    "op": "EQUAL",
                    "value": {"stringValue": status_filter}
                }
            }

        query = {"structuredQuery": structured_query}

        try:
            resp = self.session.post(url, headers=self._get_headers(), json=query, timeout=10)
            resp.raise_for_status()
            results = resp.json()
            
            orders = []
            for item in results:
                if "document" in item:
                    orders.append(self._parse_document(item["document"]))
            return orders
        except Exception as e:
            print(f"Error fetching orders: {e}")
            try:
                self._authenticate()
                resp = self.session.post(url, headers=self._get_headers(), json=query, timeout=10)
                resp.raise_for_status()
                results = resp.json()
                orders = []
                for item in results:
                    if "document" in item:
                        orders.append(self._parse_document(item["document"]))
                return orders
            except Exception as re_err:
                print(f"Retry fetching orders failed: {re_err}")
                return []

    def get_order_by_id(self, order_id):
        """Fetch a single order by ID"""
        url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/orders/{order_id}"
        try:
            resp = self.session.get(url, headers=self._get_headers(), timeout=10)
            resp.raise_for_status()
            return self._parse_document(resp.json())
        except Exception as e:
            print(f"Error fetching order {order_id}: {e}")
            return None

    def update_order_status(self, order_id, new_status):
        """Update an order status using PATCH and updateMask"""
        url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/orders/{order_id}?updateMask.fieldPaths=status"
        payload = {
            "fields": {
                "status": {
                    "stringValue": new_status
                }
            }
        }
        try:
            resp = self.session.patch(url, headers=self._get_headers(), json=payload, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as e:
            print(f"Error updating status of order {order_id}: {e}")
            return False

    def get_admin_chat_id(self):
        """Fetch admin chat ID from Firestore settings/gateways"""
        url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/settings/gateways"
        try:
            resp = self.session.get(url, headers=self._get_headers(), timeout=5)
            if resp.status_code == 200:
                doc = self._parse_document(resp.json())
                chat_id = doc.get("telegram_admin_chat_id")
                if chat_id:
                    return int(chat_id)
        except Exception as e:
            print(f"Error fetching admin chat ID from Firestore: {e}")
        return None

    def save_admin_chat_id(self, chat_id):
        """Save admin chat ID to Firestore settings/gateways"""
        url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/settings/gateways?updateMask.fieldPaths=telegram_admin_chat_id"
        payload = {
            "fields": {
                "telegram_admin_chat_id": {
                    "integerValue": str(chat_id)
                }
            }
        }
        try:
            resp = self.session.patch(url, headers=self._get_headers(), json=payload, timeout=5)
            return resp.status_code == 200
        except Exception as e:
            print(f"Error saving admin chat ID to Firestore: {e}")
            return False

    def get_gateway_settings(self):
        """Fetch all gateway settings from Firestore settings/gateways"""
        url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/settings/gateways"
        try:
            resp = self.session.get(url, headers=self._get_headers(), timeout=5)
            if resp.status_code == 200:
                return self._parse_document(resp.json())
        except Exception as e:
            print(f"Error fetching gateway settings: {e}")
        return {}

    def get_products(self):
        """Fetch all products from Firestore"""
        url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/products?pageSize=300"
        try:
            resp = self.session.get(url, headers=self._get_headers(), timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                products = []
                for doc in data.get("documents", []):
                    products.append(self._parse_document(doc))
                return products
        except Exception as e:
            print(f"Error fetching products for backup: {e}")
        return []

    def get_customers(self):
        """Fetch all customers from Firestore"""
        url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/customers?pageSize=300"
        try:
            resp = self.session.get(url, headers=self._get_headers(), timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                customers = []
                for doc in data.get("documents", []):
                    customers.append(self._parse_document(doc))
                return customers
        except Exception as e:
            print(f"Error fetching customers for backup: {e}")
        return []

    def get_orders_backup(self):
        """Fetch all orders from Firestore (for backup)"""
        url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/orders?pageSize=300"
        try:
            resp = self.session.get(url, headers=self._get_headers(), timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                orders = []
                for doc in data.get("documents", []):
                    orders.append(self._parse_document(doc))
                return orders
        except Exception as e:
            print(f"Error fetching orders for backup: {e}")
        return []

    def get_categories(self):
        """Fetch categories list from Firestore settings/categories"""
        url = f"https://firestore.googleapis.com/v1/projects/{self.project_id}/databases/(default)/documents/settings/categories"
        try:
            resp = self.session.get(url, headers=self._get_headers(), timeout=10)
            if resp.status_code == 200:
                doc = self._parse_document(resp.json())
                return doc.get("list", [])
        except Exception as e:
            print(f"Error fetching categories for backup: {e}")
        return []

db_client = FirebaseFirestoreClient(FIREBASE_API_KEY, FIREBASE_PROJECT_ID)

# ----------------------------------------------------
# 🤖 TELEGRAM BOT IMPLEMENTATION
# ----------------------------------------------------
bot = None
_cached_admin_chat_id = None

def discover_admin_chat_id_from_bot_updates():
    """Try to discover the admin private chat id from recent bot updates."""
    if not BOT_TOKEN:
        return None
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
        resp = requests.get(url, params={"limit": 100, "timeout": 0}, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
        if not payload.get("ok"):
            return None

        updates = payload.get("result", [])
        for update in reversed(updates):
            message = update.get("message") or update.get("edited_message")
            if not message:
                callback_msg = (update.get("callback_query") or {}).get("message")
                message = callback_msg
            if not message:
                continue

            chat = message.get("chat") or {}
            chat_id = chat.get("id")
            chat_type = chat.get("type")
            if chat_id and chat_type == "private":
                return int(chat_id)
    except Exception as e:
        print(f"Error discovering admin chat ID from bot updates: {e}")
    return None

def save_admin_chat_id(chat_id):
    global _cached_admin_chat_id
    _cached_admin_chat_id = chat_id
    try:
        with open(ADMIN_CHAT_FILE, "w") as f:
            f.write(str(chat_id))
    except Exception as e:
        print(f"Error saving admin chat ID locally: {e}")
    db_client.save_admin_chat_id(chat_id)

def check_for_new_orders():
    print("Background order notifier: Initializing seen orders list...")
    initial_orders = db_client.get_orders()
    seen_orders = {o["id"] for o in initial_orders}
    print(f"Background order notifier: Loaded {len(seen_orders)} initial orders.")

    while True:
        try:
            time.sleep(10)
            admin_chat_id = load_admin_chat_id()
            if not admin_chat_id or not bot:
                continue

            current_orders = db_client.get_orders()
            for o in current_orders:
                order_id = o.get("id")
                if order_id not in seen_orders:
                    seen_orders.add(order_id)
                    
                    if o.get("status") == "Pending":
                        cust = o.get("customer", {})
                        total = o.get("totalAmount", 0)
                        cust_phone = cust.get('phone') or 'Auto-linking via WhatsApp...'
                        
                        notify_msg = (
                            f"🔔 *New Order Received! (# {order_id})*\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"👤 *Customer:* {cust.get('name', 'N/A')}\n"
                            f"📞 *Phone:* `{cust_phone}`\n"
                            f"💵 *Total:* ${total:.2f}\n"
                        )
                        
                        markup = types.InlineKeyboardMarkup()
                        markup.add(types.InlineKeyboardButton("👁️ View Order Details", callback_data=f"view_{order_id}"))
                        
                        try:
                            bot.send_message(admin_chat_id, notify_msg, parse_mode="Markdown", reply_markup=markup)
                        except Exception as send_err:
                            print(f"Failed to send background notification: {send_err}")
        except Exception as poll_err:
            print(f"Error in background notifier thread: {poll_err}")

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn_active = types.KeyboardButton("📋 Active Orders")
    btn_history = types.KeyboardButton("📜 History")
    markup.add(btn_active, btn_history)
    return markup

def notify_customer_whatsapp(phone: str, order_id: str, new_status: str, customer_name: str):
    """Send a WhatsApp status notification to the customer in a background thread."""
    if not WHATSAPP_GATEWAY_URL:
        print("[WA Notify] WHATSAPP_GATEWAY_URL not set — skipping customer notification.")
        return

    status_emoji = {"Shipped": "🔵", "Delivered": "🟢", "Cancelled": "🔴"}.get(new_status, "🟡")
    msg = (
        f"{status_emoji} *AYE Store — Order Update*\n\n"
        f"Hello {customer_name}!\n"
        f"Your order *#{order_id}* has been updated to:\n\n"
        f"{status_emoji} *{new_status}*\n\n"
        f"Thank you for shopping with us! 💙"
    )

    def _send():
        try:
            resp = requests.post(
                f"{WHATSAPP_GATEWAY_URL}/send-message",
                json={"to": phone, "message": msg},
                timeout=15
            )
            print(f"[WA Notify] Sent to {phone}: {resp.status_code} {resp.text[:100]}")
        except Exception as e:
            print(f"[WA Notify] Failed: {e}")

    threading.Thread(target=_send, daemon=True).start()


def setup_bot():
    global bot
    if not BOT_TOKEN:
        return False
    bot = telebot.TeleBot(BOT_TOKEN)
    
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        save_admin_chat_id(message.chat.id)
        welcome_text = (
            "👋 Welcome to AYE Store Admin Bot!\n\n"
            "Here you can manage your store orders directly:\n"
            "• *Active Orders* (Pending status)\n"
            "• *History* (All orders list)\n\n"
            "Use the buttons below to navigate."
        )
        bot.send_message(
            message.chat.id, 
            welcome_text, 
            parse_mode="Markdown", 
            reply_markup=get_main_keyboard()
        )

    @bot.message_handler(func=lambda msg: msg.text == "📋 Active Orders")
    def show_active_orders(message):
        sent_msg = bot.send_message(message.chat.id, "🔄 Fetching active orders...")
        orders = db_client.get_orders(status_filter="Pending")
        
        if not orders:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=sent_msg.message_id,
                text="✅ No pending active orders found."
            )
            return

        markup = types.InlineKeyboardMarkup(row_width=1)
        for o in orders:
            cust_name = o.get("customer", {}).get("name", "Unknown")
            total = o.get("totalAmount", 0)
            btn_text = f"📦 #{o['id']} - {cust_name} (${total:.2f})"
            markup.add(types.InlineKeyboardButton(text=btn_text, callback_data=f"view_{o['id']}"))

        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=sent_msg.message_id,
            text=f"📋 *Active Orders ({len(orders)} pending):*\nSelect an order to view details and manage status:",
            parse_mode="Markdown",
            reply_markup=markup
        )

    @bot.message_handler(func=lambda msg: msg.text == "📜 History")
    def show_history(message):
        sent_msg = bot.send_message(message.chat.id, "🔄 Fetching orders history...")
        orders = db_client.get_orders()
        
        if not orders:
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=sent_msg.message_id,
                text="📭 No orders found in the database."
            )
            return

        orders_slice = orders[:25]
        text = f"📜 *Latest Orders History ({len(orders_slice)} shown):*\n\n"
        markup = types.InlineKeyboardMarkup(row_width=1)
        
        for o in orders_slice:
            status = o.get("status", "Pending")
            status_emoji = "🟡"
            if status == "Shipped": status_emoji = "🔵"
            elif status == "Delivered": status_emoji = "🟢"
            elif status == "Cancelled": status_emoji = "🔴"
            
            cust_name = o.get("customer", {}).get("name", "Unknown")
            total = o.get("totalAmount", 0)
            
            btn_text = f"{status_emoji} #{o['id']} - {cust_name} (${total:.2f})"
            markup.add(types.InlineKeyboardButton(text=btn_text, callback_data=f"view_{o['id']}"))

        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=sent_msg.message_id,
            text=text + "Click any order to view details or modify status:",
            parse_mode="Markdown",
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("view_"))
    def view_order_details(call):
        order_id = call.data.split("_")[1]
        order = db_client.get_order_by_id(order_id)
        
        if not order:
            bot.answer_callback_query(call.id, "❌ Order not found!")
            return

        bot.answer_callback_query(call.id)
        
        status = order.get("status", "Pending")
        status_emoji = "🟡"
        if status == "Shipped": status_emoji = "🔵"
        elif status == "Delivered": status_emoji = "🟢"
        elif status == "Cancelled": status_emoji = "🔴"

        cust = order.get("customer", {})
        items = order.get("items", [])
        
        items_text = ""
        for item in items:
            title = item.get("title", "Item")
            qty = item.get("quantity", 1)
            price = item.get("price", 0)
            items_text += f" - {title} x{qty} (${price:.2f})\n"

        cust_phone = cust.get('phone') or 'Auto-linking via WhatsApp...'
        details_msg = (
            f"📦 *Order Details #{order['id']}*\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Customer:* {cust.get('name', 'N/A')}\n"
            f"📞 *Phone:* `{cust_phone}`\n"
            f"📍 *Address:* {cust.get('address', 'N/A')}\n"
            f"📧 *Email:* {cust.get('email', 'N/A')}\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🛍️ *Items:*\n{items_text}"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"💵 *Total:* ${order.get('totalAmount', 0):.2f}\n"
            f"🚦 *Status:* {status_emoji} {status}\n"
            f"📅 *Date:* {order.get('createdAt', 'N/A')[:19].replace('T', ' ')}\n"
        )

        markup = types.InlineKeyboardMarkup(row_width=2)
        btn_pending = types.InlineKeyboardButton("Pending 🟡", callback_data=f"set_Pending_{order_id}")
        btn_ship = types.InlineKeyboardButton("Shipped 🔵", callback_data=f"set_Shipped_{order_id}")
        btn_deliv = types.InlineKeyboardButton("Delivered 🟢", callback_data=f"set_Delivered_{order_id}")
        btn_cancel = types.InlineKeyboardButton("Cancelled 🔴", callback_data=f"set_Cancelled_{order_id}")
        
        markup.add(btn_pending, btn_ship, btn_deliv, btn_cancel)
        markup.add(types.InlineKeyboardButton("⬅️ Back to Active Orders", callback_data="back_active"))

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=details_msg,
            parse_mode="Markdown",
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("set_"))
    def update_status(call):
        parts = call.data.split("_")
        new_status = parts[1]
        order_id = parts[2]
        
        bot.answer_callback_query(call.id, f"🔄 Updating status to {new_status}...")
        success = db_client.update_order_status(order_id, new_status)
        
        if success:
            bot.answer_callback_query(call.id, f"✅ Order status updated to {new_status}!", show_alert=True)

            # Notify the customer via WhatsApp
            print(f"[WA Notify] Status updated to {new_status} for order {order_id} — fetching order...")
            try:
                order = db_client.get_order_by_id(order_id)
                if order:
                    customer_phone = order.get("customer", {}).get("phone", "")
                    customer_name = order.get("customer", {}).get("name", "")
                    print(f"[WA Notify] Customer: {customer_name}, Phone: '{customer_phone}', WA_URL: '{WHATSAPP_GATEWAY_URL}'")
                    if customer_phone:
                        notify_customer_whatsapp(customer_phone, order_id, new_status, customer_name)
                    else:
                        print("[WA Notify] No phone number found on order — skipping.")
                else:
                    print(f"[WA Notify] Order {order_id} not found in DB.")
            except Exception as notify_err:
                print(f"[WA Notify] Error fetching order for notification: {notify_err}")

            call.data = f"view_{order_id}"
            view_order_details(call)
        else:
            bot.answer_callback_query(call.id, "❌ Failed to update status.", show_alert=True)

    @bot.callback_query_handler(func=lambda call: call.data == "back_active")
    def back_to_active(call):
        bot.answer_callback_query(call.id)
        orders = db_client.get_orders(status_filter="Pending")
        
        if not orders:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="✅ No pending active orders found."
            )
            return

        markup = types.InlineKeyboardMarkup(row_width=1)
        for o in orders:
            cust_name = o.get("customer", {}).get("name", "Unknown")
            total = o.get("totalAmount", 0)
            btn_text = f"📦 #{o['id']} - {cust_name} (${total:.2f})"
            markup.add(types.InlineKeyboardButton(text=btn_text, callback_data=f"view_{o['id']}"))

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"📋 *Active Orders ({len(orders)} pending):*\nSelect an order to view details and manage status:",
            parse_mode="Markdown",
            reply_markup=markup
        )
    return True

# Enable CORS middleware so the browser storefront can call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class TelegramRequest(BaseModel):
    to: str
    message: str
    is_admin: Optional[bool] = False
    order_id: Optional[str] = None

ADMIN_CHAT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin_chat_id.txt")
BOT_TOKEN = "8778703104:AAFq9PeX8jbNkAdNs3lBMxdmkVy387ZZ0K8"

def load_admin_chat_id():
    global _cached_admin_chat_id
    if _cached_admin_chat_id is not None:
        return _cached_admin_chat_id

    # 1. Try env variable
    env_chat_id = os.environ.get('TELEGRAM_ADMIN_CHAT_ID')
    if env_chat_id:
        try:
            _cached_admin_chat_id = int(env_chat_id)
            return _cached_admin_chat_id
        except ValueError:
            pass

    # 2. Try Firestore
    firestore_chat_id = db_client.get_admin_chat_id()
    if firestore_chat_id:
        _cached_admin_chat_id = firestore_chat_id
        return _cached_admin_chat_id

    # 2.5 Try to discover from bot updates if admin has already started the bot
    discovered_chat_id = discover_admin_chat_id_from_bot_updates()
    if discovered_chat_id:
        save_admin_chat_id(discovered_chat_id)
        return discovered_chat_id

    # 3. Try local file
    if os.path.exists(ADMIN_CHAT_FILE):
        try:
            with open(ADMIN_CHAT_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    _cached_admin_chat_id = int(content)
                    return _cached_admin_chat_id
        except Exception as e:
            print(f"Error loading admin chat ID locally: {e}")
    return None

def verify_api_key(x_api_key: Optional[str]) -> None:
    if not GATEWAY_API_KEY:
        return
    if not x_api_key or x_api_key != GATEWAY_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

def keep_alive_ping_loop():
    print("[Keep-Alive] Starting background keep-alive ping thread...")
    while True:
        try:
            time.sleep(300)
            settings = db_client.get_gateway_settings()
            whatsapp_bot_url = settings.get("whatsapp_bot_url")
            if whatsapp_bot_url:
                target_url = whatsapp_bot_url.rstrip("/") + "/status"
                print(f"[Keep-Alive] Pinging WhatsApp Bot: {target_url}")
                resp = requests.get(target_url, timeout=10)
                print(f"[Keep-Alive] WhatsApp Bot response: {resp.status_code}")
            else:
                print("[Keep-Alive] No whatsapp_bot_url configured in settings/gateways.")
        except Exception as e:
            print(f"[Keep-Alive] Error pinging WhatsApp Bot: {e}")

def daily_backup_scheduler():
    print("[Backup Scheduler] Starting background backup check thread...")
    last_backup_file = "last_backup_date.txt"
    last_backup_date = ""
    if os.path.exists(last_backup_file):
        try:
            with open(last_backup_file, "r") as f:
                last_backup_date = f.read().strip()
        except Exception:
            pass

    # Initial check upon startup, then check every hour
    initial_check = True
    while True:
        try:
            if not initial_check:
                time.sleep(3600)
            initial_check = False
            
            import datetime
            today = datetime.date.today().isoformat()
            if today == last_backup_date:
                continue

            # Fetch settings
            settings = db_client.get_gateway_settings()
            backup_email = settings.get("backup_email")
            gmail_script_url = settings.get("gmail_script_url")
            backup_drive_folder_id = settings.get("backup_drive_folder_id")

            if not backup_email or not gmail_script_url:
                continue

            print(f"[Backup Scheduler] Running daily backup for date {today}...")
            
            # Fetch database data
            products = db_client.get_products()
            orders = db_client.get_orders_backup()
            customers = db_client.get_customers()
            categories = db_client.get_categories()

            backup_data = {
                "products": products,
                "orders": orders,
                "customers": customers,
                "categories": categories,
                "timestamp": datetime.datetime.utcnow().isoformat() + 'Z'
            }

            backup_json = json.dumps(backup_data, indent=2)
            
            subject = f"[Auto-Backup] AYE Store Database - {today}"
            body = (
                f"أهلاً بك،\n\n"
                f"مرفق أدناه النسخة الاحتياطية اليومية التلقائية لقاعدة بيانات متجر AYE Store:\n\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📅 التاريخ: {today}\n"
                f"📦 المنتجات: {len(products)}\n"
                f"📦 الطلبيات: {len(orders)}\n"
                f"👤 العملاء: {len(customers)}\n"
                f"━━━━━━━━━━━━━━━━━━━\n\n"
                f"محتوى قاعدة البيانات بتنسيق JSON:\n\n"
                f"{backup_json}"
            )

            payload = {
                "to": backup_email,
                "subject": subject,
                "body": body
            }

            if backup_drive_folder_id:
                payload["driveFolderId"] = backup_drive_folder_id
                payload["fileName"] = f"aye_store_backup_{today}.json"

            # Post to Apps Script
            headers = {"Content-Type": "text/plain;charset=utf-8"}
            resp = requests.post(gmail_script_url, data=json.dumps(payload), headers=headers, timeout=30)
            
            if resp.status_code == 200:
                print(f"[Backup Scheduler] Backup email sent successfully for {today}!")
                last_backup_date = today
                try:
                    with open(last_backup_file, "w") as f:
                        f.write(today)
                except Exception:
                    pass
            else:
                print(f"[Backup Scheduler] Failed to send backup email, status code: {resp.status_code}")

        except Exception as e:
            print(f"[Backup Scheduler] Error in daily backup process: {e}")

@app.on_event("startup")
async def startup_event():
    # Connect client if not already connected
    if not client.is_connected():
        await client.connect()
    
    is_authorized = await client.is_user_authorized()
    if is_authorized:
        print("Telegram client is connected, authorized, and ready!")
    else:
        print("WARNING: Telegram client is connected but NOT authorized! Please check your credentials.")

    # Start bot and order notifier threads
    if setup_bot():
        print("🤖 Telegram Bot initialized successfully.")
        
        # Start bot polling in a background daemon thread
        bot_thread = threading.Thread(target=bot.infinity_polling, daemon=True)
        bot_thread.start()
        print("🤖 Telegram Bot polling started in background.")
        
        # Start automatic daily backup thread
        backup_thread = threading.Thread(target=daily_backup_scheduler, daemon=True)
        backup_thread.start()
        print("💾 Automatic daily backup scheduler thread started.")
        
        # Start keep-alive ping thread
        keep_alive_thread = threading.Thread(target=keep_alive_ping_loop, daemon=True)
        keep_alive_thread.start()
        print("⚡ Keep-alive mutual ping scheduler thread started.")
        
        # Start background order checking thread (disabled to rely entirely on direct storefront API notifications)
        # notifier_thread = threading.Thread(target=check_for_new_orders, daemon=True)
        # notifier_thread.start()
        # print("🔔 Order checking background notifier thread started.")

@app.post("/send-telegram")
async def send_telegram_message(
    request: TelegramRequest,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    verify_api_key(x_api_key)

    phone = request.to.strip()
    msg = request.message
    is_admin = request.is_admin
    
    if is_admin:
        admin_chat_id = load_admin_chat_id()
        if not admin_chat_id:
            discovered_chat_id = discover_admin_chat_id_from_bot_updates()
            if discovered_chat_id:
                save_admin_chat_id(discovered_chat_id)
                admin_chat_id = discovered_chat_id

        if not admin_chat_id:
            try:
                if client and client.is_connected():
                    me = await client.get_me()
                    if me:
                        admin_chat_id = me.id
                        save_admin_chat_id(admin_chat_id)
            except Exception as me_err:
                print(f"Failed to get admin ID from Telethon: {me_err}")

        if admin_chat_id:
            try:
                markup = None
                if request.order_id:
                    markup = {
                        "inline_keyboard": [
                            [{
                                "text": "👁️ View Order Details",
                                "callback_data": f"view_{request.order_id}"
                            }],
                            [{
                                "text": "Pending 🟡",
                                "callback_data": f"set_Pending_{request.order_id}"
                            }, {
                                "text": "Shipped 🔵",
                                "callback_data": f"set_Shipped_{request.order_id}"
                            }],
                            [{
                                "text": "Delivered 🟢",
                                "callback_data": f"set_Delivered_{request.order_id}"
                            }, {
                                "text": "Cancelled 🔴",
                                "callback_data": f"set_Cancelled_{request.order_id}"
                            }]
                        ]
                    }

                # Always use direct HTTP Bot API — no dependency on bot polling thread
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {
                    "chat_id": admin_chat_id,
                    "text": msg,
                    "parse_mode": "Markdown"
                }
                if markup:
                    payload["reply_markup"] = json.dumps(markup)

                print(f"[BOT] Sending to chat_id={admin_chat_id} via Bot HTTP API...")
                resp = requests.post(url, json=payload, timeout=10)
                print(f"[BOT] Response: {resp.status_code} - {resp.text[:200]}")
                resp.raise_for_status()
                resp_data = resp.json()
                if resp_data.get("ok") and request.order_id:
                    message_id = resp_data["result"]["message_id"]
                    try:
                        patch_url = f"https://firestore.googleapis.com/v1/projects/{db_client.project_id}/databases/(default)/documents/orders/{request.order_id}?updateMask.fieldPaths=telegram_message_id&updateMask.fieldPaths=telegram_message_text"
                        patch_payload = {
                            "fields": {
                                "telegram_message_id": {"stringValue": str(message_id)},
                                "telegram_message_text": {"stringValue": msg}
                            }
                        }
                        db_client.session.patch(patch_url, headers=db_client._get_headers(), json=patch_payload, timeout=10)
                        print(f"[BOT] Saved telegram_message_id={message_id} to Firestore order {request.order_id}")
                    except Exception as firestore_err:
                        print(f"[BOT] Failed to save Telegram message details to Firestore: {firestore_err}")
                return {"success": True, "message": "Notification sent to admin via Bot"}
            except Exception as bot_err:
                print(f"[BOT] Failed to send via Bot API: {bot_err}. Falling back to Saved Messages.")

        # Fallback: send directly to 'me' (Saved Messages) using Telethon
        try:
            await client.send_message('me', msg)

            return {"success": True, "message": "Notification sent to admin via Saved Messages"}
        except Exception as me_fallback_err:
            print(f"Failed to send directly to 'me': {me_fallback_err}. Proceeding with contact import fallback.")

    if not phone or not msg:
        raise HTTPException(status_code=400, detail="Missing 'to' or 'message'")

    # Normalize phone number structure (must start with +)
    if not phone.startswith('+'):
        phone = '+' + ''.join(filter(str.isdigit, phone))

    try:
        from telethon.tl.types import InputPhoneContact
        from telethon.tl.functions.contacts import ImportContactsRequest, DeleteContactsRequest

        # 1. Temporarily import user to contacts list so Telegram resolves the phone number to an entity
        contact = InputPhoneContact(client_id=0, phone=phone, first_name="AYE Store Customer", last_name="")
        import_result = await client(ImportContactsRequest([contact]))

        if not import_result.users:
            return {"success": False, "error": "This phone number is not registered on Telegram."}

        target_user = import_result.users[0]

        # 2. Send the message via Telethon client to the resolved user entity
        await client.send_message(target_user, msg)

        # 3. Clean up: delete from contacts immediately to keep list clean
        await client(DeleteContactsRequest(id=[target_user.id]))

        return {"success": True, "message": "Telegram message sent successfully"}
    except Exception as e:
        print(f"Error sending message: {e}")
        return {"success": False, "error": str(e)}

@app.get("/status")
async def get_status():
    is_authorized = await client.is_user_authorized() if client.is_connected() else False
    return {
        "status": "online",
        "telegram_connected": client.is_connected(),
        "telegram_authorized": is_authorized,
        "api_key_required": bool(GATEWAY_API_KEY),
    }

class SocialPostRequest(BaseModel):
    title: str
    price: float
    currency: str
    image: str
    description: str
    link: str
    facebook_enabled: bool
    facebook_page_id: Optional[str] = None
    facebook_page_token: Optional[str] = None
    instagram_enabled: bool
    instagram_business_id: Optional[str] = None
    instagram_token: Optional[str] = None
    tiktok_enabled: bool
    tiktok_access_token: Optional[str] = None
    webhook_url: Optional[str] = None
    whatsapp_enabled: bool
    whatsapp_channel_name: Optional[str] = None

def make_multipart_request(url, fields, files):
    boundary = b'----WebKitFormBoundary7MA4YWxkTrZu0gW'
    body = []
    
    for key, value in fields.items():
        body.append(b'--' + boundary)
        body.append(f'Content-Disposition: form-data; name="{key}"'.encode('utf-8'))
        body.append(b'')
        body.append(str(value).encode('utf-8'))
        
    for key, (filename, content, mimetype) in files.items():
        body.append(b'--' + boundary)
        body.append(f'Content-Disposition: form-data; name="{key}"; filename="{filename}"'.encode('utf-8'))
        body.append(f'Content-Type: {mimetype}'.encode('utf-8'))
        body.append(b'')
        body.append(content)
        
    body.append(b'--' + boundary + b'--')
    body.append(b'')
    
    req_body = b'\r\n'.join(body)
    
    req = urllib.request.Request(url, data=req_body)
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary.decode("utf-8")}')
    
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

def make_json_request(url, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode('utf-8'))

@app.post("/post-social")
async def post_to_social_media(request: SocialPostRequest):
    results = {}
    caption = f"{request.title}\n\nPrice: {request.price} {request.currency}\n\n{request.description}\n\nBuy here: {request.link}"
    
    # 1. Webhook Automation (Make.com/Zapier/TikTok)
    if request.webhook_url:
        try:
            webhook_payload = {
                "event": "product_created",
                "title": request.title,
                "price": request.price,
                "currency": request.currency,
                "image": request.image,
                "description": request.description,
                "link": request.link
            }
            res = make_json_request(request.webhook_url, webhook_payload)
            results["webhook"] = {"success": True, "response": res}
        except Exception as e:
            results["webhook"] = {"success": False, "error": str(e)}

    # 2. Direct Facebook Graph API Posting
    if request.facebook_enabled and request.facebook_page_id and request.facebook_page_token:
        try:
            fb_url = f"https://graph.facebook.com/v19.0/{request.facebook_page_id}/photos"
            if request.image.startswith("data:image"):
                header, encoded = request.image.split(",", 1)
                mime_type = header.split(";")[0].split(":")[1]
                image_bytes = base64.b64decode(encoded)
                files = {'source': ('image.png', image_bytes, mime_type)}
                fields = {'message': caption, 'access_token': request.facebook_page_token}
                res = make_multipart_request(fb_url, fields, files)
            else:
                fields = {'url': request.image, 'message': caption, 'access_token': request.facebook_page_token}
                data = urllib.parse.urlencode(fields).encode('utf-8')
                req = urllib.request.Request(fb_url, data=data, method='POST')
                with urllib.request.urlopen(req) as response:
                    res = json.loads(response.read().decode('utf-8'))
            results["facebook"] = {"success": True, "response": res}
        except Exception as e:
            results["facebook"] = {"success": False, "error": str(e)}

    # 3. Direct Instagram Graph API Posting
    if request.instagram_enabled and request.instagram_business_id and request.instagram_token:
        try:
            if not request.image.startswith("data:image"):
                container_url = f"https://graph.facebook.com/v19.0/{request.instagram_business_id}/media"
                payload = {
                    "image_url": request.image,
                    "caption": caption,
                    "access_token": request.instagram_token
                }
                container_res = make_json_request(container_url, payload)
                
                if "id" in container_res:
                    publish_url = f"https://graph.facebook.com/v19.0/{request.instagram_business_id}/media_publish"
                    pub_payload = {
                        "creation_id": container_res["id"],
                        "access_token": request.instagram_token
                    }
                    pub_res = make_json_request(publish_url, pub_payload)
                    results["instagram"] = {"success": True, "response": pub_res}
                else:
                    results["instagram"] = {"success": False, "error": "Failed to create media container", "details": container_res}
            else:
                results["instagram"] = {"success": False, "error": "Instagram API does not support local base64 images directly. Please use automation webhook for full support."}
        except Exception as e:
            results["instagram"] = {"success": False, "error": str(e)}

# Selenium Profile Directory in the project folder
PROFILE_DIR = os.path.join(os.getcwd(), "whatsapp_selenium_profile")

def get_whatsapp_driver():
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={PROFILE_DIR}")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def run_whatsapp_post_bg(channel_name: str, text: str, image_str: str):
    driver = None
    temp_image_path = None
    try:
        print(f"[WhatsApp Automation] Initializing browser for channel: {channel_name}")
        driver = get_whatsapp_driver()
        driver.get("https://web.whatsapp.com")
        
        wait = WebDriverWait(driver, 60)
        
        search_box = wait.until(EC.presence_of_element_located((
            By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]'
        )))
        
        search_box.clear()
        search_box.send_keys(channel_name)
        time.sleep(3)
        search_box.send_keys(Keys.ENTER)
        time.sleep(3)
        
        if image_str and image_str.startswith("data:image"):
            header, encoded = image_str.split(",", 1)
            mime_type = header.split(";")[0].split(":")[1]
            ext = mime_type.split("/")[1]
            image_bytes = base64.b64decode(encoded)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as temp_file:
                temp_file.write(image_bytes)
                temp_image_path = temp_file.name
            
            attach_btn = wait.until(EC.element_to_be_clickable((
                By.XPATH, '//div[@title="Attach"] | //span[@data-icon="plus"]'
            )))
            attach_btn.click()
            time.sleep(1.5)
            
            file_input = driver.find_element(By.XPATH, '//input[@type="file"]')
            file_input.send_keys(temp_image_path)
            time.sleep(3)
            
            caption_box = wait.until(EC.presence_of_element_located((
                By.XPATH, '//div[@contenteditable="true"][@data-tab="10"] | //div[@contenteditable="true"][@aria-placeholder="Add a caption"]'
            )))
            caption_box.send_keys(text)
            time.sleep(1.5)
            
            send_media_btn = wait.until(EC.element_to_be_clickable((
                By.XPATH, '//span[@data-icon="send"] | //div[@aria-label="Send"]'
            )))
            send_media_btn.click()
            time.sleep(4)
            print("[WhatsApp Automation] Successfully posted to WhatsApp Channel with image!")
        else:
            message_box = wait.until(EC.presence_of_element_located((
                By.XPATH, '//div[@contenteditable="true"][@data-tab="10"] | //div[@aria-placeholder="Type a message"]'
            )))
            message_box.send_keys(text)
            time.sleep(1.5)
            message_box.send_keys(Keys.ENTER)
            time.sleep(3)
            print("[WhatsApp Automation] Successfully posted text to WhatsApp Channel!")
    except Exception as e:
        print(f"[WhatsApp Automation] Failed to post message: {e}")
    finally:
        if driver:
            driver.quit()
        if temp_image_path and os.path.exists(temp_image_path):
            try:
                os.remove(temp_image_path)
            except Exception:
                pass

@app.post("/post-social")
async def post_to_social_media(request: SocialPostRequest, background_tasks: BackgroundTasks):
    results = {}
    caption = f"{request.title}\n\nPrice: {request.price} {request.currency}\n\n{request.description}\n\nBuy here: {request.link}"
    
    # 1. TikTok Direct API Posting
    if request.tiktok_enabled and request.tiktok_access_token:
        try:
            tiktok_url = "https://open.tiktokapis.com/v2/post/publish/content/init/"
            payload = {
                "post_info": {
                    "title": request.title[:150],
                    "description": caption[:2000],
                    "disable_comment": False
                },
                "source_info": {
                    "source": "PULL_FROM_URL",
                    "video_url": request.image
                },
                "post_mode": "DIRECT_POST",
                "media_type": "PHOTO" if not request.image.lower().endswith((".mp4", ".mov", ".avi", ".mkv")) else "VIDEO"
            }
            req_data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(tiktok_url, data=req_data, method='POST')
            req.add_header('Authorization', f'Bearer {request.tiktok_access_token}')
            req.add_header('Content-Type', 'application/json')
            
            with urllib.request.urlopen(req) as response:
                res = json.loads(response.read().decode('utf-8'))
            results["tiktok"] = {"success": True, "response": res}
        except Exception as e:
            results["tiktok"] = {"success": False, "error": str(e)}

    # 2. Direct Facebook Graph API Posting
    if request.facebook_enabled and request.facebook_page_id and request.facebook_page_token:
        try:
            fb_url = f"https://graph.facebook.com/v19.0/{request.facebook_page_id}/photos"
            if request.image.startswith("data:image"):
                header, encoded = request.image.split(",", 1)
                mime_type = header.split(";")[0].split(":")[1]
                image_bytes = base64.b64decode(encoded)
                files = {'source': ('image.png', image_bytes, mime_type)}
                fields = {'message': caption, 'access_token': request.facebook_page_token}
                res = make_multipart_request(fb_url, fields, files)
            else:
                fields = {'url': request.image, 'message': caption, 'access_token': request.facebook_page_token}
                data = urllib.parse.urlencode(fields).encode('utf-8')
                req = urllib.request.Request(fb_url, data=data, method='POST')
                with urllib.request.urlopen(req) as response:
                    res = json.loads(response.read().decode('utf-8'))
            results["facebook"] = {"success": True, "response": res}
        except Exception as e:
            results["facebook"] = {"success": False, "error": str(e)}

    # 3. Direct Instagram Graph API Posting
    if request.instagram_enabled and request.instagram_business_id and request.instagram_token:
        try:
            if not request.image.startswith("data:image"):
                container_url = f"https://graph.facebook.com/v19.0/{request.instagram_business_id}/media"
                payload = {
                    "image_url": request.image,
                    "caption": caption,
                    "access_token": request.instagram_token
                }
                container_res = make_json_request(container_url, payload)
                
                if "id" in container_res:
                    publish_url = f"https://graph.facebook.com/v19.0/{request.instagram_business_id}/media_publish"
                    pub_payload = {
                        "creation_id": container_res["id"],
                        "access_token": request.instagram_token
                    }
                    pub_res = make_json_request(publish_url, pub_payload)
                    results["instagram"] = {"success": True, "response": pub_res}
                else:
                    results["instagram"] = {"success": False, "error": "Failed to create media container", "details": container_res}
            else:
                results["instagram"] = {"success": False, "error": "Instagram API does not support local base64 images directly. Please use automation webhook for full support."}
        except Exception as e:
            results["instagram"] = {"success": False, "error": str(e)}

    # 4. WhatsApp Channel automation (via Selenium in background)
    if request.whatsapp_enabled and request.whatsapp_channel_name:
        background_tasks.add_task(
            run_whatsapp_post_bg, 
            request.whatsapp_channel_name, 
            caption, 
            request.image
        )
        results["whatsapp"] = {"success": True, "status": "queued_in_background"}

    return {"status": "completed", "results": results}


if __name__ == '__main__':
    print("==========================================================")
    print("Starting AYE Store Telegram Gateway...")
    print("==========================================================")
    
    if not GATEWAY_API_KEY:
        print("WARNING: TELEGRAM_GATEWAY_API_KEY is not set. /send-telegram will accept all requests without verification.")
    
    # Pre-authorize and log in via terminal if needed before starting web server (only if no StringSession)
    if not SESSION_STRING:
        print("No TELEGRAM_SESSION environment variable found. Starting interactive client...")
        client.start()
        try:
            generated_session = StringSession.save(client.session)
            if generated_session:
                print("\n================ TELEGRAM_SESSION (Copy to Render) ================")
                print(generated_session)
                print("===================================================================\n")
        except Exception as session_err:
            print(f"Could not generate TELEGRAM_SESSION string automatically: {session_err}")
    else:
        print("TELEGRAM_SESSION environment variable found. Running in headless mode.")
    
    # Run FastAPI server
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
