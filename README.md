# Pokemon2

This repo is a simple Pokémon card monitoring and buying-helper site.

GitHub repo: https://github.com/tonywastaken/Pokemon2

## Features

- simple storefront / product watch page
- product entry for online and in-store tracking
- release-window monitoring for upcoming drops
- stock status detection for online listings
- safe auto-buy toggle that is intentionally blocked unless the retailer has an approved checkout flow
- subscriber signup for alerts
- admin dashboard + CSV export

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Then open:

- http://localhost:5000
- http://localhost:5000/admin

## What this is designed to do

This is intentionally simple and practical:

- watch a product before a release happens
- check for stock when it goes live
- watch for in-store availability for local shop pickups
- flag likely restocks and early release windows
- enable a guarded auto-buy trigger only when the retailer allows it

## Important note

The auto-buy function is not a real checkout bot by default. It only simulates a trigger and is meant to be replaced with retailer-approved automation logic.
