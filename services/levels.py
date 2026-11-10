"""Niveles de inglés: qué niveles existen, cómo adapta Delilah su forma de escribir y el nivel de cada persona.

No sabe nada de Telegram.
"""

from storage import db

NIVEL_INICIAL = "A2"

# Instrucciones que recibe la IA según el nivel. Solo se manda el bloque del nivel de la persona.
NIVELES = {
    "A2": (
        '- Reply: short sentences, common everyday words, basic tenses (present, past simple, "going to"). '
        "No idioms or phrasal verbs.\n"
        "- More natural: keep it simple, with no idioms.\n"
        "- Explanation: very simple words, no grammar terms, and one short example."
    ),
    "B1": (
        "- Reply: connected sentences (because, but, so, when), everyday vocabulary, "
        "common tenses including present perfect.\n"
        "- More natural: common everyday expressions.\n"
        "- Explanation: name the grammar rule briefly in simple words."
    ),
    "B2": (
        "- Reply: varied sentences and vocabulary, with common idioms and phrasal verbs.\n"
        "- More natural: natural collocations and common idioms.\n"
        "- Explanation: explain the rule and why it applies here."
    ),
    "C1": (
        "- Reply: fluent, natural English with complex sentences and idiomatic language.\n"
        "- More natural: focus on nuance, register and idiomatic phrasing.\n"
        "- Explanation: explain nuances of usage and tone. Also treat problems of tone or register as mistakes."
    ),
}


def nivel_de_usuario(user_id):
    """Devuelve el nivel de una persona. Si no ha elegido uno o el guardado no es válido, usa el inicial."""
    nivel = db.obtener_nivel(user_id)
    return nivel if nivel in NIVELES else NIVEL_INICIAL


def cambiar_nivel(user_id, nivel):
    """Guarda el nivel de una persona. Si el nivel no existe, lanza ValueError."""
    if nivel not in NIVELES:
        raise ValueError(f"Nivel no válido: {nivel}")
    db.guardar_nivel(user_id, nivel)
