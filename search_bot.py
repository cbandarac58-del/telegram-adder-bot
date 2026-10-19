import os
import re
import time
import requests
from telegram import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update
)
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    InlineQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8928636596:AAGhaQvLAXrJ2p1R0LDpF1GnUqCHRhW3U")
SITE_URL = "https://movies.vixtube.net"
CHANNEL_URL = "https://t.me/free_movies_stream_hd"
CHANNEL_NAME = "@free_movies_stream_hd"

# Cache movie titles and links
CACHED_MOVIES = []
LAST_CACHE_TIME = 0

def get_all_movies():
    """Fetch movie URLs from sitemaps and cache them in memory."""
    global CACHED_MOVIES, LAST_CACHE_TIME
    now = time.time()
    if CACHED_MOVIES and (now - LAST_CACHE_TIME < 3600):
        return CACHED_MOVIES

    movies = []
    sitemaps = [
        f"{SITE_URL}/sitemaps/movies-1.xml",
        f"{SITE_URL}/sitemaps/movies-2.xml"
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"}

    for sm in sitemaps:
        try:
            r = requests.get(sm, headers=headers, timeout=15)
            if r.status_code == 200:
                urls = re.findall(r'https://movies\.vixtube\.net/movie/\d+', r.text)
                for u in urls:
                    slug = u.split("/")[-1]
                    movies.append({"url": u, "slug": slug})
        except Exception as e:
            print(f"Sitemap fetch error: {e}")

    if movies:
        CACHED_MOVIES = movies
        LAST_CACHE_TIME = now
        print(f"Cached {len(CACHED_MOVIES)} movies.")
    return CACHED_MOVIES


def search_movies(query):
    query_clean = query.lower().strip()
    all_movies = get_all_movies()
    if not all_movies:
        return []

    # If query is empty, return trending/top 10
    if not query_clean:
        return all_movies[:10]

    matched = []
    for m in all_movies:
        # Match slug or numeric ID
        if query_clean in m["slug"]:
            matched.append(m)
        if len(matched) >= 15:
            break
    return matched


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    found = search_movies(query)

    results = []
    for i, item in enumerate(found[:10]):
        url = item["url"]
        movie_title = f"Movie #{item['slug']}"

        # Channel join & watch buttons attached to shared card
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🍿 Watch in HD", url=url),
                InlineKeyboardButton("📢 Join Channel", url=CHANNEL_URL)
            ]
        ])

        message_text = (
            f"🎬 **Watch on Vix Movies**\n\n"
            f"🍿 **Link:** [Click to Watch Online]({url})\n\n"
            f"👉 **Join our Channel for Daily HD Movies:** {CHANNEL_NAME}"
        )

        results.append(
            InlineQueryResultArticle(
                id=str(i),
                title=f"🎬 Watch {movie_title}",
                description="Tap to share HD stream & invite link",
                thumb_url="https://image.tmdb.org/t/p/w200/1n37BJchWHLiSYQkuFxe5KjB951.jpg",
                input_message_content=InputTextMessageContent(
                    message_text=message_text,
                    parse_mode="markdown",
                    disable_web_page_preview=False
                ),
                reply_markup=keyboard
            )
        )

    await update.inline_query.answer(results, cache_time=10)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Official Channel", url=CHANNEL_URL)],
        [InlineKeyboardButton("🌐 Visit Website", url=SITE_URL)]
    ])
    text = (
        "👋 **Welcome to HD Movies Hub Bot!**\n\n"
        "🍿 Search any movie instantly in any chat by typing:\n"
        "`@free_movies_stream_hd_bot <movie name>`\n\n"
        f"📢 Make sure to join our official channel for daily updates:\n{CHANNEL_NAME}"
    )
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    if query.startswith("/"):
        return

    found = search_movies(query)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Join Official Channel", url=CHANNEL_URL)]
    ])

    if found:
        response_text = f"🔍 **Search Results for '{query}':**\n\n"
        for item in found[:5]:
            response_text += f"🎬 [Watch Movie #{item['slug']}]({item['url']})\n"
        response_text += f"\n👉 Daily HD releases at {CHANNEL_NAME}"
    else:
        response_text = (
            f"❌ No movies found for '{query}'.\n\n"
            f"Browse all movies here: {SITE_URL}\n"
            f"Or join {CHANNEL_NAME} for requests!"
        )

    await update.message.reply_text(
        response_text,
        reply_markup=keyboard,
        parse_mode="markdown",
        disable_web_page_preview=True
    )


if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(InlineQueryHandler(inline_query))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    print("🚀 Interactive Search & Promote Bot is running live...")
    app.run_polling()