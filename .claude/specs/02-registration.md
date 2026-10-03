# Spec: Registration

## Overview
Turn the existing `/register` page from a static form into a working sign-up flow. A visitor submits name, email and password; the server validates the input, hashes the password with werkzeug, stores a new row in `users`, and redirects to the login page. This is the first user-facing feature built on the Step 1 data layer and is the prerequisite for login/logout (Step 3) and every logged-in page after it.

## Depends on
- Step 1 — Database setup (`get_db()`, `init_db()`, `users` table with a UNIQUE `email` column).

## Routes
- `GET /register` — render the registration form (already exists) — public
- `POST /register` — validate the form, create the user, redirect to `/login` on success; re-render the form with an error message on failure — public

The existing `register` view is extended to accept both methods; no other routes change.

## Database changes
No database changes. The `users` table in `database/db.py` already has `name`, `email` (UNIQUE), `password_hash` and `created_at`.

## Templates
- **Create:** none
- **Modify:**
  - `templates/register.html` — change the form `action` to `{{ url_for('register') }}`; re-populate `name` and `email` (never the password) after a failed submit; add `minlength="8"` to the password input. The existing `{% if error %}` block is reused to show errors.
  - `templates/login.html` — optionally show a success notice (e.g. "Account created. Please sign in.") when redirected from registration, using a `?registered=1` query parameter or equivalent.

## Files to change
- `app.py` — accept `POST` on `/register`; add form handling, validation, insert, and redirect; import `request`, `redirect`, `url_for`, `generate_password_hash`, and `sqlite3`.
- `templates/register.html`
- `templates/login.html` (success notice only)
- `static/css/style.css` — only if a success-notice style is added; reuse existing variables.

## Files to create
- `tests/test_registration.py` — pytest tests for the registration flow (uses `pytest-flask`, already in `requirements.txt`).

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never build SQL with string formatting
- Passwords hashed with werkzeug (`generate_password_hash`); never store or log the plain password
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `get_db()` from `database/db.py`; close the connection in a `finally` block
- Validation, performed server-side:
  - `name`, `email`, `password` are all present after `.strip()` (password is not stripped)
  - email contains an `@` and a domain part; normalise to lowercase and strip whitespace before storing
  - password is at least 8 characters (matches the form placeholder)
- Duplicate emails: rely on the UNIQUE constraint — catch `sqlite3.IntegrityError` and show "An account with that email already exists." Do not do a separate SELECT-then-INSERT check as the only guard.
- Error responses re-render `register.html` with the `error` variable and HTTP 400 (or 200); never reveal stack traces.
- Do not log the user in on registration (sessions are Step 3); redirect to `/login`.
- Keep the placeholder route names and "Step N" labels for the other routes untouched.

## Definition of done
- [ ] `python app.py` starts without errors and `GET /register` renders the form
- [ ] Submitting valid name, email and password creates a row in `users` and redirects to `/login`
- [ ] The stored `password_hash` is a werkzeug hash, not the plain password (check with `sqlite3 spendly.db "select password_hash from users order by id desc limit 1"`)
- [ ] Registering the same email again (including different letter case) shows "An account with that email already exists." and creates no second row
- [ ] Submitting a password shorter than 8 characters shows an error and creates no row
- [ ] Submitting with a blank name or an invalid email shows an error and creates no row
- [ ] After a failed submit the name and email fields keep their values; the password field is empty
- [ ] The login page shows a confirmation notice after a successful registration
- [ ] `pytest` passes, including tests for success, duplicate email, short password and missing fields
