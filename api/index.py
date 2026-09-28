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

async def setup_bot():
    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("help", help_cmd))
    bot_app.add_handler(CommandHandler("about", about))
    bot_app.add_handler(CommandHandler("json", json_cmd))
    bot_app.add_handler(CommandHandler("num", num_cmd))
    bot_app.add_handler(CallbackQueryHandler(on_cb))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))
    return bot_app

@app.route('/', methods=['POST'])
def webhook():
    try:
        update_data = request.get_json()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        bot_app = loop.run_until_complete(setup_bot())
        tg_update = Update.de_json(update_data, bot_app.bot)
        loop.run_until_complete(bot_app.process_update(tg_update))
        
        loop.close()
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({'status': 'error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))