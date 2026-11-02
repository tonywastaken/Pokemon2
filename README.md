# Pokemon2

This repo includes a Pokémon card stock checker and a Flask-based waiting list for release/restock alerts.

GitHub repo: https://github.com/tonywastaken/Pokemon2

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run the alert site

```bash
python app.py
```

Then open:

- http://localhost:5000

## Admin dashboard

Use the admin view to review subscribers:

- http://localhost:5000/admin

Optionally protect it with an environment variable:

```bash
export ADMIN_TOKEN=supersecret
```

Then open:

- http://localhost:5000/admin?token=supersecret

CSV export:

- http://localhost:5000/admin/export?token=supersecret

## Run the stock checker

```bash
python main.py --demo
```

## What users can customize

The signup form supports:

- product interest, set name, or specific search term
- price target / max MSRP
- alert type: all, release, restock, set-based, MSRP, or specific card
- preferred retailer or product category
- email + SMS preferences

This makes it useful for collectors who only care about specific sets, price ceilings, or product categories rather than every Pokémon release.

## Data storage

- local SQLite DB: `subscribers.db`
- admin view shows all tracked preferences
- `/api/subscribers` exposes the same data in JSON for easy integration

## Production notes

- the stock checker polls retailer pages for stock/restock signals and release windows
- auto-buy logic is intentionally disabled by default and should only be enabled with retailer-approved automation
- the app is ready to be extended with Twilio, SendGrid, or a hosted database later
