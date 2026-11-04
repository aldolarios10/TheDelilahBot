from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from groq import AsyncGroq
import os
import logging
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "800"))  # tope de tokens por respuesta (cualquier modelo)

if not TOKEN or not GROQ_API_KEY or not GROQ_MODEL:
    raise SystemExit("Falta TOKEN, GROQ_API_KEY o GROQ_MODEL en el archivo .env")

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)  # oculta el log de cada petición HTTP

groq = AsyncGroq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = "You are a helpful assistant. Always answer in English, clearly and concisely."
TELEGRAM_LIMIT = 4096  # máximo de caracteres por mensaje en Telegram


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Send me any question and I'll answer it.")


async def preguntar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Sin memoria: cada mensaje se manda solo, sin historial (pregunta -> respuesta)
    pregunta = update.message.text
    await context.bot.send_chat_action(update.effective_chat.id, "typing")

    try:
        respuesta = await groq.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": pregunta},
            ],
        )
        opcion = respuesta.choices[0]
        texto = opcion.message.content or "(empty answer)"
        if opcion.finish_reason == "length":  # la respuesta se cortó por llegar al tope
            texto += "\n\n[...] (answer cut off: too long)"
    except Exception:
        logging.exception("Error al llamar a Groq")
        texto = "Sorry, something went wrong. Please try again later."

    # Si la respuesta es muy larga, se manda en varios mensajes
    for i in range(0, len(texto), TELEGRAM_LIMIT):
        await update.message.reply_text(texto[i:i + TELEGRAM_LIMIT])


app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))                                # responde a /start
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, preguntar))    # responde a mensajes de texto
app.run_polling()
