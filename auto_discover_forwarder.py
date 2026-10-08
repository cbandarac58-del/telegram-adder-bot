import os
import random
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
STRING_SESSION = os.environ.get('STRING_SESSION')
TARGET_CHANNEL = '@free_movies_stream_hd'
SITE_URL = 'https://movies.vixtube.net'

# සිංහල කීවර්ඩ්ස් නැතුව, ජාත්‍යන්තර ඉංග්‍රීසි මූවි කීවර්ඩ්ස් පමණක් පාවිච්චි කරයි
GLOBAL_KEYWORDS = [
    'hollywood movies',
    'blockbuster cinema',
    'hd movie stream',
    'latest movies hub',
    'netflix updates hd',
]

# ප්‍රසිද්ධ ග්ලෝබල් පබ්ලික් මූවි චැනල්ස් කිහිපයක් ස්වයංක්‍රීය සෝර්ස් ලෙස
SOURCE_CHANNELS = [
    'Hollywood_Movies_HD_Channel_Sample',  # උදාහරණ පබ්ලික් චැනල්ස් (ඔබට අවශ්‍ය නම් වෙනස් කළ හැක)
    'NetFlix_Updates_HD',
]


async def auto_discover_and_post():
  client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
  await client.start()

  collected_posts = []

  try:
    # පබ්ලික් චැනල්ස් වලින් ලേറ്റම පෝස්ට්ස් ස්ක්‍රේප් කරගැනීම
    for channel in SOURCE_CHANNELS:
      try:
        async for message in client.iter_messages(channel, limit=3):
          if message.text and len(message.text) > 20:
            collected_posts.append(message.text)
      except Exception as e:
        print(f'[!] Could not fetch from {channel}: {e}')

    # පෝස්ට් එකක් හමුවුණොත්, අපේ සයිට් ලින්ක් එකත් එකතු කර ටාගට් චැනල් එකට පෝස්ට් කරයි
    if collected_posts:
      selected_post = random.choice(collected_posts)
      final_caption = (
          f'🎬 **Trending Movie Update**\n\n{selected_post}\n\n👉 Watch HD'
          f' Stream: {SITE_URL}'
      )

      await client.send_message(TARGET_CHANNEL, final_caption)
      print('[✔] Successfully forwarded and posted with site link!')
    else:
      print('[!] No posts found to forward.')

  except Exception as e:
    print(f'[x] Error in auto discovery: {e}')

  await client.disconnect()


if __name__ == '__main__':
  import asyncio

  asyncio.run(auto_discover_and_post())
