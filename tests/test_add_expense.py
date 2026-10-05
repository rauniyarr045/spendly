from datetime import date

import pytest
from werkzeug.security import generate_password_hash

from database.db import CATEGORIES, get_db

EMAIL = "jane@example.com"
PASSWORD = "supersecret"
OTHER_EMAIL = "bob@example.com"

VALID = {
    "amount": "250.50",
    "category": "Food",
    "date": "2026-10-01",
    "description": "Team lunch",
}


def _create_user(name, email):
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(PASSWORD)),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _expenses(user_id=None):
    conn = get_db()
    try:
        if user_id is None:
            rows = conn.execute("SELECT * FROM expenses").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM expenses WHERE user_id = ?", (user_id,)
            ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@pytest.fixture
def user_id(app):
    return _create_user("Jane", EMAIL)


@pytest.fixture
def logged_in(client, user_id):
    client.post("/login", data={"email": EMAIL, "password": PASSWORD})
    return client


# Auth ------------------------------------------------------------------

def test_get_requires_login(client):
    resp = client.get("/expenses/add")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_post_requires_login(client, user_id):
    resp = client.post("/expenses/add", data=VALID)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")
    assert _expenses() == []


# Form ------------------------------------------------------------------

def test_form_renders(logged_in):
    resp = logged_in.get("/expenses/add")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    for name in ("amount", "category", "date", "description"):
        assert f'name="{name}"' in html
    for c in CATEGORIES:
        assert f'<option value="{c}"' in html
    assert f'value="{date.today().isoformat()}"' in html


def test_profile_links_to_add_expense(logged_in):
    html = logged_in.get("/profile").get_data(as_text=True)
    assert 'href="/expenses/add"' in html


# Success ---------------------------------------------------------------

def test_valid_submission_inserts_and_redirects(logged_in, user_id):
    resp = logged_in.post("/expenses/add", data=VALID)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")

    rows = _expenses(user_id)
    assert len(rows) == 1
    row = rows[0]
    assert row["amount"] == 250.50
    assert row["category"] == "Food"
    assert row["date"] == "2026-10-01"
    assert row["description"] == "Team lunch"


def test_new_expense_appears_on_profile(logged_in):
    logged_in.post("/expenses/add", data=VALID)
    html = logged_in.get("/profile").get_data(as_text=True)
    assert "Team lunch" in html
    assert "₹250.50" in html


def test_amount_is_rounded_to_two_places(logged_in, user_id):
    logged_in.post("/expenses/add", data={**VALID, "amount": "10.456"})
    assert _expenses(user_id)[0]["amount"] == 10.46


def test_empty_description_stored_as_null(logged_in, user_id):
    logged_in.post("/expenses/add", data={**VALID, "description": "   "})
    assert _expenses(user_id)[0]["description"] is None
    html = logged_in.get("/profile").get_data(as_text=True)
    assert "None" not in html


# Validation ------------------------------------------------------------

@pytest.mark.parametrize(
    "amount", ["", "0", "-5", "abc", "nan", "inf", "0.001"]
)
def test_invalid_amount_rejected(logged_in, amount):
    resp = logged_in.post("/expenses/add", data={**VALID, "amount": amount})
    assert resp.status_code == 400
    assert "auth-error" in resp.get_data(as_text=True)
    assert _expenses() == []


@pytest.mark.parametrize("category", ["", "Rent", "food"])
def test_invalid_category_rejected(logged_in, category):
    resp = logged_in.post("/expenses/add", data={**VALID, "category": category})
    assert resp.status_code == 400
    assert _expenses() == []


@pytest.mark.parametrize("day", ["", "2026-13-40", "01/10/2026", "abc"])
def test_invalid_date_rejected(logged_in, day):
    resp = logged_in.post("/expenses/add", data={**VALID, "date": day})
    assert resp.status_code == 400
    assert _expenses() == []


def test_long_description_rejected(logged_in):
    resp = logged_in.post(
        "/expenses/add", data={**VALID, "description": "x" * 201}
    )
    assert resp.status_code == 400
    assert _expenses() == []


def test_errors_preserve_input(logged_in):
    resp = logged_in.post(
        "/expenses/add",
        data={**VALID, "amount": "-1", "category": "Bills"},
    )
    html = resp.get_data(as_text=True)
    assert 'value="-1"' in html
    assert 'value="2026-10-01"' in html
    assert 'value="Team lunch"' in html
    assert '<option value="Bills" selected>' in html


# Isolation -------------------------------------------------------------

def test_user_id_from_form_is_ignored(logged_in, user_id):
    other_id = _create_user("Bob", OTHER_EMAIL)
    logged_in.post("/expenses/add", data={**VALID, "user_id": str(other_id)})
    assert len(_expenses(user_id)) == 1
    assert _expenses(other_id) == []


def test_other_user_profile_unaffected(client, logged_in):
    _create_user("Bob", OTHER_EMAIL)
    logged_in.post("/expenses/add", data=VALID)
    logged_in.get("/logout")
    client.post("/login", data={"email": OTHER_EMAIL, "password": PASSWORD})
    html = client.get("/profile").get_data(as_text=True)
    assert "Team lunch" not in html
    assert "₹0.00" in html
