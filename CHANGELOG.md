# Changelog

All notable changes to this project are documented here, newest first. Dates are when the change was made, not a formal release.

## [Unreleased]

### Added
- `/search` — free-text search plus dropdowns to search by a specific known name or place. Backs the previously-dead "Search:" forms on the home and day-in-history pages.
- Entries now render their names/places as deduped pill links (with a `(2)`-style count when mentioned more than once) instead of a raw Python list; clicking one searches for it.
- `/status`: a "X of Y entries analyzed" summary above the table, per-row checkboxes with a live "N entries selected" count, a "Select Unanalyzed" helper, and a client-side date-range filter (no page reload) replacing the old start/end-month dropdowns. "Analyze Selected" now POSTs just the checked entry IDs to `/analyze`.

### Changed
- `main.js`/`main.css` split: page-specific behavior and styles (`analyze`, `classify`, `status`) moved into their own files, loaded only by the templates that use them. Only what's shared by 2+ pages stays in `main.js`/`main.css`.
- Status page table styling cleaned up (padding, `border-collapse`, centered numeric columns, row hover) — it was using unstyled browser table defaults.
- Chart report pages (`/words`, `/ngrams`, `/sentiment`, `/distribution_sentiment`, `/places`, `/names`) now pick their date range with two native month pickers instead of four separate month/year dropdowns.
- `/monthly_sentiment` now takes a single year (a dropdown, since it aggregates every entry into 12 calendar-month buckets regardless of range) instead of the same start/end range picker as the other sentiment views.
- Sentiment chart pages now show a heading and short description of what each view means, plus the same "-1 to +1, 0 is neutral" tooltip already used on individual entries.

## 2026-09-29 — Upload-based import, no more static export file

### Changed
- `/import` is now an upload form instead of requiring a file placed at `app/static/diary-downloaded.json` — pick your export and it's parsed and imported directly from the upload, nothing written to disk. That path is gone from the code, docs, and `.gitignore`.

### Added
- Uploads via `/import` are capped at 20MB (`MAX_CONTENT_LENGTH`).

## 2026-09-29 — Nav redesign, welcome page, import hardening, dev server fixes

### Added
- Responsive nav: the 9 flat links are grouped into a "Charts" dropdown (down to 4 top-level items), collapsing to a hamburger menu below 700px; added the missing viewport meta tag and made `.entry` and the places/status tables fluid instead of overflowing on narrow screens.
- `welcome.html` — a real setup-instructions page for a fresh install with zero entries, instead of an empty search/list view. `/import` added directly to the nav (previously only reachable by typing the URL).
- `make run` now passes `--debug`, so the dev server auto-reloads on file changes.

### Fixed
- `/import` failed with a raw traceback on a missing file, invalid JSON, or JSON in the wrong shape, instead of a friendly, logged error with a way to try again.
- Dev server defaulted to port 5000, which macOS's AirPlay Receiver silently intercepts on `localhost` (403, nothing in Flask's log, request never arrives) — default moved to 8571.

## 2026-09-29 — Empty-database crashes, /names chart, Makefile

### Fixed
- `SentimentBucketPresenter.bucket_info()` raised `KeyError` on an empty database (all buckets zero) — the leading/trailing-empty-bucket trim deleted keys from the dict while a second pass still iterated the original key list.
- `/names` crashed on render (`dict_values` isn't JSON-serializable) and, even fixed, never actually drew a usable chart — rebuilt it to render one correctly colored, legended line per name (capped to the top 15 by mention count) instead of dumping raw bucket dicts into the chart payload. Also stopped it from mutating pyChart.JS's shared `data`/`options` classes, which every chart type inherits — the old one-liner already did this on a smaller scale, and the naive per-name fix would have leaked accumulating dataset attributes across every future request.
- `/`, `/day_in_history`, and every `DEFAULT_ALL`-range route (`/names`, `/places`, `/status`, `/distribution_sentiment`, etc.) crashed with `AttributeError` on an empty database — several places assumed `JournalEntry.query...first()` always returns a row.
- `day_in_history()` referenced a `year` variable that was never assigned in that function (`NameError`, independent of the empty-database bug).

### Added
- `Makefile` with shortcuts for setup, local Postgres management, migrations, running the server, and testing (`make help` for the full list).

## 2026-09-29 — Local data, photo scanning, entry status, test restructure

### Added
- Project owns its own Postgres cluster under `data/postgres/` (`bin/db.sh`) instead of relying on a system-wide install.
- `/import_photos` scans `data/photos/`, matches images to entries by EXIF/filename date, and links them via a new `JournalPhoto` model — idempotent re-scans.
- `/status` — per-entry analysis dashboard (word/sentence counts, names, places, photos) with actions to analyze only unanalyzed entries, re-analyze everything, or trigger a photo scan.
- `tests/` package with `conftest.py` (isolated `journal_python_test` database, auto-created if missing) and `tests/factories.py` for building fake records in tests.

### Changed
- Test suite and its factories moved out of `app/` into a top-level `tests/` package — test-only code doesn't belong in the shipped application package.

## 2026-09-29 — Dependency upgrade, spaCy NER, places timeline, daily score, photo schema

### Added
- Names and places extracted via spaCy NER (`entry.names`, `entry.locations`), replacing the NLTK POS-tag heuristic that mistook any sentence-initial capitalized word for a name.
- `/places` — clusters location mentions into date ranges (gap-tolerant, default 14 days) to give a rough sense of when you were where.
- Nullable `daily_score` (1–5) field on journal entries.
- `JournalPhoto` schema + `app/static/photos/` storage convention (schema only at this point — scanning came later, see above).
- venv-based dev setup; `config.py` now centralizes app configuration instead of it being built inline in `app/__init__.py`.

### Changed
- All dependencies upgraded for Python 3.11 (Flask 3, SQLAlchemy 2, Flask-SQLAlchemy 3, Flask-Migrate 4, nltk 3.9, spaCy 3.8, etc.).

### Fixed
- `.flaskenv` pointed `FLASK_APP` at a `journalformatter.py` that didn't exist in the repo; now points at the real `app` package.
