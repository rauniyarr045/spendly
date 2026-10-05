# Spec: Add Expense

## Overview
Steps 5 and 6 made `/profile` show and filter a user's real expenses, but the only way to get expenses into the database is still `seed_db()`. This step lets a logged-in user record a new expense: amount, category, date and an optional description. It fills in the `/expenses/add` placeholder with a form that validates input on the server, inserts one row into the existing `expenses` table for the session user, and then redirects to `/profile`. The new expense then shows up in the stats, the category breakdown and the transactions list. This is the first write to `expenses` and the base for edit (Step 8) and delete (Step 9).

## Depends on
- Step 1: Database setup (`expenses` table, `get_db()`, `CATEGORIES`)
- Step 3: Login + Logout (`session["user_id"]`)
- Step 5: Profile page connected to the database (to verify the new expense appears)
- Step 6: Date filter for profile page (`_parse_date` helper in `app.py`)

## Routes
- `GET /expenses/add` — render the add-expense form, with the date defaulting to today — logged-in
- `POST /expenses/add` — validate the form, insert the expense for the session user, redirect to `/profile` — logged-in

Both reuse the existing `add_expense` view function and `/expenses/add` path, which becomes `methods=["GET", "POST"]`. A logged-out user on either method is redirected to `/login`.

## Database changes
No database changes. The existing `expenses` table (`id`, `user_id`, `amount REAL`, `category TEXT`, `date TEXT YYYY-MM-DD`, `description TEXT NULL`, `created_at`) already covers this step. Verified against `database/db.py`.

Add one write helper to `database/db.py`:
- `create_expense(user_id, amount, category, date, description=None)` — runs one parameterised `INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)`, commits, and returns the new row id. Uses the `get_db()` / `try` / `finally: conn.close()` pattern.

## Templates
- **Create:** `templates/add_expense.html`
  - Extends `base.html`; title block "Add expense".
  - `<form method="POST" action="{{ url_for('add_expense') }}">` with:
    - Amount: `<input type="number" name="amount" step="0.01" min="0.01" required>`
    - Category: `<select name="category">` with one `<option>` per entry in `CATEGORIES` (passed from the view, not hardcoded)
    - Date: `<input type="date" name="date" required>`, defaulting to today
    - Description: `<input type="text" name="description" maxlength="200">`, optional
  - A submit button "Add expense" and a "Cancel" link to `url_for('profile')`.
  - Shows a validation error in the existing `auth-error` style.
  - Reuses the existing `form-group` / `form-input` classes.
  - After a failed submit, refills every field with what the user typed and keeps the chosen category selected.
- **Modify:** `templates/profile.html` — add an "Add expense" link/button (`url_for('add_expense')`) in the profile header or above the transactions card.

## Files to change
- `app.py`
  - Implement `add_expense()`. GET renders the form with `today`; POST validates, calls `create_expense`, then redirects to `url_for('profile')`.
  - Import `CATEGORIES` and `create_expense`.
  - Reuse `_parse_date` for the date.
- `database/db.py` — add `create_expense`.
- `templates/profile.html` — "Add expense" link.
- `static/css/profile.css` — style for the new link, only if existing button classes are not enough.

## Files to create
- `templates/add_expense.html`
- `tests/test_add_expense.py`
- `static/css/expense_form.css`, only if the form needs page-specific styles. If created, load it through the `head` block.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs. Use raw sqlite3 via `get_db()`.
- Parameterised queries only. Never format user input into SQL.
- Passwords hashed with werkzeug (no auth changes in this step)
- Use CSS variables. Never hardcode hex values.
- All templates extend `base.html`
- No inline styles
- `user_id` always comes from `session["user_id"]`, never from the form or URL
- Server-side validation is authoritative, whatever the HTML attributes say:
  - `amount`: required, parsed with `float()`, must be finite (reject `nan` and `inf`) and greater than 0; round to 2 decimal places before storing
  - `category`: required, must be exactly one of `CATEGORIES`
  - `date`: required, validated with the existing `_parse_date` (`YYYY-MM-DD`); empty or malformed is an error
  - `description`: optional, stripped, at most 200 characters; an empty string is stored as `NULL`
- On a validation error, re-render `add_expense.html` with an error message and the submitted values, returning HTTP 400. Never return a 500.
- On success, redirect (Post/Redirect/Get) to `/profile` so a refresh does not resubmit.
- Do not modify the Step 8 (`/expenses/<id>/edit`) and Step 9 (`/expenses/<id>/delete`) placeholders
- Do not change the context variable names used by `profile.html`

## Definition of done
- [ ] `GET /expenses/add` while logged out redirects to `/login`; `POST` while logged out redirects to `/login` and inserts nothing
- [ ] `GET /expenses/add` while logged in shows the form with amount, a category dropdown listing every entry in `CATEGORIES`, a date defaulting to today, and a description
- [ ] `/profile` has an "Add expense" link that opens the form
- [ ] A valid submission inserts exactly one row for the logged-in user and redirects to `/profile`
- [ ] The new expense appears in recent transactions, and total spent, transaction count and the category breakdown update
- [ ] Submitting with an empty description stores `NULL` and the expense still displays correctly
- [ ] Amount of `0`, a negative number, `abc`, `nan` or empty each shows an error with status 400 and inserts nothing
- [ ] A category not in `CATEGORIES` (for example a tampered `<select>`) shows an error and inserts nothing
- [ ] An empty or malformed date (e.g. `2026-13-40`) shows an error and inserts nothing
- [ ] A description longer than 200 characters shows an error and inserts nothing
- [ ] After any validation error, the form keeps the values that were entered
- [ ] The expense is always saved to the session user: a `user_id` field added to the form is ignored, and other users' totals are unchanged
- [ ] Refreshing `/profile` after adding does not create a duplicate
- [ ] `pytest` passes, including new tests in `tests/test_add_expense.py` for: auth redirect, successful insert plus redirect, each validation error, `NULL` description, and per-user isolation
