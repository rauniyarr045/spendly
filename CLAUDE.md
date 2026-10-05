# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

"Spendly" — a Flask + SQLite expense tracker (Jinja templates, plain CSS/JS, no frontend build step). It is a step-by-step teaching scaffold: much of the app is intentionally unimplemented.

## Commands

```
pip install -r requirements.txt   # flask, werkzeug, pytest, pytest-flask
python app.py                     # dev server, debug mode, http://localhost:5001
pytest                            # run all tests
pytest path/to/test_file.py::test_name   # single test
```

No linter or build config exists.

## Workflow

One step = one spec + one feature branch. `/create-spec <N> <name>` writes `.claude/specs/NN-<slug>.md` and branches from `main`; implement, run `pytest`, then PR to `main`. Done: Steps 1–6 (database, registration, login/logout, profile design, profile from DB, profile date filter). Remaining Flask steps: 7 add expense, 8 edit expense, 9 delete expense. Steps 10+ migrate to AWS (SAM, Lambda, API Gateway, Cognito, DynamoDB, S3/CloudFront, PWA).

## Architecture

- `app.py` — single Flask app holding all routes. Implemented: `/`, `/register`, `/login`, `/logout`, `/profile` (session-guarded; optional `?from=&to=` date filter), `/terms`, `/privacy`. Auth is werkzeug password hashing + Flask `session["user_id"]`. `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete` are still placeholders labelled "Step 7/8/9" — keep those step numbers and route names when filling them in.
- `database/db.py` — raw sqlite3, no ORM. `get_db()` (row_factory + foreign keys; caller closes in `finally`), `init_db()`, `seed_db()` (demo user `demo@spendly.com` / `demo123` with 8 expenses), `CATEGORIES`, and per-user read helpers `get_user_by_id`, `get_summary_stats`, `get_recent_transactions`, `get_category_breakdown` (the last three take optional inclusive `date_from`/`date_to`, built by `_expense_filter`). Every expense query must filter by `user_id` and use `?` parameters.
- `tests/` — pytest + pytest-flask; `conftest.py` points `DB_PATH` at a temp DB per test.
- `templates/` — all pages extend `base.html` (navbar, footer, blocks: `title`, `head`, `content`, `scripts`). Use `url_for(...)` for links; note the footer in `base.html` hardcodes `/terms` and `/privacy`.
- `static/css/style.css` is loaded globally by `base.html` and defines the CSS variables (never hardcode hex values in templates or page CSS); `landing.css` and `profile.css` are page-specific (load via the `head` block). `static/js/main.js` is loaded on every page.
