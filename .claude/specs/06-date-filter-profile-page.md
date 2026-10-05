# Spec: Date Filter For Profile Page

## Overview
Step 5 made `/profile` show real data, but always for the user's entire expense history. This step adds an optional date range filter (From / To) so a user can see their summary stats, category breakdown and transactions for a chosen period, such as one month. The filter is driven by query-string parameters so filtered views can be bookmarked and refreshed, and it requires no new tables.

## Depends on
- Step 1: Database setup (`expenses.date` stored as `YYYY-MM-DD` text)
- Step 3: Login + Logout (`session["user_id"]`)
- Step 4: Profile page design (`templates/profile.html`, `static/css/profile.css`)
- Step 5: Profile page connected to the database (`get_summary_stats`, `get_recent_transactions`, `get_category_breakdown`)

## Routes
No new routes. The existing `GET /profile` (logged-in only) accepts two optional query parameters:
- `from` — start date, inclusive, `YYYY-MM-DD`
- `to` — end date, inclusive, `YYYY-MM-DD`

Either, both or neither may be supplied. With neither, behaviour is identical to Step 5.

## Database changes
No database changes. `expenses.date` is `TEXT` in ISO `YYYY-MM-DD` format, so range comparison with `>=` / `<=` is correct. Verified against `database/db.py`.

## Templates
- **Create:** none
- **Modify:** `templates/profile.html`
  - Add a filter form above the stats row: two `<input type="date">` fields (From, To), an "Apply" submit button and a "Clear" link to `url_for('profile')`. The form uses `method="get"` and prefills the current values.
  - Show an inline error message when the supplied dates are invalid (see rules).
  - The empty-state texts ("No spending yet." / "No transactions yet.") stay; when a filter is active they should still read sensibly for the chosen range.
  - Section titles and the stats label may indicate when a filter is active (e.g. "Total spent" stays, the transactions card title becomes "Transactions" when filtered instead of "Recent transactions").

## Files to change
- `database/db.py` — add optional `date_from=None, date_to=None` parameters to `get_summary_stats`, `get_recent_transactions` and `get_category_breakdown`. Build the `WHERE` clause with `user_id = ?` plus optional `date >= ?` / `date <= ?` conditions, always passing values as parameters. Existing calls without the new arguments must behave exactly as before.
- `app.py` — in `profile()`, read `from` and `to` from `request.args`, validate them, pass them to the three helpers and pass `date_from`, `date_to` and `filter_error` to the template. Add a small `_parse_date(value)` helper.
- `templates/profile.html` — filter form and error display as described above.
- `static/css/profile.css` — styles for the filter form, using existing CSS variables.
- `tests/test_profile.py` — tests for the filter.

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw sqlite3 via `get_db()`
- Parameterised queries only — never string-format dates or any user input into SQL (only the fixed condition fragments may be concatenated)
- Passwords hashed with werkzeug (no changes to auth in this step)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Every query must still filter by the session's `user_id`; the date conditions are added to it, never replace it
- Validate `from` / `to` with `datetime.strptime(value, "%Y-%m-%d")`; an empty value means "no bound"
- If a supplied date is malformed, or `from` is later than `to`, do not return a 500: show the error message, ignore the invalid filter and display the unfiltered data
- Both bounds are inclusive
- Keep the `limit=10` on the transactions list; the stats and category breakdown cover the whole filtered range
- Percentages in the category breakdown are computed against the filtered total
- Use GET (not POST) so the filter survives refresh and can be bookmarked
- Keep the context variable names `user`, `stats`, `transactions`, `categories` unchanged
- Do not modify other routes or the placeholder expense routes (Steps 7–9)

## Definition of done
- [ ] `/profile` with no parameters shows the same data as before this step
- [ ] The filter form appears on `/profile` with From and To date inputs, an Apply button and a Clear link
- [ ] Setting only From shows data on or after that date
- [ ] Setting only To shows data on or before that date
- [ ] Setting both shows only expenses within the range, bounds inclusive (an expense dated exactly on From or To is included)
- [ ] Total spent, transaction count, top category, category breakdown and transactions list all reflect the filtered range
- [ ] Category percentages add up against the filtered total, not the all-time total
- [ ] The form inputs are prefilled with the active filter after applying
- [ ] Clear returns to the unfiltered view
- [ ] A range with no expenses shows `₹0.00`, `0`, "—" and the empty-state messages without error
- [ ] An invalid date (e.g. `from=abc`) or `from` later than `to` shows an error message and does not crash
- [ ] A filter never exposes another user's expenses
- [ ] The filtered URL (e.g. `/profile?from=2026-10-01&to=2026-10-31`) can be refreshed and bookmarked
- [ ] `/profile` logged out still redirects to `/login`
- [ ] `pytest` passes, including new tests for from-only, to-only, both, empty range, invalid input and per-user isolation
