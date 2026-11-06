"""Llamadas a la IA (Groq) con streaming. No sabe nada de Telegram."""

from groq import AsyncGroq

import config

_cliente = None


def _groq():
    """Crea el cliente de Groq la primera vez que se usa (no al importar este archivo)."""
    global _cliente
    if _cliente is None:
        _cliente = AsyncGroq(api_key=config.GROQ_API_KEY)
    return _cliente


async def generar(mensajes, al_avanzar=None):
    """Pide la respuesta a Groq por pedacitos (streaming).

    - `mensajes`: lista en el formato de Groq (ver services/tutor.py → construir_mensajes).
    - `al_avanzar`: función async opcional; se llama con el texto acumulado cada vez que
      llega un pedacito nuevo (por ejemplo, para mostrar un borrador en Telegram).

    Devuelve (texto completo, se_cortó). Si Groq falla, lanza la excepción.
    """
    stream = await _groq().chat.completions.create(
        model=config.GROQ_MODEL,
        max_tokens=config.MAX_TOKENS,
        stream=True,
        messages=mensajes,
    )

    texto = ""
    cortada = False
    async for chunk in stream:
        if not chunk.choices:  # algunos pedazos solo traen estadísticas, sin texto
            continue
        opcion = chunk.choices[0]
        fragmento = opcion.delta.content or ""
        texto += fragmento
        if opcion.finish_reason == "length":  # se llegó al tope de MAX_TOKENS
            cortada = True
        if al_avanzar and fragmento:
            await al_avanzar(texto)

    return texto, cortada
