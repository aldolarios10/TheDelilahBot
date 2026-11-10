"""Identidad de Delilah y armado de los mensajes que se le mandan a la IA."""

import re

# Identidad de Delilah y formato de tutor (Reply → Correction → Explanation).
# Se manda al inicio de cada petición a la IA. Los encabezados deben coincidir con los
# que busca el código para separar las secciones.
SYSTEM_PROMPT = """\
You are Delilah, an English tutor and conversation partner on Telegram.
Your purpose is to help the user improve their written English through natural conversation on any topic.
Always write in English only, even if the user writes in Spanish. Use simple, clear English.
If asked who you are or what you do, introduce yourself as Delilah and explain your purpose.
If asked, be honest that you are an AI.

For EVERY user message, answer with these sections, in this order, with these exact headings:

**💬 Reply**
- Answer the message naturally in simple English and end with a question to keep the conversation going.
- Never stop after the Reply: the Correction section is always required.

**✍️ Correction**
- Rewrite the user's whole message correctly and put every changed word in **bold**.
- If the user wrote in Spanish, write the English version of what they meant, starting with "*In English:*".
- Always add "*More natural:*" with how a native speaker would say it, unless the message already sounds natural.
- If there are no mistakes and it sounds natural, write only: Perfect! No mistakes. 🎉
- If there are no mistakes but it could sound more natural, write: No mistakes! 🎉 and then the "*More natural:*" line.

**📝 Explanation**
- Only if there were mistakes, or the user wrote in Spanish. Otherwise skip this section completely, heading included.
- One short bullet per mistake: what was wrong and why. For Spanish messages, explain 1-3 key words or structures.
- Correct grammar, vocabulary, spelling and the capital "I". Don't correct minor chat punctuation (missing final period, optional commas) unless it changes the meaning.
"""


# Reconoce una línea que es solo un encabezado de sección, con o sin emoji, negritas, "#" o ":".
# Ej.: "**✍️ Correction**", "✍️ **Correction**", "## Correction", "Correction:"
_ENCABEZADO = re.compile(
    r"^\s*(?:#+\s*)?(?:\*\*)?\s*(?:[^\w\s*]+\s*)?(?:\*\*)?\s*"
    r"(correction|explanation|reply)"
    r"\s*:?\s*(?:\*\*)?\s*:?\s*$",
    re.IGNORECASE,
)


def separar_secciones(texto):
    """Separa una respuesta de Delilah en sus secciones.

    Devuelve un diccionario solo con las secciones encontradas, por ejemplo
    {"correction": "...", "explanation": "...", "reply": "..."}. Si el texto no tiene
    encabezados (por ejemplo, un mensaje de antes del formato de tutor), devuelve {}.
    """
    secciones = {}
    actual = None
    for linea in texto.splitlines():
        encontrado = _ENCABEZADO.match(linea)
        if encontrado:
            actual = encontrado.group(1).lower()
            secciones[actual] = []
        elif actual:
            secciones[actual].append(linea)
    return {nombre: "\n".join(lineas).strip() for nombre, lineas in secciones.items()}


def extraer_reply(texto):
    """Devuelve solo la parte del Reply. Si no la encuentra, devuelve el texto completo."""
    return separar_secciones(texto).get("reply") or texto


# Encabezados que se muestran en sus mensajes separados (el Reply va sin encabezado)
_TITULOS = {"correction": "**✍️ Correction**", "explanation": "**📝 Explanation**"}


def _se_puede_dividir(texto):
    """Dice si la respuesta está bien formada: sin texto antes del primer encabezado ni encabezados repetidos."""
    vistos = []
    for linea in texto.splitlines():
        encontrado = _ENCABEZADO.match(linea)
        if encontrado:
            vistos.append(encontrado.group(1).lower())
        elif linea.strip() and not vistos:
            return False  # hay texto antes del primer encabezado y se perdería al separar
    return bool(vistos) and len(vistos) == len(set(vistos))


def dividir_respuesta(texto):
    """Devuelve la lista de mensajes a enviar, en orden: Reply, Correction y Explanation.

    Las secciones vacías no se incluyen. Si la respuesta no se puede dividir sin perder
    texto, devuelve el texto completo como un solo mensaje.
    """
    if not _se_puede_dividir(texto):
        return [texto]
    secciones = separar_secciones(texto)
    partes = [secciones["reply"]] if secciones.get("reply") else []
    partes += [f"{titulo}\n\n{secciones[nombre]}" for nombre, titulo in _TITULOS.items() if secciones.get(nombre)]
    return partes or [texto]


def _puede_ser_encabezado(linea):
    """Dice si una línea incompleta todavía podría terminar siendo un encabezado de sección."""
    letras = re.sub(r"[^a-z]", "", linea.lower())
    return any(nombre.startswith(letras) for nombre in ("correction", "explanation", "reply"))


def texto_para_borrador(texto):
    """Del texto que va llegando, devuelve lo que se muestra en vivo: solo el Reply.

    La última línea se omite si puede ser un encabezado que apenas se está escribiendo.
    Si la respuesta no trae encabezados, devuelve lo que haya. Puede devolver "" cuando
    todavía no hay nada que mostrar.
    """
    lineas = texto.split("\n")
    if lineas[-1].strip() and _puede_ser_encabezado(lineas[-1]):
        lineas.pop()
    completo = "\n".join(lineas)
    secciones = separar_secciones(completo)
    return secciones.get("reply", "") if secciones else completo.strip()


def construir_mensajes(historial, pregunta):
    """Arma la lista que se le manda a la IA: identidad + historial + pregunta nueva.

    De las respuestas anteriores de Delilah solo se manda el Reply (sin Correction ni
    Explanation), para gastar menos tokens. En la base de datos se guarda la respuesta completa.
    """
    historial_corto = [
        {"role": m["role"], "content": extraer_reply(m["content"])} if m["role"] == "assistant" else m
        for m in historial
    ]
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        *historial_corto,
        {"role": "user", "content": pregunta},
    ]
