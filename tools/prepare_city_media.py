#!/usr/bin/env python3
"""Download licensed Wikimedia Commons photos, strip EXIF, and build city media derivatives."""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
STAGING = Path("/tmp/city-media-staging")
UA = "UrbanConcierge/1.0 (https://bamedia.agency; city brief media; research@bamedia.agency)"
COMMONS = "https://commons.wikimedia.org/w/api.php"
COMMONS_FILE = "https://commons.wikimedia.org/wiki/"

# Image helpers copied from optimize_media.py (same quality targets).
sys.path.insert(0, str(Path(__file__).parent))
from optimize_media import (  # noqa: E402
    crop_ratio,
    exif_clean,
    fit_bytes,
    resize_long_edge,
    save_jpeg,
    verify_clean,
)

def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def commons_info(title: str) -> dict:
    url = COMMONS + "?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "titles": title,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|size|mime",
        "iiurlwidth": 2400,
    })
    pages = (get_json(url).get("query") or {}).get("pages") or {}
    p = next(iter(pages.values()))
    if "imageinfo" not in p:
        raise SystemExit(f"missing on Commons: {title}")
    info = p["imageinfo"][0]
    meta = info.get("extmetadata") or {}

    def g(k: str) -> str:
        v = (meta.get(k) or {}).get("value") or ""
        v = re.sub(r"<[^>]+>", " ", v)
        return re.sub(r"\s+", " ", v).strip()

    # Prefer the 2400px transcode when available, else original.
    return {
        "title": p.get("title") or title,
        "url": info.get("thumburl") or info.get("url"),
        "orig_url": info.get("url"),
        "width": info.get("width"),
        "height": info.get("height"),
        "license": g("LicenseShortName") or g("License"),
        "license_url": g("LicenseUrl"),
        "artist": g("Artist"),
        "credit": g("Credit"),
        "description": g("ImageDescription"),
        "attribution": g("Attribution"),
        "usage": g("UsageTerms"),
    }

def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(1024 * 64)
            if not chunk:
                break
            f.write(chunk)

def process(city: str, photo: dict, info: dict) -> dict:
    out = ROOT / city
    originals = out / "media" / "originals"
    web = out / "media" / "web"
    events = out / "assets" / "events"
    originals.mkdir(parents=True, exist_ok=True)
    web.mkdir(parents=True, exist_ok=True)
    events.mkdir(parents=True, exist_ok=True)

    src = STAGING / f"{city}-{photo['id']}"
    im = exif_clean(Image.open(src))
    # Downscale huge originals before saving the clean original (max long edge 2400).
    orig_im = resize_long_edge(im, 2400)
    orig_path = originals / f"{photo['id']}.jpg"
    save_jpeg(orig_im, orig_path, 90)

    web_im = resize_long_edge(im, 1600)
    web_jpg = web / f"{photo['id']}.jpg"
    web_webp = web / f"{photo['id']}.webp"
    jq = fit_bytes(web_im, web_jpg, "jpeg", 180_000, 420_000, min_q=68, max_q=88)
    wq = fit_bytes(web_im, web_webp, "webp", 140_000, 400_000, min_q=68, max_q=86)

    thumb_im = resize_long_edge(im, 800)
    thumb_jpg = web / f"{photo['id']}-thumb.jpg"
    thumb_webp = web / f"{photo['id']}-thumb.webp"
    fit_bytes(thumb_im, thumb_jpg, "jpeg", 40_000, 160_000, min_q=65, max_q=82)
    fit_bytes(thumb_im, thumb_webp, "webp", 30_000, 140_000, min_q=65, max_q=80)

    credit = photo["credit_line"]
    entry = {
        "id": photo["id"],
        "original": f"originals/{photo['id']}.jpg",
        "commons_title": info["title"],
        "commons_url": COMMONS_FILE + urllib.parse.quote(info["title"].replace(" ", "_")),
        "license": info["license"],
        "license_url": info.get("license_url") or "",
        "artist": info.get("artist") or photo.get("artist") or "",
        "title": photo["title"],
        "description": photo["description"],
        "alt": photo["alt"],
        "caption": photo.get("caption"),
        "location": photo.get("location"),
        "suggested_section": photo.get("suggested_section"),
        "placements": photo["placements"],
        "on_page": photo.get("on_page", True),
        "orientation": "portrait" if web_im.size[1] > web_im.size[0] else "landscape",
        "web": {"webp": f"web/{photo['id']}.webp", "jpeg": f"web/{photo['id']}.jpg", "width": web_im.size[0], "height": web_im.size[1]},
        "thumb": {"webp": f"web/{photo['id']}-thumb.webp", "jpeg": f"web/{photo['id']}-thumb.jpg", "width": thumb_im.size[0], "height": thumb_im.size[1]},
        "credit": credit,
    }

    if "hero" in photo["placements"] or photo.get("hero_crop"):
        hero = crop_ratio(im, 2, 1, bias=photo.get("hero_crop", "center"))
        hero = resize_long_edge(hero, 1600)
        hero_jpg = web / f"{photo['id']}-hero.jpg"
        hero_webp = web / f"{photo['id']}-hero.webp"
        fit_bytes(hero, hero_jpg, "jpeg", 160_000, 400_000, min_q=68, max_q=86)
        fit_bytes(hero, hero_webp, "webp", 120_000, 380_000, min_q=68, max_q=84)
        entry["hero"] = {"webp": f"web/{photo['id']}-hero.webp", "jpeg": f"web/{photo['id']}-hero.jpg", "width": hero.size[0], "height": hero.size[1]}

    if photo.get("event_slug"):
        ev = crop_ratio(im, 16, 9, bias=photo.get("event_crop", "center"))
        ev = ev.resize((960, 540), Image.Resampling.LANCZOS)
        ev_path = events / f"{photo['event_slug']}.webp"
        fit_bytes(ev, ev_path, "webp", 40_000, 120_000, min_q=65, max_q=80)
        ev_jpg = web / f"{photo['id']}-event.jpg"
        ev_webp = web / f"{photo['id']}-event.webp"
        ev.save(ev_webp, "WEBP", quality=78, method=6)
        save_jpeg(ev, ev_jpg, 80)
        entry["event"] = {
            "slug": photo["event_slug"],
            "alt": photo.get("event_alt") or photo["alt"],
            "webp": f"assets/events/{photo['event_slug']}.webp",
            "width": 960, "height": 540,
        }
        if photo.get("keywords"):
            entry["keywords"] = list(photo["keywords"])
            entry["event"]["keywords"] = list(photo["keywords"])

    print(f"{city}/{photo['id']}: {im.size[0]}x{im.size[1]} -> web {web_im.size[0]}x{web_im.size[1]} jpg={web_jpg.stat().st_size//1024}KB@{jq} webp={web_webp.stat().st_size//1024}KB@{wq}")
    return entry


PHOTOS = {
    "detroit": [
        {
            "id": "detroit-skyline",
            "commons": "File:Detroit Skyline (123143197).jpeg",
            "title": "Detroit skyline from Windsor",
            "description": "The Detroit skyline at sunset, seen from across the river in Windsor, Ontario.",
            "alt": "The Detroit skyline at sunset across the Detroit River, with the Renaissance Center towers at center",
            "caption": "Detroit skyline from Windsor. Photo: Michael Tighe, CC0, via Wikimedia Commons",
            "location": "Detroit River, looking toward downtown Detroit",
            "suggested_section": "hero",
            "placements": ["hero"],
            "hero_crop": "center",
            "event_slug": "detroit-skyline",
            "event_alt": "The Detroit skyline at sunset across the Detroit River, with the Renaissance Center towers at center",
            "keywords": [],
            "credit_line": "Photo: Michael Tighe, CC0, via Wikimedia Commons",
        },
        {
            "id": "spirit-of-detroit-night",
            "commons": "File:The Spirit of Detroit at night, wide angle.jpg",
            "title": "The Spirit of Detroit at night",
            "description": "The Spirit of Detroit sculpture at night in downtown Detroit.",
            "alt": "The Spirit of Detroit bronze sculpture lit at night, with downtown buildings behind it",
            "caption": "The Spirit of Detroit. Photo: 42-BRT, public domain, via Wikimedia Commons",
            "location": "Coleman A. Young Municipal Center, downtown Detroit",
            "suggested_section": "events",
            "placements": ["event", "gallery"],
            "event_slug": "detroit-night",
            "event_alt": "The Spirit of Detroit bronze sculpture lit at night, with downtown buildings behind it",
            "event_crop": "center",
            "keywords": ["beacon park", "holiday lights", "winter lighting", "aglow", "lights", "downtown detroit"],
            "credit_line": "Photo: 42-BRT, public domain, via Wikimedia Commons",
        },
        {
            "id": "fisher-building",
            "commons": "File:Detroit December 2021 09 (Fisher Building).jpg",
            "title": "The Fisher Building",
            "description": "The Fisher Building in Detroit's New Center, home of the Fisher Theatre.",
            "alt": "The ornate stone facade and tall tower of the Fisher Building in Detroit's New Center",
            "caption": "The Fisher Building, New Center. Photo: Michael Barera, CC BY-SA 4.0, via Wikimedia Commons",
            "location": "New Center, Detroit",
            "suggested_section": "events",
            "placements": ["event", "stay", "gallery"],
            "event_slug": "fisher-building",
            "event_alt": "The ornate stone facade and tall tower of the Fisher Building in Detroit's New Center",
            "event_crop": "upper",
            "keywords": ["fisher", "fisher theatre", "fisher theater", "gatsby", "great gatsby"],
            "credit_line": "Photo: Michael Barera, CC BY-SA 4.0, via Wikimedia Commons",
        },
        {
            "id": "little-caesars-arena",
            "commons": "File:Detroit December 2018 09 (Little Caesars Arena).jpg",
            "title": "Little Caesars Arena",
            "description": "The exterior of Little Caesars Arena in downtown Detroit.",
            "alt": "The glass and steel exterior of Little Caesars Arena in downtown Detroit",
            "caption": "Little Caesars Arena. Photo: Michael Barera, CC BY-SA 4.0, via Wikimedia Commons",
            "location": "Downtown Detroit",
            "suggested_section": "events",
            "placements": ["event", "gallery"],
            "event_slug": "little-caesars-arena",
            "event_alt": "The glass and steel exterior of Little Caesars Arena in downtown Detroit",
            "event_crop": "center",
            "keywords": ["little caesars", "red wings", "pistons", "hockey", "nba", "nhl"],
            "credit_line": "Photo: Michael Barera, CC BY-SA 4.0, via Wikimedia Commons",
        },
        {
            "id": "michigan-central",
            "commons": "File:Detroit August 2025 23 (Michigan Central Station).jpg",
            "title": "Michigan Central Station",
            "description": "Michigan Central Station in Corktown, Detroit.",
            "alt": "The restored Michigan Central Station building in Corktown, Detroit, under a clear sky",
            "caption": "Michigan Central Station, Corktown. Photo: Michael Barera, CC BY-SA 4.0, via Wikimedia Commons",
            "location": "Corktown, Detroit",
            "suggested_section": "gallery",
            "placements": ["gallery"],
            "credit_line": "Photo: Michael Barera, CC BY-SA 4.0, via Wikimedia Commons",
        },
        {
            "id": "detroit-institute-of-arts",
            "commons": "File:Detroit Institute of Arts January 2015 01.jpg",
            "title": "Detroit Institute of Arts",
            "description": "The Detroit Institute of Arts on Woodward Avenue.",
            "alt": "The limestone facade and grand entrance of the Detroit Institute of Arts on Woodward Avenue",
            "caption": "Detroit Institute of Arts. Photo: Michael Barera, CC BY-SA 4.0, via Wikimedia Commons",
            "location": "Midtown, Detroit",
            "suggested_section": "gallery",
            "placements": ["gallery"],
            "credit_line": "Photo: Michael Barera, CC BY-SA 4.0, via Wikimedia Commons",
        },
        {
            "id": "guardian-building",
            "commons": "File:Detroit December 2015 28 (Guardian Building).jpg",
            "title": "The Guardian Building",
            "description": "The Guardian Building in downtown Detroit.",
            "alt": "The brick and terracotta Guardian Building rising above downtown Detroit",
            "caption": "The Guardian Building. Photo: Michael Barera, CC BY-SA 4.0, via Wikimedia Commons",
            "location": "Downtown Detroit",
            "suggested_section": "gallery",
            "placements": ["eat", "gallery"],
            "credit_line": "Photo: Michael Barera, CC BY-SA 4.0, via Wikimedia Commons",
        },
        {
            "id": "campus-martius",
            "commons": "File:Detroit December 2019 10 (Campus Martius Park).jpg",
            "title": "Campus Martius Park",
            "description": "Campus Martius Park in downtown Detroit.",
            "alt": "Campus Martius Park in downtown Detroit, with lawn, paths and surrounding office buildings",
            "caption": "Campus Martius Park. Photo: Michael Barera, CC BY-SA 4.0, via Wikimedia Commons",
            "location": "Downtown Detroit",
            "suggested_section": "gallery",
            "placements": ["gallery"],
            "credit_line": "Photo: Michael Barera, CC BY-SA 4.0, via Wikimedia Commons",
        },
        {
            "id": "renaissance-center",
            "commons": "File:Detroit-Renaissance Center.jpg",
            "title": "Renaissance Center",
            "description": "The Renaissance Center on the Detroit riverfront.",
            "alt": "The cylindrical glass towers of the Renaissance Center on the Detroit riverfront",
            "caption": "The Renaissance Center. Photo: Patricia Drury, CC BY 2.0, via Wikimedia Commons",
            "location": "Detroit riverfront",
            "suggested_section": "transit",
            "placements": ["transit", "gallery"],
            "credit_line": "Photo: Patricia Drury, CC BY 2.0, via Wikimedia Commons",
        },
    ],
    "phoenix": [
        {
            "id": "phoenix-skyline-night",
            "commons": "File:Downtown Phoenix Skyline at Night.jpg",
            "title": "Downtown Phoenix at night",
            "description": "The downtown Phoenix skyline at night.",
            "alt": "The downtown Phoenix skyline at night, with lit high-rises under a deep blue sky",
            "caption": "Downtown Phoenix at night. Photo: Alan Stark, CC BY-SA 2.0, via Wikimedia Commons",
            "location": "Downtown Phoenix",
            "suggested_section": "hero",
            "placements": ["hero"],
            "hero_crop": "center",
            "event_slug": "phoenix-skyline",
            "event_alt": "The downtown Phoenix skyline at night, with lit high-rises under a deep blue sky",
            "keywords": ["crescent ballroom", "downtown phoenix", "concert"],
            "credit_line": "Photo: Alan Stark, CC BY-SA 2.0, via Wikimedia Commons",
        },
        {
            "id": "papago-camelback",
            "commons": "File:2013, Papago Park, Papago Buttes, Hole in the Rock, Camelback Mountain in the Distance - panoramio.jpg",
            "title": "Papago Park and Camelback Mountain",
            "description": "Papago Buttes and Hole-in-the-Rock in Papago Park, with Camelback Mountain in the distance.",
            "alt": "Red sandstone buttes in Papago Park, with Camelback Mountain visible in the distance",
            "caption": "Papago Park, looking toward Camelback Mountain. Photo: Chris English, CC BY-SA 3.0, via Wikimedia Commons",
            "location": "Papago Park, Phoenix",
            "suggested_section": "gallery",
            "placements": ["gallery"],
            "event_slug": "papago-park",
            "event_alt": "Red sandstone buttes in Papago Park, with Camelback Mountain visible in the distance",
            "keywords": ["papago", "camelback"],
            "credit_line": "Photo: Chris English, CC BY-SA 3.0, via Wikimedia Commons",
        },
        {
            "id": "gammage-auditorium",
            "commons": "File:Gammage Auditorium, Arizona State University, Forest Avenue, Tempe, AZ - 54438015923.jpg",
            "title": "ASU Gammage Auditorium",
            "description": "Frank Lloyd Wright's Gammage Auditorium at Arizona State University in Tempe.",
            "alt": "The circular brick colonnade of ASU Gammage Auditorium in Tempe, designed by Frank Lloyd Wright",
            "caption": "ASU Gammage, Tempe. Photo: w_lemay, CC BY-SA 2.0, via Wikimedia Commons",
            "location": "Tempe, Arizona",
            "suggested_section": "events",
            "placements": ["event", "gallery"],
            "event_slug": "gammage",
            "event_alt": "The circular brick colonnade of ASU Gammage Auditorium in Tempe, designed by Frank Lloyd Wright",
            "event_crop": "center",
            "keywords": ["gammage", "wind symphony", "wind ensemble", "glory of the organ", "asu gammage"],
            "credit_line": "Photo: w_lemay, CC BY-SA 2.0, via Wikimedia Commons",
        },
        {
            "id": "phoenix-zoo",
            "commons": "File:Phoenix Zoo 20250525 - 84.jpg",
            "title": "Phoenix Zoo",
            "description": "A scene at the Phoenix Zoo.",
            "alt": "A view from the grounds of the Phoenix Zoo",
            "caption": "Phoenix Zoo. Photo: k7hpn, CC BY 2.0, via Wikimedia Commons",
            "location": "Papago Park, Phoenix",
            "suggested_section": "events",
            "placements": ["event"],
            "event_slug": "phoenix-zoo",
            "event_alt": "A view from the grounds of the Phoenix Zoo",
            "event_crop": "center",
            "keywords": ["zoolights", "zoo lights", "phoenix zoo"],
            "credit_line": "Photo: k7hpn, CC BY 2.0, via Wikimedia Commons",
        },
        {
            "id": "desert-botanical-garden",
            "commons": "File:Desert Botanical Garden Phoenix.jpg",
            "title": "Desert Botanical Garden",
            "description": "A view of the Desert Botanical Garden in Phoenix.",
            "alt": "Cacti and desert plants along a path at the Desert Botanical Garden in Phoenix",
            "caption": "Desert Botanical Garden. Photo: Slywire, CC BY-SA 4.0, via Wikimedia Commons",
            "location": "Papago Park, Phoenix",
            "suggested_section": "gallery",
            "placements": ["gallery"],
            "credit_line": "Photo: Slywire, CC BY-SA 4.0, via Wikimedia Commons",
        },
        {
            "id": "chase-field",
            "commons": "File:Chase Field (51809484371).jpg",
            "title": "Chase Field",
            "description": "Chase Field, home of the Arizona Diamondbacks, in downtown Phoenix.",
            "alt": "The exterior of Chase Field in downtown Phoenix, with the stadium name on the facade",
            "caption": "Chase Field. Photo: Gage Skidmore, CC BY-SA 2.0, via Wikimedia Commons",
            "location": "Downtown Phoenix",
            "suggested_section": "gallery",
            "placements": ["gallery"],
            "credit_line": "Photo: Gage Skidmore, CC BY-SA 2.0, via Wikimedia Commons",
        },
        {
            "id": "tempe-town-lake-rail",
            "commons": "File:Tempe Town Lake Light Rail.jpg",
            "title": "Valley Metro rail over Tempe Town Lake",
            "description": "A Valley Metro light rail train crossing Tempe Town Lake.",
            "alt": "A Valley Metro light rail train crossing the bridge over Tempe Town Lake",
            "caption": "Valley Metro rail at Tempe Town Lake. Photo: JoseE1471, CC BY-SA 4.0, via Wikimedia Commons",
            "location": "Tempe, Arizona",
            "suggested_section": "transit",
            "placements": ["transit", "gallery"],
            "credit_line": "Photo: JoseE1471, CC BY-SA 4.0, via Wikimedia Commons",
        },
        {
            "id": "heard-museum",
            "commons": "File:HeardMuseum May2013.jpg",
            "title": "Heard Museum",
            "description": "The Heard Museum in Phoenix.",
            "alt": "The adobe-style buildings and courtyard of the Heard Museum in Phoenix",
            "caption": "Heard Museum. Photo: Yassie, CC BY-SA 3.0, via Wikimedia Commons",
            "location": "Phoenix",
            "suggested_section": "gallery",
            "placements": ["gallery"],
            "credit_line": "Photo: Yassie, CC BY-SA 3.0, via Wikimedia Commons",
        },
        {
            "id": "hole-in-the-rock",
            "commons": "File:Phoenix-Hole-in-the-Rock-Papago Park.JPG",
            "title": "Hole-in-the-Rock, Papago Park",
            "description": "Hole-in-the-Rock, a sandstone formation in Papago Park.",
            "alt": "The sandstone Hole-in-the-Rock formation in Papago Park, Phoenix",
            "caption": "Hole-in-the-Rock, Papago Park. Photo: Tony the Marine, CC BY-SA 3.0, via Wikimedia Commons",
            "location": "Papago Park, Phoenix",
            "suggested_section": "gallery",
            "placements": ["gallery"],
            "credit_line": "Photo: Tony the Marine, CC BY-SA 3.0, via Wikimedia Commons",
        },
    ],
}


def main() -> None:
    cities = sys.argv[1:] or ["detroit", "phoenix"]
    STAGING.mkdir(parents=True, exist_ok=True)
    for city in cities:
        photos = PHOTOS[city]
        entries = []
        for photo in photos:
            info = commons_info(photo["commons"])
            dest = STAGING / f"{city}-{photo['id']}"
            print(f"download {info['title']} ({info['license']}) {info['width']}x{info['height']}")
            download(info["url"], dest)
            entries.append(process(city, photo, info))
        media_dir = ROOT / city / "media"
        media_dir.mkdir(parents=True, exist_ok=True)
        for p in (media_dir / "originals").glob("*.jpg"):
            verify_clean(p)
        for p in (media_dir / "web").glob("*"):
            if p.suffix.lower() in {".jpg", ".jpeg", ".webp"}:
                verify_clean(p)
        payload = {
            "credit": "Photos: Wikimedia Commons contributors, used under the license on each caption",
            "media_root": f"{city}/media/",
            "source": "Wikimedia Commons. Attribution and license appear on each photo.",
            "photos": entries,
        }
        (media_dir / "media.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        (media_dir / "README.md").write_text(
            f"# {city.title()} media\n\n"
            "Licensed stills from Wikimedia Commons. EXIF stripped. "
            "Do not replace these with unlicensed photos. "
            "Each record in media.json has the Commons title, license and photographer credit.\n",
            encoding="utf-8",
        )
        print(f"wrote {media_dir / 'media.json'} ({len(entries)} photos)")


if __name__ == "__main__":
    main()
