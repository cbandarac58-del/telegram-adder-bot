import os
import re
import json
import time
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

# ============================
# SITE REQUEST FUNCTION
# ============================
def fetch_site():
    """Fetch site HTML using curl or curl_cffi to bypass Cloudflare 403 blocks."""
    # 1. System curl (Bypasses Python requests TLS fingerprinting and Cloudflare 403)
    try:
        cmd = [
            "curl", "-sL", "--compressed",
            "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "-H", "Accept-Language: en-US,en;q=0.9",
            SITE_URL
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        if res.returncode == 0 and len(res.stdout) > 500:
            print(f"✅ Site HTML fetched successfully via curl ({len(res.stdout)} bytes)")
            return res.stdout
    except Exception as e:
        print(f"⚠️ curl attempt error: {e}")

    # 2. curl_cffi with browser impersonation
    try:
        from curl_cffi import requests as cffi_requests
        resp = cffi_requests.get(SITE_URL, impersonate="chrome124", timeout=30)
        if resp.status_code == 200 and len(resp.text) > 500:
            print(f"✅ Site HTML fetched successfully via curl_cffi ({len(resp.text)} bytes)")
            return resp.text
    except Exception as e:
        print(f"⚠️ curl_cffi attempt error: {e}")

    # 3. Standard requests fallback
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        resp = requests.get(SITE_URL, headers=headers, timeout=30)
        if resp.status_code == 200:
            print(f"✅ Site HTML fetched via requests ({len(resp.text)} bytes)")
            return resp.text
        else:
            print(f"❌ requests status: {resp.status_code}")
    except Exception as e:
        print(f"❌ requests attempt error: {e}")

    return None


# ============================
# MOVIES LIST EXTRACTOR
# ============================
def get_movies_from_site():
    html = fetch_site()
    if not html:
        print("❌ Site HTML ලබාගත නොහැකි විය.")
        return []

    movies = []
    seen_urls = set()

    # 1. JSON-LD structured schema (Most reliable)
    try:
        json_blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
        for block in json_blocks:
            try:
                data = json.loads(block)
                graphs = data.get("@graph", [data]) if isinstance(data, dict) else []
                for item in graphs:
                    if item.get("@type") == "ItemList":
                        for el in item.get("itemListElement", []):
                            m = el.get("item", {})
                            url = m.get("url")
                            if url and url not in seen_urls:
                                seen_urls.add(url)
                                movies.append({
                                    "url": url,
                                    "title": m.get("name", "").strip(),
                                    "poster": m.get("image", ""),
                                    "rating": "N/A"
                                })
            except Exception:
                continue
    except Exception as e:
        print(f"⚠️ JSON-LD error: {e}")

    # 2. Extract ratings and additional movie cards from HTML
    pattern = r'<a\s+href="(/movie/\d+)"[^>]*class="movie-card"[^>]*title="Watch\s+([^"]+)\s+online"[^>]*>.*?<img\s+src="([^"]+)".*?<span[^>]*class="badge-(?:hd|rating)"[^>]*>\s*(?:⭐\s*)?([\d.]+|N/A).*?<h3[^>]*class="card-title">\s*([^<]+?)\s*</h3>'
    card_matches = re.findall(pattern, html, re.DOTALL)

    ratings_map = {}
    for cm in card_matches:
        full_url = f"{SITE_URL}{cm[0]}"
        rating_val = cm[3].strip()
        ratings_map[full_url] = rating_val
        if full_url not in seen_urls:
            seen_urls.add(full_url)
            movies.append({
                "url": full_url,
                "title": cm[4].strip(),
                "poster": cm[2],
                "rating": rating_val
            })

    # Update ratings from HTML cards into JSON-LD movies
    for m in movies:
        if m["url"] in ratings_map and ratings_map[m["url"]] != "N/A":
            m["rating"] = ratings_map[m["url"]]

    print(f"🎬 Movies {len(movies)} ක් සොයාගන්නා ලදී.")
    return movies


# ============================
# TELEGRAM POSTING
# ============================
async def post_to_telegram():
    movies = get_movies_from_site()

    if not movies:
        print("❌ කිසිදු movie එකක් හමු නොවීය.")
        return

    posted_file = "posted_movies.txt"
    posted = set()
    if os.path.exists(posted_file):
        with open(posted_file, "r") as f:
            posted = set(line.strip() for line in f if line.strip())

    new_movies = [m for m in movies if m["url"] not in posted]

    if not new_movies:
        print("ℹ️ අලුත් movies නැත (සියල්ල දැනටමත් post කර ඇත).")
        return

    to_post = new_movies[:POSTS_PER_DAY]
    print(f"🚀 Post කිරීමට නියමිත movies: {len(to_post)}")

    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()

    target = TARGET_CHANNEL
    # If target is channel username format (@channel)
    channel_tag = target if str(target).startswith("@") else ""

    for movie in to_post:
        try:
            caption = f"🎬 **{movie['title']}**\n\n"
            if movie.get('rating') and movie['rating'] != 'N/A':
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
                        safe_title = "".join(c for c in movie['title'] if c.isalnum() or c in (' ', '_', '-')).strip()
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

            print(f"✅ Posted: {movie['title']}")

            with open(posted_file, "a") as f:
                f.write(movie["url"] + "\n")

            time.sleep(15)

        except Exception as e:
            print(f"❌ Error posting {movie.get('title')}: {e}")
            continue

    await client.disconnect()
    print("🎉 සියලුම movies සාර්ථකව post කර අවසන්!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(post_to_telegram())