import os
import sys
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

sys.stdout.reconfigure(line_buffering=True)

API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
STRING_SESSION = os.environ.get("STRING_SESSION")

# ඔයාගේ competitor channels
CHANNELS = [
    "english_films_with_subtitle",
    "English_Movie_Zone",
]


async def main():
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    print("✅ Connected\n")
    
    for ch_name in CHANNELS:
        print(f"🔍 Channel: @{ch_name}")
        try:
            channel = await client.get_entity(f"@{ch_name}")
            
            # Linked discussion group හොයන්න
            from telethon.tl.functions.channels import GetFullChannelRequest
            full = await client(GetFullChannelRequest(channel))
            
            linked_chat_id = full.full_chat.linked_chat_id
            
            if linked_chat_id:
                linked = await client.get_entity(linked_chat_id)
                print(f"  ✅ Discussion Group: @{linked.username}")
                print(f"     Name: {linked.title}")
                print(f"     ID: {linked.id}")
            else:
                print(f"  ❌ Discussion Group නෑ")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        print()
    
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
