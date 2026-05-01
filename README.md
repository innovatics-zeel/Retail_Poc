# Innovatics — Program 1: Product & Market Intelligence

> **Architecture POC** · Apparel-First · US Marketplace Intelligence
> No live API keys or production data included — this repository demonstrates the full system design.
> Stack: **Python · Playwright/Camoufox · PostgreSQL · Streamlit · Claude AI**

---

## Overview

A modular, registry-driven intelligence platform for US apparel marketplaces (Nordstrom, Amazon).
The system scrapes product data, stores it in a unified PostgreSQL schema, and surfaces four layers
of business intelligence through a Streamlit dashboard powered by Claude AI.

### Four Intelligence Layers

| Layer | What it does |
|---|---|
| **Descriptive** | KPI cards, price/rating histograms, attribute breakdowns, platform comparison |
| **Conversational** | Natural-language Q&A over live product data via Claude API |
| **Predictive** | 4-week trend forecasts for price, demand signals, and top attributes |
| **Recommendations** | AI-generated ranked buying/sourcing recommendations with accept/modify/dismiss feedback loop |

---

## Project Structure

```
retail/
│
├── .env                         ← your local secrets (gitignored)
├── .env.example                 ← template — commit this
├── requirements.txt
├── scrape_runner.py             ← run to trigger scrapers manually
├── scheduler.py                 ← APScheduler — weekly cron every Sunday 02:00 ET
│
├── config/
│   └── settings.py              ← all env vars loaded from .env
│
├── scraper/
│   ├── base_scraper.py          ← shared Playwright/camoufox session
│   ├── registry.py              ← auto-discovers *_scraper.py, builds (platform, category) lookup
│   ├── nordstrom_scraper.py     ← Nordstrom men's T-shirts
│   ├── nordstrom_womens_dress_scraper.py  ← Nordstrom women's dresses
│   └── schemas.py               ← Pydantic validation models
│
├── database/
│   ├── connection.py            ← SQLAlchemy engine + SessionLocal
│   ├── models.py                ← unified Product + RecommendationFeedback ORM models
│   └── alembic/
│       └── versions/            ← migration history
│
├── pipeline/
│   └── ingest.py                ← registry-driven upsert — no hardcoded category branching
│
└── streamlit_app/
    ├── app.py                   ← single entry point, 4 st.tabs()
    └── db.py                    ← all DB query helpers (returns plain dicts / DataFrames)
```

---

## Database Schema

### `products` — unified table for all platforms and categories

| Column | Type | Notes |
|---|---|---|
| `id` | Integer PK | |
| `platform` | String(50) | `nordstrom`, `amazon`, … |
| `platform_id` | Integer | internal platform FK if applicable |
| `url` | Text UNIQUE | canonical product URL |
| `asin` | String(20) | Amazon only |
| `title` | Text | |
| `brand` | String(200) | |
| `category` | String(100) | `mens_tshirts`, `womens_dresses`, … |
| `gender` | String(30) | |
| `current_price` | Numeric(10,2) | flat column for fast SQL aggregation |
| `original_price` | Numeric(10,2) | |
| `discount_percent` | Numeric(5,2) | |
| `rating` | Numeric(3,2) | |
| `review_count` | Integer | |
| `attributes_json` | Text | JSON blob: color, size, material, fit, pattern, … |
| `price_json` | Text | JSON blob: price_text, discount_text, stock_variants |
| `review_json` | Text | JSON blob: fit, star_distribution, pros, cons |
| `raw_json` | Text | full raw scrape payload |
| `data_label` | String(100) | default `demonstration_data` |
| `scraped_at` | DateTime | auto server default |
| `updated_at` | DateTime | auto-updated on upsert |

### `recommendation_feedback`

Stores user accept / modify / dismiss actions from the Streamlit Recommendations tab.

| Column | Type |
|---|---|
| `id` | Integer PK |
| `recommendation_text` | Text |
| `category` | String(100) |
| `action` | String(20) — `accept` / `modify` / `dismiss` |
| `modified_text` | Text |
| `created_at` | DateTime |

---

## Tech Stack

| Component | Library | Version |
|---|---|---|
| Browser automation | Playwright / camoufox / patchright | latest |
| Data validation | Pydantic v2 | |
| ORM | SQLAlchemy 2 | |
| Migrations | Alembic | |
| Database | PostgreSQL (local) | |
| Scheduling | APScheduler | 3.10.4 |
| Dashboard | Streamlit | 1.35.0 |
| Charts | Plotly | 5.22.0 |
| AI layer | Anthropic Python SDK | 0.28.0 |
| Forecasting | NumPy / scikit-learn / statsmodels | |

---

## Registry Pattern — Adding a New Scraper

Every `*_scraper.py` file in `scraper/` is auto-discovered at startup. To add a new platform/category:

1. Create `scraper/mynewsite_scraper.py`
2. Define these class-level attributes:

```python
class MyNewSiteScraper(BaseScraper):
    PLATFORM     = "mynewsite"
    CATEGORY     = "my_category"
    SCHEMA_CLASS = MyProductSchema   # Pydantic model
    DB_MODEL     = Product           # always Product

    @staticmethod
    def to_db_values(data: MyProductSchema) -> dict:
        # build and return the unified dict for Product upsert
        ...
```

3. No changes needed anywhere else — `ingest.py` and `scrape_runner.py` pick it up automatically.

---

## Setup (when ready to run)

> **This is an architecture POC. No scraping keys, proxy credentials, or production data are included.**
> Follow these steps when you are ready to connect real infrastructure.

### 1. PostgreSQL — create the database

```sql
CREATE DATABASE innovatics_retail;
```

### 2. Environment variables

```bash
cp .env.example .env
```

`.env.example` template:

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=innovatics_retail
DB_USER=postgres
DB_PASSWORD=your_password

ANTHROPIC_API_KEY=sk-ant-...    # required for Conversational + Recommendations tabs
```

### 3. Python environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
camoufox fetch                  # downloads camoufox browser binary
```

### 4. Run database migration

```bash
alembic upgrade head
```

This creates the `products` and `recommendation_feedback` tables.

### 5. Run a manual scrape

```bash
python scrape_runner.py
```

### 6. Start the Streamlit dashboard

```bash
streamlit run streamlit_app/app.py
```

### 7. Start the weekly scheduler (optional, background process)

```bash
python scheduler.py
```

Runs every Sunday at 02:00 AM ET. Safe to run as a `systemd` service or Docker container.

---

## Verify data in pgAdmin

```sql
-- Record counts by platform and category
SELECT platform, category, COUNT(*) AS products
FROM products
GROUP BY platform, category
ORDER BY platform, category;

-- Top-rated products
SELECT title, brand, platform, current_price, rating, review_count
FROM products
WHERE is_active = TRUE
ORDER BY rating DESC NULLS LAST
LIMIT 20;

-- Feedback summary
SELECT action, COUNT(*) AS count
FROM recommendation_feedback
GROUP BY action;
```

---

## Known Limitations (POC Scope)

- **Single IP / no proxy rotation** — suitable for low-volume demos; production would need rotating residential proxies
- **Synthetic historical data** — the Predictive tab generates 13 weeks of synthetic history with NumPy until multiple real scrape runs have accumulated
- **No authentication** — Streamlit app is unauthenticated; add `streamlit-authenticator` for multi-user deployments
- **Local PostgreSQL only** — production path is RDS or Cloud SQL with connection pooling (PgBouncer)
- **Claude API costs** — Conversational and Recommendations tabs call Claude on every interaction; add `st.cache_data` TTLs or a prompt cache layer for cost control at scale

---

## Notes

- All scraped records are tagged `data_label = 'demonstration_data'` to clearly distinguish POC data from production
- Re-running the scraper is safe — `ingest.py` upserts by URL, never duplicates
- The registry in `scraper/registry.py` scans for `*_scraper.py` at import time — no manual registration required
