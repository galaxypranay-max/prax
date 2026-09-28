#!/usr/bin/env python3
# Vercel Serverless Function for Telegram Bot Webhook
# This adapts the polling-based bot to work on Vercel's serverless platform

import os
import sys
import json
import logging
import asyncio

# Add parent directory to path so we can import from bot.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram import Update
from telegram.ext import Application, ContextTypes

# Import all components from bot.py
from bot import (
    get_number_info,
    clean_data,
    extract_records,
    dedupe,
    prettify,
    build_json_file,
    split_msg,
    number_kb,
    start,
    help_cmd,
    about,
    json_cmd,
    num_cmd,
    handle_number,
    on_cb,
    _handle,
    BOT_TOKEN,
    BOT_NAME,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(BOT_NAME)

# Store the application instance globally
_app_instance = None

def get_app():
    """Create or return cached application instance."""
    global _app_instance
    if _app_instance is None:
        _app_instance = Application.builder().token(BOT_TOKEN).build()

        # Register all handlers
        from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters

        _app_instance.add_handler(CommandHandler("start", start))
        _app_instance.add_handler(CommandHandler("help", help_cmd))
        _app_instance.add_handler(CommandHandler("about", about))
        _app_instance.add_handler(CommandHandler("json", json_cmd))
        _app_instance.add_handler(CommandHandler("num", num_cmd))
        _app_instance.add_handler(CallbackQueryHandler(on_cb))
        _app_instance.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))

    return _app_instance

async def set_webhook_async():
    """Set the webhook URL for the bot."""
    webhook_url = os.environ.get("WEBHOOK_URL")
    if webhook_url:
        app = get_app()
        try:
            await app.bot.set_webhook(url=webhook_url)
            log.info(f"Webhook set to: {webhook_url}")
        except Exception as e:
            log.error(f"Failed to set webhook: {e}")

def handler(event, context=None):
    """Vercel serverless function handler for Telegram webhook updates."""
    try:
        # Parse the incoming event body
        body = event.get('body', '{}')
        if isinstance(body, str):
            body = json.loads(body)

        # Create telegram Update object
        update = Update.de_json(body, None)

        # Process the update
        app = get_app()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(app.process_update(update))
        finally:
            loop.close()

        return {"statusCode": 200, "body": "OK"}
    except Exception as e:
        log.error(f"Webhook handler error: {e}")
        return {"statusCode": 200, "body": "OK"}  # Always return 200 to Telegram

# Setup webhook on module import (Vercel runs this when the function is first called)
try:
    asyncio.run(set_webhook_async())
except Exception as e:
    log.warning(f"Auto webhook setup failed (manual setup needed): {e}")