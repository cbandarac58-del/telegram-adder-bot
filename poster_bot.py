import os
import re
import json
import time
import random
import subprocess
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession

# ============================
# CONFIG
# ============================
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
STRING_SESSION = os.environ.get("STRING_SESSION")
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL")
SITE_URL = "https://movies.vixtube.net"
POSTS_PER_RUN = 1

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def get_movies_via_jina():
    """Fetch movies via r.jina.ai reader which bypasses Cloudflare datacenter blocks 100%."""
    try:
        url = f"https://r.jina.ai/{SITE_URL}"
        print(f"🌐 Fetching movies from: {url}")
        cmd = ["curl", "-sL", url]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
        text = res.stdout if (res.returncode == 0 and len(res.stdout) > 200) else requests.get(url, timeout=35).text

        movies = []
        pattern = r'\[!\[Image \d+:[^\]]*\]\((https://image\.tmdb\.org/[^\)]+)\)(.*?###\s*([^\]]+))\]\((https://movies\.vixtube\.net/movie/\d+)'
        matches = re.findall(pattern, text)
        for m in matches:
            poster = m[0]
            middle = m[1]
            title = m[2].strip()
            movie_url = m[3].strip()

            rate_match = re.search(r'⭐\s*([\d.]+|N/A)', middle)
            rating = rate_match.group(1) if rate_match else "N/A"

            movies.append({
                "url": movie_url,
                "title": title,
                "poster": poster,
                "rating": rating,
                "description": None
            })

        print(f"✅ Extracted {len(movies)} trending movies via Jina reader!")
        return movies
    except Exception as e:
        print(f"⚠️ Jina reader error: {e}")
        return []


async def get_target_entity(client, raw_target):
    """Robustly resolve target channel entity for Telethon."""
    raw = str(raw_target).strip()
    
    # 1. Prepare candidates for get_entity
    candidates = []
    if raw.startswith("-100") and raw[4:].isdigit():
        candidates.append(int(raw))
    elif raw.startswith("-") and raw[1:].isdigit():
        candidates.append(int(raw))
    elif raw.isdigit():
        candidates.append(int(f"-100{raw}"))
        candidates.append(int(raw))
    
    if raw.startswith("@"):
        candidates.append(raw)
    else:
        candidates.append(f"@{raw}")
        candidates.append(raw)

    for c in candidates:
        try:
            ent = await client.get_entity(c)
            print(f"✅ Direct entity resolution succeeded for: {c} -> {getattr(ent, 'title', ent.id)}")
            return ent
        except Exception as e:
            continue

    # 2. Iterate through user's dialogs to find the channel
    print("🔍 Searching account dialogs for channel match...")
    clean_target = raw.lower().lstrip("@").lstrip("-100").lstrip("-")
    
    async for dialog in client.iter_dialogs():
        if dialog.is_channel:
            d_id = str(dialog.id)
            d_user = (getattr(dialog.entity, 'username', '') or '').lower()
            d_title = (dialog.title or '').lower()
            
            if clean_target in d_id or (d_user and clean_target == d_user) or clean_target in d_title:
                print(f"✅ Matched channel dialog: {dialog.title} (ID: {dialog.id})")
                return dialog.entity

    # 3. Fallback: select any movie broadcast channel in account
    async for dialog in client.iter_dialogs():
        if dialog.is_channel:
            d_title = (dialog.title or '').lower()
            if "movie" in d_title or "stream" in d_title or "hub" in d_title:
                print(f"✅ Auto-selected movie channel: {dialog.title} (ID: {dialog.id})")
                return dialog.entity

    # 4. Fallback: select first channel dialog
    async for dialog in client.iter_dialogs():
        if dialog.is_channel and not getattr(dialog, 'is_group', False):
            print(f"✅ Fallback to first channel in account: {dialog.title} (ID: {dialog.id})")
            return dialog.entity

    return raw_target


async def post_to_telegram():
    posted_file = "posted_movies.txt"
    posted = set()
    if os.path.exists(posted_file):
        with open(posted_file, "r") as f:
            posted = set(line.strip() for line in f if line.strip())

    # Get trending movies
    movies = get_movies_via_jina()

    if not movies:
        print("❌ කිසිදු movie එකක් සොයාගත නොහැකි විය.")
        return

    # Filter out already posted movies
    new_movies = [m for m in movies if m["url"] not in posted]
    print(f"📊 අලුත් movies ගණන: {len(new_movies)} (දැනටමත් post කල ගණන: {len(posted)})")

    if not new_movies:
        print("ℹ️ අලුත් movies නැත (සියල්ල දැනටමත් post කර ඇත). posted_movies.txt reset කරනු ලැබේ...")
        # If all 20 have been posted, reset posted_file so it can cycle again
        if os.path.exists(posted_file):
            os.remove(posted_file)
            posted = set()
        new_movies = movies

    to_post = new_movies[:POSTS_PER_RUN]
    print(f"🚀 Telegram වෙත post කිරීමට නියමිත movies: {len(to_post)}")

    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()

    # Resolve entity safely
    entity = await get_target_entity(client, TARGET_CHANNEL)
    channel_name = getattr(entity, 'title', str(TARGET_CHANNEL))
    print(f"🎯 Target Channel: {channel_name}")

    for movie in to_post:
        try:
            # Dynamic SEO Hashtags
            tags = ["#Movie", "#Hollywood", "#HD", "#WatchOnline", "#Cinema"]
            year_match = re.search(r'\b(202\d|19\d\d)\b', movie['title'])
            if year_match:
                tags.append(f"#Movie{year_match.group(1)}")
            else:
                tags.append("#Movie2026")
            
            clean_title = re.sub(r'[^a-zA-Z0-9]', '', movie['title'])
            if clean_title and len(clean_title) <= 20:
                tags.append(f"#{clean_title}")
            
            hashtags = " ".join(tags[:6])

            caption = f"🎬 **{movie['title']}**\n\n"
            if movie.get("rating") and movie["rating"] != "N/A":
                caption += f"⭐ Rating: {movie['rating']}/10\n\n"
            caption += f"🍿 [Watch Online]({movie['url']})\n\n"
            caption += f"👉 Join for Daily HD Movies: @free_movies_stream_hd\n\n"
            caption += f"{hashtags}"

            # Poster download
            img_path = None
            if movie.get("poster"):
                try:
                    img_res = requests.get(movie["poster"], timeout=30)
                    if img_res.status_code == 200:
                        safe_title = "".join(c for c in movie["title"] if c.isalnum() or c in (" ", "_", "-")).rstrip()
                        img_path = f"/tmp/{safe_title.replace(' ', '_')}.jpg"
                        with open(img_path, "wb") as f:
                            f.write(img_res.content)
                except Exception as ie:
                    print(f"⚠️ Poster download error: {ie}")

            # Send to Telegram
            if img_path and os.path.exists(img_path):
                await client.send_file(
                    entity,
                    img_path,
                    caption=caption,
                    parse_mode="md"
                )
            else:
                await client.send_message(
                    entity,
                    caption,
                    parse_mode="md"
                )

            print(f"✅ Successfully Posted to Telegram: {movie['title']}")

            with open(posted_file, "a") as f:
                f.write(movie["url"] + "\n")

            time.sleep(10)

        except Exception as e:
            print(f"❌ Error posting {movie.get('title')}: {e}")
            continue

    await client.disconnect()
    print("🎉 සාර්ථකව movie එකක් post කර අවසන්!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(post_to_telegram())