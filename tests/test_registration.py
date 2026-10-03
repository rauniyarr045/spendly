import pytest
from werkzeug.security import check_password_hash

from database.db import get_db

VALID = {"name": "Test User", "email": "Test@Example.com", "password": "password123"}


def _users():
    conn = get_db()
    try:
        return conn.execute("SELECT * FROM users").fetchall()
    finally:
        conn.close()


def test_get_register_renders_form(client):
    resp = client.get("/register")
    assert resp.status_code == 200
    assert b"<form" in resp.data


def test_successful_registration(client):
    resp = client.post("/register", data=VALID)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login?registered=1")
    rows = _users()
    assert len(rows) == 1
    assert rows[0]["email"] == "test@example.com"
    assert rows[0]["password_hash"] != VALID["password"]
    assert check_password_hash(rows[0]["password_hash"], VALID["password"])


def test_duplicate_email_case_insensitive(client):
    client.post("/register", data=VALID)
    resp = client.post("/register", data={**VALID, "email": "TEST@EXAMPLE.COM"})
    assert resp.status_code == 400
    assert b"An account with that email already exists." in resp.data
    assert len(_users()) == 1


def test_short_password(client):
    resp = client.post("/register", data={**VALID, "password": "1234567"})
    assert resp.status_code == 400
    assert b"at least 8 characters" in resp.data
    assert _users() == []


@pytest.mark.parametrize("field", ["name", "email", "password"])
def test_missing_field(client, field):
    resp = client.post("/register", data={**VALID, field: ""})
    assert resp.status_code == 400
    assert _users() == []


def test_whitespace_only_name(client):
    resp = client.post("/register", data={**VALID, "name": "   "})
    assert resp.status_code == 400
    assert _users() == []


@pytest.mark.parametrize("email", ["foo", "foo@", "@bar.com", "foo@bar"])
def test_invalid_email(client, email):
    resp = client.post("/register", data={**VALID, "email": email})
    assert resp.status_code == 400
    assert b"valid email" in resp.data
    assert _users() == []


def test_failed_submit_keeps_name_and_email_not_password(client):
    resp = client.post("/register", data={**VALID, "password": "short"})
    assert b'value="Test User"' in resp.data
    assert b'value="test@example.com"' in resp.data
    assert b"short" not in resp.data.replace(b"at least 8 characters", b"")


def test_login_notice(client):
    assert b"Account created" in client.get("/login?registered=1").data
    assert b"Account created" not in client.get("/login").data
