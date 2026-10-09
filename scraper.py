import os
import csv
import sys
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.errors import FloodWaitError

# Buffering off කරන්න (log එකේ output පේන්න)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

print("🚀 Scraper පටන් ගන්නවා...")

# ============================
# CONFIG
# ============================
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
STRING_SESSION = os.environ.get("STRING_SESSION")

COMPETITOR_CHANNELS = [
    "english_films_with_subtitle",
    "English_Movie_Zone",
]

MAX_USERS_PER_CHANNEL = 100
OUTPUT_CSV = "scraped_users.csv"


async def scrape_channel(client, channel_name):
    print(f"\n🔍 Scraping: @{channel_name}")
    
    try:
        channel = await client.get_entity(f"@{channel_name}")
        print(f"✅ Channel හම්බුනා: {channel.title}")
    except Exception as e:
        print(f"❌ Channel එකට access නෑ: {e}")
        return []
    
    users = []
    offset = 0
    limit = 100
    
    try:
        while len(users) < MAX_USERS_PER_CHANNEL:
            print(f"  📥 Offset {offset} එකෙන් ගන්නවා...")
            
            participants = await client(GetParticipantsRequest(
                channel=channel,
                filter=ChannelParticipantsSearch(''),
                offset=offset,
                limit=limit,
                hash=0
            ))
            
            if not participants.users:
                print("  ⚠️ තව users නෑ")
                break
            
            for user in participants.users:
                if user.bot or user.deleted:
                    continue
                if not user.username:
                    continue
                
                users.append({
                    "id": user.id,
                    "access_hash": user.access_hash,
                    "username": user.username,
                    "first_name": user.first_name or "",
                    "last_name": user.last_name or "",
                })
                
                if len(users) >= MAX_USERS_PER_CHANNEL:
                    break
            
            offset += limit
            print(f"  📥 මේ වෙනකොට {len(users)} users")
            
            await asyncio.sleep(2)
            
    except FloodWaitError as e:
        print(f"⚠️ FloodWait: {e.seconds} seconds")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"✅ @{channel_name} එකෙන් {len(users)} users හම්බුනා")
    return users


async def main():
    print("🔌 Telegram client connect කරනවා...")
    
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    print("✅ Telegram client connected")
    
    all_users = []
    
    for channel in COMPETITOR_CHANNELS:
        users = await scrape_channel(client, channel)
        all_users.extend(users)
        await asyncio.sleep(5)
    
    # Duplicates අයින් කරන්න
    seen_ids = set()
    unique_users = []
    for user in all_users:
        if user["id"] not in seen_ids:
            seen_ids.add(user["id"])
            unique_users.append(user)
    
    print(f"\n📊 මුළු users: {len(all_users)}")
    print(f"📊 Unique users: {len(unique_users)}")
    
    # CSV එකට save කරන්න
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "access_hash", "username", "first_name", "last_name"])
        writer.writeheader()
        writer.writerows(unique_users)
    
    print(f"✅ {OUTPUT_CSV} එකට save කරා")
    print(f"📁 File size: {os.path.getsize(OUTPUT_CSV)} bytes")
    
    await client.disconnect()
    print("🔌 Disconnected")


if __name__ == "__main__":
    asyncio.run(main())
