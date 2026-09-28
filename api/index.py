import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

# Import handlers from bot.py
from bot import (
    get_number_info, clean_data, extract_records, dedupe, 
    prettify, build_json_file, split_msg, number_kb,
    start, help_cmd, about, json_cmd, num_cmd, 
    handle_number, on_cb, _handle,
    BOT_TOKEN, BOT_NAME, API_URL
)

app = Flask(__name__)

# Initialize bot application globally
_bot_app = None
_event_loop = None

def get_bot_app():
    global _bot_app, _event_loop
    if _bot_app is None:
        _event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_event_loop)
        _bot_app = Application.builder().token(BOT_TOKEN).build()
        
        # Add all handlers
        _bot_app.add_handler(CommandHandler("start", start))
        _bot_app.add_handler(CommandHandler("help", help_cmd))
        _bot_app.add_handler(CommandHandler("about", about))
        _bot_app.add_handler(CommandHandler("json", json_cmd))
        _bot_app.add_handler(CommandHandler("num", num_cmd))
        _bot_app.add_handler(CallbackQueryHandler(on_cb))
        _bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))
        
    return _bot_app

@app.route('/', methods=['GET'])
def index():
    """Health check endpoint"""
    return jsonify({"status": "Telegram bot is running", "bot_name": BOT_NAME})

@app.route('/', methods=['POST'])
def webhook():
    try:
        update_data = request.get_json()
        if not update_data:
            return jsonify({"status": "error", "message": "No JSON data received"}), 400
        
        bot_app = get_bot_app()
        loop = asyncio.get_event_loop()
        tg_update = Update.de_json(update_data, bot_app.bot)
        
        # Process update in the existing event loop
        loop.run_until_complete(bot_app.process_update(tg_update))
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)), debug=False)
