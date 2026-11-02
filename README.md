# Pokemon2

A simple Pokémon card stock checker and release monitor.

## What it does

- Watches retailer product pages for stock changes
- Detects likely restocks and pre-order status
- Identifies when a product is in its release window
- Can optionally trigger a guarded auto-buy path when the retailer supports it

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py --demo
```

## Configure products

Edit `products.json` with real retailer URLs and release times.

## Example run

```bash
python main.py --products products.json --interval 60
```

## Important

Auto-buy is disabled by default. Only enable it for retailer APIs or checkout flows you explicitly control and have permission to automate.
