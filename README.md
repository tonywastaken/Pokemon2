# Pokemon2

This repo is a simple Pokémon card stock and release watcher website with a customizable buy-bot trigger.

GitHub repo: https://github.com/tonywastaken/Pokemon2

## Features

- simple website dashboard for card watch items
- product cards with stock/release status tags
- online product watch and local store watch support
- quick "Check now" action for each product
- configurable buy-bot settings with max price, retailer, product type, and quantity
- manual approval toggle so the trigger stays safe and controlled
- admin page and subscriber export

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

## Buy-bot safety

The buy-bot is intentionally customizable and guarded.

It is designed to be:

- editable by product type and retailer
- capped by max price and quantity
- able to require manual approval before firing
- safe by default so it does not blindly buy without rules

This keeps it practical and usable without making it a hidden or reckless checkout bot.

## Notes

- The stock checker uses page-content detection for product availability and release windows.
- A real retailer API or approved checkout flow should be plugged in if you want live purchasing automation.
