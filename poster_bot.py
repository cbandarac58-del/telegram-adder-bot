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

def fetch_url(url):
    """Fetch URL using curl or requests."""
    try:
        cmd = ["curl", "-sL", "--compressed", "-H", f"User-Agent: {USER_AGENT}", url]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        if res.returncode == 0 and len(res.stdout) > 50:
            return res.stdout
    except Exception as e:
        print(f"⚠️ curl error for {url}: {e}")

    try:
        headers = {"User-Agent": USER_AGENT}
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.text
    except Exception as e:
        print(f"⚠️ requests error for {url}: {e}")

    return None


def get_movie_details(movie_url):
    """Extract details for a single movie page from its JSON-LD and meta tags."""
    html = fetch_url(movie_url)
    if not html:
        return None

    title = None
    poster = None
    rating = "N/A"
    description = None

    # 1. Parse JSON-LD
    try:
        json_blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
        for block in json_blocks:
            try:
                data = json.loads(block)
                graphs = data.get("@graph", [data]) if isinstance(data, dict) else []
                for item in graphs:
                    if item.get("@type") == "Movie":
                        title = item.get("name")
                        poster = item.get("image")
                        desc = item.get("description")
                        if desc:
                            description = desc
            except Exception:
                continue
    except Exception as e:
        print(f"⚠️ JSON-LD error on {movie_url}: {e}")

    # 2. Fallbacks from OpenGraph meta tags
    if not title:
        m = re.search(r'<meta property="og:title" content="([^"]+)"', html)
        if m:
            title = m.group(1).split(" - ")[0].strip()

    if not poster:
        m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
        if m:
            poster = m.group(1)

    if not description:
        m = re.search(r'<meta property="og:description" content="([^"]+)"', html)
        if m:
            description = m.group(1)

    # 3. Rating extraction
    m_rate = re.search(r'rating of ([\d.]+)/10 on TMDB', html)
    if m_rate:
        rating = m_rate.group(1)
    else:
        m_rate2 = re.search(r'class="badge-(?:hd|rating)"[^>]*>\s*(?:⭐\s*)?([\d.]+)', html)
        if m_rate2:
            rating = m_rate2.group(1)

    if not title:
        return None

    return {
        "url": movie_url,
        "title": title,
        "poster": poster,
        "rating": rating,
        "description": description
    }


def get_movies_from_sitemaps(posted_set):
    """Get unposted movie URLs from the site's XML sitemaps using regex."""
    movie_urls = []
    seen = set()
    sitemaps = [
        f"{SITE_URL}/sitemaps/movies-1.xml",
        f"{SITE_URL}/sitemaps/movies-2.xml"
    ]

    for sm_url in sitemaps:
        print(f"📄 Checking sitemap: {sm_url}")
        content = fetch_url(sm_url)
        if not content:
            continue
        try:
            matches = re.findall(r'https://movies\.vixtube\.net/movie/\d+', content)
            for m in matches:
                if m not in posted_set and m not in seen:
                    seen.add(m)
                    movie_urls.append(m)
        except Exception as e:
            print(f"⚠️ Sitemap regex error: {e}")

    print(f"📊 Found {len(movie_urls)} unposted movie URLs in sitemaps")
    return movie_urls


def get_trending_from_homepage():
    """Try to extract trending movies from the homepage JSON-LD."""
    html = fetch_url(SITE_URL)
    if not html:
        return []

    movies = []
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
                            if url and "/movie/" in url:
                                movies.append({
                                    "url": url,
                                    "title": m.get("name", "").strip(),
                                    "poster": m.get("image", ""),
                                    "rating": "N/A",
                                    "description": None
                                })
            except Exception:
                continue
    except Exception as e:
        print(f"⚠️ Homepage JSON-LD error: {e}")

    return movies


async def post_to_telegram():
    posted_file = "posted_movies.txt"
    posted = set()
    if os.path.exists(posted_file):
        with open(posted_file, "r") as f:
            posted = set(line.strip() for line in f if line.strip())

    candidates = []

    # 1. Try homepage trending movies
    trending = get_trending_from_homepage()
    for t in trending:
        if t["url"] not in posted and not any(c["url"] == t["url"] for c in candidates):
            candidates.append(t)

    # 2. Fill from sitemaps
    if len(candidates) < POSTS_PER_DAY:
        sitemap_urls = get_movies_from_sitemaps(posted)
        random.shuffle(sitemap_urls)
        for sm_url in sitemap_urls:
            if not any(c["url"] == sm_url for c in candidates):
                print(f"🔍 Fetching details for: {sm_url}")
                det = get_movie_details(sm_url)
                if det:
                    candidates.append(det)
                if len(candidates) >= POSTS_PER_DAY:
                    break
                time.sleep(1)

    if not candidates:
        print("❌ කිසිදු movie එකක් සොයාගත නොහැකි විය.")
        return

    to_post = candidates[:POSTS_PER_DAY]
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
            if movie.get("description"):
                desc = movie["description"]
                if len(desc) > 200:
                    desc = desc[:200] + "..."
                caption += f"📝 {desc}\n\n"
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

            print(f"✅ Successfully Posted: {movie['title']}")

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