import os
import csv
import sys
import random
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import InviteToChannelRequest
from telethon.tl.types import InputPeerUser
from telethon.errors import FloodWaitError, UserPrivacyRestrictedError, PeerFloodError

# Buffering off
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

print("🚀 Adder පටන් ගන්නවා...")

# ============================
# CONFIG
# ============================
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
STRING_SESSION = os.environ.get("STRING_SESSION")
TARGET_CHANNEL = "free_movies_stream_hd"

DAILY_LIMIT = 20
MIN_DELAY = 60
MAX_DELAY = 120

ADDED_FILE = "added_users.txt"
CSV_FILE = "scraped_users.csv"


async def main():
    print("🔌 Telegram client connect කරනවා...")
    
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    print("✅ Telegram client connected")
    
    # Target channel
    try:
        target = await client.get_entity(f"@{TARGET_CHANNEL}")
        print(f"✅ Target channel: {target.title}")
    except Exception as e:
        print(f"❌ Target channel error: {e}")
        return
    
    # Already added
    added = set()
    if os.path.exists(ADDED_FILE):
        with open(ADDED_FILE, "r") as f:
            added = set(line.strip() for line in f)
        print(f"📊 Already added: {len(added)}")
    
    # CSV
    if not os.path.exists(CSV_FILE):
        print(f"❌ {CSV_FILE} නෑ")
        return
    
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        all_users = list(reader)
    
    print(f"📊 Total users in CSV: {len(all_users)}")
    
    to_add = [u for u in all_users if u["id"] not in added]
    print(f"📊 Add කරන්න ඕන: {len(to_add)}")
    
    if not to_add:
        print("✅ ඔක්කොම add කරලා ඉවරයි!")
        return
    
    batch = to_add[:DAILY_LIMIT]
    print(f"\n🎯 අද add කරන්නේ: {len(batch)} users\n")
    
    success = 0
    failed = 0
    
    for i, user in enumerate(batch, 1):
        try:
            user_id = int(user["id"])
            access_hash = int(user["access_hash"])
            
            user_peer = InputPeerUser(user_id, access_hash)
            
            await client(InviteToChannelRequest(target, [user_peer]))
            
            print(f"[{i}/{len(batch)}] ✅ Added: @{user['username']}")
            success += 1
            
            with open(ADDED_FILE, "a") as f:
                f.write(user["id"] + "\n")
            
            delay = random.randint(MIN_DELAY, MAX_DELAY)
            print(f"    ⏳ ඊළඟ එකට {delay}s...")
            await asyncio.sleep(delay)
            
        except FloodWaitError as e:
            print(f"⚠️ FloodWait: {e.seconds}s")
            await asyncio.sleep(e.seconds)
        except UserPrivacyRestrictedError:
            print(f"[{i}/{len(batch)}] 🔒 @{user['username']} — privacy")
            failed += 1
        except PeerFloodError:
            print(f"❌ PeerFlood — Telegram block. නවත්තනවා.")
            break
        except Exception as e:
            print(f"[{i}/{len(batch)}] ❌ @{user['username']}: {e}")
            failed += 1
            continue
    
    print(f"\n📊 Results:")
    print(f"   ✅ Success: {success}")
    print(f"   ❌ Failed: {failed}")
    
    await client.disconnect()
    print("🔌 Disconnected")


if __name__ == "__main__":
    asyncio.run(main())
