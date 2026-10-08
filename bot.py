import csv
import os
import time
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.types import InputPeerUser

API_ID = int(os.environ.get('API_ID'))
API_HASH = os.environ.get('API_HASH')
STRING_SESSION = os.environ.get('STRING_SESSION')

# ඩිරෙක්ට්ම මෙතැනට ඔයාගේ චැනල් එක දෙනවා (Secrets වල ප්‍රශ්න මඟහරවා ගැනීමට)
TARGET_CHANNEL = '@free_movies_stream_hd'


async def run_adder():
  client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
  await client.start()

  print(f'[🔍] Connecting to channel: {TARGET_CHANNEL}')
  my_channel = await client.get_entity(TARGET_CHANNEL)

  if not os.path.exists('scraped_users.csv'):
    print('[!] scraped_users.csv file not found.')
    return

  with open('scraped_users.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    count = 0

    for row in reader:
      if count >= 15:
        break
      try:
        user_to_add = InputPeerUser(int(row['id']), int(row['access_hash']))
        await client(InviteToChannelRequest(my_channel, [user_to_add]))
        print(f"[✔] Successfully added: {row['username']}")
        count += 1
        time.sleep(45)
      except FloodWaitError as e:
        print(f"[!] FloodWait triggered: Sleeping for {e.seconds} seconds...")
        break
      except Exception as e:
        print(f"[x] Error adding user: {e}")

  await client.disconnect()


if __name__ == '__main__':
  import asyncio

  asyncio.run(run_adder())
