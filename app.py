from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")
DB_PATH = Path(__file__).with_name("subscribers.db")


def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema() -> None:
    with get_db_connection() as conn:
        existing = conn.execute(
            "SELECT name FROM PRAGMA_TABLE_INFO('subscribers')"
        ).fetchall()
        cols = {row[0] for row in existing}

        if not cols:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS subscribers (
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()
            return

        additions = {
            "desired_set": "ALTER TABLE subscribers ADD COLUMN desired_set TEXT",
            "max_msrp": "ALTER TABLE subscribers ADD COLUMN max_msrp TEXT",
            "alert_type": "ALTER TABLE subscribers ADD COLUMN alert_type TEXT DEFAULT 'all'",
            "product_category": "ALTER TABLE subscribers ADD COLUMN product_category TEXT",
            "retailer": "ALTER TABLE subscribers ADD COLUMN retailer TEXT",
            "custom_search": "ALTER TABLE subscribers ADD COLUMN custom_search TEXT",
        }

        for column_name, statement in additions.items():
            if column_name not in cols:
                try:
                    conn.execute(statement)
                except sqlite3.Error:
                    pass

        conn.commit()


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/subscribe")
def subscribe():
    name = (request.form.get("name") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    phone = (request.form.get("phone") or "").strip()
    preferred_channel = (request.form.get("preferred_channel") or "email").strip().lower()
    product_interest = (request.form.get("product_interest") or "").strip()
    desired_set = (request.form.get("desired_set") or "").strip()
    max_msrp = (request.form.get("max_msrp") or "").strip()
    alert_type = (request.form.get("alert_type") or "all").strip().lower()
    product_category = (request.form.get("product_category") or "").strip()
    retailer = (request.form.get("retailer") or "").strip()
    custom_search = (request.form.get("custom_search") or "").strip()

    if not email or "@" not in email:
        flash("Please enter a valid email address.")
        return redirect(url_for("index"))

    if preferred_channel not in {"email", "sms", "both"}:
        preferred_channel = "email"

    if alert_type not in {"all", "msrp", "set", "specific", "restock", "release"}:
        alert_type = "all"

    if phone:
        phone = phone.replace(" ", "")

    try:
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO subscribers (
                    name, email, phone, preferred_channel, product_interest,
                    desired_set, max_msrp, alert_type, product_category, retailer, custom_search
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    custom_search = excluded.custom_search
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
                   desired_set, max_msrp, alert_type, product_category, retailer, custom_search,
                   created_at
            FROM subscribers
            ORDER BY created_at DESC
            """
        ).fetchall()

    return render_template("admin.html", subscribers=subscribers)


@app.get("/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    ensure_schema()
    app.run(host="0.0.0.0", port=5000, debug=True)
