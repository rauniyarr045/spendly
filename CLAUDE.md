# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

"Spendly" — a Flask + SQLite expense tracker (Jinja templates, plain CSS/JS, no frontend build step). It is a step-by-step teaching scaffold: much of the app is intentionally unimplemented.

## Commands

```
pip install -r requirements.txt   # flask, werkzeug, pytest, pytest-flask
python app.py                     # dev server, debug mode, http://localhost:5001
pytest                            # run tests (none exist yet)
pytest path/to/test_file.py::test_name   # single test
```

No linter or build config exists.

## Architecture

- `app.py` — single Flask app holding all routes. Implemented: `/`, `/register`, `/login`, `/terms`, `/privacy` (render templates only; no form handling yet). The remaining routes (`/logout`, `/profile`, `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`) are placeholders returning strings, labelled with the tutorial "Step N" that implements them. Keep those step numbers/route names when filling them in.
- `database/db.py` — currently only a comment stub specifying the intended API: `get_db()` (SQLite connection with `row_factory` and foreign keys enabled), `init_db()` (`CREATE TABLE IF NOT EXISTS`), `seed_db()` (dev sample data). Nothing imports it yet.
- `templates/` — all pages extend `base.html` (navbar, footer, blocks: `title`, `head`, `content`, `scripts`). Use `url_for(...)` for links; note the footer in `base.html` hardcodes `/terms` and `/privacy`.
- `static/css/style.css` is loaded globally by `base.html`; `static/css/landing.css` is page-specific for the landing page (load via the `head` block). `static/js/main.js` is loaded on every page.
