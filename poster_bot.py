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
POSTS_PER_DAY = 5

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
        print("ℹ️ අලුත් movies නැත (සියල්ල දැනටමත් post කර ඇත).")
        return

    to_post = new_movies[:POSTS_PER_DAY]
    print(f"🚀 Telegram වෙත post කිරීමට නියමිත movies: {len(to_post)}")

    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()

    target = TARGET_CHANNEL
    channel_tag = target if str(target).startswith("@") else ""

    for movie in to_post:
        try:
            caption = f"🎬 **{movie['title']}**\n\n"
            if movie.get("rating") and movie["rating"] != "N/A":
                caption += f"⭐ Rating: {movie['rating']}/10\n\n"
            caption += f"🍿 [Watch Online]({movie['url']})\n"
            if channel_tag:
                caption += f"\n📢 Join: {channel_tag}"

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
                    target,
                    img_path,
                    caption=caption,
                    parse_mode="md"
                )
            else:
                await client.send_message(
                    target,
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
    print("🎉 සාර්ථකව movies post කර අවසන්!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(post_to_telegram())