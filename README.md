# Pokemon2

This repo includes a Pokémon card stock checker and a small Flask signup site for people to join release/restock alerts.

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

## Notes

- The website saves signups in a local SQLite database: `subscribers.db`
- The alert form accepts email, phone number, preferred channel, and item interest
- The stock checker polls product pages and looks for stock/restock signals and release windows
- Auto-buy logic is intentionally disabled by default and should only be enabled when retailer-approved

## Example alert flow

The MVP is built for:

- collecting emails and phone numbers
- storing subscriber interest
- preparing for real restock/release alerts via email and SMS providers
- combining a stock monitor with a waiting list
