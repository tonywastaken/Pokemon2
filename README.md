# Pokemon2

This repo now includes two parts:

1. A Python stock-checker for Pokémon card retailers
2. A simple web app where people can sign up for release and restock alerts by email and phone

## Run the web app

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Then open:

- http://localhost:5000

## Run the stock checker

```bash
python main.py --demo
```

## Configure the web signup

The app stores signups in a local SQLite database named `subscribers.db`. It accepts:

- email address
- phone number
- preferred notification method (`email`, `sms`, or `both`)
- product interest

This is a good MVP for collecting signup intent before wiring in a real notification provider.

## Optional production upgrades

- email delivery via SendGrid / Postmark / SMTP
- SMS delivery via Twilio
- admin dashboard for viewing signups
- product watchlist synced with subscriber interest
- scheduled alerts when stock changes or a release window opens
