from __future__ import annotations

import csv
import io
import os
import sqlite3
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")
app.config["JSON_SORT_KEYS"] = False

DB_PATH = Path(__file__).with_name("subscribers.db")

VALID_CHANNELS = {"email", "sms", "both"}
VALID_ALERT_TYPES = {"all", "release", "restock", "set", "msrp", "specific"}


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema() -> None:
    with get_db_connection() as conn:
        table_exists = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='subscribers'"
        ).fetchone()

        if not table_exists:
            conn.execute(
                """
                CREATE TABLE subscribers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    email TEXT NOT NULL UNIQUE,
                    phone TEXT,
                    preferred_channel TEXT NOT NULL DEFAULT 'email',
                    product_interest TEXT,
                    desired_set TEXT,
                    max_msrp TEXT,
                    alert_type TEXT DEFAULT 'all',
                    product_category TEXT,
                    retailer TEXT,
                    custom_search TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
            return

        existing_cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(subscribers)").fetchall()
        }

        additions = {
            "desired_set": "ALTER TABLE subscribers ADD COLUMN desired_set TEXT",
            "max_msrp": "ALTER TABLE subscribers ADD COLUMN max_msrp TEXT",
            "alert_type": "ALTER TABLE subscribers ADD COLUMN alert_type TEXT DEFAULT 'all'",
            "product_category": "ALTER TABLE subscribers ADD COLUMN product_category TEXT",
            "retailer": "ALTER TABLE subscribers ADD COLUMN retailer TEXT",
            "custom_search": "ALTER TABLE subscribers ADD COLUMN custom_search TEXT",
            "updated_at": "ALTER TABLE subscribers ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
        }

        for column_name, statement in additions.items():
            if column_name not in existing_cols:
                try:
                    conn.execute(statement)
                except sqlite3.Error:
                    pass

        conn.execute(
            "UPDATE subscribers SET updated_at = COALESCE(updated_at, created_at) WHERE updated_at IS NULL"
        )
        conn.commit()


def normalize_channel(value: str) -> str:
    channel = (value or "email").strip().lower()
    return channel if channel in VALID_CHANNELS else "email"


def normalize_alert_type(value: str) -> str:
    alert_type = (value or "all").strip().lower()
    return alert_type if alert_type in VALID_ALERT_TYPES else "all"


def serialize_subscriber(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"],
        "preferred_channel": row["preferred_channel"],
        "product_interest": row["product_interest"],
        "desired_set": row["desired_set"],
        "max_msrp": row["max_msrp"],
        "alert_type": row["alert_type"],
        "product_category": row["product_category"],
        "retailer": row["retailer"],
        "custom_search": row["custom_search"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/subscribe")
def subscribe():
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    phone = (request.form.get("phone") or "").strip()
    preferred_channel = normalize_channel(request.form.get("preferred_channel"))
    product_interest = (request.form.get("product_interest") or "").strip()
    desired_set = (request.form.get("desired_set") or "").strip()
    max_msrp = (request.form.get("max_msrp") or "").strip()
    alert_type = normalize_alert_type(request.form.get("alert_type"))
    product_category = (request.form.get("product_category") or "").strip()
    retailer = (request.form.get("retailer") or "").strip()
    custom_search = (request.form.get("custom_search") or "").strip()

    if not email or "@" not in email:
        flash("Please enter a valid email address.")
        return redirect(url_for("index"))

    if phone:
        phone = phone.replace(" ", "")

    try:
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO subscribers (
                    name, email, phone, preferred_channel, product_interest,
                    desired_set, max_msrp, alert_type, product_category,
                    retailer, custom_search, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(email) DO UPDATE SET
                    name = excluded.name,
                    phone = excluded.phone,
                    preferred_channel = excluded.preferred_channel,
                    product_interest = excluded.product_interest,
                    desired_set = excluded.desired_set,
                    max_msrp = excluded.max_msrp,
                    alert_type = excluded.alert_type,
                    product_category = excluded.product_category,
                    retailer = excluded.retailer,
                    custom_search = excluded.custom_search,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    name,
                    email,
                    phone,
                    preferred_channel,
                    product_interest,
                    desired_set,
                    max_msrp,
                    alert_type,
                    product_category,
                    retailer,
                    custom_search,
                ),
            )
            conn.commit()
    except sqlite3.Error:
        flash("There was a problem saving your signup. Please try again.")
        return redirect(url_for("index"))

    return redirect(url_for("thank_you"))


@app.route("/thank-you")
def thank_you():
    return render_template("thank_you.html")


@app.route("/admin")
def admin():
    admin_token = os.environ.get("ADMIN_TOKEN")
    provided_token = request.args.get("token")

    if admin_token and provided_token != admin_token:
        return "Unauthorized", 401

    with get_db_connection() as conn:
        subscribers = conn.execute(
            """
            SELECT id, name, email, phone, preferred_channel, product_interest,
                   desired_set, max_msrp, alert_type, product_category,
                   retailer, custom_search, created_at, updated_at
            FROM subscribers
            ORDER BY created_at DESC
            """
        ).fetchall()

    return render_template("admin.html", subscribers=[serialize_subscriber(row) for row in subscribers])


@app.route("/admin/export")
def admin_export():
    admin_token = os.environ.get("ADMIN_TOKEN")
    provided_token = request.args.get("token")

    if admin_token and provided_token != admin_token:
        return "Unauthorized", 401

    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name, email, phone, preferred_channel, product_interest,
                   desired_set, max_msrp, alert_type, product_category,
                   retailer, custom_search, created_at, updated_at
            FROM subscribers
            ORDER BY created_at DESC
            """
        ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id",
        "name",
        "email",
        "phone",
        "preferred_channel",
        "product_interest",
        "desired_set",
        "max_msrp",
        "alert_type",
        "product_category",
        "retailer",
        "custom_search",
        "created_at",
        "updated_at",
    ])

    for row in rows:
        writer.writerow([
            row["id"],
            row["name"],
            row["email"],
            row["phone"],
            row["preferred_channel"],
            row["product_interest"],
            row["desired_set"],
            row["max_msrp"],
            row["alert_type"],
            row["product_category"],
            row["retailer"],
            row["custom_search"],
            row["created_at"],
            row["updated_at"],
        ])

    csv_data = output.getvalue()
    return (csv_data, 200, {"Content-Type": "text/csv", "Content-Disposition": "attachment; filename=subscribers.csv"})


@app.get("/api/subscribers")
def api_subscribers():
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name, email, phone, preferred_channel, product_interest,
                   desired_set, max_msrp, alert_type, product_category,
                   retailer, custom_search, created_at, updated_at
            FROM subscribers
            ORDER BY created_at DESC
            """
        ).fetchall()

    return {"count": len(rows), "subscribers": [serialize_subscriber(row) for row in rows]}


@app.get("/health")
def health():
    return {"ok": True, "database": str(DB_PATH)}


if __name__ == "__main__":
    ensure_schema()
    app.run(host="0.0.0.0", port=5000, debug=True)
