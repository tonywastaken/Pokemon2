#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ProductWatch:
    name: str
    url: str
    retailer: str
    expected_release: str
    release_buffer_minutes: int = 30
    auto_buy: bool = False
    current_status: str = "unknown"
    last_seen_at: Optional[datetime] = None

    @property
    def expected_release_dt(self) -> datetime:
        return datetime.fromisoformat(self.expected_release.replace("Z", "+00:00"))


@dataclass
class StockEvent:
    product: ProductWatch
    status: str
    observed_at: datetime
    details: str
    release_window: bool = False


class StockMonitor:
    def __init__(self, timeout_seconds: int = 15):
        self.timeout_seconds = timeout_seconds
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        }

    def fetch_html(self, url: str) -> str:
        response = requests.get(url, headers=self.headers, timeout=self.timeout_seconds)
        response.raise_for_status()
        return response.text

    def detect_stock_status(self, html: str, retailer: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True).lower()

        if not text:
            return "unknown"

        in_stock_signals = [
            "add to cart",
            "add to bag",
            "buy now",
            "purchase now",
            "in stock",
            "available now",
            "ships immediately",
            "ships in stock",
        ]
        sold_out_signals = [
            "sold out",
            "out of stock",
            "unavailable",
            "not available",
            "notify me",
            "coming soon",
            "backorder",
        ]
        preorder_signals = [
            "pre-order",
            "preorder",
            "reserve now",
            "coming soon",
        ]

        if any(signal in text for signal in in_stock_signals):
            return "in_stock"
        if any(signal in text for signal in sold_out_signals):
            return "out_of_stock"
        if any(signal in text for signal in preorder_signals):
            return "preorder"
        if retailer and retailer.lower() in text:
            return "page_loaded"
        return "unknown"

    def evaluate_release_window(self, product: ProductWatch) -> bool:
        now = utc_now()
        release_time = product.expected_release_dt
        window_start = release_time - timedelta(minutes=product.release_buffer_minutes)
        window_end = release_time + timedelta(minutes=15)
        return window_start <= now <= window_end

    def build_event(self, product: ProductWatch, status: str, details: str) -> StockEvent:
        return StockEvent(
            product=product,
            status=status,
            observed_at=utc_now(),
            details=details,
            release_window=self.evaluate_release_window(product),
        )

    def poll_product(self, product: ProductWatch) -> StockEvent:
        try:
            html = self.fetch_html(product.url)
            status = self.detect_stock_status(html, product.retailer)

            if status == "in_stock":
                details = f"{product.name} is showing in stock or available to purchase."
            elif status == "out_of_stock":
                details = f"{product.name} is showing out of stock."
            elif status == "preorder":
                details = f"{product.name} is in a pre-order period."
            elif status == "page_loaded":
                details = f"{product.name} page loaded successfully, but the product state is not easy to interpret."
            else:
                details = f"{product.name} status is unclear from the current product page."

            event = self.build_event(product, status, details)
            product.current_status = status
            product.last_seen_at = event.observed_at
            return event
        except requests.RequestException as exc:
            event = self.build_event(product, "error", f"Request failed for {product.name}: {exc}")
            product.current_status = "error"
            product.last_seen_at = event.observed_at
            return event

    def maybe_auto_buy(self, product: ProductWatch, event: StockEvent) -> Optional[str]:
        if not product.auto_buy:
            return None
        if event.status != "in_stock":
            return None

        return (
            f"AUTO_BUY_TRIGGERED: {product.name} is in stock and matches the configured auto-buy policy. "
            "This path should only be used with retailer-approved APIs or explicit checkout automation."
        )

    def demo_run(self, products: list[ProductWatch]) -> None:
        for product in products:
            event = self.poll_product(product)
            print(f"[{event.observed_at.isoformat()}] {product.name} -> {event.status} | {event.details}")
            if event.release_window:
                print(f"Release window detected for {product.name}. Exact drop may be imminent.")

            auto_note = self.maybe_auto_buy(product, event)
            if auto_note:
                print(auto_note)


def load_products(path: str | Path) -> list[ProductWatch]:
    file_path = Path(path)
    raw = json.loads(file_path.read_text())
    return [ProductWatch(**item) for item in raw.get("products", [])]


def run_watch_loop(products: list[ProductWatch], interval_seconds: int, timeout: int) -> None:
    monitor = StockMonitor(timeout_seconds=timeout)

    print(f"Monitoring {len(products)} products every {interval_seconds} seconds.")
    while True:
        for product in products:
            event = monitor.poll_product(product)
            print(f"[{event.observed_at.isoformat()}] {product.name} -> {event.status} | {event.details}")
            if event.release_window:
                print(f"Release window detected for {product.name}. Stock should be watched closely.")

            auto_note = monitor.maybe_auto_buy(product, event)
            if auto_note:
                print(auto_note)

        time.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pokémon card stock checker and release watcher.")
    parser.add_argument("--products", default="products.json", help="JSON path containing watchlist entries.")
    parser.add_argument("--interval", type=int, default=60, help="Polling interval in seconds.")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout per request.")
    parser.add_argument("--demo", action="store_true", help="Run a single poll cycle against every product.")
    args = parser.parse_args()

    products = load_products(args.products)

    if args.demo:
        StockMonitor(timeout_seconds=args.timeout).demo_run(products)
        return

    run_watch_loop(products, args.interval, args.timeout)


if __name__ == "__main__":
    main()

