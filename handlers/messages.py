"""Mensajes de texto de Telegram: pregunta → IA (con borradores en vivo) → respuesta guardada."""

import time
import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import HISTORY_LIMIT, TELEGRAM_LIMIT, DRAFT_INTERVAL
from storage import db
from services import ai, tutor
from services.conversations import elegir_conversacion
from telegram_rich import enviar_rich, enviar_borrador, RICH_LIMIT


async def preguntar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Con memoria: se manda a la IA el historial de la conversación + la pregunta nueva
    pregunta = update.message.text
    await context.bot.send_chat_action(update.effective_chat.id, "typing")

    citado = update.message.reply_to_message
    conversacion_id = elegir_conversacion(
        update.effective_chat.id, citado.message_id if citado else None
    )
    historial = db.get_history(conversacion_id, HISTORY_LIMIT)

    try:
        respuesta_ia, cortada = await generar_respuesta(update, context, historial, pregunta)
        respuesta_ia = respuesta_ia or "(empty answer)"
        texto = respuesta_ia
        if cortada:  # la respuesta se cortó por llegar al tope de MAX_TOKENS
            texto += "\n\n*[...] answer cut off: too long*"
    except Exception:
        # Si la IA falla no se guarda nada, para que el historial no quede con preguntas sin respuesta
        logging.exception("Error al llamar a Groq")
        await update.message.reply_text("Sorry, something went wrong. Please try again later.")
        return

    enviado = await enviar_respuesta(update, context, texto)

    # Se guardan la pregunta y la respuesta (sin la nota de "cut off", que no es de la IA)
    db.save_message(conversacion_id, "user", pregunta, update.message.message_id)
    db.save_message(conversacion_id, "assistant", respuesta_ia, enviado.message_id)


async def generar_respuesta(update: Update, context: ContextTypes.DEFAULT_TYPE, historial, pregunta):
    """Pide la respuesta a la IA (services/ai.py) y la va mostrando como borrador en Telegram.

    Devuelve (texto completo, se_cortó). Si la IA falla, lanza la excepción.
    """
    chat_id = update.effective_chat.id
    usar_borradores = update.effective_chat.type == "private"  # Telegram solo los permite en privado
    draft_id = update.message.message_id  # nunca es 0 y es distinto para cada pregunta
    ultimo_borrador = 0.0

    async def al_avanzar(texto):
        # La IA avisa cada vez que llega un pedacito; aquí se decide si se manda un borrador
        nonlocal usar_borradores, ultimo_borrador
        if not usar_borradores or time.monotonic() - ultimo_borrador < DRAFT_INTERVAL:
            return  # se manda un borrador como máximo cada DRAFT_INTERVAL segundos
        try:
            await enviar_borrador(context.bot, chat_id, draft_id, texto)
        except Exception:
            logging.exception("Falló sendRichMessageDraft; se sigue sin borradores")
            usar_borradores = False
        ultimo_borrador = time.monotonic()

    mensajes = tutor.construir_mensajes(historial, pregunta)
    return await ai.generar(mensajes, al_avanzar)


async def enviar_respuesta(update: Update, context: ContextTypes.DEFAULT_TYPE, texto):
    """Manda la respuesta como rich message (con formato). Si falla, la manda como texto normal.

    Devuelve el mensaje enviado (o el primero, si se dividió) para guardar su id.
    """
    if len(texto) <= RICH_LIMIT:
        try:
            return await enviar_rich(context.bot, update.effective_chat.id, texto)
        except Exception:
            logging.exception("Falló sendRichMessage; se manda como texto normal")

    # Respaldo: texto normal, dividido en mensajes de máximo 4096 caracteres
    primer_mensaje = None
    for i in range(0, len(texto), TELEGRAM_LIMIT):
        enviado = await update.message.reply_text(texto[i:i + TELEGRAM_LIMIT])
        primer_mensaje = primer_mensaje or enviado
    return primer_mensaje
