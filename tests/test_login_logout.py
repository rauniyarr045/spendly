import pytest
from werkzeug.security import generate_password_hash

from database.db import get_db

EMAIL = "jane@example.com"
PASSWORD = "supersecret"


@pytest.fixture
def user(app):
    conn = get_db()
    try:
        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Jane", EMAIL, generate_password_hash(PASSWORD)),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def _login(client, email=EMAIL, password=PASSWORD):
    return client.post("/login", data={"email": email, "password": password})


def test_login_page_renders(client):
    assert client.get("/login").status_code == 200


def test_login_success(client, user):
    resp = _login(client)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")
    with client.session_transaction() as sess:
        assert sess["user_id"] == user


def test_login_email_case_and_whitespace_insensitive(client, user):
    resp = _login(client, email="  JANE@Example.COM ")
    assert resp.status_code == 302


def test_login_wrong_password(client, user):
    resp = _login(client, password="wrongpassword")
    assert resp.status_code == 400
    assert b"Invalid email or password." in resp.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_login_unknown_email(client, user):
    resp = _login(client, email="nobody@example.com")
    assert resp.status_code == 400
    assert b"Invalid email or password." in resp.data


@pytest.mark.parametrize(
    "email,password", [("", PASSWORD), (EMAIL, ""), ("", "")]
)
def test_login_missing_fields(client, user, email, password):
    resp = _login(client, email=email, password=password)
    assert resp.status_code == 400
    assert b"Email and password are required." in resp.data
    with client.session_transaction() as sess:
        assert "user_id" not in sess


def test_failed_login_keeps_email_not_password(client, user):
    resp = _login(client, password="wrongpassword")
    assert f'value="{EMAIL}"'.encode() in resp.data
    assert b"wrongpassword" not in resp.data


def test_login_page_redirects_when_logged_in(client, user):
    _login(client)
    resp = client.get("/login")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/profile")


def test_navbar_reflects_auth_state(client, user):
    assert b"Sign in" in client.get("/").data
    _login(client)
    page = client.get("/").data
    assert b"Sign out" in page
    assert b"Get started" not in page


def test_logout_clears_session(client, user):
    _login(client)
    resp = client.get("/logout")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")
    with client.session_transaction() as sess:
        assert "user_id" not in sess
    assert b"Sign in" in client.get("/").data
