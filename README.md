# bamedia.agency: Bay Area Media (BAMedia)

Static site served by GitHub Pages from `main` at `/` (custom domain in `CNAME`).

| Path | What | Built by |
|---|---|---|
| `/` (`index.html`, `assets/brand.css`) | Bay Area Media company homepage linking to its brands | hand-edited |
| `/law/` (`law/index.html`) | Law-Firm Client Concierge | hand-edited |
| `/bads/` (`bads/`) | Urban Concierge - Bay Area briefs, archive, RSS, PWA | `publish.py` |
| `/detroit/` (`detroit/`) | Urban Concierge - Detroit | `publish.py --city detroit` |
| `/phoenix/` (`phoenix/`) | Urban Concierge - Greater Phoenix | `publish.py --city phoenix` |
| `/archive/*.html`, `/offline.html`, `/feed.xml`, `/sw.js` | legacy (BADS used to live at the root): redirect stubs, feed copy, retired service worker | `publish.py` / static |

Brand images: `python3 tools/make_brand_images.py`.

## BADS publishing

    python3 publish.py /path/to/bayareadailysync-YYYY-MM-DD-HHMM.md
    python3 publish.py --city detroit /path/to/detroitdailysync-YYYY-MM-DD-HHMM.md
    python3 publish.py --city phoenix /path/to/phoenixdailysync-YYYY-MM-DD-HHMM.md

Bay Area: copies the source to `briefs/` (repo root), renders `bads/archive/<name>.html`, updates `bads/index.html`,
`bads/archive/index.html`, `bads/feed.xml` (+ copy at `/feed.xml`), the legacy redirect stubs, then commits
and pushes to main. `site.json`: `site_url` = `https://bamedia.agency/bads/`, `out_dir` = `bads`.
Detroit and Phoenix use `briefs/detroit/` and `briefs/phoenix/`, and publish to `/detroit/` and `/phoenix/`.
City settings live in `cities.json`. Do not run a Bay Area `--rebuild` against another city's briefs.
`python3 publish.py --rebuild` re-renders the selected city (default Bay Area). Requires `python-markdown`.

- `bads/manifest.webmanifest`, `bads/sw.js`, `bads/assets/app.js`: installable app scoped to `/bads/`. Network-first
  for pages, cached shell for offline.
- Email signup: set `signup.form_action` in `site.json`, then `python3 publish.py --rebuild`.
Built from public sources. Snapshot, not real-time; check official links before you go.
