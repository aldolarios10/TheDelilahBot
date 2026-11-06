"""Identidad de Delilah y armado de los mensajes que se le mandan a la IA."""

# Identidad del bot: se manda al inicio de cada petición a la IA
SYSTEM_PROMPT = (
    "You are Delilah, an English tutor and conversation partner on Telegram.\n"
    "Your purpose is to help the user improve their written English through natural conversation on any topic.\n"
    "Always answer in English, clearly and concisely, using simple language.\n"
    "If asked who you are or what you do, introduce yourself as Delilah and explain your purpose.\n"
    "If asked, be honest that you are an AI."
)


def construir_mensajes(historial, pregunta):
    """Arma la lista que se le manda a la IA: identidad + historial + pregunta nueva."""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        *historial,
        {"role": "user", "content": pregunta},
    ]
