"""Mensajes de texto de Telegram: pregunta → IA (con borradores en vivo) → respuesta guardada."""

import asyncio
import time
import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import HISTORY_LIMIT, TELEGRAM_LIMIT, DRAFT_INTERVAL, PAUSA_ENTRE_MENSAJES
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

    ids_enviados = await enviar_respuesta(update, context, texto)
    if not ids_enviados:
        logging.error("No se pudo enviar ninguna parte de la respuesta; no se guarda nada")
        return

    # Se guardan la pregunta y la respuesta completa en una sola fila, con los ids de todos
    # sus mensajes (sin la nota de "cut off", que no es de la IA)
    db.save_message(conversacion_id, "user", pregunta, update.message.message_id)
    db.save_message(
        conversacion_id, "assistant", respuesta_ia, ids_enviados[0], ids_extra=ids_enviados[1:]
    )


async def generar_respuesta(update: Update, context: ContextTypes.DEFAULT_TYPE, historial, pregunta):
    """Pide la respuesta a la IA (services/ai.py) y la va mostrando como borrador en Telegram.

    Devuelve (texto completo, se_cortó). Si la IA falla, lanza la excepción.
    """
    chat_id = update.effective_chat.id
    usar_borradores = update.effective_chat.type == "private"  # Telegram solo los permite en privado
    draft_id = update.message.message_id  # nunca es 0 y es distinto para cada pregunta
    ultimo_borrador = 0.0
    ultimo_texto = ""

    async def al_avanzar(texto):
        # La IA avisa cada vez que llega un pedacito; aquí se decide si se manda un borrador
        nonlocal usar_borradores, ultimo_borrador, ultimo_texto
        if not usar_borradores or time.monotonic() - ultimo_borrador < DRAFT_INTERVAL:
            return  # se manda un borrador como máximo cada DRAFT_INTERVAL segundos
        parcial = tutor.texto_para_borrador(texto)  # en vivo solo se muestra el Reply
        if not parcial or parcial == ultimo_texto:
            return
        try:
            await enviar_borrador(context.bot, chat_id, draft_id, parcial)
            ultimo_texto = parcial
        except Exception:
            logging.exception("Falló sendRichMessageDraft; se sigue sin borradores")
            usar_borradores = False
        ultimo_borrador = time.monotonic()

    mensajes = tutor.construir_mensajes(historial, pregunta)
    return await ai.generar(mensajes, al_avanzar)


async def enviar_respuesta(update: Update, context: ContextTypes.DEFAULT_TYPE, texto):
    """Manda la respuesta en mensajes separados: Reply, Correction y Explanation.

    Solo el primer mensaje que llega notifica. Si una parte falla, las demás se siguen enviando.
    Devuelve los ids de todos los mensajes enviados (lista vacía si no llegó ninguno).
    """
    ids_enviados = []
    for indice, parte in enumerate(tutor.dividir_respuesta(texto)):
        if indice:
            await asyncio.sleep(PAUSA_ENTRE_MENSAJES)
        ids_enviados += await enviar_parte(update, context, parte, silencioso=bool(ids_enviados))
    return ids_enviados


async def enviar_parte(update: Update, context: ContextTypes.DEFAULT_TYPE, parte, silencioso):
    """Manda una parte como rich message (con formato). Si falla, la manda como texto normal.

    Devuelve los ids de los mensajes que sí llegaron.
    """
    if len(parte) <= RICH_LIMIT:
        try:
            enviado = await enviar_rich(context.bot, update.effective_chat.id, parte, silencioso)
            return [enviado.message_id]
        except Exception:
            logging.exception("Falló sendRichMessage; se manda como texto normal")

    # Respaldo: texto normal, dividido en mensajes de máximo 4096 caracteres
    ids = []
    try:
        for i in range(0, len(parte), TELEGRAM_LIMIT):
            enviado = await update.message.reply_text(
                parte[i:i + TELEGRAM_LIMIT], disable_notification=silencioso or bool(ids)
            )
            ids.append(enviado.message_id)
    except Exception:
        logging.exception("Tampoco se pudo enviar como texto normal")
    return ids
