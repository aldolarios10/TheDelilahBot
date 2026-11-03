from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

async def hola(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hola mundo")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", hola))        # responde a /start
app.add_handler(MessageHandler(filters.ALL, hola))    # responde a cualquier mensaje
app.run_polling()