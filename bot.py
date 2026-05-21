import os
import re
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from processor import agregar_por_nombre
from database import (init_db, search_recommendations, find_one, list_by_category,
                      list_by_genre, list_by_year, list_by_country, save_recommendation)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Matches: "Dune, movie" / "Dune - book" / "Attack on Titan, anime"
MANUAL_REGEX = re.compile(
    r"^(.+?)\s*[,\-–]\s*(movie|book|show|anime)\s*$",
    re.IGNORECASE
)

EMOJI = {"movie": "🎬", "book": "📚", "show": "📺", "anime": "⛩️"}


def fmt_list(r: dict) -> str:
    emoji = EMOJI.get(r["category"].lower(), "🎯")
    line = f"{emoji} *{r['title']}*"
    details = []
    if r.get("genre"):           details.append(r["genre"])
    if r.get("year"):            details.append(str(r["year"]))
    if r.get("director_author"): details.append(r["director_author"])
    if details:
        line += f" — _{', '.join(details)}_"
    return line


def fmt_card(r: dict) -> str:
    emoji = EMOJI.get(r["category"].lower(), "🎯")
    lines = [f"{emoji} *{r['title']}*  _{r['category'].capitalize()}_\n"]
    if r.get("synopsis"):
        lines.append(r["synopsis"] + "\n")
    details = []
    if r.get("genre"):           details.append(f"🎭 *Genre:* {r['genre']}")
    if r.get("country"):         details.append(f"🌍 *Country:* {r['country']}")
    if r.get("year"):            details.append(f"📅 *Year:* {r['year']}")
    if r.get("director_author"):
        label = "Author" if r["category"] == "book" else "Director"
        details.append(f"✍️ *{label}:* {r['director_author']}")
    if details:
        lines.append("\n".join(details) + "\n")
    if r.get("description"):
        lines.append(f"💬 _{r['description']}_")
    if r.get("added_by"):
        lines.append(f"\n👤 Added by {r['added_by']}")
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Recommendations Bot*\n\n"
        "Add something by typing: `Dune, movie`\n"
        "Works with: `movie`, `book`, `show`, `anime`\n\n"
        "*View entries:*\n"
        "🔍 /view `<title>` — full card with synopsis\n"
        "🔎 /search `<text>` — search by title, genre or director\n\n"
        "*List by category:*\n"
        "🎬 /movies   📚 /books   📺 /shows   ⛩️ /anime   📋 /all\n\n"
        "*Filter:*\n"
        "🎭 /genre `<genre>` — e.g. /genre horror\n"
        "📅 /year `<year>` — e.g. /year 2023\n"
        "🌍 /country `<country>` — e.g. /country France",
        parse_mode="Markdown",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    match = MANUAL_REGEX.match(text)
    if not match:
        await update.message.reply_text(
            "To add something type: `Dune, movie`\n"
            "Categories: `movie`, `book`, `show`, `anime`",
            parse_mode="Markdown",
        )
        return

    title_raw = match.group(1).strip()
    category = match.group(2).lower()
    msg = await update.message.reply_text(f"⏳ Looking up *{title_raw}*...", parse_mode="Markdown")
    try:
        result = await asyncio.to_thread(agregar_por_nombre, title_raw, category)
        save_recommendation(
            title=result["title"],
            category=result["category"],
            description=result.get("description"),
            synopsis=result.get("synopsis"),
            genre=result.get("genre"),
            country=result.get("country"),
            year=result.get("year"),
            director_author=result.get("director_author"),
            url=None,
            added_by=update.message.from_user.first_name or "Unknown",
        )
        await msg.edit_text(
            "✅ Added:\n\n" + fmt_card(result),
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Error adding {title_raw}: {e}")
        await msg.edit_text(f"❌ Couldn't find info for \"{title_raw}\".")


async def cmd_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /view `<title>` — e.g. /view Dune", parse_mode="Markdown")
        return
    result = find_one(" ".join(context.args))
    if not result:
        await update.message.reply_text(f'❌ "{" ".join(context.args)}" not found.')
        return
    await update.message.reply_text(fmt_card(result), parse_mode="Markdown")


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /search `<text>`", parse_mode="Markdown")
        return
    query = " ".join(context.args)
    results = search_recommendations(query)
    if not results:
        await update.message.reply_text(f'🔎 Nothing found for "{query}".')
        return
    text = f"🔎 *\"{query}\":*\n\n"
    text += "\n".join(fmt_list(r) for r in results[:8])
    text += "\n\n_Use /view \\<title\\> for the full card_"
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_category(update: Update, context: ContextTypes.DEFAULT_TYPE, category: str):
    results = list_by_category(category)
    emoji = EMOJI.get(category, "🎯")
    labels = {"movie": "Movies", "book": "Books", "show": "Shows", "anime": "Anime"}
    label = labels.get(category, category.capitalize())
    if not results:
        await update.message.reply_text(f"{emoji} No {label} saved yet.")
        return
    text = f"{emoji} *{label}:*\n\n"
    text += "\n".join(fmt_list(r) for r in results)
    text += "\n\n_Use /view \\<title\\> for the full card_"
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /genre `<genre>`", parse_mode="Markdown")
        return
    genre = " ".join(context.args)
    results = list_by_genre(genre)
    if not results:
        await update.message.reply_text(f'🎭 Nothing found for genre "{genre}".')
        return
    text = f"🎭 *{genre.capitalize()}:*\n\n" + "\n".join(fmt_list(r) for r in results)
    text += "\n\n_Use /view \\<title\\> for the full card_"
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /year `<year>`", parse_mode="Markdown")
        return
    year = int(context.args[0])
    results = list_by_year(year)
    if not results:
        await update.message.reply_text(f'📅 Nothing found from {year}.')
        return
    text = f"📅 *{year}:*\n\n" + "\n".join(fmt_list(r) for r in results)
    text += "\n\n_Use /view \\<title\\> for the full card_"
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: /country `<country>`", parse_mode="Markdown")
        return
    country = " ".join(context.args)
    results = list_by_country(country)
    if not results:
        await update.message.reply_text(f'🌍 Nothing found from "{country}".')
        return
    text = f"🌍 *{country}:*\n\n" + "\n".join(fmt_list(r) for r in results)
    text += "\n\n_Use /view \\<title\\> for the full card_"
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_movies(update, context): await cmd_category(update, context, "movie")
async def cmd_books(update, context):  await cmd_category(update, context, "book")
async def cmd_shows(update, context):  await cmd_category(update, context, "show")
async def cmd_anime(update, context):  await cmd_category(update, context, "anime")
async def cmd_all(update, context):
    for cat in ["movie", "book", "show", "anime"]:
        await cmd_category(update, context, cat)


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    init_db()
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("view", cmd_view))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("movies", cmd_movies))
    app.add_handler(CommandHandler("books", cmd_books))
    app.add_handler(CommandHandler("shows", cmd_shows))
    app.add_handler(CommandHandler("anime", cmd_anime))
    app.add_handler(CommandHandler("all", cmd_all))
    app.add_handler(CommandHandler("genre", cmd_genre))
    app.add_handler(CommandHandler("year", cmd_year))
    app.add_handler(CommandHandler("country", cmd_country))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot started ✅")
    app.run_polling()


if __name__ == "__main__":
    main()
