from telegram.ext import ApplicationBuilder, CallbackQueryHandler, MessageHandler, CommandHandler, filters
import logging
import config
from storage import db
from handlers.commands import registrar_comandos, start, nueva
from handlers.messages import preguntar
from handlers.settings import ajustes, manejar_boton, PATRON_AJUSTES

logging.basicConfig(level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING)  # oculta el log de cada petición HTTP


def main():
    """Arranca el bot. Solo se ejecuta al correr `python main.py`, no al importar este archivo."""
    config.validar()  # se detiene si falta algo en el .env
    db.init_db()  # crea las tablas si no existen

    app = ApplicationBuilder().token(config.TOKEN).post_init(registrar_comandos).build()
    app.add_handler(CommandHandler("start", start))                                # responde a /start
    app.add_handler(CommandHandler("new", nueva))                                  # empieza otra conversación
    app.add_handler(CommandHandler("settings", ajustes))                           # abre el menú de ajustes
    app.add_handler(CallbackQueryHandler(manejar_boton, pattern=PATRON_AJUSTES))   # botones del menú de ajustes
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, preguntar))    # responde a mensajes de texto
    app.run_polling()


if __name__ == "__main__":
    main()
