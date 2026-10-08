import os
import requests
import xml.etree.ElementTree as ET
from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    InlineQueryHandler,
    MessageHandler,
    filters,
)

# BotFather ගෙන් ලැබුණු API Token එක මෙතැනට සෙට් වෙයි
BOT_TOKEN = os.environ.get(
    'BOT_TOKEN', '8928636596:AAGhaQvLAXrJ2p1R0LDpF1GnUqCHRhW3U'
)
SITE_URL = 'https://movies.vixtube.net'


def search_site_movies(query):
  matching_movies = []
  try:
    response = requests.get(f'{SITE_URL}/sitemap.xml')
    if response.status_code == 200:
      root = ET.fromstring(response.content)
      for child in root:
        for elem in child:
          if 'loc' in elem.tag:
            url = elem.text
            if '/movie/' in url:
              movie_slug = url.split('/')[-1].replace('-', ' ').lower()
              if not query or query.lower() in movie_slug:
                matching_movies.append(url)
  except Exception as e:
    print(f'Error reading sitemap: {e}')

  return matching_movies[:10]


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
  query = update.inline_query.query
  found_movies = search_site_movies(query)

  results = []
  for i, link in enumerate(found_movies):
    movie_name = link.split('/')[-1].replace('-', ' ').title()
    results.append(
        InlineQueryResultArticle(
            id=str(i),
            title=f'🎬 {movie_name}',
            description='Click to share HD stream link',
            input_message_content=InputTextMessageContent(
                message_text=(
                    f'🎬 **{movie_name}**\n\nWatch & Download in HD Stream'
                    f' now:\n{link}'
                )
            ),
        )
    )

  await update.inline_query.answer(results, cache_time=5)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user_query = update.message.text
  if user_query.startswith('/'):
    return

  found_movies = search_site_movies(user_query)

  if found_movies:
    response_text = (
        f'🎬 **Search Results for "{user_query}":**\n\nClick below to watch in'
        ' HD:\n'
    )
    for link in found_movies[:5]:
      response_text += f'👉 {link}\n'
  else:
    response_text = (
        f'❌ No movies found for "{user_query}".\n\nBrowse all movies here:'
        f' {SITE_URL}'
    )

  await update.message.reply_text(response_text)


if __name__ == '__main__':
  app = ApplicationBuilder().token(BOT_TOKEN).build()
  app.add_handler(InlineQueryHandler(inline_query))
  app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

  print('Interactive Search Bot is running live...')
  app.run_polling()
