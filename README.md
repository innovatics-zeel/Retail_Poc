# Innovatics — Program 1: Product & Market Intelligence

> POC · Apparel-First · US Marketplace Intelligence  
> Stack: **Python · Playwright · PostgreSQL (local) · Streamlit**

---

## One-time Local Setup

### 1. PostgreSQL — create the database in pgAdmin

Open **pgAdmin 4** on your machine and run this in the Query Tool:

```sql
CREATE DATABASE Innovatics_Retail;
```

That's it. The migration script creates all tables automatically on first run.

---

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` and fill in **only these two lines** with your local credentials:

```env
DB_USER=postgres          # your pgAdmin username
DB_PASSWORD=your_password # your pgAdmin password
```

Leave everything else as-is unless your PostgreSQL runs on a different port.

---

### 3. Python environment

```bash
python -m venv venv

# Mac / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium
```

---

### 4. Run the scraper

```bash
python scrape_runner.py
```

This will:
1. Connect to your local `innovatics_p1` database
2. Create all 4 tables automatically (safe to re-run)
3. Scrape Amazon + Nordstrom for Men's T-shirts and Women's Casual Dresses
4. Validate and store everything in PostgreSQL

---

## Project Structure

```
innovatics-p1-market-intelligence/
│
├── .env                        ← your local secrets (gitignored)
├── .env.example                ← template — commit this
├── requirements.txt
├── scrape_runner.py            ← RUN THIS to start scraping
│
├── config/
│   └── settings.py             ← all env vars, single DB URL
│
├── scraper/
│   ├── base_scraper.py         ← shared Playwright session
│   ├── amazon_scraper.py       ← Amazon search + product pages
│   ├── nordstrom_scraper.py    ← Nordstrom search + product pages
│   ├── attribute_parser.py     ← color / material / fit extraction
│   └── schemas.py              ← Pydantic validation models
│
├── database/
│   ├── connection.py           ← SQLAlchemy engine + migrations runner
│   ├── models.py               ← ORM models for all 4 tables
│   └── migrations/
│       ├── 001_create_sku_listings.sql
│       ├── 002_create_sku_attributes.sql
│       ├── 003_create_price_snapshots.sql
│       └── 004_create_review_signals.sql
│
├── pipeline/
│   └── ingest.py               ← validates + upserts to PostgreSQL
│
└── tests/
    └── fixtures/               ← sample HTML for unit tests
```

---

## Database Tables

| Table | What it stores |
|---|---|
| `sku_listings` | Core product — platform, SKU ID, title, brand, category |
| `sku_attributes` | Color, material, fit, neck type, sleeve type, gender |
| `price_snapshots` | Price per scrape with auto price-band assignment |
| `review_signals` | Rating, review count, velocity delta per scrape |

---

## Verify in pgAdmin

After running the scraper, open pgAdmin and run:

```sql
-- Check record counts
SELECT platform, category, COUNT(*) as products
FROM sku_listings
GROUP BY platform, category
ORDER BY platform, category;

-- Check latest prices
SELECT l.title, l.platform, p.price, p.price_band, p.snapshot_at
FROM sku_listings l
JOIN price_snapshots p ON p.listing_id = l.id
ORDER BY p.snapshot_at DESC
LIMIT 20;

-- Check attribute breakdown
SELECT color_family, COUNT(*) as count
FROM sku_attributes
GROUP BY color_family
ORDER BY count DESC;
```

---

## Notes

- All scraped data is tagged `data_label = 'demonstration_data'`
- No proxies needed — Playwright runs as a real browser with realistic headers
- If Amazon shows a CAPTCHA, the scraper skips that page and continues
- Re-running the scraper is safe — it upserts, never duplicates
