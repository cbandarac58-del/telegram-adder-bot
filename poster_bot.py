import os
import re
import time
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

# ============================
# SITE එකට request එක යවන function එක
# ============================
def fetch_site():
    """Site එකට browser එකක් වගේ request එකක් යවනවා"""
    
    # බොරු browser headers - Cloudflare එකට රවට්ටන්න
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    
    # Session එකක් පාවිච්චි කරනවා (cookies handle කරන්න)
    session = requests.Session()
    session.headers.update(headers)
    
    try:
        response = session.get(SITE_URL, timeout=30)
        print(f"📡 Status Code: {response.status_code}")
        
        if response.status_code == 403:
            print("❌ 403 Forbidden - Site එක block කරනවා")
            return None
        
        response.raise_for_status()
        return response.text
        
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


# ============================
# Movies list එක scrape කරනවා
# ============================
def get_movies_from_site():
    html = fetch_site()
    if not html:
        return []
    
    # Movie cards pattern එක
    pattern = r'<a href="(/movie/\d+)" class="movie-card"[^>]*title="Watch ([^"]+) online"[^>]*>.*?<img src="([^"]+)".*?badge-rating">\s*⭐\s*([\d.]+|N/A).*?<h3 class="card-title">\s*([^<]+?)\s*</h3>'
    
    matches = re.findall(pattern, html, re.DOTALL)
    
    movies = []
    for match in matches:
        movies.append({
            "url": f"{SITE_URL}{match[0]}",
            "title": match[4].strip(),
            "poster": match[2],
            "rating": match[3].strip()
        })
    
    print(f"✅ Movies {len(movies)} ක් හම්බුනා")
    return movies


# ============================
# Telegram post කරන එක
# ============================
async def post_to_telegram():
    movies = get_movies_from_site()
    
    if not movies:
        print("❌ Movies නෑ")
        return
    
    posted_file = "posted_movies.txt"
    posted = set()
    if os.path.exists(posted_file):
        with open(posted_file, "r") as f:
            posted = set(line.strip() for line in f)
    
    new_movies = [m for m in movies if m["url"] not in posted]
    
    if not new_movies:
        print("❌ අලුත් movies නෑ")
        return
    
    to_post = new_movies[:POSTS_PER_DAY]
    print(f"📤 Post කරන්න යන movies: {len(to_post)}")
    
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    
    for movie in to_post:
        try:
            caption = f"🎬 **{movie['title']}**\n\n"
            caption += f"⭐ Rating: {movie['rating']}/10\n\n"
            caption += f"👉 [Watch Now]({movie['url']})\n\n"
            caption += f"📢 @free_movies_stream_hd"
            
            # Poster download
            img_response = requests.get(movie["poster"], timeout=30)
            img_path = f"/tmp/{movie['title'].replace(' ', '_').replace('/', '_')}.jpg"
            with open(img_path, "wb") as f:
                f.write(img_response.content)
            
            # Post to Telegram
            await client.send_file(
                TARGET_CHANNEL,
                img_path,
                caption=caption,
                parse_mode="md"
            )
            
            print(f"✅ Posted: {movie['title']}")
            
            with open(posted_file, "a") as f:
                f.write(movie["url"] + "\n")
            
            time.sleep(30)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
    
    await client.disconnect()
    print("✅ ඔක්කොම post ඉවරයි!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(post_to_telegram())
