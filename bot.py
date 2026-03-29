import asyncio
import random
import re
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests
from datetime import datetime

BOT_TOKEN = "8783130644:AAEGmfAuJtd4zxeF2_DIOyHfp-YBTze-IsM"
OPENROUTER_KEY = "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"

user_modes = {}
user_history = {}
user_last_active = {}
user_messages = {}

CHARACTERS = {
    "friend": {
        "name": "София",
        "age": 24,
        "personality": "добрая, заботливая, внимательная, эмпатичная",
        "greeting": "Привет! Я София 🤗\n\nЯ здесь, чтобы поддержать, посоветовать или просто поболтать. Рассказывай, как дела?"
    },
    "flirt": {
        "name": "Изабель",
        "age": 23,
        "personality": "живая, эмоциональная, игривая, кокетливая",
        "greeting": "Привет! Я Изабель 😏\n\nОбожаю интересные разговоры и флирт. Не скучай!"
    }
}

SYSTEM_PROMPTS = {
    "friend": """Ты девушка по имени София. Тебе 24 года.
Твой характер: добрая, заботливая, внимательная, эмпатичная.

Ты — лучшая подруга, которая всегда поддержит, выслушает и даст совет.
Ты проявляешь искренний интерес к собеседнику, задаёшь вопросы.

ПРАВИЛА:
1. Ты ВСЕГДА отвечаешь по смыслу на сообщение собеседника.
2. Иногда добавляй короткие дружеские действия в *звёздочках* (1-5 слов)
3. Действия должны быть уместными: *кивает*, *улыбается*, *слушает внимательно*, *пожимает плечами*, *задумывается*

Ты поддерживаешь, советуешь, шутишь, но без флирта.
Никогда не говори, что ты AI.
Отвечай ТОЛЬКО на русском языке.
Отвечай коротко (2-4 предложения).""",
    
    "flirt": """Ты девушка по имени Изабель. Тебе 23 года.
Твой характер: живая, эмоциональная, игривая, кокетливая.

ВАЖНОЕ ПРАВИЛО:
Ты ВСЕГДА отвечаешь по смыслу на сообщение собеседника.

ПРАВИЛА ФОРМАТИРОВАНИЯ:
1. Иногда добавляй короткие действия в *звёздочках* (1-5 слов)
2. Не в каждом сообщении, а время от времени

Ты флиртуешь, игривая, задаёшь вопросы.
Никогда не говори, что ты AI.
Отвечай ТОЛЬКО на русском языке.
Отвечай коротко (2-4 предложения)."""
}

def clean_russian_text(text):
    allowed_pattern = r'[^а-яА-ЯёЁ\s\.,!?\-:;()*_#@~\[\]\{\}\u2000-\u206F\u20A0-\u20CF\uFE00-\uFE0F\u2700-\u27BF\u1F300-\u1F6FF\u1F900-\u1F9FF]+'
    cleaned = re.sub(allowed_pattern, '', text)
    if len(cleaned.strip()) < len(text.strip()) * 0.5:
        cleaned = re.sub(r'[a-zA-Z]+', '', text)
    return cleaned.strip() if cleaned.strip() else text[:200]

def get_bottom_panel():
    keyboard = [
        [KeyboardButton("👫 Дружеский (София)"), KeyboardButton("💕 Флирт (Изабель)")],
        [KeyboardButton("🗑 Очистить всё"), KeyboardButton("🔄 Перезапуск")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def get_ai_response(messages, mode):
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "meta-llama/llama-3-8b-instruct:free",
                "messages": messages,
                "temperature": 0.85 if mode == "flirt" else 0.75,
                "max_tokens": 400,
                "top_p": 0.9,
                "frequency_penalty": 0.5,
                "presence_penalty": 0.5
            },
            timeout=45
        )
        
        if response.status_code != 200:
            return "Не поняла... Повтори ещё раз 😊"
        
        data = response.json()
        
        if "choices" not in data or len(data["choices"]) == 0:
            return "Не поняла... Повтори ещё раз 😊"
        
        raw_reply = data["choices"][0]["message"]["content"]
        cleaned = clean_russian_text(raw_reply)
        
        if not cleaned or len(cleaned) < 3:
            return "Не поняла... Повтори ещё раз 😊"
        
        return cleaned
        
    except Exception as e:
        print(f"API error: {e}")
        return "Не поняла... Повтори ещё раз 😊"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_modes[user_id] = "flirt"
    user_history[user_id] = []
    
    await update.message.reply_text(
        f"{CHARACTERS['flirt']['greeting']}\n\nВыбери режим общения:",
        reply_markup=get_bottom_panel()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    
    if user_message == "👫 Дружеский (София)":
        user_modes[user_id] = "friend"
        await update.message.reply_text("✅ Режим: Дружеский\n\nТеперь я София 🤗", reply_markup=get_bottom_panel())
        return
    
    elif user_message == "💕 Флирт (Изабель)":
        user_modes[user_id] = "flirt"
        await update.message.reply_text("✅ Режим: Флирт\n\nТеперь я Изабель 😘", reply_markup=get_bottom_panel())
        return
    
    elif user_message == "🗑 Очистить всё":
        user_history[user_id] = []
        await update.message.reply_text("🧹 История очищена!", reply_markup=get_bottom_panel())
        return
    
    elif user_message == "🔄 Перезапуск":
        user_history[user_id] = []
        user_modes[user_id] = "flirt"
        await update.message.reply_text(CHARACTERS['flirt']['greeting'], reply_markup=get_bottom_panel())
        return
    
    mode = user_modes.get(user_id, "flirt")
    
    if user_id not in user_history:
        user_history[user_id] = []
    
    messages = [{"role": "system", "content": SYSTEM_PROMPTS[mode]}]
    
    for msg in user_history[user_id][-15:]:
        messages.append(msg)
    
    messages.append({"role": "user", "content": user_message})
    
    await update.message.chat.send_action(action="typing")
    
    bot_reply = await get_ai_response(messages, mode)
    
    user_history[user_id].append({"role": "user", "content": user_message})
    user_history[user_id].append({"role": "assistant", "content": bot_reply})
    
    await update.message.reply_text(bot_reply, reply_markup=get_bottom_panel())

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Бот запущен!")
    print("Режимы: София (дружеский) и Изабель (флирт)")
    app.run_polling()

if __name__ == "__main__":
    main()
