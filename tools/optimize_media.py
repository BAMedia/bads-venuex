#!/usr/bin/env python3
"""Build EXIF-stripped originals and web derivatives for bads/media/.

Reads the photo list below (or media.json sources) from a staging directory,
writes:
  bads/media/originals/<id>.jpg   full-resolution, oriented, no EXIF/GPS
  bads/media/web/<id>.{webp,jpg}  long edge 1600px, ~200-400KB
  bads/media/web/<id>-thumb.{webp,jpg}
  optional hero and 16:9 event-card crops
  bads/assets/events/<slug>.webp  when an event_slug is set

Safe to re-run; it overwrites derivatives only.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "bads" / "media"
ORIGINALS = MEDIA / "originals"
WEB = MEDIA / "web"
EVENTS = ROOT / "bads" / "assets" / "events"
STAGING = Path(os.environ.get("MEDIA_STAGING", "/tmp/john-sf-photos"))

# Source files in the staging dir (already given friendly names).
PHOTOS = [
    {
        "id": "red-sculpture-rincon",
        "source": "red-sculpture-rincon.jpg",
        "source_hash": "4f93ee74967ec8f093328e5b77f19c927108866e8fe5ef219699f82e66ec5650.jpg",
        "title": "Red sculpture and the SoMa skyline",
        "description": "A red sculpture on a lawn with the SoMa and Rincon skyline behind it.",
        "alt": "A red steel sculpture on a green lawn, with palm trees and the San Francisco SoMa skyline beyond",
        "caption": "South Beach, looking toward the SoMa skyline",
        "location": "South Beach / Rincon, San Francisco",
        "suggested_section": "hero",
        "placements": ["hero"],
        "on_page": True,
        "hero_crop": "upper-2x1",
    },
    {
        "id": "rincon-park-cupids-span",
        "source": "rincon-park-cupids-span.jpg",
        "source_hash": "6d2e006b6f931def97c2b4a0aba42b2cda47f136ebef23cd6792487aac4a433a.jpg",
        "title": "Cupid's Span at Rincon Park",
        "description": "The Cupid's Span bow-and-arrow sculpture in Rincon Park, with the Embarcadero skyline.",
        "alt": "The Cupid's Span bow-and-arrow sculpture in Rincon Park along the Embarcadero, with San Francisco office towers behind it",
        "caption": "Cupid's Span, Rincon Park",
        "location": "Rincon Park, Embarcadero, San Francisco",
        "suggested_section": "transit",
        "placements": ["transit", "gallery"],
        "on_page": True,
    },
    {
        "id": "oracle-park-mccovey-statue",
        "source": "oracle-park-mccovey-statue.jpg",
        "source_hash": "9c014bc19e47bac1c57ef025a6becaf9a3a0af5469ce0c9ecbcca0753fdc1ddc.jpg",
        "title": "Oracle Park and the Willie McCovey statue",
        "description": "Oracle Park across McCovey Cove, with boats on the water and the Willie McCovey statue in the foreground.",
        "alt": "The Willie McCovey statue in the foreground, with boats in McCovey Cove and Oracle Park beyond",
        "caption": "Oracle Park from McCovey Cove",
        "location": "McCovey Cove, San Francisco",
        "suggested_section": "sports",
        "placements": ["gallery", "event"],
        "on_page": True,
        "event_slug": "oracle-park",
        "event_alt": "Oracle Park across McCovey Cove, with the Willie McCovey statue in the foreground",
        "event_crop": "upper-16x9",
    },
    {
        "id": "oracle-park-marina-gate",
        "source": "oracle-park-marina-gate.jpg",
        "source_hash": "ab224d200f5e07966b7c54880d6ff7a67f90600b914aed1f746e5d5d1b54ae23.jpg",
        "title": "Oracle Park Marina Gate",
        "description": "The Marina Gate at Oracle Park, with palm trees and the Bay Bridge in the distance.",
        "alt": "Oracle Park's Marina Gate under a row of palm trees, with the Bay Bridge in the distance",
        "caption": "Oracle Park, Marina Gate",
        "location": "Oracle Park, San Francisco",
        "suggested_section": "sports",
        "placements": ["gallery"],
        "on_page": True,
    },
    {
        "id": "oracle-park-mccovey-cove",
        "source": "oracle-park-mccovey-cove.jpg",
        "source_hash": "4bca1b596766f953efbca37ea726aca4e610daadcc433963333ae3021188cbd2.jpg",
        "title": "Oracle Park across McCovey Cove",
        "description": "Oracle Park seen across McCovey Cove from the shoreline path.",
        "alt": "Oracle Park across McCovey Cove, seen from the shoreline path with people walking by the water",
        "caption": "Oracle Park across McCovey Cove",
        "location": "McCovey Cove, San Francisco",
        "suggested_section": "sports",
        "placements": ["gallery"],
        "on_page": True,
    },
    {
        "id": "financial-district-dusk",
        "source": "financial-district-dusk.jpg",
        "source_hash": "edfa6046dd399428a026ef099b697054dd16ec8e136c57e3a659b3dcbd0ad1a9.jpg",
        "title": "Financial District at dusk",
        "description": "Financial District towers at dusk, including a US Bank sign and a Chime sign.",
        "alt": "Financial District towers at dusk, with a US Bank building and a Chime sign lit against a deep blue sky",
        "caption": "The Financial District at dusk",
        "location": "Financial District, San Francisco",
        "suggested_section": "stay",
        "placements": ["stay"],
        "on_page": True,
        "orientation": "portrait",
    },
    {
        "id": "columbus-tower",
        "source": "columbus-tower.jpg",
        "source_hash": "3ccc947364c9b01a08d766db0cd9ff55347e82b50e964e03274d940899ce594f.jpg",
        "title": "Columbus Tower and Cafe Zoetrope",
        "description": "Columbus Tower (the Sentinel Building) in North Beach, with Cafe Zoetrope at street level.",
        "alt": "The green copper Columbus Tower in North Beach, with Cafe Zoetrope's red awning at the corner",
        "caption": "Columbus Tower, North Beach",
        "location": "North Beach, San Francisco",
        "suggested_section": "eat",
        "placements": ["eat"],
        "on_page": True,
        "orientation": "portrait",
    },
    {
        "id": "grace-cathedral",
        "source": "grace-cathedral.jpg",
        "source_hash": "3a2641905fa3cc43000b702439e7ff024e1265d517042029485e87f6e0bf7c37.jpg",
        "title": "Grace Cathedral",
        "description": "The front steps and facade of Grace Cathedral on Nob Hill.",
        "alt": "The front steps and Gothic facade of Grace Cathedral on Nob Hill, under a clear blue sky",
        "caption": "Grace Cathedral, Nob Hill",
        "location": "Nob Hill, San Francisco",
        "suggested_section": "events",
        "placements": ["gallery", "event"],
        "on_page": True,
        "orientation": "portrait",
        "event_slug": "grace-cathedral",
        "event_alt": "The front steps and facade of Grace Cathedral on Nob Hill",
        "event_crop": "upper-16x9",
        "note": "The original has a small date stamp in the lower right corner; left as shot.",
    },
    {
        "id": "ferry-building",
        "source": "ferry-building.jpg",
        "source_hash": "c0dcb6cc6b2311b74e0bf541cbcc990d9a91177dd6d7d5daa6902dbff1cc5fc0.jpg",
        "title": "Ferry Building from the Embarcadero",
        "description": "The Ferry Building clock tower on the Embarcadero, beside a public toilet kiosk.",
        "alt": "The Ferry Building clock tower on the Embarcadero, seen beside a metal public toilet kiosk and a palm tree",
        "caption": "The Ferry Building, Embarcadero",
        "location": "Embarcadero, San Francisco",
        "suggested_section": "transit",
        "placements": ["gallery"],
        "on_page": True,
        "orientation": "portrait",
    },
    {
        "id": "steam-navigation-sign-old-sacramento",
        "source": "steam-navigation-sign-old-sacramento.jpg",
        "source_hash": "f32c55ecf231c70b206094e3cd0d50d73457e3ce1dd40deccfc6968018f970c2.jpg",
        "title": "California Steam Navigation Co. sign",
        "description": "A sign reading “California Steam Navigation Co's Steamers for San Francisco,” photographed on the Old Sacramento waterfront, not in San Francisco.",
        "alt": "A white sign on the Old Sacramento waterfront reading California Steam Navigation Co's Steamers for San Francisco",
        "caption": "California Steam Navigation Co. sign, Old Sacramento waterfront",
        "location": "Old Sacramento (not San Francisco)",
        "suggested_section": "gallery",
        "placements": ["gallery"],
        "on_page": True,
        "orientation": "portrait",
        "note": "This photo is from Old Sacramento, not San Francisco. Caption says so on the page.",
    },
    {
        "id": "collage-sf-scenes",
        "source": "collage-sf-scenes.jpg",
        "source_hash": "9914053011489598f103813c7da42c337fb66ed0a6d55af5faaf78c4c7df0069.jpg",
        "title": "San Francisco scenes, collage",
        "description": "A Google Photos collage of San Francisco scenes, kept in the library for later use.",
        "alt": "A Google Photos collage of San Francisco scenes, including Oracle Park, the Ferry Building, and Grace Cathedral",
        "caption": "San Francisco scenes",
        "location": "Various, mostly San Francisco",
        "suggested_section": "library",
        "placements": ["library"],
        "on_page": False,
        "note": "Google Photos collage with a visible Google Photos mark. Kept in the media library, not placed on the live page.",
    },
]

CREDIT = "Photos: John Leyes / Bay Area Media"


def exif_clean(im: Image.Image) -> Image.Image:
    im = ImageOps.exif_transpose(im) or im
    return im.convert("RGB")


def resize_long_edge(im: Image.Image, long_edge: int) -> Image.Image:
    w, h = im.size
    if max(w, h) <= long_edge:
        return im.copy()
    if w >= h:
        nw, nh = long_edge, round(h * long_edge / w)
    else:
        nh, nw = long_edge, round(w * long_edge / h)
    return im.resize((nw, nh), Image.Resampling.LANCZOS)


def crop_ratio(im: Image.Image, rw: int, rh: int, bias: str = "center") -> Image.Image:
    """Crop to rw:rh, keeping width. bias=upper keeps more of the top."""
    w, h = im.size
    target_h = round(w * rh / rw)
    if target_h <= h:
        if bias == "upper":
            top = max(0, min(round((h - target_h) * 0.22), h - target_h))
        else:
            top = max(0, (h - target_h) // 2)
        return im.crop((0, top, w, top + target_h))
    target_w = round(h * rw / rh)
    left = max(0, (w - target_w) // 2)
    return im.crop((left, 0, left + target_w, h))


def save_jpeg(im: Image.Image, path: Path, quality: int) -> None:
    im.save(path, "JPEG", quality=quality, optimize=True, progressive=True, subsampling=0 if quality >= 90 else 2)


def save_webp(im: Image.Image, path: Path, quality: int) -> None:
    im.save(path, "WEBP", quality=quality, method=6)


def fit_bytes(im: Image.Image, path: Path, fmt: str, lo: int, hi: int, min_q=62, max_q=86) -> int:
    """Binary-search quality so the file lands near lo-hi bytes. Returns quality used."""
    # Prefer the high side of the range; don't go below min_q.
    best_q, best_diff = max_q, None
    q = max_q
    # try a few qualities from high to low
    for trial in range(max_q, min_q - 1, -4):
        if fmt == "jpeg":
            save_jpeg(im, path, trial)
        else:
            save_webp(im, path, trial)
        size = path.stat().st_size
        if lo <= size <= hi:
            return trial
        if size > hi:
            continue
        # undersized: keep the closest under the max, then stop (higher q already too big or not tried as under)
        diff = abs(((lo + hi) / 2) - size)
        if best_diff is None or diff < best_diff:
            best_q, best_diff = trial, diff
            # if still reasonably large, good enough
            if size >= lo * 0.7:
                return trial
    # last write was min_q or last undersize; rewrite at best_q
    if fmt == "jpeg":
        save_jpeg(im, path, best_q)
    else:
        save_webp(im, path, best_q)
    return best_q


def process(photo: dict) -> dict:
    src = STAGING / photo["source"]
    if not src.exists():
        raise SystemExit(f"missing source: {src}")
    im = exif_clean(Image.open(src))
    ORIGINALS.mkdir(parents=True, exist_ok=True)
    WEB.mkdir(parents=True, exist_ok=True)
    EVENTS.mkdir(parents=True, exist_ok=True)

    orig_path = ORIGINALS / f"{photo['id']}.jpg"
    save_jpeg(im, orig_path, 90)
    # originals can be large; 90 is plenty and strips EXIF because we don't pass exif=

    web_im = resize_long_edge(im, 1600)
    web_jpg = WEB / f"{photo['id']}.jpg"
    web_webp = WEB / f"{photo['id']}.webp"
    jq = fit_bytes(web_im, web_jpg, "jpeg", 180_000, 420_000, min_q=68, max_q=88)
    wq = fit_bytes(web_im, web_webp, "webp", 140_000, 400_000, min_q=68, max_q=86)

    thumb_im = resize_long_edge(im, 800)
    thumb_jpg = WEB / f"{photo['id']}-thumb.jpg"
    thumb_webp = WEB / f"{photo['id']}-thumb.webp"
    fit_bytes(thumb_im, thumb_jpg, "jpeg", 40_000, 160_000, min_q=65, max_q=82)
    fit_bytes(thumb_im, thumb_webp, "webp", 30_000, 140_000, min_q=65, max_q=80)

    entry = {
        "id": photo["id"],
        "original": f"originals/{photo['id']}.jpg",
        "source_hash": photo["source_hash"],
        "title": photo["title"],
        "description": photo["description"],
        "alt": photo["alt"],
        "caption": photo.get("caption"),
        "location": photo.get("location"),
        "suggested_section": photo.get("suggested_section"),
        "placements": photo["placements"],
        "on_page": photo.get("on_page", True),
        "orientation": photo.get("orientation", "landscape"),
        "web": {
            "webp": f"web/{photo['id']}.webp",
            "jpeg": f"web/{photo['id']}.jpg",
            "width": web_im.size[0],
            "height": web_im.size[1],
        },
        "thumb": {
            "webp": f"web/{photo['id']}-thumb.webp",
            "jpeg": f"web/{photo['id']}-thumb.jpg",
            "width": thumb_im.size[0],
            "height": thumb_im.size[1],
        },
        "credit": CREDIT,
    }
    if photo.get("note"):
        entry["note"] = photo["note"]

    if "hero" in photo["placements"] or photo.get("hero_crop"):
        hero = crop_ratio(im, 2, 1, bias="upper")
        hero = resize_long_edge(hero, 1600)
        hero_jpg = WEB / f"{photo['id']}-hero.jpg"
        hero_webp = WEB / f"{photo['id']}-hero.webp"
        fit_bytes(hero, hero_jpg, "jpeg", 160_000, 400_000, min_q=68, max_q=86)
        fit_bytes(hero, hero_webp, "webp", 120_000, 380_000, min_q=68, max_q=84)
        entry["hero"] = {
            "webp": f"web/{photo['id']}-hero.webp",
            "jpeg": f"web/{photo['id']}-hero.jpg",
            "width": hero.size[0],
            "height": hero.size[1],
        }

    if photo.get("event_slug"):
        ev = crop_ratio(im, 16, 9, bias="upper")
        ev = ev.resize((960, 540), Image.Resampling.LANCZOS)
        ev_path = EVENTS / f"{photo['event_slug']}.webp"
        fit_bytes(ev, ev_path, "webp", 40_000, 120_000, min_q=65, max_q=80)
        ev_jpg = WEB / f"{photo['id']}-event.jpg"
        ev_webp = WEB / f"{photo['id']}-event.webp"
        ev.save(ev_webp, "WEBP", quality=78, method=6)
        save_jpeg(ev, ev_jpg, 80)
        entry["event"] = {
            "slug": photo["event_slug"],
            "alt": photo.get("event_alt") or photo["alt"],
            "webp": f"assets/events/{photo['event_slug']}.webp",
            "width": 960,
            "height": 540,
        }

    print(
        f"{photo['id']}: orig {im.size[0]}x{im.size[1]} {orig_path.stat().st_size//1024}KB | "
        f"web {web_im.size[0]}x{web_im.size[1]} jpg={web_jpg.stat().st_size//1024}KB@{jq} "
        f"webp={web_webp.stat().st_size//1024}KB@{wq}"
    )
    return entry


def verify_clean(path: Path) -> None:
    im = Image.open(path)
    ex = im.getexif()
    if ex and len(ex) > 0:
        raise SystemExit(f"EXIF still present on {path}: {dict(list(ex.items())[:6])}")


def main() -> None:
    entries = [process(p) for p in PHOTOS]
    for p in ORIGINALS.glob("*.jpg"):
        verify_clean(p)
    for p in WEB.glob("*"):
        verify_clean(p)
    manifest = {
        "credit": CREDIT,
        "media_root": "bads/media/",
        "how_to_add": (
            "Drop a new original into a staging folder, add a record to PHOTOS in "
            "tools/optimize_media.py (filename, description, suggested_section, "
            "placements, alt text), then run: python3 tools/optimize_media.py. "
            "publish.py reads media.json, so the next brief refresh will pick up "
            "new placements without editing the HTML by hand."
        ),
        "photos": entries,
    }
    out = MEDIA / "media.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("wrote", out, "photos:", len(entries))


if __name__ == "__main__":
    main()
