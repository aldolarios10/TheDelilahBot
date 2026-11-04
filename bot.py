from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from groq import AsyncGroq
import os
import logging
from dotenv import load_dotenv
import db

load_dotenv()
TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "800"))  # tope de tokens por respuesta (cualquier modelo)
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", "10"))  # mensajes anteriores que se mandan a la IA

if not TOKEN or not GROQ_API_KEY or not GROQ_MODEL:
    raise SystemExit("Falta TOKEN, GROQ_API_KEY o GROQ_MODEL en el archivo .env")

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)  # oculta el log de cada petición HTTP

groq = AsyncGroq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = "You are a helpful assistant. Always answer in English, clearly and concisely."
TELEGRAM_LIMIT = 4096  # máximo de caracteres por mensaje en Telegram

# Comandos que aparecen en el botón "Menu" de Telegram (y como sugerencias al escribir "/")
COMANDOS = [
    BotCommand("new", "Start a new conversation"),
    BotCommand("start", "Show the welcome message"),
]


async def registrar_comandos(app):
    # Se ejecuta una vez al arrancar: le manda a Telegram la lista de comandos del menú
    await app.bot.set_my_commands(COMANDOS)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Send me any question and I'll answer it.")


async def nueva(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /new: cierra la conversación actual y empieza una nueva (la vieja queda guardada)
    db.start_new_conversation(update.effective_chat.id)
    await update.message.reply_text("Started a new conversation. What do you want to talk about?")


def elegir_conversacion(update: Update):
    """Devuelve el id de la conversación a la que va este mensaje.

    Si el usuario respondió (reply) a un mensaje guardado, se retoma esa conversación
    y queda activa. Si no, se usa la conversación activa del chat (o se crea una).
    """
    chat_id = update.effective_chat.id
    citado = update.message.reply_to_message
    if citado:
        conversacion_id = db.find_conversation_by_message(chat_id, citado.message_id)
        if conversacion_id:
            db.activate_conversation(chat_id, conversacion_id)
            return conversacion_id
    return db.get_or_create_active_conversation(chat_id)


async def preguntar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Con memoria: se manda a la IA el historial de la conversación + la pregunta nueva
    pregunta = update.message.text
    await context.bot.send_chat_action(update.effective_chat.id, "typing")

    conversacion_id = elegir_conversacion(update)
    historial = db.get_history(conversacion_id, HISTORY_LIMIT)

    try:
        respuesta = await groq.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *historial,
                {"role": "user", "content": pregunta},
            ],
        )
        opcion = respuesta.choices[0]
        respuesta_ia = opcion.message.content or "(empty answer)"
        texto = respuesta_ia
        if opcion.finish_reason == "length":  # la respuesta se cortó por llegar al tope
            texto += "\n\n[...] (answer cut off: too long)"
    except Exception:
        # Si la IA falla no se guarda nada, para que el historial no quede con preguntas sin respuesta
        logging.exception("Error al llamar a Groq")
        await update.message.reply_text("Sorry, something went wrong. Please try again later.")
        return

    # Si la respuesta es muy larga, se manda en varios mensajes; se guarda el id del primero
    primer_mensaje = None
    for i in range(0, len(texto), TELEGRAM_LIMIT):
        enviado = await update.message.reply_text(texto[i:i + TELEGRAM_LIMIT])
        primer_mensaje = primer_mensaje or enviado

    # Se guardan la pregunta y la respuesta (sin la nota de "cut off", que no es de la IA)
    db.save_message(conversacion_id, "user", pregunta, update.message.message_id)
    db.save_message(conversacion_id, "assistant", respuesta_ia, primer_mensaje.message_id)


db.init_db()  # crea las tablas si no existen

app = ApplicationBuilder().token(TOKEN).post_init(registrar_comandos).build()
app.add_handler(CommandHandler("start", start))                                # responde a /start
app.add_handler(CommandHandler("new", nueva))                                  # empieza otra conversación
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, preguntar))    # responde a mensajes de texto
app.run_polling()
