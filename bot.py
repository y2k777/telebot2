import os
import time
import secrets
import sqlite3

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

STAFF_CHAT_ID = -1003941910641

GROUP_LINK = "https://t.me/cornballsv2"

LTC_ADDRESS = "0xf02E25A7722f4937e92ebCC67c2DEE9B58C503eB"

ADMIN_IDS = {
    8910478622, 7792840636
}

ORDER_TIMEOUT = 10800

# =========================================================
# DATABASE
# =========================================================

conn = sqlite3.connect(
    "orders.db",
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders (

    order_id TEXT PRIMARY KEY,
    user_id INTEGER,
    username TEXT,
    product TEXT,
    note TEXT,
    amount TEXT,
    status TEXT,
    created_at INTEGER

)
""")

conn.commit()

# =========================================================
# TEMP STATE
# =========================================================

order_drafts = {}

status_waiting = {}

# =========================================================
# PRODUCTS
# =========================================================

PRODUCTS = {

    "intelx": {
        "name": "IntelX Lookup - First x3 Free",
        "price": "0.0090 LTC"
    },

    "basic": {
        "name": "Basic Person Search",
        "price": "0.096 LTC"
    },

    "comprehensive": {
        "name": "Comprehensive Report",
        "price": "0.28 LTC"
    },

    "full": {
        "name": "Full Background Report",
        "price": "0.068 LTC"
    },

    "phone": {
        "name": "Social Catfish Report - Free",
        "price": "0.000 LTC"
    },

    "email": {
        "name": "Osint.Industries Report",
        "price": "0.0097 LTC"
    },

    "aihoto": {
        "name": "AI Photo Geo-Location Report",
        "price": "0.095 LTC"
    },

    "db": {
        "name": "Data Breach Report",
        "price": "0.020 LTC"
    },

    "leakosint": {
        "name": "LeakOsint Lookup - Free",
        "price": "0.000 LTC"
    },

    "dl": {
        "name": "DL Lookup",
        "price": "0.28 LTC"
    },

    "tlo": {
        "name": "TLO",
        "price": "0.30 LTC"
    },

    "npd": {
        "name": "NPD",
        "price": "0.18 LTC"
    },

    "logs": {
        "name": "Website ULP Logs",
        "price": "0.015 LTC"
    },

    "discord": {
        "name": "Discord Lookup",
        "price": "0.019 LTC"
    },

    "aiperson": {
        "name": "AI Person Search",
        "price": "0.035 LTC"
    },

    "handbook": {
        "name": "Free OSINT Handbook",
        "price": "0.00 LTC"
    }
}

# =========================================================
# HELPERS
# =========================================================

def gen_order_id():
    return "ORD-" + secrets.token_hex(4).upper()

def is_admin(user_id):
    return user_id in ADMIN_IDS

# =========================================================
# MENUS
# =========================================================

def main_menu():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🛒 Order",
                callback_data="buy"
            )
        ],

        [
            InlineKeyboardButton(
                "📦 Products",
                callback_data="products"
            ),

            InlineKeyboardButton(
                "📋 Order Status",
                callback_data="status"
            )
        ],

        [
            InlineKeyboardButton(
                "💬 Group Telegram",
                url=GROUP_LINK
            )
        ],

        [
            InlineKeyboardButton(
                "ℹ️ Information",
                callback_data="info"
            )
        ]
    ])

def buy_menu():

    buttons = []

    for key, product in PRODUCTS.items():

        buttons.append([

            InlineKeyboardButton(
                f"{product['name']} - {product['price']}",
                callback_data=f"buy_{key}"
            )

        ])

    buttons.append([
        InlineKeyboardButton(
            "⬅ Back",
            callback_data="back"
        )
    ])

    return InlineKeyboardMarkup(buttons)

# =========================================================
# TEXT
# =========================================================

WELCOME_TEXT = """
◇ Welcome to v2 ◇

▸ Premium lookup & investigative services.
▸ Use the menu below to begin.
"""

PRODUCT_TEXT = """
🔎 - IntelX Lookups - 
IX lookup - Uses System ID to download an Intelx breach / log. - FIRST x3 ARE FREE

🕵 ️- Basic Persons Search -
A basic person search. Will gather basic details about a person, like age and location.

🕵-️- Comprehensive Person Search -
Extensive PII report, including family, address history and marriage certificates.

🕵-️- Full Report -
Full background check - Includes TLOxp, DL, comprehensive person search and criminal records.

🔎 - Social Catfish Lookup -
A free lookup from socialcatfish.com. - FREE

🔎 - Osint.Industries - 
Multi platform OSINT checker and verifier - checks websites such as Facebook, Snapchat, Apple, Google, etc...

🔎 - Discord Lookup -
Uses breached Discord DB's and RestoreCord DB's.

🔎 - Breach Search -
Uses multiple different data breach aggregators such as Snusbase and Fetchbase to show leaked information on a website / company / individual.

🔎 - LeakOsint Search - 
Uses the LeakOsint API to lookup information, including PII, breached info and NPD. - FREE

🔎 - DL Search -
Provides you with the DL of the target.

🔎 - NPD Search -
Provides you with information from the National Public Database.

🔎 - AI Search -
Uses AI to gather and compile large amounts of information about targets. May not be 100% accurate.

🔎 - TLO -
Performs a TLO - Gathers accurate personal information, and family information. Develops connections with targets.

📖 - Website Logs - 
Get up to 10k logs for any website of your choice! Includes username/email:password:site - Fresh logins.

💻 - LeakOsint API - 
$15 credit LeakOSINT APIs - Fully upgraded API and has high request limit. Not shared.

📕 - Handbook -
A detailed handbook on using OSINT. Includes suggestions for free OSINT tools and ways of using them. - FREE
"""

INFO_TEXT = """
ℹ️ INFORMATION

• Orders are processed manually
• Free items require no payment.

== We currently accept Litecoin (LTC) only. More added soon. == 

⚠️ Important
• No fake order IDs
• No use for illegal activity
• Misuse may result in restricted access
• Orders are processed manually

💬 Support
@SlowlyFallingDown
@feario
"""

# =========================================================
# START
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=main_menu()
    )

# =========================================================
# CALLBACK BUTTONS
# =========================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query

    await q.answer()

    user = q.from_user

    # =========================
    # MAIN MENU
    # =========================

    if q.data == "back":

        await q.edit_message_text(
            text=WELCOME_TEXT,
            reply_markup=main_menu()
        )

        return

    # =========================
    # BUY MENU
    # =========================

    if q.data == "buy":

        await q.edit_message_text(
            text="🛒 Select Product",
            reply_markup=buy_menu()
        )

        return

    # =========================
    # PRODUCTS
    # =========================

    if q.data == "products":

        await q.edit_message_text(
            text=PRODUCT_TEXT,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "⬅ Back",
                        callback_data="back"
                    )
                ]
            ])
        )

        return

    # =========================
    # INFO
    # =========================

    if q.data == "info":

        await q.edit_message_text(
            text=INFO_TEXT,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "⬅ Back",
                        callback_data="back"
                    )
                ]
            ])
        )

        return

    # =========================
    # STATUS
    # =========================

    if q.data == "status":

        status_waiting[user.id] = True

        await q.edit_message_text(
            text="📋 Enter your ORDER ID:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "⬅ Back",
                        callback_data="back"
                    )
                ]
            ])
        )

        return

    # =========================
    # BUY PRODUCT
    # =========================

    if q.data.startswith("buy_"):

        key = q.data.replace("buy_", "")

        product = PRODUCTS.get(key)

        if not product:
            return

        order_drafts[user.id] = {

            "step": "username",

            "product": product["name"],

            "amount": product["price"]

        }

        await q.edit_message_text(
            text=f"""
🛒 ORDERING

📦 {product['name']}
💰 {product['price']}

👤 Enter your Telegram username:
""",

            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "⬅ Cancel",
                        callback_data="back"
                    )
                ]
            ])
        )

# =========================================================
# MESSAGE FLOW
# =========================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    text = update.message.text

    # =====================================================
    # ORDER STATUS FLOW
    # =====================================================

    if user.id in status_waiting:

        order_id = text.strip()

        status_waiting.pop(user.id, None)

        row = cursor.execute("""

            SELECT product, status
            FROM orders
            WHERE order_id=? AND user_id=?

        """, (order_id, user.id)).fetchone()

        if not row:

            await update.message.reply_text(
                "❌ Order not found."
            )

            return

        await update.message.reply_text(f"""

📋 ORDER STATUS

🆔 {order_id}

📦 {row[0]}

📌 {row[1]}

""", reply_markup=main_menu())

        return

    # =====================================================
    # ORDER CREATION FLOW
    # =====================================================

    if user.id in order_drafts:

        draft = order_drafts[user.id]

        # USERNAME STEP

        if draft["step"] == "username":

            draft["username"] = text

            draft["step"] = "note"

            await update.message.reply_text(
                "📝 Search Term (EG: Name, Phone, System ID)"
            )

            return

        # NOTE STEP

        if draft["step"] == "note":

            draft["note"] = text

            order_id = gen_order_id()

            created_at = int(time.time())

            expires = created_at + ORDER_TIMEOUT

            cursor.execute("""

                INSERT INTO orders
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)

            """, (

                order_id,

                user.id,

                draft["username"],

                draft["product"],

                draft["note"],

                draft["amount"],

                "Awaiting Payment",

                created_at

            ))

            conn.commit()

            await update.message.reply_text(f"""

✅ Order has been created.
🆔 {order_id}

👤 Your Username:
{draft['username']}

📝 Search Term:
{draft['note']}

📦 Product:
{draft['product']}


━━━━━━━━━━━━━━━

💸 SEND LTC TO:
{LTC_ADDRESS}

💰 EXACT AMMOUNT:
{draft['amount']}

━━━━━━━━━━━━━━━

⌛ Expires:
{time.strftime('%H:%M:%S', time.localtime(expires))}

""", reply_markup=main_menu())

            # STAFF ALERT

            await context.bot.send_message(

                STAFF_CHAT_ID,

                f"""

🆕 NEW ORDER

🆔 {order_id}

👤 @{user.username}

📦 {draft['product']}

💰 {draft['amount']}

👤 Username:
{draft['username']}

📝 Search Term:
{draft['note']}

"""
            )

            del order_drafts[user.id]

            return

# =========================================================
# ADMIN: APPROVE
# =========================================================

async def approve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    if len(context.args) != 1:

        return await update.message.reply_text(
            "/approve <order_id>"
        )

    order_id = context.args[0]

    cursor.execute("""

        UPDATE orders
        SET status='Approved - Awaiting Delivery'
        WHERE order_id=?

    """, (order_id,))

    conn.commit()

    row = cursor.execute("""

        SELECT user_id
        FROM orders
        WHERE order_id=?

    """, (order_id,)).fetchone()

    if row:

        await context.bot.send_message(

            row[0],

            f"""

✅ ORDER APPROVED

🆔 {order_id}

Your order has been approved
and is awaiting delivery.

"""
        )

    await update.message.reply_text(
        "Approved."
    )

# =========================================================
# ADMIN: DENY
# =========================================================

async def deny_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    if len(context.args) != 1:

        return await update.message.reply_text(
            "/deny <order_id>"
        )

    order_id = context.args[0]

    cursor.execute("""

        UPDATE orders
        SET status='Denied'
        WHERE order_id=?

    """, (order_id,))

    conn.commit()

    row = cursor.execute("""

        SELECT user_id
        FROM orders
        WHERE order_id=?

    """, (order_id,)).fetchone()

    if row:

        await context.bot.send_message(

            row[0],

            f"""

❌ ORDER DENIED

🆔 {order_id}

Your order has been denied.

"""
        )

    await update.message.reply_text(
        "Denied."
    )

# =========================================================
# ADMIN: SEND
# =========================================================

async def send_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    if len(context.args) < 2:

        return await update.message.reply_text(
            "/send <order_id> <message>"
        )

    order_id = context.args[0]

    msg = " ".join(context.args[1:])

    row = cursor.execute("""

        SELECT user_id
        FROM orders
        WHERE order_id=?

    """, (order_id,)).fetchone()

    if not row:

        return await update.message.reply_text(
            "Order not found."
        )

    await context.bot.send_message(

        row[0],

        f"""

📩 MESSAGE ABOUT YOUR ORDER

🆔 {order_id}

{msg}

""",

        disable_web_page_preview=False

    )

    await update.message.reply_text(
        "Message sent."
    )

# =========================================================
# ADMIN: DELIVER
# =========================================================

async def deliver_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    if len(context.args) < 2:

        return await update.message.reply_text(
            "/deliver <order_id> <delivery>"
        )

    order_id = context.args[0]

    delivery_text = " ".join(context.args[1:])

    cursor.execute("""

        UPDATE orders
        SET status='Delivered'
        WHERE order_id=?

    """, (order_id,))

    conn.commit()

    row = cursor.execute("""

        SELECT user_id
        FROM orders
        WHERE order_id=?

    """, (order_id,)).fetchone()

    if not row:

        return await update.message.reply_text(
            "Order not found."
        )

    await context.bot.send_message(

        row[0],

        f"""

📦 ORDER DELIVERED

🆔 {order_id}

{delivery_text}

""",

        disable_web_page_preview=False

    )

    await update.message.reply_text(
        "Delivered."
    )

# =========================================================
# ADMIN: ORDERS
# =========================================================

async def orders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    rows = cursor.execute("""

        SELECT order_id, username, product, status
        FROM orders
        ORDER BY created_at DESC
        LIMIT 20

    """).fetchall()

    if not rows:

        return await update.message.reply_text(
            "No orders found."
        )

    msg = "📦 RECENT ORDERS\n\n"

    for r in rows:

        msg += (

            f"🆔 {r[0]}\n"

            f"👤 {r[1]}\n"

            f"📦 {r[2]}\n"

            f"📌 {r[3]}\n\n"

        )

    await update.message.reply_text(msg)

# =========================================================
# RUN
# =========================================================

app = (
    ApplicationBuilder()
    .token(BOT_TOKEN)
    .connect_timeout(30)
    .read_timeout(30)
    .write_timeout(30)
    .build()
)

# USER

app.add_handler(CommandHandler("start", start))

app.add_handler(
    CallbackQueryHandler(button_handler)
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_message
    )
)

# ADMIN

app.add_handler(CommandHandler("approve", approve_cmd))

app.add_handler(CommandHandler("deny", deny_cmd))

app.add_handler(CommandHandler("send", send_cmd))

app.add_handler(CommandHandler("deliver", deliver_cmd))

app.add_handler(CommandHandler("orders", orders_cmd))

print("🔥 v2 running...")

app.run_polling()
