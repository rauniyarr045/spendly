import os
import re

import pytest
from werkzeug.security import generate_password_hash

from database.db import get_db

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


def test_profile_shows_user_info_and_stats(logged_in):
    page = logged_in.get("/profile").data
    assert b"Demo User" in page
    assert b"demo@spendly.com" in page
    assert b"Total spent" in page
    assert b"Transactions" in page
    assert b"Top category" in page


def test_profile_has_transactions_and_categories(logged_in):
    page = logged_in.get("/profile").data.decode()
    assert page.count("<tr>") - 1 >= 3  # minus the header row
    assert page.count('class="profile-breakdown-row"') >= 3


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
