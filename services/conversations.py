"""Reglas para decidir a qué conversación pertenece cada mensaje. No sabe nada de Telegram."""

from storage import db


def elegir_conversacion(chat_id, mensaje_citado_id=None):
    """Devuelve el id de la conversación a la que va este mensaje.

    Si el usuario respondió (reply) a un mensaje guardado (`mensaje_citado_id`), se retoma
    esa conversación y queda activa. Si no, se usa la conversación activa del chat (o se crea una).
    """
    if mensaje_citado_id:
        conversacion_id = db.find_conversation_by_message(chat_id, mensaje_citado_id)
        if conversacion_id:
            db.activate_conversation(chat_id, conversacion_id)
            return conversacion_id
    return db.get_or_create_active_conversation(chat_id)
