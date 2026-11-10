"""Menú de ajustes: el comando /settings y sus botones. Todo ocurre en un mismo mensaje."""

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from services import levels

# Datos que lleva cada botón. Telegram los devuelve cuando alguien toca el botón.
PATRON_AJUSTES = r"^ajustes:"
_MENU = "ajustes:menu"
_NIVELES = "ajustes:niveles"
_ELEGIR_NIVEL = "ajustes:nivel:"

_BOTON_ATRAS = InlineKeyboardButton("⬅️ Back", callback_data=_MENU)


def _pantalla_menu(user_id):
    """Primera pantalla. Para agregar otro ajuste, basta con sumar otra fila de botones."""
    nivel = levels.nivel_de_usuario(user_id)
    botones = [[InlineKeyboardButton(f"🎚️ Level: {nivel}", callback_data=_NIVELES)]]
    return "⚙️ Settings", InlineKeyboardMarkup(botones)


def _pantalla_niveles(user_id):
    """Pantalla para elegir nivel, con una palomita en el nivel actual y dos botones por fila."""
    actual = levels.nivel_de_usuario(user_id)
    botones = [
        InlineKeyboardButton(f"{nivel} ✓" if nivel == actual else nivel, callback_data=f"{_ELEGIR_NIVEL}{nivel}")
        for nivel in levels.NIVELES
    ]
    filas = [botones[i:i + 2] for i in range(0, len(botones), 2)]
    return "🎚️ Choose your level", InlineKeyboardMarkup([*filas, [_BOTON_ATRAS]])


def _pantalla_confirmacion(nivel):
    return f"✅ Level set to {nivel}", InlineKeyboardMarkup([[_BOTON_ATRAS]])


async def ajustes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /settings: muestra la primera pantalla del menú
    texto, teclado = _pantalla_menu(update.effective_user.id)
    await update.message.reply_text(texto, reply_markup=teclado)


async def manejar_boton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Responde a los botones del menú cambiando el mismo mensaje. El nivel es de quien toca el botón."""
    consulta = update.callback_query
    await consulta.answer()  # sin esto, Telegram deja el botón "cargando"
    user_id = update.effective_user.id

    if consulta.data == _MENU:
        texto, teclado = _pantalla_menu(user_id)
    elif consulta.data == _NIVELES:
        texto, teclado = _pantalla_niveles(user_id)
    elif consulta.data.startswith(_ELEGIR_NIVEL):
        nivel = consulta.data.removeprefix(_ELEGIR_NIVEL)
        if nivel not in levels.NIVELES:
            logging.warning("Botón con un nivel no válido: %s", nivel)
            return
        levels.cambiar_nivel(user_id, nivel)
        texto, teclado = _pantalla_confirmacion(nivel)
    else:
        logging.warning("Botón de ajustes desconocido: %s", consulta.data)
        return

    try:
        await consulta.edit_message_text(texto, reply_markup=teclado)
    except BadRequest as error:
        # Si se toca dos veces el mismo botón, el mensaje no cambia y Telegram avisa con un error
        if "not modified" not in str(error).lower():
            raise
