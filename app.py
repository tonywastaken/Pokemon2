from __future__ import annotations

import csv
import io
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from flask import Flask, flash, redirect, render_template, request, url_for

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")
app.config["JSON_SORT_KEYS"] = False

DB_PATH = Path(__file__).with_name("subscribers.db")

VALID_CHANNELS = {"email", "sms", "both"}
VALID_ALERT_TYPES = {"all", "release", "restock", "set", "msrp", "specific"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


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

        watch_table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='watchlist'"
        ).fetchone()

        if not watch_table:
            conn.execute(
                """
                CREATE TABLE watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_name TEXT NOT NULL,
                    retailer TEXT,
                    product_url TEXT,
                    store_location TEXT,
                    target_price TEXT,
                    expected_release TEXT,
                    alert_type TEXT DEFAULT 'all',
                    auto_buy INTEGER DEFAULT 0,
                    product_type TEXT,
                    notes TEXT,
                    status TEXT DEFAULT 'unknown',
                    last_checked TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

        conn.execute(
            "CREATE TABLE IF NOT EXISTS alerts ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "watch_id INTEGER,"
            "status TEXT,"
            "message TEXT,"
            "detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
            "FOREIGN KEY(watch_id) REFERENCES watchlist(id)"
            ")"
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


def decode_status(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "product_name": row["product_name"],
        "retailer": row["retailer"],
        "product_url": row["product_url"],
        "store_location": row["store_location"],
        "target_price": row["target_price"],
        "expected_release": row["expected_release"],
        "alert_type": row["alert_type"],
        "auto_buy": bool(row["auto_buy"]),
        "product_type": row["product_type"],
        "notes": row["notes"],
        "status": row["status"],
        "last_checked": row["last_checked"],
        "created_at": row["created_at"],
    }


def fetch_page_text(url: str) -> str:
    if not url:
        return ""
    try:
        response = requests.get(url, timeout=12, headers={
            "User-Agent": "Mozilla/5.0"
        })
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.get_text(" ", strip=True).lower()
    except Exception:
        return ""


def assess_retailer_status(product_url: str, retailer: str, store_location: str = "") -> dict[str, Any]:
    text = fetch_page_text(product_url)
    if not text:
        return {
            "status": "offline",
            "message": "Could not load page; site may be down or blocked.",
            "release_window": False,
        }

    in_stock_signals = [
        "add to cart",
        "buy now",
        "in stock",
        "available now",
        "ships immediately",
        "pickup today",
        "ready for pickup",
    ]
    out_of_stock_signals = [
        "sold out",
        "out of stock",
        "unavailable",
        "not available",
        "notify me",
        "currently unavailable",
    ]
    release_signals = [
        "coming soon",
        "pre-order",
        "preorder",
        "release date",
        "dropping soon",
    ]

    status = "unknown"
    message = "No clear availability signal detected."

    if any(signal in text for signal in in_stock_signals):
        status = "in_stock"
        message = "Product is live and available online or at the retailer."
    elif any(signal in text for signal in out_of_stock_signals):
        status = "out_of_stock"
        message = "Product is showing out of stock or unavailable."
    elif any(signal in text for signal in release_signals):
        status = "release_window"
        message = "This product is in a pre-launch or release window."

    if retailer and retailer.lower() in text and status == "unknown":
        status = "page_loaded"
        message = f"Product page loaded for {retailer}, but stock state is unclear."

    if store_location and not product_url:
        status = "in_store_watch"
        message = f"Store check requested for {store_location}; product URL not provided yet."

    return {
        "status": status,
        "message": message,
        "release_window": status in {"release_window", "in_stock"},
    }


def run_watch_check(watch_id: int) -> dict[str, Any]:
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM watchlist WHERE id = ?", (watch_id,)).fetchone()
        if not row:
            return {"status": "missing"}

    result = assess_retailer_status(row["product_url"], row["retailer"], row["store_location"])
    updated_status = result["status"]
    message = result["message"]

    with get_db_connection() as conn:
        conn.execute(
            "UPDATE watchlist SET status = ?, last_checked = CURRENT_TIMESTAMP WHERE id = ?",
            (updated_status, watch_id),
        )
        conn.execute(
            "INSERT INTO alerts (watch_id, status, message) VALUES (?, ?, ?)",
            (watch_id, updated_status, message),
        )
        conn.commit()

    if row["auto_buy"] and updated_status == "in_stock":
        message = f"AUTO_BUY_TRIGGERED: {row['product_name']} is in stock. This is a guarded simulation only and should be replaced with a retailer-approved checkout flow."

    return {"status": updated_status, "message": message, "release_window": result["release_window"]}


@app.route("/")
def index():
    with get_db_connection() as conn:
        watchlist = conn.execute(
            "SELECT * FROM watchlist ORDER BY created_at DESC"
        ).fetchall()
        items = [decode_status(row) for row in watchlist]
    return render_template("index.html", items=items)


@app.post("/watch/add")
def add_watch():
    product_name = (request.form.get("product_name") or "").strip()
    retailer = (request.form.get("retailer") or "").strip()
    product_url = (request.form.get("product_url") or "").strip()
    store_location = (request.form.get("store_location") or "").strip()
    target_price = (request.form.get("target_price") or "").strip()
    expected_release = (request.form.get("expected_release") or "").strip()
    alert_type = normalize_alert_type(request.form.get("alert_type"))
    auto_buy = 1 if (request.form.get("auto_buy") == "on") else 0
    product_type = (request.form.get("product_type") or "").strip()
    notes = (request.form.get("notes") or "").strip()

    if not product_name:
        flash("Please enter a product name.")
        return redirect(url_for("index"))

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO watchlist (
                product_name, retailer, product_url, store_location,
                target_price, expected_release, alert_type, auto_buy, product_type, notes, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'unknown')
            """,
            (
                product_name,
                retailer,
                product_url,
                store_location,
                target_price,
                expected_release,
                alert_type,
                auto_buy,
                product_type,
                notes,
            ),
        )
        conn.commit()

    flash("Product added to your watch list.")
    return redirect(url_for("index"))


@app.post("/watch/check")
def run_watch():
    watch_id = request.form.get("watch_id")
    if not watch_id:
        flash("No product selected.")
        return redirect(url_for("index"))

    result = run_watch_check(int(watch_id))
    flash(result["message"])
    return redirect(url_for("index"))


@app.get("/api/watchlist")
def api_watchlist():
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM watchlist ORDER BY created_at DESC").fetchall()
    return {"count": len(rows), "items": [decode_status(row) for row in rows]}


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
            FROM subscribers ORDER BY created_at DESC
            """
        ).fetchall()
        watchlist = conn.execute(
            "SELECT * FROM watchlist ORDER BY created_at DESC"
        ).fetchall()

    return render_template(
        "admin.html",
        subscribers=[serialize_subscriber(row) for row in subscribers],
        watchlist=[decode_status(row) for row in watchlist],
    )


@app.route("/admin/export")
def admin_export():
    admin_token = os.environ.get("ADMIN_TOKEN")
    provided_token = request.args.get("token")

    if admin_token and provided_token != admin_token:
        return "Unauthorized", 401

    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, email, phone, preferred_channel, product_interest, desired_set, max_msrp, alert_type, product_category, retailer, custom_search, created_at, updated_at FROM subscribers ORDER BY created_at DESC"
        ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "email", "phone", "preferred_channel", "product_interest", "desired_set", "max_msrp", "alert_type", "product_category", "retailer", "custom_search", "created_at", "updated_at"])
    for row in rows:
        writer.writerow([row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10], row[11], row[12], row[13]])

    return (output.getvalue(), 200, {"Content-Type": "text/csv", "Content-Disposition": "attachment; filename=subscribers.csv"})


@app.get("/health")
def health():
    return {"ok": True, "database": str(DB_PATH)}


if __name__ == "__main__":
    ensure_schema()
    app.run(host="0.0.0.0", port=5000, debug=True)
