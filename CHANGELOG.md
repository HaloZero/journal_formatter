# Changelog

All notable changes to this project are documented here, newest first. Dates are when the change was made, not a formal release.

## [Unreleased]

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
