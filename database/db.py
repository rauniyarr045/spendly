import os
import sqlite3
from datetime import date

from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "spendly.db"
)

CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                name          TEXT NOT NULL,
                email         TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at    TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id),
                amount      REAL NOT NULL,
                category    TEXT NOT NULL,
                date        TEXT NOT NULL,
                description TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()


def _expense_filter(user_id, date_from=None, date_to=None):
    """Build the WHERE clause for one user's expenses, optionally within an
    inclusive date range. Only fixed fragments are joined; values are params."""
    clause = "user_id = ?"
    params = [user_id]
    if date_from:
        clause += " AND date >= ?"
        params.append(date_from)
    if date_to:
        clause += " AND date <= ?"
        params.append(date_to)
    return clause, params


def get_summary_stats(user_id, date_from=None, date_to=None):
    where, params = _expense_filter(user_id, date_from, date_to)
    conn = get_db()
    try:
        total, count = conn.execute(
            "SELECT COALESCE(SUM(amount), 0), COUNT(*) FROM expenses "
            f"WHERE {where}",
            params,
        ).fetchone()
        top = conn.execute(
            f"SELECT category FROM expenses WHERE {where} "
            "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            params,
        ).fetchone()
    finally:
        conn.close()
    return {
        "total_spent": total,
        "transaction_count": count,
        "top_category": top["category"] if top else None,
    }


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    where, params = _expense_filter(user_id, date_from, date_to)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses "
            f"WHERE {where} ORDER BY date DESC, id DESC LIMIT ?",
            params + [limit],
        ).fetchall()
    finally:
        conn.close()
    return [dict(r) for r in rows]


def get_category_breakdown(user_id, date_from=None, date_to=None):
    where, params = _expense_filter(user_id, date_from, date_to)
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, SUM(amount) AS amount FROM expenses "
            f"WHERE {where} GROUP BY category ORDER BY amount DESC",
            params,
        ).fetchall()
    finally:
        conn.close()
    total = sum(r["amount"] for r in rows)
    if not total:
        return []
    return [
        {
            "name": r["category"],
            "amount": r["amount"],
            "percent": round(r["amount"] / total * 100),
        }
        for r in rows
    ]


def seed_db():
    conn = get_db()
    try:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return

        cur = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123")),
        )
        user_id = cur.lastrowid

        today = date.today()
        samples = [
            (1, 12.50, "Food", "Lunch at cafe"),
            (3, 45.00, "Transport", "Monthly bus pass top-up"),
            (5, 120.00, "Bills", "Electricity bill"),
            (8, 30.75, "Health", "Pharmacy"),
            (11, 18.00, "Entertainment", "Movie ticket"),
            (14, 64.99, "Shopping", "New headphones"),
            (18, 9.25, "Other", "Miscellaneous"),
            (22, 27.40, "Food", "Groceries"),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                (user_id, amount, category, today.replace(day=day).isoformat(), desc)
                for day, amount, category, desc in samples
            ],
        )
        conn.commit()
    finally:
        conn.close()
