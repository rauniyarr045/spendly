import os
import re

import pytest
from werkzeug.security import generate_password_hash

from database.db import get_db, seed_db

EMAIL = "jane@example.com"
PASSWORD = "supersecret"


@pytest.fixture
def user(app):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Jane", EMAIL, generate_password_hash(PASSWORD)),
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def logged_in(client, user):
    client.post("/login", data={"email": EMAIL, "password": PASSWORD})
    return client


def test_profile_requires_login(client):
    resp = client.get("/profile")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_profile_renders_when_logged_in(logged_in):
    assert logged_in.get("/profile").status_code == 200


@pytest.fixture
def demo_logged_in(client, app):
    seed_db()
    client.post(
        "/login", data={"email": "demo@spendly.com", "password": "demo123"}
    )
    return client


def _add_expense(email, amount, category, day, description):
    conn = get_db()
    try:
        uid = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description)"
            " VALUES (?, ?, ?, ?, ?)",
            (uid, amount, category, day, description),
        )
        conn.commit()
    finally:
        conn.close()


def test_profile_shows_user_info_and_stats(demo_logged_in):
    page = demo_logged_in.get("/profile").data.decode()
    assert "Demo User" in page
    assert "demo@spendly.com" in page
    assert "Member since" in page
    assert "₹327.89" in page
    assert "Bills" in page
    assert '<p class="profile-stat-value">8</p>' in page


def test_profile_has_transactions_and_categories(demo_logged_in):
    page = demo_logged_in.get("/profile").data.decode()
    assert page.count("<tr>") - 1 == 8  # minus the header row
    assert page.count('class="profile-breakdown-row"') == 7


def test_transactions_are_newest_first(demo_logged_in):
    page = demo_logged_in.get("/profile").data.decode()
    assert page.index("Groceries") < page.index("Electricity bill")
    assert page.index("Electricity bill") < page.index("Lunch at cafe")


def test_categories_sorted_by_amount(demo_logged_in):
    page = demo_logged_in.get("/profile").data.decode()
    names = re.findall(r'profile-breakdown-name">(\w+)<', page)
    assert names[0] == "Bills"
    assert names[1] == "Shopping"


def test_empty_user_sees_empty_states(logged_in):
    page = logged_in.get("/profile").data.decode()
    assert "₹0.00" in page
    assert '<p class="profile-stat-value">0</p>' in page
    assert '<p class="profile-stat-value">—</p>' in page
    assert "No transactions yet." in page
    assert "No spending yet." in page


def test_users_only_see_their_own_expenses(demo_logged_in, client):
    _add_expense("demo@spendly.com", 1.0, "Food", "2026-01-01", "demo-only")
    demo_page = demo_logged_in.get("/profile").data.decode()
    assert "demo-only" in demo_page

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Jane", EMAIL, generate_password_hash(PASSWORD)),
        )
        conn.commit()
    finally:
        conn.close()
    _add_expense(EMAIL, 5.0, "Other", "2026-01-02", "jane-only")

    client.get("/logout")
    client.post("/login", data={"email": EMAIL, "password": PASSWORD})
    jane_page = client.get("/profile").data.decode()
    assert "jane-only" in jane_page
    assert "demo-only" not in jane_page
    assert "Groceries" not in jane_page


def test_new_expense_shows_after_refresh(demo_logged_in):
    assert "₹327.89" in demo_logged_in.get("/profile").data.decode()
    _add_expense("demo@spendly.com", 10.0, "Food", "2026-01-01", "extra")
    assert "₹337.89" in demo_logged_in.get("/profile").data.decode()


def test_deleted_user_session_redirects_to_login(demo_logged_in):
    conn = get_db()
    try:
        conn.execute("DELETE FROM expenses")
        conn.execute("DELETE FROM users")
        conn.commit()
    finally:
        conn.close()
    resp = demo_logged_in.get("/profile")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


@pytest.mark.parametrize("path", ["/", "/login", "/register"])
def test_logged_in_user_is_redirected_to_profile(logged_in, path):
    resp = logged_in.get(path)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")


def test_navbar_shows_username_and_sign_out(logged_in):
    page = logged_in.get("/profile").data
    assert b"Jane" in page
    assert b"Sign out" in page


# Date filter (Step 6) ------------------------------------------------------


@pytest.fixture
def jane_with_expenses(logged_in):
    _add_expense(EMAIL, 10.0, "Food", "2026-01-05", "jan-lunch")
    _add_expense(EMAIL, 100.0, "Bills", "2026-02-01", "feb-rent")
    _add_expense(EMAIL, 20.0, "Food", "2026-02-15", "feb-dinner")
    _add_expense(EMAIL, 5.0, "Other", "2026-03-31", "mar-misc")
    return logged_in


def test_filter_form_is_shown(logged_in):
    page = logged_in.get("/profile").data.decode()
    assert 'name="from"' in page
    assert 'name="to"' in page
    assert "Clear" in page


def test_no_filter_shows_everything(jane_with_expenses):
    page = jane_with_expenses.get("/profile").data.decode()
    assert "₹135.00" in page
    assert "Recent transactions" in page


def test_filter_from_only(jane_with_expenses):
    page = jane_with_expenses.get("/profile?from=2026-02-15").data.decode()
    assert "feb-dinner" in page and "mar-misc" in page
    assert "jan-lunch" not in page and "feb-rent" not in page
    assert "₹25.00" in page


def test_filter_to_only(jane_with_expenses):
    page = jane_with_expenses.get("/profile?to=2026-02-01").data.decode()
    assert "jan-lunch" in page and "feb-rent" in page
    assert "feb-dinner" not in page
    assert "₹110.00" in page


def test_filter_range_is_inclusive_and_updates_all_sections(jane_with_expenses):
    page = jane_with_expenses.get(
        "/profile?from=2026-02-01&to=2026-02-15"
    ).data.decode()
    assert "feb-rent" in page and "feb-dinner" in page
    assert "jan-lunch" not in page and "mar-misc" not in page
    assert "₹120.00" in page
    assert '<p class="profile-stat-value">2</p>' in page
    assert '<p class="profile-stat-value">Bills</p>' in page
    names = re.findall(r'profile-breakdown-name">(\w+)<', page)
    assert names == ["Bills", "Food"]
    assert 'value="83"' in page  # Bills share of the filtered total
    assert 'value="2026-02-01"' in page and 'value="2026-02-15"' in page
    assert "Recent transactions" not in page


def test_filter_with_no_matches_shows_empty_states(jane_with_expenses):
    page = jane_with_expenses.get(
        "/profile?from=2025-01-01&to=2025-12-31"
    ).data.decode()
    assert "₹0.00" in page
    assert '<p class="profile-stat-value">—</p>' in page
    assert "No transactions yet." in page
    assert "No spending yet." in page


@pytest.mark.parametrize(
    "query", ["from=abc", "to=2026-13-01", "from=2026-03-01&to=2026-01-01"]
)
def test_invalid_filter_shows_error_and_unfiltered_data(
    jane_with_expenses, query
):
    resp = jane_with_expenses.get(f"/profile?{query}")
    page = resp.data.decode()
    assert resp.status_code == 200
    assert "auth-error" in page
    assert "₹135.00" in page


def test_filter_never_shows_other_users_expenses(jane_with_expenses):
    seed_db()
    page = jane_with_expenses.get(
        "/profile?from=2000-01-01&to=2099-12-31"
    ).data.decode()
    assert "Groceries" not in page
    assert "₹135.00" in page


def test_template_has_no_inline_styles_or_hex_colours():
    path = os.path.join(
        os.path.dirname(__file__), "..", "templates", "profile.html"
    )
    with open(path, encoding="utf-8") as f:
        source = f.read()
    assert 'style="' not in source
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", source)
