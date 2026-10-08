import os
import random
import time
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
STRING_SESSION = os.environ.get('STRING_SESSION')
TARGET_CHANNEL = '@free_movies_stream_hd'

# උදාහරණයක් විදිහට අපි පෝස්ට් කරන්න ඕන මූවි ලිස්ට් එකක් (ඔයාට මේකට සයිට් එකේ ඩේටා හෝ ලිස්ට් එකක් දෙන්න පුළුවන්)
movies = [
    {
        'title': 'Spider-Man: Brand New Day (2026)',
        'desc': (
            'Action, Sci-Fi | HD Stream Available!\nWatch now: '
            'https://movies.vixtube.net/movie/969681'
        ),
        'image': 'https://image.tmdb.org/t/p/w500/sample_poster.jpg',
    },
    {
        'title': 'Avengers: Doomsday (2026)',
        'desc': (
            'Blockbuster Action | HD Stream Available!\nWatch now: '
            'https://movies.vixtube.net'
        ),
        'image': 'https://image.tmdb.org/t/p/w500/sample_poster2.jpg',
    },
]


async def auto_post():
  client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
  await client.start()

  # අහඹු ලෙස මූවි එකක් තෝරාගෙන පෝස්ට් කිරීම
  movie = random.choice(movies)
  caption = f'🎬 **{movie["title"]}**\n\n{movie["desc"]}'

  try:
    await client.send_message(TARGET_CHANNEL, caption)
    print(f'[✔] Successfully posted: {movie["title"]}')
  except Exception as e:
    print(f'[x] Error posting: {e}')

  await client.disconnect()


if __name__ == '__main__':
  import asyncio

  asyncio.run(auto_post())
