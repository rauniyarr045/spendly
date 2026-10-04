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


def test_template_has_no_inline_styles_or_hex_colours():
    path = os.path.join(
        os.path.dirname(__file__), "..", "templates", "profile.html"
    )
    with open(path, encoding="utf-8") as f:
        source = f.read()
    assert 'style="' not in source
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", source)
