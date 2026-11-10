"""Base de datos del bot (SQLite): conversaciones y mensajes por chat de Telegram."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

import config

# La ruta viene de config.py (raíz del proyecto), sin importar desde dónde se ejecute el bot
DB_PATH = config.DB_PATH


@contextmanager
def _connect():
    """Abre la base, guarda los cambios si todo salió bien (o los deshace si hubo error) y la cierra."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row            # permite leer columnas por nombre: fila["content"]
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite no revisa las llaves foráneas si no se activa
    try:
        with conn:  # commit al terminar, rollback si hay excepción
            yield conn
    finally:
        conn.close()


def _now():
    """Fecha y hora actual en UTC, como texto ISO (ej. 2026-11-03T20:15:00+00:00)."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_db():
    """Crea las tablas e índices si todavía no existen."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id     INTEGER NOT NULL,
                started_at  TEXT    NOT NULL,
                is_active   INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS messages (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id     INTEGER NOT NULL REFERENCES conversations(id),
                role                TEXT    NOT NULL CHECK (role IN ('user', 'assistant')),
                content             TEXT    NOT NULL,
                telegram_message_id INTEGER,
                created_at          TEXT    NOT NULL
            );

            -- Mensajes extra de Telegram de una misma respuesta (cuando se manda en varios).
            -- El primero sigue en messages.telegram_message_id.
            CREATE TABLE IF NOT EXISTS message_parts (
                telegram_message_id INTEGER NOT NULL,
                message_id          INTEGER NOT NULL REFERENCES messages(id)
            );

            -- Datos de cada persona, que no dependen del chat ni de la conversación
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                level       TEXT    NOT NULL,
                updated_at  TEXT    NOT NULL
            );

            -- Buscar rápido la conversación activa de un chat
            CREATE INDEX IF NOT EXISTS idx_conversations_chat
                ON conversations (chat_id, is_active);

            -- Leer rápido el historial de una conversación
            CREATE INDEX IF NOT EXISTS idx_messages_conversation
                ON messages (conversation_id, id);

            -- Encontrar rápido un mensaje de Telegram (para el reply)
            CREATE INDEX IF NOT EXISTS idx_messages_telegram
                ON messages (telegram_message_id);

            -- Encontrar rápido las partes extra de una respuesta (para el reply)
            CREATE INDEX IF NOT EXISTS idx_message_parts_telegram
                ON message_parts (telegram_message_id);
        """)


def get_or_create_active_conversation(chat_id):
    """Devuelve el id de la conversación activa del chat; si no hay ninguna, crea una."""
    with _connect() as conn:
        fila = conn.execute(
            "SELECT id FROM conversations WHERE chat_id = ? AND is_active = 1 "
            "ORDER BY id DESC LIMIT 1",
            (chat_id,),
        ).fetchone()
        if fila:
            return fila["id"]
        cursor = conn.execute(
            "INSERT INTO conversations (chat_id, started_at, is_active) VALUES (?, ?, 1)",
            (chat_id, _now()),
        )
        return cursor.lastrowid


def start_new_conversation(chat_id):
    """Desactiva la conversación actual del chat y crea una nueva (comando /new). Devuelve su id."""
    with _connect() as conn:
        conn.execute("UPDATE conversations SET is_active = 0 WHERE chat_id = ?", (chat_id,))
        cursor = conn.execute(
            "INSERT INTO conversations (chat_id, started_at, is_active) VALUES (?, ?, 1)",
            (chat_id, _now()),
        )
        return cursor.lastrowid


def find_conversation_by_message(chat_id, telegram_message_id):
    """Devuelve el id de la conversación a la que pertenece un mensaje de Telegram, o None.

    Busca tanto el mensaje principal como las partes extra de una respuesta. Se filtra por
    chat_id porque Telegram solo garantiza que el message_id sea único dentro de un chat.
    """
    with _connect() as conn:
        fila = conn.execute(
            "SELECT m.conversation_id FROM messages m "
            "JOIN conversations c ON c.id = m.conversation_id "
            "WHERE c.chat_id = ? AND m.telegram_message_id = ? "
            "UNION ALL "
            "SELECT m.conversation_id FROM message_parts p "
            "JOIN messages m ON m.id = p.message_id "
            "JOIN conversations c ON c.id = m.conversation_id "
            "WHERE c.chat_id = ? AND p.telegram_message_id = ? "
            "LIMIT 1",
            (chat_id, telegram_message_id, chat_id, telegram_message_id),
        ).fetchone()
        return fila["conversation_id"] if fila else None


def activate_conversation(chat_id, conversation_id):
    """Deja activa solo esa conversación dentro del chat (las demás quedan inactivas)."""
    with _connect() as conn:
        conn.execute(
            "UPDATE conversations SET is_active = (id = ?) WHERE chat_id = ?",
            (conversation_id, chat_id),
        )


def save_message(conversation_id, role, content, telegram_message_id=None, ids_extra=()):
    """Guarda un mensaje ('user' o 'assistant') en una conversación.

    Si la respuesta se mandó en varios mensajes de Telegram, `telegram_message_id` es el
    primero e `ids_extra` los demás. Se guarda todo junto: si algo falla, no se guarda nada.
    """
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO messages (conversation_id, role, content, telegram_message_id, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (conversation_id, role, content, telegram_message_id, _now()),
        )
        conn.executemany(
            "INSERT INTO message_parts (telegram_message_id, message_id) VALUES (?, ?)",
            [(id_extra, cursor.lastrowid) for id_extra in ids_extra],
        )


def get_history(conversation_id, limit):
    """Devuelve los últimos `limit` mensajes de la conversación, del más viejo al más nuevo,
    en el formato que espera Groq: [{"role": ..., "content": ...}, ...]
    """
    with _connect() as conn:
        filas = conn.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (conversation_id, limit),
        ).fetchall()
    return [{"role": f["role"], "content": f["content"]} for f in reversed(filas)]


def obtener_nivel(user_id):
    """Devuelve el nivel guardado de una persona, o None si todavía no ha elegido uno."""
    with _connect() as conn:
        fila = conn.execute("SELECT level FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return fila["level"] if fila else None


def guardar_nivel(user_id, nivel):
    """Guarda el nivel de una persona. Si ya tenía uno, lo reemplaza."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO users (user_id, level, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT (user_id) DO UPDATE SET level = excluded.level, updated_at = excluded.updated_at",
            (user_id, nivel, _now()),
        )
