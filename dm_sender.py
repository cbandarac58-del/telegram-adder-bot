import os
import csv
import sys
import random
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import InputPeerUser
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError, PeerFloodError

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

print("🚀 DM Sender පටන් ගන්නවා...")

# ============================
# CONFIG
# ============================
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
STRING_SESSION = os.environ.get("STRING_SESSION")

# දවසට කීයක් DM යවන්නද
# අලුත් account නම් 20-30, පරණ නම් 50-100
DAILY_LIMIT = 25

# Delay (seconds) - safe
MIN_DELAY = 60    # 1 minute
MAX_DELAY = 180   # 3 minutes

# Files
SENT_FILE = "sent_dms.txt"
CSV_FILE = "scraped_users.csv"

# Poster image URL (ඔයාගේ චැනල් එකේ poster එකක් හෝ ඕන movie poster එකක්)
POSTER_URL = "https://image.tmdb.org/t/p/w500/lFKA4GMz36dImEy3DQPdPF7G4V9.jpg"

# DM Message (English only)
DM_MESSAGE = """🎬 **Hi {name}!**

Looking for the latest **English movies** with **HD quality**?

Join our channel for:
✅ Latest Hollywood movies
✅ HD quality streams
✅ Daily updates
✅ Free watch links

👉 **@free_movies_stream_hd**

🍿 Don't miss out!"""


async def main():
    print("🔌 Telegram client connect කරනවා...")
    
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    print("✅ Connected")
    
    # Already sent
    sent = set()
    if os.path.exists(SENT_FILE):
        with open(SENT_FILE, "r") as f:
            sent = set(line.strip() for line in f)
        print(f"📊 Already sent: {len(sent)}")
    
    # CSV load
    if not os.path.exists(CSV_FILE):
        print(f"❌ {CSV_FILE} නෑ")
        return
    
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        all_users = list(reader)
    
    print(f"📊 Total users: {len(all_users)}")
    
    to_send = [u for u in all_users if u["id"] not in sent]
    print(f"📊 DM යවන්න ඕන: {len(to_send)}")
    
    if not to_send:
        print("✅ ඔක්කොම යවලා ඉවරයි!")
        return
    
    batch = to_send[:DAILY_LIMIT]
    print(f"\n🎯 අද යවන්නේ: {len(batch)} users\n")
    
    # Poster එක download කරන්න (එක පාරයි)
    print("📥 Poster download කරනවා...")
    import requests
    try:
        img_data = requests.get(POSTER_URL, timeout=30).content
        poster_path = "/tmp/poster.jpg"
        with open(poster_path, "wb") as f:
            f.write(img_data)
        print(f"✅ Poster saved: {poster_path}")
    except Exception as e:
        print(f"❌ Poster download error: {e}")
        poster_path = None
    
    success = 0
    failed = 0
    
    for i, user in enumerate(batch, 1):
        try:
            user_id = int(user["id"])
            access_hash = int(user["access_hash"])
            
            user_peer = InputPeerUser(user_id, access_hash)
            
            # Message එක හදන්න
            name = user.get("first_name", "").strip() or "friend"
            message = DM_MESSAGE.format(name=name)
            
            # Poster එකත් එක්ක යවන්න
            if poster_path and os.path.exists(poster_path):
                await client.send_file(
                    user_peer,
                    poster_path,
                    caption=message,
                    parse_mode="md"
                )
            else:
                await client.send_message(user_peer, message, parse_mode="md")
            
            print(f"[{i}/{len(batch)}] ✅ Sent to @{user['username']}")
            success += 1
            
            with open(SENT_FILE, "a") as f:
                f.write(user["id"] + "\n")
            
            delay = random.randint(MIN_DELAY, MAX_DELAY)
            print(f"    ⏳ ඊළඟ එකට {delay}s...")
            await asyncio.sleep(delay)
            
        except FloodWaitError as e:
            print(f"⚠️ FloodWait: {e.seconds}s — ඉවසන්න")
            await asyncio.sleep(e.seconds)
        except UserPrivacyRestrictedError:
            print(f"[{i}/{len(batch)}] 🔒 @{user['username']} — DM block")
            failed += 1
            with open(SENT_FILE, "a") as f:
                f.write(user["id"] + "\n")
        except PeerFloodError:
            print(f"❌ PeerFlood — නවත්තනවා")
            break
        except Exception as e:
            print(f"[{i}/{len(batch)}] ❌ @{user['username']}: {e}")
            failed += 1
            continue
    
    print(f"\n📊 Results:")
    print(f"   ✅ Sent: {success}")
    print(f"   ❌ Failed: {failed}")
    
    await client.disconnect()
    print("🔌 Disconnected")


if __name__ == "__main__":
    asyncio.run(main())
