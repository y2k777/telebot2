import os
import time
import secrets
import sqlite3

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# =========================
# CONFIG
# =========================

BOT_TOKEN = "os.getenv("BOT_TOKEN")"

STAFF_CHAT_ID = -1003941910641
GROUP_LINK = "https://t.me/cornballsv2"
LTC_ADDRESS = "YOUR_LTC_ADDRESS"

ADMIN_IDS = {8910478622}

ORDER_TIMEOUT = 10800  # 3 hours

# =========================
# DATABASE
# =========================

conn = sqlite3.connect("orders.db", check_same_thread=False)
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

# =========================
# STATE
# =========================

order_drafts = {}
status_waiting = {}

# =========================
# PRODUCTS
# =========================

PRODUCTS = {
    "intelx": {"name": "IntelX Lookup", "price": "0.009 LTC"},
    "basic": {"name": "Basic Search", "price": "0.020 LTC"},
    "full": {"name": "Full Report", "price": "0.080 LTC"},
}

# =========================
# HELPERS
# =========================

def is_admin(uid):
    return uid in ADMIN_IDS

def gen_order_id():
    return "ORD-" + secrets.token_hex(4).upper()

# =========================
# EXPIRY JOB
# =========================

async def expire_order(context: ContextTypes.DEFAULT_TYPE):
    order_id = context.job.data

    row = cursor.execute(
        "SELECT user_id, status FROM orders WHERE order_id=?",
        (order_id,)
    ).fetchone()

    if not row:
        return

    user_id, status = row

    if status != "Awaiting Payment":
        return

    cursor.execute(
        "UPDATE orders SET status='Expired' WHERE order_id=?",
        (order_id,)
    )
    conn.commit()

    await context.bot.send_message(
        user_id,
        f"⛔ ORDER EXPIRED\n\n🆔 {order_id}"
    )

# =========================
# MENUS
# =========================

def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Order", callback_data="buy")],
        [
            InlineKeyboardButton("📦 Products", callback_data="products"),
            InlineKeyboardButton("📋 Status", callback_data="status")
        ],
        [InlineKeyboardButton("💬 Group", url=GROUP_LINK)]
    ])

def buy_menu():
    return InlineKeyboardMarkup([
        *[
            [InlineKeyboardButton(
                f"{p['name']} - {p['price']}",
                callback_data=f"buy_{k}"
            )]
            for k, p in PRODUCTS.items()
        ],
        [InlineKeyboardButton("⬅ Back", callback_data="back")]
    ])

# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 Welcome to v2", reply_markup=main_menu())

# =========================
# CALLBACKS
# =========================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = q.from_user

    if q.data == "back":
        await q.edit_message_text("🏠 Menu", reply_markup=main_menu())
        return

    if q.data == "buy":
        await q.edit_message_text("🛒 Select product:", reply_markup=buy_menu())
        return

    if q.data == "products":
        await q.edit_message_text("📦 Products menu", reply_markup=main_menu())
        return

    if q.data == "status":
        status_waiting[user.id] = True
        await q.edit_message_text("Enter Order ID:")
        return

    if q.data.startswith("buy_"):
        key = q.data.replace("buy_", "")
        product = PRODUCTS.get(key)

        order_drafts[user.id] = {
            "step": "username",
            "product": product["name"],
            "amount": product["price"]
        }

        await q.edit_message_text("👤 Enter username:")
        return

# =========================
# MESSAGE FLOW
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text

    # STATUS CHECK
    if user.id in status_waiting:
        order_id = text.strip()
        status_waiting.pop(user.id, None)

        row = cursor.execute(
            "SELECT product, status FROM orders WHERE order_id=? AND user_id=?",
            (order_id, user.id)
        ).fetchone()

        if not row:
            return await update.message.reply_text("Not found")

        return await update.message.reply_text(
            f"{order_id}\n{row[0]}\n{row[1]}",
            reply_markup=main_menu()
        )

    # ORDER FLOW
    if user.id in order_drafts:
        draft = order_drafts[user.id]

        if draft["step"] == "username":
            draft["username"] = text
            draft["step"] = "note"
            return await update.message.reply_text("Enter search term:")

        if draft["step"] == "note":
            draft["note"] = text

            order_id = gen_order_id()
            created_at = int(time.time())

            cursor.execute("""
                INSERT INTO orders (
                    order_id, user_id, username, product,
                    note, amount, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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

            context.job_queue.run_once(
                expire_order,
                when=ORDER_TIMEOUT,
                data=order_id
            )

            await update.message.reply_text(
                f"""
✅ ORDER CREATED

🆔 {order_id}
👤 {draft['username']}
📝 {draft['note']}
📦 {draft['product']}
💰 {draft['amount']}
"""
            )

            del order_drafts[user.id]
            return

    return

# =========================
# ADMIN COMMANDS
# =========================

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    order_id = context.args[0]

    cursor.execute(
        "UPDATE orders SET status='Approved' WHERE order_id=?",
        (order_id,)
    )
    conn.commit()

    await update.message.reply_text("Approved")

async def deny(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    order_id = context.args[0]

    cursor.execute(
        "UPDATE orders SET status='Denied' WHERE order_id=?",
        (order_id,)
    )
    conn.commit()

    await update.message.reply_text("Denied")

async def deliver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

    order_id = context.args[0]
    msg = " ".join(context.args[1:])

    cursor.execute(
        "UPDATE orders SET status='Delivered' WHERE order_id=?",
        (order_id,)
    )
    conn.commit()

    row = cursor.execute(
        "SELECT user_id FROM orders WHERE order_id=?",
        (order_id,)
    ).fetchone()

    if row:
        await context.bot.send_message(row[0], msg)

    await update.message.reply_text("Delivered")

# =========================
# RUN
# =========================

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.add_handler(CommandHandler("approve", approve))
app.add_handler(CommandHandler("deny", deny))
app.add_handler(CommandHandler("deliver", deliver))

print("v2 running...")
app.run_polling()
