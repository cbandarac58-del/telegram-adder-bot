import os
import random
import requests
import xml.etree.ElementTree as ET
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
STRING_SESSION = os.environ.get('STRING_SESSION')
TARGET_CHANNEL = '@free_movies_stream_hd'

SITE_URL = 'https://movies.vixtube.net'


def get_site_movies():
  movies = []
  try:
    # සයිට් එකේ sitemap එකෙන් මූවි ලිංක්ස් ටික ගන්නවා
    response = requests.get(f'{SITE_URL}/sitemap.xml')
    if response.status_code == 200:
      root = ET.fromstring(response.content)
      for child in root:
        for elem in child:
          if 'loc' in elem.tag:
            url = elem.text
            if '/movie/' in url:  # මූවි ලින්ක්ස් විතරක් ෆිල්ටර් කරගන්නවා
              movies.append(url)
  except Exception as e:
    print(f'[x] Sitemap read error: {e}')

  # සයිට් එකෙන් ලින්ක්ස් ගන්න බැරි වුණොත් පාවිච්චි කරන්න ඩිෆල්ට් ලිස්ට් එකක්
  if not movies:
    movies = [f'{SITE_URL}/movie/969681']

  return movies


async def auto_post():
  client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
  await client.start()

  all_movies = get_site_movies()

  # දවසට මූවිස් 5ක් පෝස්ට් කරන නිසා, මේ රන් එකෙන් 1 මූවි එකක් තෝරලා පෝස්ට් කරනවා
  if all_movies:
    chosen_movie = random.choice(all_movies)
    caption = (
        '🎬 **New Movie Available!**\n\nHD Stream Available on our site!\nWatch'
        f' now: {chosen_movie}'
    )

    try:
      await client.send_message(TARGET_CHANNEL, caption)
      print(f'[✔] Successfully posted movie: {chosen_movie}')
    except Exception as e:
      print(f'[x] Error posting: {e}')

  await client.disconnect()


if __name__ == '__main__':
  import asyncio

  asyncio.run(auto_post())
