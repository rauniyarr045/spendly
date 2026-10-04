# Spec: Connect Profile Page Tables To Database

## Overview
Step 4 built the `/profile` page UI with hardcoded sample data. This step replaces that hardcoded data with real queries against the `users` and `expenses` tables, so each logged-in user sees their own account details, summary stats, category breakdown and recent transactions. The template contract from Step 4 (`user`, `stats`, `transactions`, `categories`) stays the same, so `profile.html` should need little or no change.

## Depends on
- Step 1: Database setup (`users` and `expenses` tables, `get_db()`, `seed_db()`)
- Step 2: Registration (users can be created)
- Step 3: Login + Logout (`session["user_id"]` is set)
- Step 4: Profile page design (`templates/profile.html`, `static/css/profile.css`)

## Routes
No new routes. The existing `GET /profile` (logged-in only, redirects to `/login` otherwise) changes from hardcoded data to DB-backed data.

## Database changes
No database changes. The existing `users` (`id`, `name`, `email`, `password_hash`, `created_at`) and `expenses` (`id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`) tables are sufficient. Verified against `database/db.py`.

New query helper functions are added to `database/db.py` (see Files to change).

## Templates
- **Create:** none
- **Modify:** `templates/profile.html` — only if needed to match the real data (e.g. empty-state handling for a user with no expenses: the category breakdown section should show an empty message instead of an empty list). Context variable names must not change.

## Files to change
- `database/db.py` — add read-only helpers, each taking `user_id` and using parameterised queries via `get_db()`:
  - `get_user_by_id(user_id)` — returns `name`, `email`, `created_at` or `None`
  - `get_summary_stats(user_id)` — total spent, transaction count, top category (highest total; `None` if no expenses)
  - `get_recent_transactions(user_id, limit=10)` — rows ordered by `date DESC, id DESC`
  - `get_category_breakdown(user_id)` — per-category totals ordered by amount DESC, each with an integer `percent` of total spent
- `app.py` — in `profile()`, keep the `session.get("user_id")` guard, then build `user`, `stats`, `transactions`, `categories` from the helpers and remove the hardcoded data. If the user id in the session no longer exists in the DB, clear the session and redirect to `/login`.
- `templates/profile.html` — only the empty-state tweak described above, if needed.
- `tests/test_profile.py` — update/add tests for the DB-backed behaviour.

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw sqlite3 via `get_db()`
- Parameterised queries only — never string-format SQL
- Passwords hashed with werkzeug (no changes to auth in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Every query must filter by the session's `user_id`; a user must never see another user's expenses
- Connections must be closed in a `finally` block, matching the existing pattern in `app.py` and `db.py`
- Compute totals and percentages in SQL/Python from stored data; do not hardcode any numbers
- Derive `initials` from the user's name (first letter of up to the first two words, uppercased) and `member_since` from `created_at` formatted as "Month YYYY"
- Keep the `₹` currency formatting already used in `profile.html`
- Handle a user with zero expenses: total 0.00, count 0, top category `None` (template shows "—"), empty transactions and categories without errors
- Do not modify other routes or the placeholder expense routes (Steps 7–9)

## Definition of done
- [ ] Visiting `/profile` logged out still redirects to `/login`
- [ ] Logging in as the seeded demo user (`demo@spendly.com` / `demo123`) shows name "Demo User", that email, and a real "Member since" month/year from `created_at`
- [ ] Total spent equals the sum of that user's expenses (seed data: 327.89 → `₹327.89`) and transaction count equals 8
- [ ] Top category shown matches the category with the highest total (Bills for seed data)
- [ ] The transactions table lists the user's expenses newest first, using real descriptions, categories and amounts from the DB
- [ ] The category breakdown lists each category with its real total, sorted highest first, with percentages that reflect each share of total spent
- [ ] A newly registered user with no expenses sees `₹0.00`, `0` transactions, "—" for top category and "No transactions yet." without a server error
- [ ] Two different users each see only their own data
- [ ] Adding an expense row directly in the DB for the logged-in user changes the numbers after a page refresh
- [ ] A session pointing at a deleted user redirects to `/login` instead of erroring
- [ ] No hardcoded sample data remains in the `profile()` view in `app.py`
- [ ] `pytest` passes
