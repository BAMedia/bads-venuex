# Urban Concierge photo library

John Leyes / Bay Area Media photos used on the Urban Concierge - Bay Area brief.

- `originals/` — full-resolution JPEGs, oriented correctly, with EXIF and GPS stripped
- `web/` — page assets (about 1600px long edge, WebP and JPEG, plus thumbnails and crops)
- `media.json` — filename, description, alt text, suggested section, and `placements` for each photo

`publish.py` reads `media.json` on every brief refresh, so placements stay on the live page after the 6 AM, 2 PM, and 10 PM runs.

## Add a photo

1. Stage the original (a folder of JPEGs is enough).
2. Add a record to `PHOTOS` in `tools/optimize_media.py` with a short description, alt text, `suggested_section`, and `placements`.
3. Run `python3 tools/optimize_media.py` (set `MEDIA_STAGING` if the files are not in `/tmp/john-sf-photos`).
4. Publish with `python3 publish.py --rebuild` (or wait for the next scheduled brief).

Useful `placements` values: `hero`, `gallery`, `eat`, `transit`, `stay`, `event`, `library`. Set `on_page` to `false` to keep a photo in the library without showing it. Use an honest caption if the photo is not in San Francisco.

Credit on the page: Photos: John Leyes / Bay Area Media
