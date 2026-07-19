const express = require('express');
const { default: makeWASocket, DisconnectReason, delay, initAuthCreds, BufferJSON, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const pino = require('pino');
const qrcode = require('qrcode');
const axios = require('axios');
const FormData = require('form-data');
const fs = require('fs');
const path = require('path');

// --- In-Memory Log Capturer ---
const logs = [];
const originalLog = console.log;
const originalError = console.error;
const originalWarn = console.warn;

function addLog(type, args) {
    const timestamp = new Date().toISOString();
    const message = args.map(arg => typeof arg === 'object' ? JSON.stringify(arg) : arg).join(' ');
    logs.push(`[${timestamp}] [${type}] ${message}`);
    if (logs.length > 300) {
        logs.shift();
    }
}

console.log = (...args) => {
    originalLog(...args);
    addLog('INFO', args);
};
console.error = (...args) => {
    originalError(...args);
    addLog('ERROR', args);
};
console.warn = (...args) => {
    originalWarn(...args);
    addLog('WARN', args);
};

const app = express();
const port = process.env.PORT || 8001;

app.use(express.json());

// Enable CORS
app.use((req, res, next) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
    if (req.method === 'OPTIONS') return res.sendStatus(200);
    next();
});

// ----------------------------------------------------
// ⚙️ CONFIGURATION
// ----------------------------------------------------
const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN || "";
const TELEGRAM_ADMIN_CHAT_ID = process.env.TELEGRAM_ADMIN_CHAT_ID || "";
const TELEGRAM_GATEWAY_API_KEY = process.env.TELEGRAM_GATEWAY_API_KEY || "";
const FIREBASE_API_KEY = process.env.FIREBASE_API_KEY || "";
const FIREBASE_PROJECT_ID = process.env.FIREBASE_PROJECT_ID || "";

const REQUIRED_ENV_VARS = [
    ['TELEGRAM_BOT_TOKEN', TELEGRAM_BOT_TOKEN],
    ['TELEGRAM_ADMIN_CHAT_ID', TELEGRAM_ADMIN_CHAT_ID],
    ['FIREBASE_API_KEY', FIREBASE_API_KEY],
    ['FIREBASE_PROJECT_ID', FIREBASE_PROJECT_ID]
];

const missingEnvVars = REQUIRED_ENV_VARS
    .filter(([, value]) => !String(value || '').trim())
    .map(([name]) => name);

if (missingEnvVars.length > 0) {
    console.error(`[Config] Missing required environment variables: ${missingEnvVars.join(', ')}`);
    process.exit(1);
}

let sock = null;
let isReady = false;

function extractChannelInviteCode(channelLink = '') {
    let code = String(channelLink || '').trim();
    if (code.includes('/channel/')) {
        code = code.split('/channel/')[1].split('/')[0].split('?')[0];
    } else if (code.includes('whatsapp.com/')) {
        code = code.split('whatsapp.com/')[1].split('/')[0].split('?')[0];
    }
    return code;
}

function buildProductCaption(product = {}) {
    const formattedPrice = product.currency === 'LBP'
        ? `${Number(product.price || 0).toLocaleString()} L.L.`
        : `$${Number(product.price || 0).toFixed(2)}`;

    const hiddenMarker = product.id ? `\n\n\u2063product:${product.id}\u2063` : '';

    return (
        `🛍️ *${product.title || 'Untitled Product'}*\n\n` +
        `💵 *Price:* ${formattedPrice}\n\n` +
        `📝 *Description:*\n${product.description || 'No description available.'}` +
        hiddenMarker
    );
}

async function resolveChannelByInviteLink(channelLink) {
    const code = extractChannelInviteCode(channelLink);
    if (!code) {
        throw new Error('Missing or invalid WhatsApp channel invite link');
    }

    console.log(`Resolving WhatsApp Channel invite code: ${code}`);
    const metadata = await sock.newsletterMetadata('invite', code);
    const channelJid = metadata.id;
    console.log(`Resolved Channel JID: ${channelJid}`);
    return channelJid;
}

async function deleteChannelMessageById(channelJid, messageId) {
    if (!messageId) return false;
    const message = await sock.getMessageById(messageId);
    if (!message) return false;
    await message.delete(true);
    return true;
}

async function deleteChannelMessageByProductId(channelJid, productId) {
    if (!channelJid || !productId) return false;
    const channel = await sock.getChatById(channelJid);
    if (!channel?.fetchMessages) return false;

    const messages = await channel.fetchMessages({ limit: 50, fromMe: true });
    const marker = `product:${productId}`;
    const match = messages.find((msg) => String(msg.body || '').includes(marker));
    if (!match) return false;
    await match.delete(true);
    return true;
}

async function syncWhatsAppChannelProduct(req, res, defaultAction = 'upsert') {
    const { action = defaultAction, channelLink, product = {}, productId, messageId } = req.body || {};

    if (!channelLink) {
        return res.status(400).json({ success: false, error: 'Missing channelLink' });
    }

    if (!isReady || !sock) {
        return res.status(503).json({ success: false, error: 'WhatsApp gateway is not connected' });
    }

    try {
        const channelJid = await resolveChannelByInviteLink(channelLink);
        const resolvedProduct = {
            ...product,
            id: product.id || productId || ''
        };

        if (action === 'delete') {
            const deletedById = await deleteChannelMessageById(channelJid, messageId || resolvedProduct.whatsappChannelMessageId || resolvedProduct.whatsapp_channel_message_id || '');
            if (!deletedById) {
                await deleteChannelMessageByProductId(channelJid, resolvedProduct.id);
            }

            return res.json({
                success: true,
                action: 'delete',
                channel_jid: channelJid
            });
        }

        if (action === 'update') {
            const existingMessageId = messageId || resolvedProduct.whatsappChannelMessageId || resolvedProduct.whatsapp_channel_message_id || '';
            if (existingMessageId) {
                await deleteChannelMessageById(channelJid, existingMessageId).catch((err) => {
                    console.warn('Could not delete existing channel message before update:', err.message);
                });
            }
        }

        const caption = buildProductCaption(resolvedProduct);
        let sent;
        if (resolvedProduct.image) {
            sent = await sock.sendMessage(channelJid, {
                image: { url: resolvedProduct.image },
                caption
            });
        } else {
            sent = await sock.sendMessage(channelJid, { text: caption });
        }

        const returnedMessageId = sent?.key?.id || null;
        return res.json({
            success: true,
            action,
            channel_jid: channelJid,
            message_id: returnedMessageId
        });
    } catch (err) {
        console.error('Error syncing product to WhatsApp channel:', err.message);
        return res.status(500).json({ success: false, error: err.message });
    }
}
let lastQrSentTime = 0;
let latestPairingCode = null;
let latestPairingAt = 0;
let lastPairingPhone = '';

const DEFAULT_PAIRING_PHONE = process.env.WHATSAPP_PAIRING_NUMBER || '';

function normalizePairingPhone(phone) {
    if (!phone) return '';
    let digits = String(phone).replace(/\D/g, '');
    if (digits.startsWith('00')) digits = digits.slice(2);

    // Lebanon normalization: +96103xxxxxx / 0096103xxxxxx -> 9613xxxxxx
    if (digits.startsWith('9610') && digits.length >= 11) {
        digits = `961${digits.slice(4)}`;
    }

    // Local Lebanese style: 03xxxxxx -> 9613xxxxxx
    if (digits.length === 8 && digits.startsWith('0')) {
        digits = `961${digits.slice(1)}`;
    }

    return digits;
}

function normalizeDestinationPhone(phone) {
    let digits = normalizePairingPhone(phone);
    if (!digits) return '';

    // Handle common local Lebanese formats automatically if country code is omitted.
    if (digits.length === 8 && digits.startsWith('0')) {
        digits = `961${digits.slice(1)}`;
    } else if (digits.length === 7 && digits.startsWith('3')) {
        digits = `961${digits}`;
    }

    return digits;
}

function formatPairingCode(code) {
    if (!code) return '';
    return String(code).match(/.{1,4}/g)?.join('-') || String(code);
}

async function generatePairingCode(phone, source = 'manual') {
    if (!sock) {
        return { ok: false, error: 'WhatsApp socket is not initialized yet' };
    }

    if (isReady) {
        return { ok: false, error: 'WhatsApp is already connected. Pairing code is blocked while an active session is online.' };
    }

    const cleanPhone = normalizePairingPhone(phone);
    if (!cleanPhone) {
        return { ok: false, error: 'Invalid phone number for pairing' };
    }

    if (sock.authState?.creds?.registered) {
        return { ok: false, error: 'Session is already registered. Logout first to pair a new number.' };
    }

    try {
        const pairingCode = await sock.requestPairingCode(cleanPhone);
        const formattedCode = formatPairingCode(pairingCode);

        latestPairingCode = formattedCode;
        latestPairingAt = Date.now();
        lastPairingPhone = cleanPhone;

        console.log(`🔐 Pairing code generated (${source}) for ${cleanPhone}: ${formattedCode}`);
        await notifyTelegramAdmin(`🔐 WhatsApp Pairing Code (${source})\nPhone: +${cleanPhone}\nCode: ${formattedCode}`);

        return {
            ok: true,
            code: formattedCode,
            phone: cleanPhone
        };
    } catch (err) {
        console.error('❌ Failed to generate pairing code:', err.message);
        return { ok: false, error: err.message };
    }
}

async function notifyTelegramAdmin(text) {
    if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_ADMIN_CHAT_ID) return;
    try {
        await axios.post(
            `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`,
            {
                chat_id: TELEGRAM_ADMIN_CHAT_ID,
                text,
                disable_web_page_preview: true
            },
            { timeout: 10000 }
        );
    } catch (err) {
        console.error('⚠️ Failed to notify Telegram admin:', err.message);
    }
}

function verifyTelegramApiKey(req, res) {
    if (!TELEGRAM_GATEWAY_API_KEY) return true;
    const provided = req.get('X-API-Key') || '';
    if (provided !== TELEGRAM_GATEWAY_API_KEY) {
        res.status(401).json({ success: false, error: 'Invalid or missing API key' });
        return false;
    }
    return true;
}

function buildTelegramOrderKeyboard(orderId) {
    if (!orderId) return undefined;
    return {
        inline_keyboard: [[
            {
                text: '👁️ View Order in Dashboard',
                url: 'https://aye-commercial-4b871.web.app/store_dashboard.html#tab-orders'
            }
        ]]
    };
}

// ----------------------------------------------------
// 🔥 FIREBASE FIRESTORE REST CLIENT
// ----------------------------------------------------
class FirebaseFirestoreClient {
    constructor(apiKey, projectId) {
        this.apiKey = apiKey;
        this.projectId = projectId;
        this.idToken = null;
        this.tokenExpiry = 0;
    }

    async authenticate() {
        const url = `https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=${this.apiKey}`;
        try {
            const res = await axios.post(url, { returnSecureToken: true }, { timeout: 10000 });
            this.idToken = res.data.idToken;
            const expiresIn = parseInt(res.data.expiresIn || '3600', 10);
            this.tokenExpiry = Date.now() + (expiresIn - 60) * 1000;
            return this.idToken;
        } catch (e) {
            console.error("Firebase Authentication Failed:", e.message);
            throw e;
        }
    }

    async getIdToken() {
        if (!this.idToken || Date.now() > this.tokenExpiry) {
            await this.authenticate();
        }
        return this.idToken;
    }

    async getHeaders() {
        const token = await this.getIdToken();
        return {
            "Authorization": `Bearer ${token}`,
            "Content-Type": "application/json"
        };
    }

    parseValue(val) {
        if ("stringValue" in val) return val.stringValue;
        if ("doubleValue" in val) return parseFloat(val.doubleValue);
        if ("integerValue" in val) return parseInt(val.integerValue);
        if ("booleanValue" in val) return val.booleanValue;
        if ("mapValue" in val) {
            const parsed = {};
            const fields = val.mapValue.fields || {};
            for (const k in fields) {
                parsed[k] = this.parseValue(fields[k]);
            }
            return parsed;
        }
        if ("arrayValue" in val) {
            const values = val.arrayValue.values || [];
            return values.map(v => this.parseValue(v));
        }
        return null;
    }

    parseDocument(docData) {
        const fields = docData.fields || {};
        const name = docData.name || "";
        const docId = name.split("/").pop() || "";
        const parsed = { id: docId };
        for (const k in fields) {
            parsed[k] = this.parseValue(fields[k]);
        }
        return parsed;
    }

    async getOrders(statusFilter = null) {
        const url = `https://firestore.googleapis.com/v1/projects/${this.projectId}/databases/(default)/documents:runQuery`;
        const query = {
            structuredQuery: {
                from: [{ collectionId: "orders" }],
                orderBy: [{
                    field: { fieldPath: "createdAt" },
                    direction: "DESCENDING"
                }],
                limit: 100
            }
        };

        try {
            const headers = await this.getHeaders();
            const res = await axios.post(url, query, { headers, timeout: 10000 });
            let orders = [];
            for (const item of res.data) {
                if (item.document) {
                    orders.push(this.parseDocument(item.document));
                }
            }
            if (statusFilter) {
                orders = orders.filter(o => o.status === statusFilter);
            }
            return orders;
        } catch (e) {
            console.error("Error fetching orders from Firestore:", e.message);
            // Retry auth once
            try {
                await this.authenticate();
                const headers = await this.getHeaders();
                const res = await axios.post(url, query, { headers, timeout: 10000 });
                let orders = [];
                for (const item of res.data) {
                    if (item.document) {
                        orders.push(this.parseDocument(item.document));
                    }
                }
                if (statusFilter) {
                    orders = orders.filter(o => o.status === statusFilter);
                }
                return orders;
            } catch (retryErr) {
                console.error("Retry fetching orders failed:", retryErr.message);
                return [];
            }
        }
    }

    async getOrderById(orderId) {
        const url = `https://firestore.googleapis.com/v1/projects/${this.projectId}/databases/(default)/documents/orders/${orderId}`;
        try {
            const headers = await this.getHeaders();
            const res = await axios.get(url, { headers, timeout: 10000 });
            return this.parseDocument(res.data);
        } catch (e) {
            console.error(`Error fetching order ${orderId}:`, e.message);
            return null;
        }
    }

    async updateOrderStatus(orderId, newStatus) {
        const url = `https://firestore.googleapis.com/v1/projects/${this.projectId}/databases/(default)/documents/orders/${orderId}?updateMask.fieldPaths=status`;
        const payload = {
            fields: {
                status: { stringValue: newStatus }
            }
        };
        try {
            const headers = await this.getHeaders();
            await axios.patch(url, payload, { headers, timeout: 10000 });
            return true;
        } catch (e) {
            console.error(`Error updating status of order ${orderId}:`, e.message);
            return false;
        }
    }

    async updateOrderCustomerPhone(orderId, phone) {
        const url = `https://firestore.googleapis.com/v1/projects/${this.projectId}/databases/(default)/documents/orders/${orderId}?updateMask.fieldPaths=customer.phone`;
        const payload = {
            fields: {
                customer: {
                    mapValue: {
                        fields: {
                            phone: { stringValue: phone }
                        }
                    }
                }
            }
        };
        try {
            const headers = await this.getHeaders();
            await axios.patch(url, payload, { headers, timeout: 10000 });
            return true;
        } catch (e) {
            console.error(`Error updating phone of order ${orderId}:`, e.message, e.response ? JSON.stringify(e.response.data) : '');
            return false;
        }
    }

    async getDocument(collection, docId) {
        const url = `https://firestore.googleapis.com/v1/projects/${this.projectId}/databases/(default)/documents/${collection}/${docId}`;
        try {
            const headers = await this.getHeaders();
            const res = await axios.get(url, { headers, timeout: 10000 });
            return this.parseDocument(res.data);
        } catch (e) {
            if (e.response && e.response.status === 404) {
                return null;
            }
            console.error(`Error getting document ${collection}/${docId}:`, e.message, e.response ? JSON.stringify(e.response.data) : '');
            return null;
        }
    }

    async setDocument(collection, docId, data) {
        const url = `https://firestore.googleapis.com/v1/projects/${this.projectId}/databases/(default)/documents/${collection}/${docId}`;
        const payload = {
            fields: {
                data: { stringValue: data }
            }
        };
        try {
            const headers = await this.getHeaders();
            await axios.patch(url, payload, { headers, timeout: 10000 });
            return true;
        } catch (e) {
            console.error(`Error setting document ${collection}/${docId}:`, e.message, e.response ? JSON.stringify(e.response.data) : '');
            return false;
        }
    }

    async deleteDocument(collection, docId) {
        const url = `https://firestore.googleapis.com/v1/projects/${this.projectId}/databases/(default)/documents/${collection}/${docId}`;
        try {
            const headers = await this.getHeaders();
            await axios.delete(url, { headers, timeout: 10000 });
            return true;
        } catch (e) {
            console.error(`Error deleting document ${collection}/${docId}:`, e.message);
            return false;
        }
    }
}

const dbClient = new FirebaseFirestoreClient(FIREBASE_API_KEY, FIREBASE_PROJECT_ID);

// ----------------------------------------------------
// 🤖 TELEGRAM QR CODE FORWARDER
// ----------------------------------------------------
async function sendQRToTelegram(qrCodeString) {
    // Throttling: send QR at most once every 30 seconds
    const now = Date.now();
    if (now - lastQrSentTime < 30000) return;
    lastQrSentTime = now;

    try {
        const buffer = await qrcode.toBuffer(qrCodeString, { scale: 8 });
        const form = new FormData();
        form.append('chat_id', TELEGRAM_ADMIN_CHAT_ID);
        form.append('caption', '📷 Scan this QR code with WhatsApp on your phone to connect your AYE Market WhatsApp Bot!');
        form.append('photo', buffer, { filename: 'whatsapp_qr.png', contentType: 'image/png' });

        await axios.post(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendPhoto`, form, {
            headers: form.getHeaders(),
            timeout: 15000
        });
        console.log('🟢 WhatsApp Login QR Code successfully forwarded to Telegram!');
    } catch (err) {
        console.error('❌ Failed to send QR to Telegram:', err.message);
    }
}

// ----------------------------------------------------
// 🤖 FIRESTORE BASED BAILEYS AUTH STATE
// ----------------------------------------------------
async function useFirestoreAuthState(dbClient, collectionName = 'whatsapp_session') {
    let creds = await dbClient.getDocument(collectionName, 'creds');
    if (!creds || !creds.data) {
        creds = initAuthCreds();
        const jsonStr = JSON.stringify(creds, BufferJSON.replacer);
        await dbClient.setDocument(collectionName, 'creds', jsonStr);
    } else {
        try {
            creds = JSON.parse(creds.data, BufferJSON.reviver);
        } catch (e) {
            console.error("Error parsing creds from Firestore, resetting:", e.message);
            creds = initAuthCreds();
            const jsonStr = JSON.stringify(creds, BufferJSON.replacer);
            await dbClient.setDocument(collectionName, 'creds', jsonStr);
        }
    }

    return {
        state: {
            creds,
            keys: {
                get: async (type, ids) => {
                    const data = {};
                    await Promise.all(
                        ids.map(async (id) => {
                            const docId = `${type}-${id}`;
                            const value = await dbClient.getDocument(collectionName, docId);
                            if (value && value.data) {
                                try {
                                    data[id] = JSON.parse(value.data, BufferJSON.reviver);
                                } catch (e) {
                                    console.error(`Error parsing key ${docId}:`, e.message);
                                }
                            }
                        })
                    );
                    return data;
                },
                set: async (data) => {
                    const tasks = [];
                    for (const category in data) {
                        for (const id in data[category]) {
                            const value = data[category][id];
                            const docId = `${category}-${id}`;
                            if (value) {
                                const jsonStr = JSON.stringify(value, BufferJSON.replacer);
                                tasks.push(dbClient.setDocument(collectionName, docId, jsonStr));
                            } else {
                                tasks.push(dbClient.deleteDocument(collectionName, docId));
                            }
                        }
                    }
                    await Promise.all(tasks);
                }
            }
        },
        saveCreds: async (nextCreds) => {
            if (nextCreds && typeof nextCreds === 'object') {
                creds = { ...creds, ...nextCreds };
            }
            const jsonStr = JSON.stringify(creds, BufferJSON.replacer);
            await dbClient.setDocument(collectionName, 'creds', jsonStr);
        }
    };
}

// ----------------------------------------------------
// 🤖 WHATSAPP SOCKET CONNECTION (BAILEYS)
// ----------------------------------------------------
async function connectToWhatsApp() {
    try {
        console.log('🔄 Fetching/Initializing WhatsApp session from Firestore...');
        const { state, saveCreds } = await useFirestoreAuthState(dbClient);

        let version;
        try {
            console.log('🔄 Fetching latest WhatsApp Web version...');
            const latest = await fetchLatestBaileysVersion();
            version = latest.version;
            console.log(`Using WhatsApp Web v${version.join('.')}, isLatest: ${latest.isLatest}`);
        } catch (err) {
            console.error('⚠️ Failed to fetch latest WhatsApp Web version, falling back to default:', err.message);
            version = [2, 3000, 1017531287]; // standard fallback
        }
        
        sock = makeWASocket({
            version,
            auth: state,
            printQRInTerminal: true,
            logger: pino({ level: 'silent' })
        });

        // Auto-generate pairing code if a default phone is configured and session is not registered yet.
        if (DEFAULT_PAIRING_PHONE && !sock.authState?.creds?.registered) {
            setTimeout(async () => {
                const autoPair = await generatePairingCode(DEFAULT_PAIRING_PHONE, 'startup');
                if (!autoPair.ok) {
                    console.warn(`⚠️ Startup pairing code request failed: ${autoPair.error}`);
                }
            }, 2500);
        }

        sock.ev.on('connection.update', async (update) => {
            const { connection, lastDisconnect, qr } = update;
            console.log('Connection Update:', JSON.stringify(update));

            if (qr) {
                console.log('🆕 QR Code received from WhatsApp. Forwarding to Telegram...');
                await sendQRToTelegram(qr);
            }

            if (connection === 'close') {
                isReady = false;
                const statusCode = lastDisconnect?.error?.output?.statusCode;
                const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
                console.log(`⚠️ WhatsApp connection closed (Status: ${statusCode}). Reconnecting: ${shouldReconnect}`);
                if (shouldReconnect) {
                    setTimeout(connectToWhatsApp, 5000);
                } else {
                    console.log('🔴 WhatsApp session logged out (401). Clearing session from Firestore and reconnecting to generate new QR...');
                    try {
                        await dbClient.deleteDocument('whatsapp_session', 'creds');
                        console.log('🟢 Successfully deleted creds document from Firestore.');
                    } catch (delErr) {
                        console.error('⚠️ Failed to delete creds document:', delErr.message);
                    }
                    setTimeout(connectToWhatsApp, 5000);
                }
            } else if (connection === 'open') {
                console.log('🚀 WhatsApp Gateway is successfully connected and online!');
                isReady = true;
            }
        });

        sock.ev.on('creds.update', saveCreds);

        // Handle Incoming WhatsApp Messages/Commands
        sock.ev.on('messages.upsert', async (m) => {
            if (m.type !== 'notify') return;
            const msg = m.messages[0];
            if (!msg.message) return;

            let senderJid = msg.key.remoteJidAlt || msg.key.remoteJid;
            if (senderJid && senderJid.endsWith('@lid') && sock.signalRepository?.lidMapping?.getPNForLID) {
                try {
                    const resolvedJid = await sock.signalRepository.lidMapping.getPNForLID(senderJid);
                    if (resolvedJid) {
                        senderJid = resolvedJid;
                    }
                } catch (resolveErr) {
                    console.error('Error resolving JID LID to PN:', resolveErr.message);
                }
            }
            const rawText = (msg.message.conversation || msg.message.extendedTextMessage?.text || '').trim();
            const text = rawText.toLowerCase();

            if (!text) return;

            console.log(`Received message from ${senderJid}: ${rawText}`);



            // Try to match Order ID from incoming customer order message
            let matchedOrderId = null;
            // Clean asterisks (used for bold formatting in WhatsApp like *رقم المعاملة:*)
            const cleanTextForMatching = text.replace(/\*/g, '');
            const txMatchEn = cleanTextForMatching.match(/transaction\s*(?:number)?\s*:\s*(\d{6})/i);
            const txMatchAr = cleanTextForMatching.match(/رقم\s*المعاملة\s*:\s*(\d{6})/i);
            if (txMatchEn) {
                matchedOrderId = txMatchEn[1];
            } else if (txMatchAr) {
                matchedOrderId = txMatchAr[1];
            } else {
                const genericMatch = cleanTextForMatching.match(/(?:order|transaction|transaction\s*number|رقم\s*المعاملة|معاملة|طلب|#)\s*:?\s*#?(\d{6})/i);
                if (genericMatch) {
                    matchedOrderId = genericMatch[1];
                }
            }

            if (matchedOrderId) {
                let cleanPhone = senderJid.split('@')[0];
                
                // If it is a self-message (admin testing) or the JID is our own JID, use the admin phone from Firestore gateways settings
                const botJidPrefix = sock.user ? sock.user.id.split('@')[0].split(':')[0] : '';
                if (msg.key.fromMe || (botJidPrefix && cleanPhone === botJidPrefix)) {
                    try {
                        const gateways = await dbClient.getDocument('settings', 'gateways');
                        if (gateways && gateways.whatsapp_admin_phone) {
                            const settingsPhone = gateways.whatsapp_admin_phone.replace(/\D/g, '');
                            if (settingsPhone) {
                                cleanPhone = settingsPhone;
                                console.log(`🎯 Admin testing or LID JID detected. Defaulting to admin phone: ${cleanPhone}`);
                            }
                        }
                    } catch (err) {
                        console.error('⚠️ Failed to fetch admin phone for testing fallback:', err.message);
                    }
                }

                console.log(`🎯 Matched Order #${matchedOrderId} to sender phone ${cleanPhone}. Updating Firestore...`);
                const updateSuccess = await dbClient.updateOrderCustomerPhone(matchedOrderId, cleanPhone);
                if (updateSuccess) {
                    console.log(`✅ Successfully saved phone number ${cleanPhone} to Order #${matchedOrderId}`);
                    // Notify Telegram admin that phone is linked
                    try {
                        await axios.post(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
                            chat_id: TELEGRAM_ADMIN_CHAT_ID,
                            text: `📞 تم ربط رقم الهاتف +${cleanPhone} بالطلب رقم #${matchedOrderId} تلقائياً`
                        }, { timeout: 10000 });
                        console.log(`🟢 Notified Telegram admin about linked phone for Order #${matchedOrderId}`);
                    } catch (tgErr) {
                        console.error('⚠️ Failed to notify Telegram admin:', tgErr.message);
                    }

                    // Try to edit original Telegram notification to replace placeholder with real phone number
                    try {
                        const orderDoc = await dbClient.getOrderById(matchedOrderId);
                        if (orderDoc && orderDoc.telegram_message_id && orderDoc.telegram_message_text) {
                            let originalText = orderDoc.telegram_message_text;
                            let updatedText = originalText
                                .replace('Auto-linking via WhatsApp...', `+${cleanPhone}`)
                                .replace('جاري الربط عبر واتساب...', `+${cleanPhone}`);
                            
                            await axios.post(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/editMessageText`, {
                                chat_id: TELEGRAM_ADMIN_CHAT_ID,
                                message_id: parseInt(orderDoc.telegram_message_id, 10),
                                text: updatedText,
                                parse_mode: 'Markdown',
                                reply_markup: {
                                    inline_keyboard: [[{
                                        text: '👁️ View Order Details',
                                        callback_data: `view_${matchedOrderId}`
                                    }]]
                                }
                            }, { timeout: 10000 });
                            console.log(`🟢 Successfully edited original Telegram message for Order #${matchedOrderId}`);
                        }
                    } catch (editErr) {
                        console.error('⚠️ Failed to edit original Telegram message:', editErr.message);
                    }
                } else {
                    console.error(`❌ Failed to save phone number ${cleanPhone} to Order #${matchedOrderId}`);
                }
            }

            // Simple interactive menu triggers
            if (!msg.key.fromMe) {
                if (text === 'menu' || text === 'list' || text === 'start' || text === 'help') {
                    await sendMainMenu(senderJid);
                } else if (text === 'active' || text === '1') {
                    await sendActiveOrders(senderJid);
                } else if (text === 'history' || text === '2') {
                    await sendOrdersHistory(senderJid);
                } else if (text.startsWith('view ')) {
                    const orderId = text.substring(5).trim();
                    await sendOrderDetails(senderJid, orderId);
                } else if (text.startsWith('ship ')) {
                    const orderId = text.substring(5).trim();
                    await updateOrder(senderJid, orderId, 'Shipped');
                } else if (text.startsWith('deliver ')) {
                    const orderId = text.substring(8).trim();
                    await updateOrder(senderJid, orderId, 'Delivered');
                } else if (text.startsWith('cancel ')) {
                    const orderId = text.substring(7).trim();
                    await updateOrder(senderJid, orderId, 'Cancelled');
                }
            }
        });
    } catch (error) {
        console.error('❌ Error during WhatsApp initialization:', error.message);
        console.log('🔄 Retrying connection in 10 seconds...');
        isReady = false;
        setTimeout(connectToWhatsApp, 10000);
    }
}

// ----------------------------------------------------
// 🤖 BOT RESPONSE HANDLERS
// ----------------------------------------------------
async function sendMainMenu(jid) {
    const menu = 
        `👋 *Welcome to AYE Market WhatsApp Admin Bot!*\n\n` +
        `Please reply with a number or command:\n` +
        `*1* or *active* - View pending active orders\n` +
        `*2* or *history* - View latest orders history\n` +
        `*help* - Show this menu again`;
    await sock.sendMessage(jid, { text: menu });
}

async function sendActiveOrders(jid) {
    await sock.sendMessage(jid, { text: '🔄 Fetching active orders...' });
    const orders = await dbClient.getOrders('Pending');
    if (!orders || orders.length === 0) {
        await sock.sendMessage(jid, { text: '✅ No pending active orders found.' });
        return;
    }

    let response = `📋 *Active Orders (${orders.length} pending):*\n\n`;
    for (const o of orders) {
        const name = o.customer?.name || 'Unknown';
        const total = o.totalAmount || 0;
        response += `📦 *#${o.id}* - ${name} ($${total.toFixed(2)})\n` +
                    `👉 Reply with: *view ${o.id}*\n\n`;
    }
    await sock.sendMessage(jid, { text: response });
}

async function sendOrdersHistory(jid) {
    await sock.sendMessage(jid, { text: '🔄 Fetching orders history...' });
    const orders = await dbClient.getOrders();
    if (!orders || orders.length === 0) {
        await sock.sendMessage(jid, { text: '📭 No orders found in the database.' });
        return;
    }

    const latest = orders.slice(0, 15);
    let response = `📜 *Latest Orders History (${latest.length} shown):*\n\n`;
    for (const o of latest) {
        const name = o.customer?.name || 'Unknown';
        const total = o.totalAmount || 0;
        const status = o.status || 'Pending';
        let emoji = '🟡';
        if (status === 'Shipped') emoji = '🔵';
        else if (status === 'Delivered') emoji = '🟢';
        else if (status === 'Cancelled') emoji = '🔴';

        response += `${emoji} *#${o.id}* - ${name} ($${total.toFixed(2)}) [${status}]\n` +
                    `👉 Reply with: *view ${o.id}*\n\n`;
    }
    await sock.sendMessage(jid, { text: response });
}

async function sendOrderDetails(jid, orderId) {
    await sock.sendMessage(jid, { text: `🔄 Fetching details for order #${orderId}...` });
    const o = await dbClient.getOrderById(orderId);
    if (!o) {
        await sock.sendMessage(jid, { text: `❌ Order #${orderId} not found.` });
        return;
    }

    let itemsText = '';
    const items = o.items || [];
    for (const item of items) {
        itemsText += ` - ${item.title} x${item.quantity || 1} ($${(item.price || 0).toFixed(2)})\n`;
    }

    const details = 
        `📦 *Order Details #${o.id}*\n` +
        `━━━━━━━━━━━━━━━━━━━\n` +
        `👤 *Customer:* ${o.customer?.name || 'N/A'}\n` +
        `📞 *Phone:* ${o.customer?.phone || 'N/A'}\n` +
        `📍 *Address:* ${o.customer?.address || 'N/A'}\n` +
        `📧 *Email:* ${o.customer?.email || 'N/A'}\n` +
        `━━━━━━━━━━━━━━━━━━━\n` +
        `🛍️ *Items:*\n${itemsText}` +
        `━━━━━━━━━━━━━━━━━━━\n` +
        `💵 *Total:* $${(o.totalAmount || 0).toFixed(2)}\n` +
        `🚦 *Status:* ${o.status || 'Pending'}\n\n` +
        `⚙️ *Manage Status:* (Reply with command)\n` +
        `👉 *ship ${o.id}* (Set to Shipped)\n` +
        `👉 *deliver ${o.id}* (Set to Delivered)\n` +
        `👉 *cancel ${o.id}* (Set to Cancelled)`;

    await sock.sendMessage(jid, { text: details });
}

async function updateOrder(jid, orderId, status) {
    await sock.sendMessage(jid, { text: `🔄 Updating order #${orderId} status to ${status}...` });
    const success = await dbClient.updateOrderStatus(orderId, status);
    if (success) {
        await sock.sendMessage(jid, { text: `✅ Order #${orderId} updated to *${status}* successfully!` });
        await sendOrderDetails(jid, orderId);
    } else {
        await sock.sendMessage(jid, { text: `❌ Failed to update order #${orderId}.` });
    }
}

// ----------------------------------------------------
// 🚀 REST API ENDPOINT (FOR STOREFRONT NOTIFICATIONS)
// ----------------------------------------------------
app.post('/send-message', async (req, res) => {
    const { to, message } = req.body;

    if (!to || !message) {
        return res.status(400).json({ success: false, error: 'Missing to or message' });
    }

    if (!isReady || !sock) {
        return res.status(503).json({ success: false, error: 'WhatsApp gateway is not connected' });
    }

    try {
        const cleanedPhone = normalizeDestinationPhone(to);
        if (!cleanedPhone) {
            return res.status(400).json({ success: false, error: 'Invalid phone number format' });
        }

        const lookup = await sock.onWhatsApp(cleanedPhone);
        const recipient = Array.isArray(lookup) ? lookup[0] : null;

        if (!recipient || !recipient.exists) {
            console.warn(`[WARN] [send-message] Recipient is not on WhatsApp: +${cleanedPhone}`);
            return res.status(400).json({
                success: false,
                error: `Recipient +${cleanedPhone} is not registered on WhatsApp`
            });
        }

        const targetJid = recipient.jid || `${cleanedPhone}@s.whatsapp.net`;
        console.log(`[INFO] [send-message] Attempting to send message to ${targetJid}. Text: ${message}`);
        
        const sent = await sock.sendMessage(targetJid, { text: message });
        const messageId = sent?.key?.id || null;
        console.log(`[INFO] [send-message] Message accepted by WhatsApp for ${targetJid}. id=${messageId || 'n/a'}`);
        res.json({
            success: true,
            message: 'Message sent successfully via WhatsApp Bot',
            to: targetJid,
            message_id: messageId
        });
    } catch (err) {
        console.error('[ERROR] Error sending storefront message:', err.message);
        res.status(500).json({ success: false, error: err.message });
    }
});

// Telegram forwarder endpoint (admin notifications)
app.post('/send-telegram', async (req, res) => {
    if (!verifyTelegramApiKey(req, res)) return;

    const { message, is_admin, order_id } = req.body || {};

    if (!message) {
        return res.status(400).json({ success: false, error: 'Missing message' });
    }

    // This gateway supports Telegram as an admin forwarder only.
    if (is_admin === false) {
        return res.status(400).json({
            success: false,
            error: 'This gateway supports Telegram admin forwarding only (set is_admin=true).'
        });
    }

    if (!TELEGRAM_BOT_TOKEN || !TELEGRAM_ADMIN_CHAT_ID) {
        return res.status(503).json({ success: false, error: 'Telegram forwarder is not configured' });
    }

    try {
        const payload = {
            chat_id: TELEGRAM_ADMIN_CHAT_ID,
            text: String(message),
            disable_web_page_preview: true
        };

        const keyboard = buildTelegramOrderKeyboard(order_id);
        if (keyboard) payload.reply_markup = keyboard;

        const tgRes = await axios.post(
            `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`,
            payload,
            { timeout: 10000 }
        );

        return res.json({
            success: true,
            ok: true,
            message: 'Notification sent to admin via Telegram bot',
            telegram_message_id: tgRes?.data?.result?.message_id || null
        });
    } catch (err) {
        const errorText = err?.response?.data?.description || err.message;
        console.error('❌ Failed to forward /send-telegram message:', errorText);
        return res.status(500).json({ success: false, error: errorText });
    }
});

// Bulk Send Message Endpoint
app.post('/send-bulk-message', async (req, res) => {
    const { recipients, message } = req.body;

    if (!recipients || !Array.isArray(recipients) || recipients.length === 0) {
        return res.status(400).json({ success: false, error: 'Missing or invalid recipients array' });
    }

    if (!message) {
        return res.status(400).json({ success: false, error: 'Missing message content' });
    }

    if (!isReady || !sock) {
        return res.status(503).json({ 
            success: false, 
            error: 'WhatsApp gateway is not connected',
            summary: { total: 0, sent: 0, failed: 0 }
        });
    }

    const results = [];
    const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

    for (const recipient of recipients) {
        try {
            // Clean and normalize phone number
            const cleanedPhone = normalizeDestinationPhone(recipient);
            if (!cleanedPhone) {
                results.push({
                    phone: recipient,
                    status: 'failed',
                    error: 'Invalid phone number format'
                });
                continue;
            }

            // Check if recipient exists on WhatsApp
            const lookup = await sock.onWhatsApp(cleanedPhone);
            const recipientData = Array.isArray(lookup) ? lookup[0] : null;

            if (!recipientData || !recipientData.exists) {
                console.warn(`[WARN] [send-bulk-message] Recipient not on WhatsApp: +${cleanedPhone}`);
                results.push({
                    phone: recipient,
                    status: 'failed',
                    error: 'Not registered on WhatsApp'
                });
                continue;
            }

            const targetJid = recipientData.jid || `${cleanedPhone}@s.whatsapp.net`;
            console.log(`[INFO] [send-bulk-message] Sending to ${targetJid}...`);
            
            const sent = await sock.sendMessage(targetJid, { text: message });
            const messageId = sent?.key?.id || null;
            
            console.log(`[INFO] [send-bulk-message] Message sent to ${targetJid}. id=${messageId || 'n/a'}`);
            results.push({
                phone: recipient,
                status: 'sent',
                jid: targetJid,
                message_id: messageId
            });

            // Add delay between messages to avoid rate limiting (1 second)
            await delay(1000);
        } catch (error) {
            console.error(`[ERROR] Error sending bulk message to ${recipient}:`, error.message);
            results.push({
                phone: recipient,
                status: 'failed',
                error: error.message
            });
        }
    }

    const successCount = results.filter(r => r.status === 'sent').length;
    const failureCount = results.filter(r => r.status === 'failed').length;

    res.json({
        success: failureCount === 0,
        summary: {
            total: results.length,
            sent: successCount,
            failed: failureCount
        },
        results: results
    });
});

app.post('/post-product', async (req, res) => {
    return syncWhatsAppChannelProduct(req, res, 'upsert');
});

app.post('/sync-product', async (req, res) => {
    return syncWhatsAppChannelProduct(req, res, 'upsert');
});

app.get('/status', (req, res) => {
    const registeredByCreds = !!sock?.authState?.creds?.registered;
    const registeredBySession = isReady && !!sock?.user?.id;

    res.json({
        status: isReady ? 'online' : 'offline',
        telegram_forwarder: !!TELEGRAM_BOT_TOKEN,
        pairing: {
            registered: registeredByCreds || registeredBySession,
            last_phone: lastPairingPhone || null,
            last_code: latestPairingCode || null,
            last_generated_at: latestPairingAt ? new Date(latestPairingAt).toISOString() : null
        }
    });
});

app.post('/request-pairing-code', async (req, res) => {
    const { phone } = req.body || {};
    const targetPhone = phone || DEFAULT_PAIRING_PHONE;

    if (!targetPhone) {
        return res.status(400).json({
            success: false,
            error: 'Missing phone. Provide { "phone": "+961XXXXXXXX" } or set WHATSAPP_PAIRING_NUMBER.'
        });
    }

    const result = await generatePairingCode(targetPhone, 'api');
    if (!result.ok) {
        return res.status(400).json({ success: false, error: result.error });
    }

    return res.json({
        success: true,
        phone: result.phone,
        code: result.code,
        message: 'Pairing code generated successfully'
    });
});

app.get('/logs', (req, res) => {
    res.type('text/plain').send(logs.join('\n'));
});

// Keep Alive Ping Loop to prevent sleep on Render
async function startKeepAlivePing() {
    console.log("[Keep-Alive] Initializing Render ping loop...");
    setInterval(async () => {
        try {
            const gateways = await dbClient.getDocument('settings', 'gateways');
            if (gateways && gateways.telegram_api_url) {
                const targetUrl = gateways.telegram_api_url.replace(/\/$/, '') + '/status';
                console.log(`[Keep-Alive] Pinging Telegram Gateway: ${targetUrl}`);
                const response = await axios.get(targetUrl, { timeout: 10000 });
                console.log(`[Keep-Alive] Telegram Gateway response status: ${response.status}`);
            } else {
                console.log("[Keep-Alive] No telegram_api_url configured in settings/gateways.");
            }
        } catch (err) {
            console.error("[Keep-Alive] Error pinging Telegram Gateway:", err.message);
        }
    }, 5 * 60 * 1000); // Ping every 5 minutes
}

// Start Express server and connect WhatsApp
app.listen(port, () => {
    console.log(`🚀 Express WhatsApp API Server listening on port ${port}`);
    connectToWhatsApp();
    startKeepAlivePing();
});
