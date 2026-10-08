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
TARGET_CHANNEL = os.environ.get('TARGET_CHANNEL')


async def run_adder():
  client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
  await client.start()

  my_channel = await client.get_entity(TARGET_CHANNEL)

  if not os.path.exists('scraped_users.csv'):
    print('[!] scraped_users.csv ෆයිල් එක හමුවුණේ නැත.')
    return

  with open('scraped_users.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    count = 0

    for row in reader:
      if (
          count >= 15
      ):  # ආරක්ෂාවට දවසකට/වරකට මෙන්බර්ස්ලා 15ක් වගේ බාගයක් දානවා
        break
      try:
        user_to_add = InputPeerUser(int(row['id']), int(row['access_hash']))
        client(InviteToChannelRequest(my_channel, [user_to_add]))
        print(f"[✔] සාර්ථකව එකතු කළා: {row['username']}")
        count += 1
        time.sleep(
            45
        )  # Telegram spam වලින් බේරෙන්න විනාඩියකට ආසන්න පරතරයක්
      except FloodWaitError as e:
        print(f"[!] FloodWait ආවා: තත්පර {e.seconds} ක් නවතිනවා...")
        break
      except Exception as e:
        print(f"[x] දෝෂයක්: {e}")

  await client.disconnect()


if __name__ == '__main__':
  import asyncio

  asyncio.run(run_adder())
