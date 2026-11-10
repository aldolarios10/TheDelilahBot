"""Comandos de Telegram: /start, /new y el menú de comandos (/settings está en handlers/settings.py)."""

from telegram import Update, BotCommand
from telegram.ext import ContextTypes

from services import levels
from storage import db

# Comandos que aparecen en el botón "Menu" de Telegram (y como sugerencias al escribir "/")
COMANDOS = [
    BotCommand("new", "Start a new conversation"),
    BotCommand("settings", "Change your settings"),
    BotCommand("start", "Show the welcome message"),
]


async def registrar_comandos(app):
    # Se ejecuta una vez al arrancar: le manda a Telegram la lista de comandos del menú
    await app.bot.set_my_commands(COMANDOS)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nivel = levels.nivel_de_usuario(update.effective_user.id)
    await update.message.reply_text(
        "Hi! I'm Delilah, your English tutor. 👋\n"
        "Write to me in English about anything, and I'll help you improve.\n"
        "I remember our conversation. Use /new (or the Menu button) to start a new one.\n"
        f"Your level is {nivel}. Use /settings to change it."
    )


async def nueva(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /new: cierra la conversación actual y empieza una nueva (la vieja queda guardada)
    db.start_new_conversation(update.effective_chat.id)
    await update.message.reply_text("Started a new conversation. What do you want to talk about?")
