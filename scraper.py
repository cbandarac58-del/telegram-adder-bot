import os
import csv
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.errors import FloodWaitError

# ============================
# CONFIG
# ============================
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
STRING_SESSION = os.environ.get("STRING_SESSION")

# Competitor channels (ඔයාගේ niche එකේ)
COMPETITOR_CHANNELS = [
    "english_films_with_subtitle",
    "English_Movie_Zone",
]

# දවසට කීයක් scrape කරන්නද
MAX_USERS_PER_CHANNEL = 100

# Output file
OUTPUT_CSV = "scraped_users.csv"


async def scrape_channel(client, channel_name):
    """එක channel එකකින් users ලා scrape කරනවා"""
    print(f"\n🔍 Scraping: @{channel_name}")
    
    try:
        # Channel එකට join වෙන්න ඕන නෑ — just get entity
        channel = await client.get_entity(f"@{channel_name}")
    except Exception as e:
        print(f"❌ Channel එකට access නෑ: {e}")
        return []
    
    users = []
    offset = 0
    limit = 100
    
    try:
        while len(users) < MAX_USERS_PER_CHANNEL:
            # Participants ලා ගන්නවා
            participants = await client(GetParticipantsRequest(
                channel=channel,
                filter=ChannelParticipantsSearch(''),
                offset=offset,
                limit=limit,
                hash=0
            ))
            
            if not participants.users:
                break
            
            for user in participants.users:
                # Bots, deleted accounts skip කරන්න
                if user.bot or user.deleted:
                    continue
                
                # Username නැති අයත් skip කරන්න (add කරන්න බෑ)
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
            print(f"  📥 {len(users)} users හම්බුනා...")
            
            # Rate limit එකට delay
            await asyncio.sleep(2)
            
    except FloodWaitError as e:
        print(f"⚠️ FloodWait: {e.seconds} seconds")
        await asyncio.sleep(e.seconds)
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"✅ @{channel_name} එකෙන් {len(users)} users හම්බුනා")
    return users


async def main():
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    print("✅ Telegram client connected")
    
    all_users = []
    
    for channel in COMPETITOR_CHANNELS:
        users = await scrape_channel(client, channel)
        all_users.extend(users)
        await asyncio.sleep(5)  # Channels අතර delay
    
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
    
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
