#!/usr/bin/env python3
# Python | DARK OSINT Bot | python-telegram-bot v20 | Astha API
# Developed by PraX
# deps: python-telegram-bot[job-queue]==20.7, requests

import json
import logging
import os
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)

# ===== CONFIG — env variables se =====
BOT_TOKEN = os.environ.get("8754893576:AAGNHqs9GWurMmYXGrCKhZsIPJVnbiTB3Nk")
API_URL   = os.environ.get(
    "API_URL",
    "https://astha-9vd8.onrender.com/tapi-3a74390dd9a68a862b9d697124bb9e04",
)
BOT_NAME  = os.environ.get("BOT_NAME", "PraX OSINT")
# =====================================

if not BOT_TOKEN:
    print("❌ BOT_TOKEN env variable missing. Exiting.")
    raise SystemExit(1)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(BOT_NAME)


# ---------- API call ----------
def get_number_info(number):
    try:
        r = requests.get(API_URL, params={"Astha": number}, timeout=25)
        if r.status_code == 200:
            data = r.json()
            if data.get("status") == "success":
                return data
        return None
    except Exception as e:
        log.error("API error: %s", e)
        return None


# ---------- clean data ----------
def clean_data(data):
    """Strip unwanted fields: credit, telegram, channel, api_info, id, alt."""
    if not data:
        return data

    for k in ("credit", "telegram", "channel", "api_info", "username",
              "provider", "developer", "remaining"):
        data.pop(k, None)

    if isinstance(data.get("result"), dict):
        for k in ("credit", "telegram", "channel", "api_info", "username",
                  "provider", "developer", "remaining"):
            data["result"].pop(k, None)

    def strip_rec(rec):
        if not isinstance(rec, dict):
            return rec
        for k in ("id", "credit", "username", "channel", "telegram", "api_info"):
            rec.pop(k, None)
        return rec

    if isinstance(data.get("data"), list):
        data["data"] = [strip_rec(r) for r in data["data"]]
    elif isinstance(data.get("data"), dict):
        data["data"] = strip_rec(data["data"])

    if isinstance(data.get("result"), dict):
        r = data["result"]
        if isinstance(r.get("data"), list):
            r["data"] = [strip_rec(x) for x in r["data"]]
        elif isinstance(r.get("data"), dict):
            r["data"] = strip_rec(r["data"])

    return data


# ---------- normalize to list of records ----------
def extract_records(data):
    """API response ke kisi bhi shape se records nikaalo."""
    if not data:
        return []

    if isinstance(data.get("result"), dict):
        r = data["result"]
        if isinstance(r.get("data"), list):
            return r["data"]
        if isinstance(r.get("data"), dict):
            return [r["data"]]

    if isinstance(data.get("data"), list):
        return data["data"]
    if isinstance(data.get("data"), dict):
        return [data["data"]]

    return []


# ---------- dedupe ----------
def dedupe(records):
    seen, out = set(), []
    for rec in records or []:
        if not isinstance(rec, dict):
            continue
        key = json.dumps({k: v for k, v in rec.items() if v}, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        out.append(rec)
    return out


# ---------- pretty formatted ----------
def prettify(data, number):
    records = dedupe(extract_records(data))

    if not records:
        return (
            "❌ <b>No records found</b>\n"
            "🔢 Number: <code>" + str(number) + "</code>"
        )

    header = (
        "🕵️ <b>" + BOT_NAME + " — Result</b>\n"
        "🔢 Number: <code>" + str(number) + "</code>\n"
        "🧹 Unique: <b>" + str(len(records)) + "</b>"
    )

    parts = [header]
    for i, rec in enumerate(records, 1):
        block = ["<b>━━━ Record #" + str(i) + " ━━━</b>"]
        field_map = [
            ("name",        "👤 Name"),
            ("fname",       "👨 Father"),
            ("father_name", "👨 Father"),
            ("mobile",      "📱 Mobile"),
            ("alt",         "📞 Alt"),
            ("alt_number",  "📞 Alt"),
            ("email",       "📧 Email"),
            ("circle",      "📡 Circle"),
            ("address",     "🏠 Address"),
        ]
        seen_labels = set()
        for key, label in field_map:
            if label in seen_labels:
                continue
            v = rec.get(key)
            if v is None or v == "" or str(v).lower() == "null":
                continue
            seen_labels.add(label)
            val = str(v)
            if key == "email" and "@" not in val and " " in val:
                val = val.replace(" ", "@", 1)
            if key == "address" and "!" in val:
                val = ", ".join(p.strip() for p in val.split("!") if p.strip())
            block.append(label + ": <code>" + val + "</code>")
        parts.append("\n".join(block))

    return "\n\n".join(parts)


# ---------- clean JSON ----------
def build_json_file(number, data):
    records = dedupe(extract_records(data))
    for r in records:
        for k in ("id", "credit", "username", "channel", "telegram", "api_info"):
            r.pop(k, None)
    return json.dumps(
        {
            "number": number,
            "total_records": len(records),
            "data": records,
        },
        ensure_ascii=False,
        indent=2,
    )


# ---------- split long msg ----------
def split_msg(text, size=4000):
    return [text[i:i + size] for i in range(0, len(text), size)]


# ---------- inline buttons ----------
def number_kb(number):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 Lookup Again", callback_data="again:" + number),
            InlineKeyboardButton("📄 JSON", callback_data="json:" + number),
        ]
    ])


# ---------- /start ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "💀 <b>" + BOT_NAME + "</b>\n\n"
        "Send 10-digit mobile number → poora data milega.\n"
        "Example: <code>9876543210</code>\n\n"
        "Commands:\n"
        "/json &lt;number&gt;  — raw JSON\n"
        "/num &lt;number&gt;   — formatted info"
    )
    await update.message.reply_text(text, parse_mode="HTML")


# ---------- /help ----------
async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>📖 Help — " + BOT_NAME + "</b>\n\n"
        "• 10-digit number bhejo → full info\n"
        "• <code>/json 9876543210</code> → raw JSON\n"
        "• <code>/num 9876543210</code> → formatted\n\n"
        "Sirf Indian mobile (6/7/8/9 se start).",
        parse_mode="HTML",
    )


# ---------- /about ----------
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🕵️ <b>" + BOT_NAME + "</b>\nPython + python-telegram-bot\n"
        "👑 Developed by PraX",
        parse_mode="HTML",
    )


# ---------- /json ----------
async def json_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: <code>/json 9876543210</code>",
                                        parse_mode="HTML")
        return
    number = context.args[0].strip()
    if not (number.isdigit() and len(number) == 10):
        await update.message.reply_text("❌ Send exactly 10 digits!")
        return
    msg = await update.message.reply_text("⏳ Searching...")
    data = get_number_info(number)
    if not data:
        await msg.edit_text("❌ No data found!")
        return
    raw = build_json_file(number, data)
    if len(raw) > 4000:
        raw = raw[:4000] + "\n... (truncated)"
    await msg.edit_text("<pre>" + raw + "</pre>", parse_mode="HTML")


# ---------- /num ----------
async def num_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: <code>/num 9876543210</code>",
                                        parse_mode="HTML")
        return
    await _handle(update, context.args[0].strip())


# ---------- text handler ----------
async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _handle(update, update.message.text.strip())


async def _handle(update: Update, raw_text: str):
    number = "".join(ch for ch in raw_text if ch.isdigit())
    if len(number) != 10 or number[0] not in "6789":
        await update.message.reply_text(
            "❌ Send exactly 10-digit Indian mobile (6/7/8/9 se start)."
        )
        return

    msg = await update.message.reply_text("⏳ Searching...")
    data = get_number_info(number)

    if not data:
        await msg.edit_text("❌ No data found!")
        return

    body = prettify(data, number)
    chunks = split_msg(body)
    for i, chunk in enumerate(chunks):
        if i == 0:
            await msg.edit_text(chunk, parse_mode="HTML",
                                reply_markup=number_kb(number))
        else:
            await update.message.reply_text(chunk, parse_mode="HTML")


# ---------- callback buttons ----------
async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    try:
        action, number = q.data.split(":", 1)
    except ValueError:
        return

    if action == "again":
        data = get_number_info(number)
        if not data:
            await q.message.reply_text("❌ No data found!")
            return
        body = prettify(data, number)
        for i, chunk in enumerate(split_msg(body)):
            if i == 0:
                await q.message.reply_text(chunk, parse_mode="HTML",
                                           reply_markup=number_kb(number))
            else:
                await q.message.reply_text(chunk, parse_mode="HTML")

    elif action == "json":
        data = get_number_info(number)
        if not data:
            await q.message.reply_text("❌ No data found!")
            return
        raw = build_json_file(number, data)
        await q.message.reply_document(
            document=raw.encode("utf-8"),
            filename=number + "_info.json",
            caption="📎 JSON — <code>" + number + "</code>",
            parse_mode="HTML",
        )


# ---------- main ----------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("json", json_cmd))
    app.add_handler(CommandHandler("num", num_cmd))
    app.add_handler(CallbackQueryHandler(on_cb))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))

    print("💀 " + BOT_NAME + " is running!")
    print("👑 Developed by PraX")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()