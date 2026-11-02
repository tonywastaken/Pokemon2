# Pokemon2

This repo includes a Pokémon card stock checker and a Flask-based signup site where people can join release/restock alerts.

GitHub repo: https://github.com/tonywastaken/Pokemon2

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run the alert website

```bash
python app.py
```

Then open:

- http://localhost:5000

## Run the stock checker

```bash
python main.py --demo
```

## What users can customize

The signup form now supports:

- product interest, set name, or specific search term
- price target / max MSRP
- alert type: all drops, MSRP, set-focused, restock, release, or specific card
- preferred retailer or product category
- email + SMS preferences

This makes it useful for people who are only watching a specific set, price ceiling, or card type instead of every Pokémon release.

## Data storage

- local SQLite DB: `subscribers.db`
- the admin view shows all tracked preferences for each signup

## Notes

- The stock checker polls retailer pages and looks for stock/restock signals and release windows
- Auto-buy logic is intentionally disabled by default and should only be enabled with retailer-approved automation
