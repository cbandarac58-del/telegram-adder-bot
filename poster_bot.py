import os
import re
import time
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import InputMediaPhoto

# ============================
# CONFIG - GitHub Secrets වලින් එනවා
# ============================
API_ID = int(os.environ.get("API_ID"))
API_HASH = os.environ.get("API_HASH")
STRING_SESSION = os.environ.get("STRING_SESSION")
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL")  # උදා: @free_movies_stream_hd
SITE_URL = "https://movies.vixtube.net"

# දවසට post කරන්න ඕන ගාන
POSTS_PER_DAY = 5

# ============================
# SITE එකේ movies list එක ගන්න
# ============================
def get_movies_from_site():
    """Site එකේ homepage එකෙන් movies ටික scrape කරනවා"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        response = requests.get(SITE_URL, headers=headers, timeout=30)
        response.raise_for_status()
        html = response.text
    except Exception as e:
        print(f"❌ Site එකට connect වෙන්න බෑ: {e}")
        return []
    
    # Movie cards ටික regex එකෙන් ගන්නවා
    # Pattern: <a href="/movie/1236045" class="movie-card" title="Watch X online">
    #          ... <img src="poster.jpg" ...>
    #          ... <span class="badge-rating">⭐ 5.7</span>
    #          ... <h3 class="card-title"> Movie Name </h3>
    
    pattern = r'<a href="(/movie/\d+)" class="movie-card"[^>]*title="Watch ([^"]+) online"[^>]*>.*?<img src="([^"]+)".*?badge-rating">\s*⭐\s*([\d.]+|N/A).*?<h3 class="card-title">\s*([^<]+?)\s*</h3>'
    
    matches = re.findall(pattern, html, re.DOTALL)
    
    movies = []
    for match in matches:
        movie_path = match[0]
        title = match[1].strip()
        poster = match[2]
        rating = match[3].strip()
        title_alt = match[4].strip()
        
        movies.append({
            "url": f"{SITE_URL}{movie_path}",
            "title": title_alt or title,
            "poster": poster,
            "rating": rating
        })
    
    print(f"✅ Movies {len(movies)} ක් හම්බුනා")
    return movies

# ============================
# Telegram එකට post කරනවා
# ============================
async def post_to_telegram():
    movies = get_movies_from_site()
    
    if not movies:
        print("❌ Movies නෑ, post කරන්න බෑ")
        return
    
    # දැනට post කරපු ඒවා track කරන්න file එකක්
    posted_file = "posted_movies.txt"
    posted = set()
    if os.path.exists(posted_file):
        with open(posted_file, "r") as f:
            posted = set(line.strip() for line in f)
    
    # අලුත් movies ටික විතරක් ගන්නවා
    new_movies = [m for m in movies if m["url"] not in posted]
    
    if not new_movies:
        print("❌ අලුත් movies නෑ")
        return
    
    # දවසට 5ක් විතරක් ගන්නවා
    to_post = new_movies[:POSTS_PER_DAY]
    print(f"📤 Post කරන්න යන movies: {len(to_post)}")
    
    # Telegram client එක start කරනවා
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()
    
    for movie in to_post:
        try:
            # Caption එක හදනවා
            caption = f"🎬 **{movie['title']}**\n\n"
            caption += f"⭐ Rating: {movie['rating']}/10\n\n"
            caption += f"👉 [Watch Now]({movie['url']})\n\n"
            caption += f"📢 @free_movies_stream_hd"
            
            # Poster එක download කරනවා
            img_response = requests.get(movie["poster"], timeout=30)
            img_path = f"/tmp/{movie['title'].replace(' ', '_')}.jpg"
            with open(img_path, "wb") as f:
                f.write(img_response.content)
            
            # Telegram එකට post කරනවා
            await client.send_file(
                TARGET_CHANNEL,
                img_path,
                caption=caption,
                parse_mode="md"
            )
            
            print(f"✅ Posted: {movie['title']}")
            
            # Post කරපු එක record කරනවා
            with open(posted_file, "a") as f:
                f.write(movie["url"] + "\n")
            
            # Rate limit එකට delay
            time.sleep(30)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
    
    await client.disconnect()
    print("✅ ඔක්කොම post ඉවරයි!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(post_to_telegram())
