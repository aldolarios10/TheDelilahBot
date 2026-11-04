"""Rich Messages de Telegram (Bot API 10.1+).

python-telegram-bot todavía no trae estos métodos, así que se llaman con `do_api_request`,
que la librería ofrece justo para usar métodos nuevos de la API de Telegram.
Docs: https://core.telegram.org/bots/api#sendrichmessage
"""

from telegram import Message

RICH_LIMIT = 32768  # máximo de caracteres en un rich message


async def enviar_rich(bot, chat_id, markdown):
    """Manda `markdown` como rich message (Telegram interpreta **negritas**, listas, tablas, etc.).

    Devuelve el Message enviado. Si Telegram lo rechaza, lanza una excepción
    (quien llama decide qué hacer, por ejemplo mandarlo como texto normal).
    """
    return await bot.do_api_request(
        "sendRichMessage",
        api_kwargs={
            "chat_id": chat_id,
            "rich_message": {"markdown": markdown},
        },
        return_type=Message,
    )
