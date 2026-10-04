# Spec: Login and Logout

## Overview
Make the existing `/login` page functional and replace the `/logout` placeholder. A registered user submits email and password; the server verifies the password against the stored werkzeug hash, stores the user's id in the Flask `session`, and redirects to the profile page. Logout clears the session and returns to the landing page. This step introduces sessions, the foundation for every logged-in page (profile, expenses) in later steps, and makes the navbar reflect auth state.

## Depends on
- Step 1 — Database setup (`get_db()`, `users` table, seeded demo user `demo@spendly.com` / `demo123`).
- Step 2 — Registration (users exist with hashed passwords; `/login?registered=1` notice already exists).

## Routes
- `GET /login` — render the sign-in form (exists); redirect to `/profile` if already logged in — public
- `POST /login` — validate credentials, set `session["user_id"]`, redirect to `/profile` on success; re-render the form with an error and HTTP 400 on failure — public
- `GET /logout` — clear the session and redirect to `/` (replaces the "Step 3" placeholder; keep the route name `logout`) — logged-in (harmless if called while logged out)

No other routes change. `/profile` stays the "Step 4" placeholder string; it is only the redirect target.

## Database changes
No database changes. The `users` table already has `email` (UNIQUE) and `password_hash`.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — change the form `action` to `{{ url_for('login') }}`; re-populate `email` (never the password) after a failed submit.
  - `templates/base.html` — navbar: when `session.user_id` is set show a "Sign out" link to `url_for('logout')` instead of "Sign in" / "Get started"; otherwise keep the current links.

## Files to change
- `app.py` — import `session` and `check_password_hash`; set `app.secret_key`; add `POST` handling to `login`; implement `logout`.
- `templates/login.html`
- `templates/base.html`

## Files to create
- `tests/test_login_logout.py` — pytest tests for the login/logout flow (uses `pytest-flask` and the existing `tests/conftest.py`).

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only — never build SQL with string formatting
- Passwords hashed with werkzeug; verify with `check_password_hash`, never compare plain text, never log passwords
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `get_db()` from `database/db.py`; close the connection in a `finally` block
- Session secret: read `app.secret_key` from the `SECRET_KEY` environment variable with a clearly-labelled dev-only fallback; do not hardcode a production secret
- Normalise the submitted email with `.strip().lower()` before lookup (matches registration)
- Use one generic error for both unknown email and wrong password ("Invalid email or password.") so account existence is not revealed
- Blank email or password shows "Email and password are required." with HTTP 400
- Store only `user_id` in the session; call `session.clear()` before setting it on login to avoid session fixation
- Logout must use `session.clear()`
- Do not add login-required protection to other routes here; that belongs to the steps that implement them
- Keep the placeholder route names and "Step N" labels for the other routes untouched

## Definition of done
- [ ] `python app.py` starts without errors and `GET /login` renders the form
- [ ] Logging in as `demo@spendly.com` / `demo123` redirects to `/profile`
- [ ] A newly registered user can log in with the credentials they registered with
- [ ] Email matching is case-insensitive and ignores surrounding whitespace
- [ ] A wrong password and an unknown email both show "Invalid email or password." with status 400
- [ ] Submitting blank fields shows an error and does not create a session
- [ ] After a failed submit the email field keeps its value; the password field is empty
- [ ] After login the navbar shows "Sign out" and hides "Sign in" / "Get started"
- [ ] Visiting `/logout` clears the session, redirects to `/`, and the navbar shows "Sign in" again
- [ ] Visiting `/login` while logged in redirects to `/profile`
- [ ] The registration success notice on `/login?registered=1` still appears
- [ ] `pytest` passes, including tests for successful login, wrong password, unknown email, missing fields, and logout clearing the session
