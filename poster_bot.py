import os
import re
import json
import time
import datetime
import html as html_lib
import requests
from telethon import TelegramClient
from telethon.sessions import StringSession

# ============================
# CONFIG
# ============================
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
STRING_SESSION = os.environ.get("STRING_SESSION", "")
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL", "@free_movies_stream_hd")
# If TARGET_CHANNEL was set to the discussion group, force it back to channel
if "4373091333" in str(TARGET_CHANNEL):
    TARGET_CHANNEL = "@free_movies_stream_hd"

SITE_URL = "https://movies.vixtube.net"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Verified high-quality fallbacks with valid TMDB IDs
FALLBACK_MOVIES = [
    {"url": f"{SITE_URL}/movie/1813355", "title": "A Story of Derry", "poster": "https://image.tmdb.org/t/p/w500/q2XCoT6AqBANz0mKmkgVeo4PyRQ.jpg", "rating": "6.7", "type": "movie"},
    {"url": f"{SITE_URL}/movie/1571955", "title": "Collision Course", "poster": "https://image.tmdb.org/t/p/w500/s2eAK0uiODjlNUSIiOBwdp3at2u.jpg", "rating": "6.9", "type": "movie"},
    {"url": f"{SITE_URL}/movie/1283515", "title": "Verity", "poster": "https://image.tmdb.org/t/p/w500/rmaNMA1seHqpjtnYKzyynFAr1g8.jpg", "rating": "7.2", "type": "movie"},
    {"url": f"{SITE_URL}/movie/1507696", "title": "Apocalypse Z: New World", "poster": "https://image.tmdb.org/t/p/w500/wXln4DUrwcyjcFPwgQxFPYTlG1Z.jpg", "rating": "6.8", "type": "movie"},
    {"url": f"{SITE_URL}/movie/1400940", "title": "Clayface", "poster": "https://image.tmdb.org/t/p/w500/9l1NuFjel2j89hiuiJbsxfblqjy.jpg", "rating": "7.0", "type": "movie"},
    {"url": f"{SITE_URL}/movie/1384216", "title": "The Dog Stars", "poster": "https://image.tmdb.org/t/p/w500/5O616X9vmRzQdB68PHzBewPittd.jpg", "rating": "7.4", "type": "movie"},
    {"url": f"{SITE_URL}/movie/1339713", "title": "Obsession", "poster": "https://image.tmdb.org/t/p/w500/bRwnj8WEKBCvmfeUNOukJPwB43K.jpg", "rating": "6.5", "type": "movie"},
    {"url": f"{SITE_URL}/movie/1465063", "title": "Forgotten Island", "poster": "https://image.tmdb.org/t/p/w500/myd1K3gefdNAWFsGNRDdMeiK9Qg.jpg", "rating": "6.8", "type": "movie"},
    {"url": f"{SITE_URL}/movie/1058424", "title": "Hope", "poster": "https://image.tmdb.org/t/p/w500/6VY1ZKgpsc8CfGsQcCGiYEgHdH0.jpg", "rating": "7.5", "type": "movie"},
    {"url": f"{SITE_URL}/movie/791523", "title": "Wildwood", "poster": "https://image.tmdb.org/t/p/w500/8g7q6o54WfKWRmUQ0Ye8OskevUY.jpg", "rating": "7.1", "type": "movie"},
    {"url": f"{SITE_URL}/movie/533535", "title": "Deadpool & Wolverine", "poster": "https://image.tmdb.org/t/p/w500/8cdWjvZQUExUUTzyp4t6EDMubfO.jpg", "rating": "7.7", "type": "movie"},
    {"url": f"{SITE_URL}/movie/1022789", "title": "Inside Out 2", "poster": "https://image.tmdb.org/t/p/w500/vpnVM9B6NMmQpWeZvzLvDESb2QY.jpg", "rating": "7.6", "type": "movie"},
    {"url": f"{SITE_URL}/movie/945961", "title": "Alien: Romulus", "poster": "https://image.tmdb.org/t/p/w500/b33nnKl1GSFbao8l3urDDgo40KG.jpg", "rating": "7.3", "type": "movie"},
    {"url": f"{SITE_URL}/movie/519182", "title": "Despicable Me 4", "poster": "https://image.tmdb.org/t/p/w500/wWba3TaojhK7NdycRhoQpsG0FaH.jpg", "rating": "7.1", "type": "movie"}
]

FALLBACK_TV = [
    {"url": f"{SITE_URL}/tv/2734", "title": "Law & Order: Special Victims Unit", "poster": "https://image.tmdb.org/t/p/w500/pHNhUwSXuDQ9jPZOCb8SgJaQZsc.jpg", "rating": "8.0", "type": "tv"},
    {"url": f"{SITE_URL}/tv/4057", "title": "Criminal Minds", "poster": "https://image.tmdb.org/t/p/w500/hWSb4UnIjlTvnvrP98NbFSO60HA.jpg", "rating": "8.3", "type": "tv"},
    {"url": f"{SITE_URL}/tv/1434", "title": "Family Guy", "poster": "https://image.tmdb.org/t/p/w500/3PFsEuAiyLkWsP4GG6dIV37Q6gu.jpg", "rating": "7.4", "type": "tv"},
    {"url": f"{SITE_URL}/tv/456", "title": "The Simpsons", "poster": "https://image.tmdb.org/t/p/w500/tf0CUEynk6GfmrlHIQKQ5mfFP5P.jpg", "rating": "8.0", "type": "tv"},
    {"url": f"{SITE_URL}/tv/1622", "title": "Supernatural", "poster": "https://image.tmdb.org/t/p/w500/KoYWsq0DvBPQ967hoxk6I9YQvj.jpg", "rating": "8.3", "type": "tv"},
    {"url": f"{SITE_URL}/tv/2316", "title": "The Office", "poster": "https://image.tmdb.org/t/p/w500/7DJKHzAi83BmQrWLrYY5qDY4JJm.jpg", "rating": "8.6", "type": "tv"},
    {"url": f"{SITE_URL}/tv/1100", "title": "How I Met Your Mother", "poster": "https://image.tmdb.org/t/p/w500/b34jPzmB0wZy7EjgAGOW0v6UmHG.jpg", "rating": "8.2", "type": "tv"},
    {"url": f"{SITE_URL}/tv/18165", "title": "The Vampire Diaries", "poster": "https://image.tmdb.org/t/p/w500/bVRaSm5bV6dZ8vV8Rrh6dO7d1Wf.jpg", "rating": "8.3", "type": "tv"},
    {"url": f"{SITE_URL}/tv/60735", "title": "The Flash", "poster": "https://image.tmdb.org/t/p/w500/rg8N7x27Ef6P3IRWs40zs895Bgv.jpg", "rating": "7.8", "type": "tv"},
    {"url": f"{SITE_URL}/tv/1399", "title": "Game of Thrones", "poster": "https://image.tmdb.org/t/p/w500/1XS1oqL89opfnbLl8WnZY1O1uJx.jpg", "rating": "8.4", "type": "tv"}
]


def fetch_movies_from_site():
    """Scrapes trending/latest movies from movies.vixtube.net homepage."""
    url = f"{SITE_URL}/"
    movies = []
    try:
        print(f"🌐 Fetching live movies from: {url}")
        res = requests.get(url, headers=HEADERS, timeout=20)
        if res.status_code != 200:
            print(f"⚠️ Non-200 status code: {res.status_code}")
            return FALLBACK_MOVIES

        html = res.text
        # Extract movie links like /movie/12345
        pattern = re.compile(r'href=["\'](/movie/(\d+))["\']')
        found_ids = set()

        # Look for movie cards in HTML
        card_pattern = re.compile(
            r'<a[^>]+href=["\'](/movie/(\d+))["\'][^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE
        )

        for match in card_pattern.finditer(html):
            path, mid, content = match.group(1), match.group(2), match.group(3)
            if mid in found_ids:
                continue

            img_match = re.search(r'src=["\']([^"\']+)["\']', content)
            img_url = img_match.group(1) if img_match else None
            if img_url and not img_url.startswith("http"):
                img_url = f"{SITE_URL}{img_url}"

            title_match = re.search(r'alt=["\']([^"\']+)["\']', content)
            if not title_match:
                title_match = re.search(r'<h[2-4][^>]*>(.*?)</h[2-4]>', content, re.DOTALL)
            title = title_match.group(1).strip() if title_match else None
            if title:
                title = re.sub(r'<[^>]+>', '', title).strip()
                title = html_lib.unescape(title)

            if mid and title:
                found_ids.add(mid)
                movies.append({
                    "url": f"{SITE_URL}/movie/{mid}",
                    "title": title,
                    "poster": img_url,
                    "rating": "N/A",
                    "type": "movie"
                })

        print(f"✅ Extracted {len(movies)} movies from site!")
        if movies:
            return movies
    except Exception as e:
        print(f"⚠️ Error fetching movies: {e}")

    return FALLBACK_MOVIES


def fetch_tv_from_site():
    """Scrapes TV series from movies.vixtube.net/tv."""
    url = f"{SITE_URL}/tv"
    series = []
    try:
        print(f"🌐 Fetching live TV series from: {url}")
        res = requests.get(url, headers=HEADERS, timeout=20)
        if res.status_code != 200:
            print(f"⚠️ Non-200 status code: {res.status_code}")
            return FALLBACK_TV

        html = res.text
        card_pattern = re.compile(
            r'<a[^>]+href=["\'](/tv/(\d+))["\'][^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE
        )
        found_ids = set()

        for match in card_pattern.finditer(html):
            path, tid, content = match.group(1), match.group(2), match.group(3)
            if tid in found_ids:
                continue

            img_match = re.search(r'src=["\']([^"\']+)["\']', content)
            img_url = img_match.group(1) if img_match else None
            if img_url and not img_url.startswith("http"):
                img_url = f"{SITE_URL}{img_url}"

            title_match = re.search(r'alt=["\']([^"\']+)["\']', content)
            if not title_match:
                title_match = re.search(r'<h[2-4][^>]*>(.*?)</h[2-4]>', content, re.DOTALL)
            title = title_match.group(1).strip() if title_match else None
            if title:
                title = re.sub(r'<[^>]+>', '', title).strip()
                title = html_lib.unescape(title)

            if tid and title:
                found_ids.add(tid)
                series.append({
                    "url": f"{SITE_URL}/tv/{tid}",
                    "title": title,
                    "poster": img_url,
                    "rating": "N/A",
                    "type": "tv"
                })

        print(f"✅ Extracted {len(series)} TV series from site!")
        if series:
            return series
    except Exception as e:
        print(f"⚠️ Error fetching TV series: {e}")
        
    return FALLBACK_TV


def get_next_item_to_post():
    """
    Manages daily quota:
    - Exactly 12 posts per day (spaced 2 hours apart)
    - 7 Movies and 5 TV Series
    Uses daily_tracker.json to keep state across runs with Sri Lanka timezone.
    """
    tracker_file = "daily_tracker.json"
    now_sl = datetime.datetime.utcnow() + datetime.timedelta(hours=5, minutes=30)
    today_str = now_sl.strftime("%Y-%m-%d")
    current_utc_hour = datetime.datetime.utcnow().hour
    
    tracker = {
        "date": today_str,
        "movies_today": 0,
        "tv_today": 0,
        "last_type": ""
    }
    
    if os.path.exists(tracker_file):
        try:
            with open(tracker_file, "r") as f:
                data = json.load(f)
                if data.get("date") == today_str:
                    tracker = data
                else:
                    print(f"🔄 New day in Sri Lanka ({today_str})! Resetting daily post counter.")
        except Exception as e:
            print(f"⚠️ Tracker read error: {e}")
            
    print(f"📅 Today (SL): {tracker['date']} | Movies posted: {tracker['movies_today']}/7 | TV posted: {tracker['tv_today']}/5 (UTC Hour: {current_utc_hour})")
    
    # TV Slots: 5 slots
    # Movie Slots: 7 slots
    choose_tv = False
    if tracker["tv_today"] < 5 and tracker["movies_today"] >= 7:
        choose_tv = True
    elif tracker["movies_today"] < 7 and tracker["tv_today"] >= 5:
        choose_tv = False
    elif current_utc_hour in [2, 6, 10, 14, 18] and tracker["tv_today"] < 5:
        choose_tv = True
    elif tracker["movies_today"] < 7:
        choose_tv = False
    else:
        choose_tv = (tracker["tv_today"] < 5)

    post_type = "tv" if choose_tv else "movie"
    print(f"🎯 Target item type for this run: {post_type.upper()}")

    # Load posted URLs history
    posted_file = "posted_movies.txt"
    posted = set()
    if os.path.exists(posted_file):
        with open(posted_file, "r") as f:
            posted = set(line.strip() for line in f if line.strip())

    candidates = fetch_tv_from_site() if post_type == "tv" else fetch_movies_from_site()
    
    new_items = [item for item in candidates if item["url"] not in posted]
    if not new_items:
        print("ℹ️ All fetched items were posted before, cycling through candidates...")
        new_items = candidates

    selected = new_items[0]
    return selected, tracker, tracker_file, posted_file


async def get_target_entity(client, raw_target):
    """Robustly resolve target channel entity for Telethon, strictly avoiding groups."""
    print(f"🔧 get_target_entity called with raw_target: {raw_target}")
    
    TARGET_CHANNEL_ID = -1003944873164
    TARGET_USERNAME = "free_movies_stream_hd"
    
    # 1. Direct candidates
    candidates = [TARGET_CHANNEL_ID, f"@{TARGET_USERNAME}", TARGET_USERNAME]
    if raw_target and "4373091333" not in str(raw_target):
        candidates.insert(0, raw_target)
        
    for c in candidates:
        try:
            ent = await client.get_entity(c)
            # Make sure it's NOT a group/megagroup
            is_group = getattr(ent, 'megagroup', False) or (getattr(ent, 'title', '') and "group" in getattr(ent, 'title', '').lower())
            if not is_group:
                print(f"✅ Direct entity resolution succeeded for channel: {getattr(ent, 'title', ent.id)} (ID: {ent.id})")
                return ent
        except Exception:
            pass

    # 2. Iterate dialogs looking ONLY for BROADCAST channels
    print("🔍 Searching account dialogs for channel match...")
    async for dialog in client.iter_dialogs():
        is_broadcast = getattr(dialog.entity, 'broadcast', False)
        is_group = dialog.is_group or getattr(dialog.entity, 'megagroup', False)
        d_title = (dialog.title or '').lower()
        
        # Strictly ignore discussion group
        if is_group or "group" in d_title or not is_broadcast:
            continue
            
        d_id = str(dialog.id)
        d_user = (getattr(dialog.entity, 'username', '') or '').lower()
        
        if "3944873164" in d_id or d_user == TARGET_USERNAME or "free_movies_stream" in d_user or "hd movies hub" in d_title:
            print(f"✅ Matched broadcast channel dialog: {dialog.title} (ID: {dialog.id})")
            return dialog.entity

    # 3. Last fallback: any broadcast channel that is NOT a group
    async for dialog in client.iter_dialogs():
        is_broadcast = getattr(dialog.entity, 'broadcast', False)
        is_group = dialog.is_group or getattr(dialog.entity, 'megagroup', False)
        d_title = (dialog.title or '').lower()
        if is_broadcast and not is_group and "group" not in d_title:
            print(f"✅ Auto-selected broadcast channel: {dialog.title} (ID: {dialog.id})")
            return dialog.entity

    raise RuntimeError("Could not find broadcast channel @free_movies_stream_hd!")


async def main():
    item, tracker, tracker_file, posted_file = get_next_item_to_post()
    if not item:
        print("❌ No item available to post.")
        return

    print(f"🚀 Preparing to post: {item['title']} ({item['type'].upper()})")
    
    # Setup caption
    is_tv = item["type"] == "tv"
    icon = "📺" if is_tv else "🎬"
    type_badge = " (TV Series)" if is_tv else ""
    
    # Hashtags
    tags = ["#TVSeries", "#Series", "#BingeWatch", "#WatchOnline", "#HD"] if is_tv else ["#Movie", "#Hollywood", "#HD", "#WatchOnline", "#Cinema"]
    year_match = re.search(r'\b(202\d|19\d\d)\b', item['title'])
    if year_match:
        tags.append(f"#{'TV' if is_tv else 'Movie'}{year_match.group(1)}")
    else:
        tags.append(f"#{'TV' if is_tv else 'Movie'}2026")
        
    clean_tag = re.sub(r'[^a-zA-Z0-9]', '', item['title'])
    if clean_tag and len(clean_tag) <= 20:
        tags.append(f"#{clean_tag}")
        
    hashtags = " ".join(tags[:6])
    
    caption = f"{icon} **{item['title']}**{type_badge}\n\n"
    if item.get("rating") and item["rating"] != "N/A":
        caption += f"⭐ Rating: {item['rating']}/10\n\n"
    caption += f"🍿 [Watch Online in HD]({item['url']})\n\n"
    caption += f"👉 Join for Daily HD Movies & Series: @free_movies_stream_hd\n\n"
    caption += f"{hashtags}"

    # Download poster image
    img_path = None
    if item.get("poster"):
        try:
            print(f"🖼️ Downloading poster from {item['poster']}...")
            img_res = requests.get(item["poster"], headers=HEADERS, timeout=25)
            if img_res.status_code == 200:
                safe_title = "".join(c for c in item["title"] if c.isalnum() or c in (" ", "_", "-")).rstrip()
                os.makedirs("/tmp", exist_ok=True)
                img_path = f"/tmp/{safe_title.replace(' ', '_')}.jpg"
                with open(img_path, "wb") as f:
                    f.write(img_res.content)
                print(f"✅ Poster downloaded to {img_path}")
        except Exception as ie:
            print(f"⚠️ Poster download error: {ie}")

    # Telethon client
    client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)
    await client.start()

    entity = await get_target_entity(client, TARGET_CHANNEL)
    channel_name = getattr(entity, 'title', str(TARGET_CHANNEL))
    print(f"🎯 Target Channel: {channel_name}")

    try:
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
        print(f"🎉 Successfully posted to Telegram Channel: {channel_name} - {item['title']}")
        
        # Update posted_movies.txt
        with open(posted_file, "a") as f:
            f.write(item["url"] + "\n")
            
        # Update tracker
        if is_tv:
            tracker["tv_today"] += 1
        else:
            tracker["movies_today"] += 1
        tracker["last_type"] = item["type"]
        
        with open(tracker_file, "w") as f:
            json.dump(tracker, f, indent=2)
            
        print(f"💾 Updated {tracker_file}: Movies {tracker['movies_today']}/7, TV {tracker['tv_today']}/5")

    except Exception as e:
        print(f"❌ Error sending to Telegram: {e}")
        raise e
    finally:
        await client.disconnect()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
