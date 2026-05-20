import os
import re
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from processor import procesar_video
from database import init_db, buscar_recomendaciones, listar_por_categoria, guardar_recomendacion

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

URL_REGEX = re.compile(
    r"(https?://(?:www\.)?"
    r"(?:tiktok\.com|instagram\.com|youtube\.com|youtu\.be|fb\.watch)"
    r"[^\s]+)"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Bot de Recomendaciones*\n\n"
        "Mandame un link de TikTok, Reel o YouTube y lo proceso automáticamente.\n\n"
        "*Comandos disponibles:*\n"
        "🔍 /buscar `<título>` — busca una recomendación\n"
        "📚 /libros — lista todos los libros\n"
        "🎬 /pelis — lista todas las películas\n"
        "📺 /series — lista todas las series\n"
        "📋 /todos — muestra todo",
        parse_mode="Markdown",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text or ""
    urls = URL_REGEX.findall(text)

    if not urls:
        return

    for url in urls:
        msg = await update.message.reply_text(f"⏳ Procesando video...")
        try:
            resultado = await asyncio.to_thread(procesar_video, url)
            if resultado:
                guardar_recomendacion(
                    titulo=resultado["titulo"],
                    categoria=resultado["categoria"],
                    descripcion=resultado["descripcion"],
                    url=url,
                    remitente=update.message.from_user.first_name or "Desconocido",
                )
                emoji = {"libro": "📚", "película": "🎬", "serie": "📺"}.get(
                    resultado["categoria"].lower(), "🎯"
                )
                await msg.edit_text(
                    f"{emoji} *{resultado['titulo']}*\n"
                    f"_{resultado['categoria'].capitalize()}_\n\n"
                    f"{resultado['descripcion']}\n\n"
                    f"🔗 [Ver video]({url})",
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )
            else:
                await msg.edit_text("❌ No pude detectar una recomendación en este video.")
        except Exception as e:
            logger.error(f"Error procesando {url}: {e}")
            await msg.edit_text(f"❌ Error procesando el video: {str(e)}")


async def cmd_buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usá: /buscar `<título>`", parse_mode="Markdown")
        return
    query = " ".join(context.args)
    resultados = buscar_recomendaciones(query)
    if not resultados:
        await update.message.reply_text(f'🔍 No encontré nada para "{query}".')
        return
    texto = f"🔍 *Resultados para \"{query}\":*\n\n"
    for r in resultados[:5]:
        emoji = {"libro": "📚", "película": "🎬", "serie": "📺"}.get(r["categoria"].lower(), "🎯")
        texto += f"{emoji} *{r['titulo']}* — _{r['categoria']}_\n{r['descripcion']}\n[Ver video]({r['url']})\n\n"
    await update.message.reply_text(texto, parse_mode="Markdown", disable_web_page_preview=True)


async def cmd_categoria(update: Update, context: ContextTypes.DEFAULT_TYPE, categoria: str):
    resultados = listar_por_categoria(categoria)
    emoji = {"libro": "📚", "película": "🎬", "serie": "📺"}.get(categoria, "🎯")
    if not resultados:
        await update.message.reply_text(f"{emoji} Todavía no hay {categoria}s guardadas.")
        return
    texto = f"{emoji} *{categoria.capitalize()}s recomendadas:*\n\n"
    for r in resultados:
        texto += f"• *{r['titulo']}* — {r['descripcion'][:80]}...\n"
    await update.message.reply_text(texto, parse_mode="Markdown")


async def cmd_libros(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_categoria(update, context, "libro")

async def cmd_pelis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_categoria(update, context, "película")

async def cmd_series(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cmd_categoria(update, context, "serie")

async def cmd_todos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for cat in ["libro", "película", "serie"]:
        await cmd_categoria(update, context, cat)


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    init_db()
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buscar", cmd_buscar))
    app.add_handler(CommandHandler("libros", cmd_libros))
    app.add_handler(CommandHandler("pelis", cmd_pelis))
    app.add_handler(CommandHandler("series", cmd_series))
    app.add_handler(CommandHandler("todos", cmd_todos))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot iniciado ✅")
    app.run_polling()


if __name__ == "__main__":
    main()
