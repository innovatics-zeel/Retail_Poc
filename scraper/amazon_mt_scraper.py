"""
amazon_scraper.py
Scrapes Amazon Men's T-Shirts and upserts directly into amazon_mens_tshirts.

Run:
    python3 scraper/amazon_scraper.py --max-products 100

Notes:
    - attributes_json, variants_json, and reviews_json are stored as single
      serialized JSON columns.
    - A crash-safe JSONL copy is written to data/amazon_mt_DDMMYY_HHMMSS.jsonl.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from bs4 import BeautifulSoup
from loguru import logger
from playwright.async_api import (
    Browser,
    BrowserContext,
    Error as PlaywrightError,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)
from sqlalchemy import or_
from sqlalchemy.orm import Session

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - keeps scraper runnable if tqdm is absent.
    tqdm = None

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config.settings import settings
from database.connection import SessionLocal
from database.models import AmazonMensTshirt


LISTING_URL = "https://www.amazon.com/s?k=men+tshirt&i=fashion-mens&rh=n%3A7141123011%2Cn%3A7147441011%2Cn%3A1040658%2Cn%3A15697821011&dc&ds=v1%3A%2BxTPWgCBnr0P2o83YbUJ5lGxLw4xkap2i8w1D6fHlNs&crid=1615ED0Q0I2CX&qid=1777382089&rnid=1040658&sprefix=men+tshirt%2Cfashion-mens%2C391&ref=sr_nr_n_14"
ZIP_CODE = "60601"
CANONICAL_DP = "https://www.amazon.com/dp/{asin}"
POC_RUN_ID = datetime.now().strftime("amazon_mt_%d%m%y_%H%M%S")
DATA_DIR = Path(__file__).resolve().parents[1] / "data"

ATTRIBUTE_MAP = {
    "occasion type": "occasion",
    "occasion": "occasion",
    "apparel silhouette": "apparel_silhouette",
    "neck style": "neck_style",
    "sleeve type": "sleeve_type",
    "season": "seasons",
    "seasons": "seasons",
    "style name": "style",
    "style": "style",
    "apparel closure type": "closure",
    "closure type": "closure",
    "closure": "closure",
    "back style": "back_style",
    "strap type": "strap_type",
    "pattern": "pattern",
    "collar-type": "collar_type",
    "collar type": "collar_type",
    "fit type": "fit_type",
    "fit": "fit_type",
    "material type": "material_type",
}


@dataclass
class ScrapeConfig:
    max_products: Optional[int] = None
    max_pages: Optional[int] = None
    headless: bool = settings.scraper_headless
    timeout_ms: int = settings.scraper_timeout
    max_retries: int = settings.scraper_max_retries
    slow_mo: int = settings.scraper_slow_mo


class JsonlWriter:
    """Append-safe product payload writer."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict[str, Any]) -> None:
        jsonl_record = dict(record)
        for key in ("variants_json", "attributes_json", "reviews_json", "raw_attributes_json"):
            jsonl_record.pop(key, None)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(jsonl_record, ensure_ascii=True, default=str))
            fh.write("\n")
            fh.flush()


class AmazonTshirtRepository:
    """Small DB service for safe AmazonMensTshirt upserts."""

    def __init__(self):
        self.db: Session = SessionLocal()

    def close(self) -> None:
        self.db.close()

    def upsert(self, payload: dict[str, Any]) -> None:
        asin = payload.get("asin")
        url = payload.get("url")
        filters = [AmazonMensTshirt.url == url]
        if asin:
            filters.append(AmazonMensTshirt.asin == asin)
        product = self.db.query(AmazonMensTshirt).filter(or_(*filters)).first()

        values = {
            "platform": payload["platform"],
            "url": payload["url"],
            "title": payload["title"],
            "brand": payload.get("brand"),
            "asin": asin,
            "category": payload["category"],
            "gender": payload["gender"],
            "unit_count": payload["unit_count"],
            "variants_json": payload["variants_json"],
            "attributes_json": payload["attributes_json"],
            "reviews_json": payload["reviews_json"],
            "raw_attributes_json": payload["raw_attributes_json"],
            "data_label": payload["data_label"],
            "poc_run_id": payload["poc_run_id"],
            "is_active": True,
        }

        try:
            if product:
                for key, value in values.items():
                    setattr(product, key, value)
                logger.debug(f"[DB] Updated ASIN={asin} URL={url}")
            else:
                self.db.add(AmazonMensTshirt(**values))
                logger.debug(f"[DB] Inserted ASIN={asin} URL={url}")
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise


class AmazonMensTshirtsScraper:
    PLATFORM = "amazon"

    def __init__(self, config: ScrapeConfig):
        self.config = config
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.repo = AmazonTshirtRepository()
        self.writer = JsonlWriter(DATA_DIR / f"{POC_RUN_ID}.jsonl")
        self.saved = 0
        self.failed = 0

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.stop()
        self.repo.close()

    async def start(self) -> None:
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.config.headless,
            slow_mo=self.config.slow_mo,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
            ],
        )
        self.context = await self.browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 950},
            locale="en-US",
            timezone_id="America/Chicago",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "DNT": "1",
            },
        )
        await self.context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        await self.context.route(
            "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,otf}",
            lambda route: route.abort(),
        )
        logger.info(f"[BROWSER] Started Amazon scraper headless={self.config.headless}")

    async def stop(self) -> None:
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("[BROWSER] Stopped")

    async def restart_browser(self) -> None:
        logger.warning("[BROWSER] Restarting browser context after recoverable failure")
        await self.stop()
        await asyncio.sleep(2)
        await self.start()

    async def new_page(self) -> Page:
        page = await self.context.new_page()
        page.set_default_timeout(self.config.timeout_ms)
        return page

    async def run(self) -> dict[str, int | str]:
        listing_page = await self.new_page()
        try:
            await self.safe_goto(listing_page, LISTING_URL)
            await self.change_region_to_usa(listing_page)
            total_pages = await self.detect_total_pages(listing_page)
            pages_to_scrape = total_pages
            if self.config.max_pages:
                pages_to_scrape = min(pages_to_scrape, self.config.max_pages)

            product_urls = await self.collect_product_urls(listing_page, pages_to_scrape)
        finally:
            await listing_page.close()

        if self.config.max_products:
            product_urls = product_urls[: self.config.max_products]

        logger.info(f"[INFO] Unique product URLs queued: {len(product_urls)}")
        item_bar = self._progress(total=len(product_urls), desc=f"Item (1/{len(product_urls)})")
        for index, url in enumerate(product_urls, start=1):
            if item_bar:
                item_bar.set_description(f"Item ({index}/{len(product_urls)})")
            try:
                payload = await self.scrape_product_with_recovery(url)
                if not payload:
                    self.failed += 1
                    continue
                self.repo.upsert(payload)
                self.writer.append(payload)
                self.saved += 1
            except Exception as exc:
                self.failed += 1
                logger.exception(f"[PRODUCT] Failed {url}: {exc}")
            finally:
                if item_bar:
                    item_bar.update(1)
                await self.polite_delay()
        if item_bar:
            item_bar.close()

        return {
            "queued": len(product_urls),
            "saved": self.saved,
            "failed": self.failed,
            "jsonl_path": str(self.writer.path),
        }

    async def safe_goto(self, page: Page, url: str) -> None:
        last_error = None
        for attempt in range(1, self.config.max_retries + 1):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=self.config.timeout_ms)
                await self.detect_captcha(page, raise_on_block=True)
                return
            except Exception as exc:
                last_error = exc
                logger.warning(f"[NAV] Attempt {attempt}/{self.config.max_retries} failed: {url} -> {exc}")
                await asyncio.sleep(2 * attempt)
        raise RuntimeError(f"Could not load {url}") from last_error

    async def change_region_to_usa(self, page: Page) -> None:
        if await self.region_is_confirmed(page):
            logger.info("[INFO] Region changed successfully to USA (60601)")
            return

        for attempt in range(1, self.config.max_retries + 1):
            try:
                if not await self.ensure_amazon_header_ready(page):
                    raise RuntimeError("Amazon header/location selector did not appear after hard reloads")

                await page.locator("#nav-global-location-popover-link").click(timeout=15000)
                zip_input = page.locator("#GLUXZipUpdateInput")
                await zip_input.wait_for(state="visible", timeout=15000)
                await zip_input.fill(ZIP_CODE)
                await page.locator("#GLUXZipUpdate").click(timeout=10000)
                await self.handle_delivery_continue_modal(page)
                done_button = page.locator('button[name="glowDoneButton"], button.a-button-text[name="glowDoneButton"]')
                try:
                    await done_button.click(timeout=10000)
                except PlaywrightTimeoutError:
                    logger.debug("[REGION] Done button not shown; continuing to verification")
                await self.handle_delivery_continue_modal(page)
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                await page.reload(wait_until="domcontentloaded", timeout=self.config.timeout_ms)
                await self.handle_delivery_continue_modal(page)
                if await self.region_is_confirmed(page):
                    logger.info("[INFO] Region changed successfully to USA (60601)")
                    return
            except Exception as exc:
                logger.warning(f"[REGION] Attempt {attempt}/{self.config.max_retries} failed: {exc}")
                await asyncio.sleep(2 * attempt)
        raise RuntimeError("Could not confirm Amazon delivery region as USA (60601)")

    async def ensure_amazon_header_ready(self, page: Page) -> bool:
        header_selectors = [
            "#nav-global-location-popover-link",
            "#nav-logo-sprites",
            "#navbar",
        ]
        for reload_attempt in range(4):
            for selector in header_selectors:
                try:
                    locator = page.locator(selector).first
                    await locator.wait_for(state="attached", timeout=5000)
                    return True
                except Exception:
                    continue

            if reload_attempt < 3:
                logger.warning(f"[REGION] Amazon header missing; hard reload {reload_attempt + 1}/3")
                try:
                    await page.reload(wait_until="domcontentloaded", timeout=self.config.timeout_ms)
                    await self.detect_captcha(page, raise_on_block=True)
                    await self.handle_delivery_continue_modal(page)
                except Exception as exc:
                    logger.debug(f"[REGION] Hard reload failed: {exc}")
                await page.wait_for_timeout(1000)

        return False

    async def region_is_confirmed(self, page: Page) -> bool:
        try:
            location_text = await page.locator("#glow-ingress-line2").inner_text(timeout=8000)
            return ZIP_CODE in normalize_space(location_text) or "Chicago" in location_text
        except Exception:
            return False

    async def handle_delivery_continue_modal(self, page: Page) -> bool:
        selectors = [
            'input[aria-labelledby*="Continue"]',
            'span.a-button:has-text("Continue") input',
            'button:has-text("Continue")',
            'input[type="submit"][value="Continue"]',
            'text="Continue"',
        ]
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.count() == 0:
                    continue
                if not await locator.is_visible(timeout=1500):
                    continue
                await locator.click(timeout=3000, force=True)
                await page.wait_for_timeout(500)
                logger.debug("[REGION] Delivery confirmation Continue button clicked")
                return True
            except Exception:
                continue
        return False

    async def detect_total_pages(self, page: Page) -> int:
        await self.scroll_to_bottom(page)
        soup = BeautifulSoup(await page.content(), "lxml")
        container = soup.select_one(".s-pagination-container") or soup.select_one('div[aria-label="pagination"]')
        numbers: list[int] = []
        if container:
            for node in container.select(".s-pagination-item.s-pagination-disabled, .s-pagination-item"):
                text = normalize_space(node.get_text(" "))
                if text.isdigit():
                    numbers.append(int(text))
        total_pages = max(numbers) if numbers else 1
        logger.info(f"[INFO] Total pages detected: {total_pages}")
        return total_pages

    async def collect_product_urls(self, page: Page, total_pages: int) -> list[str]:
        seen: set[str] = set()
        urls: list[str] = []
        page_bar = self._progress(total=total_pages, desc=f"Page (1/{total_pages})")

        for page_number in range(1, total_pages + 1):
            if page_number > 1:
                await self.safe_goto(page, listing_page_url(page_number))
                await self.scroll_to_bottom(page)
            if page_bar:
                page_bar.set_description(f"Page ({page_number}/{total_pages})")

            page_urls = self.extract_product_urls(await page.content())
            logger.info(f"[LISTING] Page {page_number}/{total_pages}: {len(page_urls)} valid URLs")
            for url in page_urls:
                if url not in seen:
                    seen.add(url)
                    urls.append(url)
                    if self.config.max_products and len(urls) >= self.config.max_products:
                        break
            if page_bar:
                page_bar.update(1)
            if self.config.max_products and len(urls) >= self.config.max_products:
                break
            await self.polite_delay()

        if page_bar:
            page_bar.close()
        return urls

    def extract_product_urls(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "lxml")
        urls: list[str] = []
        for card in soup.select('div[data-component-type="s-search-result"], div.s-result-item[data-asin]'):
            asin = (card.get("data-asin") or "").strip()
            if not valid_asin(asin):
                continue
            if is_sponsored_card(card):
                continue

            links = card.select("h2 a.a-link-normal, a.a-link-normal.s-link-style.a-text-normal")
            for link in links:
                href = link.get("href")
                canonical = canonicalize_amazon_url(href, fallback_asin=asin)
                if canonical:
                    urls.append(canonical)

        return list(dict.fromkeys(urls))

    async def scrape_product_with_recovery(self, url: str) -> Optional[dict[str, Any]]:
        last_error = None
        for attempt in range(1, self.config.max_retries + 1):
            page = await self.new_page()
            try:
                await self.safe_goto(page, url)
                payload = await self.scrape_product(page, url)
                await page.close()
                return payload
            except CaptchaDetected:
                await page.close()
                last_error = "captcha"
                logger.error(f"[CAPTCHA] Captcha detected for {url}")
                if attempt == self.config.max_retries:
                    return None
                await self.restart_browser()
            except (PlaywrightTimeoutError, PlaywrightError, RuntimeError) as exc:
                await safe_close(page)
                last_error = exc
                logger.warning(f"[PRODUCT] Attempt {attempt}/{self.config.max_retries} failed for {url}: {exc}")
                if attempt == self.config.max_retries:
                    return None
                if attempt % 2 == 0:
                    await self.restart_browser()
                await asyncio.sleep(2 * attempt)
        logger.warning(f"[PRODUCT] Giving up {url}: {last_error}")
        return None

    async def scrape_product(self, page: Page, url: str) -> dict[str, Any]:
        await page.locator("span#productTitle").wait_for(state="visible", timeout=20000)
        await self.detect_captcha(page, raise_on_block=True)

        title = clean_text(await first_text(page, ["span#productTitle"]))
        if not title:
            raise RuntimeError("Missing product title")

        asin = await self.extract_asin(page, url)
        if not asin:
            raise RuntimeError("Missing ASIN")
        canonical_url = CANONICAL_DP.format(asin=asin)

        brand = await self.extract_brand(page)
        attributes, raw_attributes = await self.extract_attributes(page)
        reviews = await self.extract_reviews(page)
        variants = await self.extract_variants(page)

        unit_raw = raw_attributes.get("Unit Count") or raw_attributes.get("Number of Items")
        unit_count = 1
        if unit_raw:
            match = re.search(r"\d+", str(unit_raw))
            if match:
                unit_count = int(match.group(0))
        if unit_count <= 0:
            unit_count = 1

        return {
            "platform": "amazon",
            "url": canonical_url,
            "title": title,
            "brand": brand,
            "asin": asin,
            "category": "men_tshirts",
            "gender": "men",
            "unit_count": unit_count,
            "variants": variants,
            "attributes": attributes,
            "reviews": reviews,
            "variants_json": json.dumps(variants, ensure_ascii=True),
            "attributes_json": json.dumps(attributes, ensure_ascii=True),
            "reviews_json": json.dumps(reviews, ensure_ascii=True),
            "raw_attributes_json": json.dumps(raw_attributes, ensure_ascii=True),
            "data_label": "demonstration_data",
            "poc_run_id": POC_RUN_ID,
            "is_active": True,
            "scraped_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }

    async def extract_asin(self, page: Page, url: str) -> Optional[str]:
        asin = asin_from_url(url)
        if asin:
            return asin
        soup = BeautifulSoup(await page.content(), "lxml")
        for row in soup.select("tr"):
            label = normalize_space(row.select_one("th, td.a-color-secondary").get_text(" ") if row.select_one("th, td.a-color-secondary") else "")
            value_node = row.select_one("td, td.a-size-base")
            value = normalize_space(value_node.get_text(" ") if value_node else "")
            if "asin" == label.lower() and valid_asin(value):
                return value
        match = re.search(r'"asin"\s*:\s*"([A-Z0-9]{10})"', await page.content())
        return match.group(1) if match else None

    async def extract_brand(self, page: Page) -> Optional[str]:
        soup = BeautifulSoup(await page.content(), "lxml")
        for row in soup.select("tr"):
            label_node = row.select_one("th, td.a-color-secondary")
            value_node = row.select_one("td, td.a-size-base")
            label = normalize_space(label_node.get_text(" ") if label_node else "")
            value = clean_text(value_node.get_text(" ") if value_node else "")
            if label.lower() in {"brand", "brand name"} and value:
                return value
        byline = clean_text(await first_text(page, ["#bylineInfo"]))
        byline = re.sub(r"^(visit the|brand:|store:)\s+", "", byline, flags=re.I)
        byline = re.sub(r"\s+store$", "", byline, flags=re.I)
        return byline or None

    async def extract_attributes(self, page: Page) -> tuple[dict[str, Any], dict[str, str]]:
        await self.open_all_specifications(page)
        soup = BeautifulSoup(await page.content(), "lxml")
        container = soup.select_one("#voyager-ns-desktop-side-sheet-main-section") or soup
        raw: dict[str, str] = {}

        for row in container.select("table.prodDetTable tr, #productDetails_detailBullets_sections1 tr, tr"):
            label_node = row.select_one("th.prodDetSectionEntry, th, td.a-color-secondary")
            value_node = row.select_one("td.prodDetAttrValue, td")
            if not label_node or not value_node:
                continue
            label = normalize_space(label_node.get_text(" "))
            value = clean_text(value_node.get_text(" "))
            if label and value and label.lower() != value.lower():
                raw[label] = value

        attributes: dict[str, Any] = {}
        for label, value in raw.items():
            key = ATTRIBUTE_MAP.get(normalize_key(label))
            if key:
                attributes[key] = split_attribute_value(value)

        return attributes, raw

    async def open_all_specifications(self, page: Page) -> None:
        selectors = [
            "a#a-autoid-7-announce",
            "#a-autoid-7",
            'a:has-text("See all product specifications")',
            'span:has-text("See all product specifications")',
        ]
        for selector in selectors:
            try:
                locator = page.locator(selector).first
                if await locator.count() == 0:
                    continue
                await locator.click(timeout=5000)
                await page.locator("#voyager-ns-desktop-side-sheet-main-section, table.prodDetTable").wait_for(
                    state="attached",
                    timeout=10000,
                )
                return
            except Exception:
                continue

    async def extract_variants(self, page: Page) -> list[dict[str, Any]]:
        colors = await self.dimension_options(page, "color_name")
        if not colors:
            colors = [{"name": await selected_dimension_text(page, "color_name"), "index": None}]

        variants: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for color in colors:
            await self.click_dimension(page, "color_name", color)
            await self.wait_after_variant_change(page)
            sizes_for_color = await self.dimension_options(page, "size_name")
            if not sizes_for_color:
                sizes_for_color = [{"name": await selected_dimension_text(page, "size_name"), "index": None}]

            for size in sizes_for_color:
                await self.click_dimension(page, "size_name", size)
                await self.wait_after_variant_change(page)
                price = await self.extract_price_snapshot(page)
                color_name = color.get("name") or await selected_dimension_text(page, "color_name")
                size_name = size.get("name") or await selected_dimension_text(page, "size_name")
                key = (color_name or "", size_name or "")
                if key in seen:
                    continue
                seen.add(key)
                variants.append(
                    {
                        "color": color_name,
                        "size": size_name,
                        "current_price": format_money(price["current_price"]),
                        "original_price": format_money(price["original_price"]),
                        "discount_price": format_money(price["discount_price"]),
                        "discount_percent": price["discount_percent"],
                        "currency": "USD",
                    }
                )
        return variants

    async def dimension_options(self, page: Page, dimension: str) -> list[dict[str, Any]]:
        selectors = dimension_selectors(dimension)
        options: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for selector in selectors:
            locators = page.locator(selector)
            count = await locators.count()
            for index in range(count):
                item = locators.nth(index)
                try:
                    classes = await item.get_attribute("class") or ""
                    disabled = await item.get_attribute("aria-disabled")
                    if "unavailable" in classes.lower() or "a-button-unavailable" in classes.lower():
                        continue
                    if disabled and disabled.lower() == "true":
                        continue
                    asin = await item.get_attribute("data-asin")
                    name = clean_text(await option_name(item))
                    key = (name.lower(), asin or "")
                    if key in seen:
                        continue
                    seen.add(key)
                    options.append({"name": name, "index": index, "asin": asin, "selector": selector})
                except Exception:
                    continue
        return [option for option in options if option.get("name") or option.get("asin")]

    async def click_dimension(self, page: Page, dimension: str, option: dict[str, Any]) -> None:
        if option.get("index") is None:
            return
        if option.get("asin"):
            try:
                asin_item = page.locator(f'li[data-asin="{option["asin"]}"]').first
                if await asin_item.count():
                    clickable = asin_item.locator("input[name], button, a").first
                    if await clickable.count():
                        await clickable.click(timeout=5000, force=True)
                    else:
                        await asin_item.click(timeout=5000, force=True)
                    return
            except Exception:
                pass

        selectors = [option.get("selector")] if option.get("selector") else dimension_selectors(dimension)
        for selector in selectors:
            if not selector:
                continue
            try:
                item = page.locator(selector).nth(option["index"])
                if await item.count() == 0:
                    continue
                clickable = item.locator("input[name], button, a").first
                if await clickable.count():
                    await clickable.click(timeout=5000, force=True)
                else:
                    await item.click(timeout=5000, force=True)
                return
            except Exception:
                continue

    async def wait_after_variant_change(self, page: Page) -> None:
        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            await page.wait_for_timeout(400)

    async def extract_price_snapshot(self, page: Page) -> dict[str, Optional[float]]:
        current_text = await first_text(
            page,
            [
                "#apex-desktop span.a-price.aok-align-center.apex-pricetopay-value span.a-offscreen",
                "span.apex-pricetopay-value span.a-offscreen",
                "#corePriceDisplay_desktop_feature_div span.apex-pricetopay-value span.a-offscreen",
                "#corePriceDisplay_desktop_feature_div span.a-price span.a-offscreen",
                "span.a-price.aok-align-center span.a-offscreen",
            ],
        )

        original_texts = await all_visible_texts(
            page,
            [
                "span.priceBlockStrikePriceString",
                "#corePriceDisplay_desktop_feature_div span.a-text-price span.a-offscreen",
                "#corePrice_desktop span.a-text-price span.a-offscreen",
            ],
        )

        current = parse_price(current_text)
        original = best_original_price(original_texts, current)

        discount_price = None
        discount_percent = None

        if current is not None and original is not None:
            if original > current:
                discount_price = round(original - current, 2)
                discount_percent = round(((original - current) / original) * 100, 2)
            else:
                original = current
                discount_price = 0.0
                discount_percent = 0.0

        elif current is not None and original is None:
            original = current
            discount_price = 0.0
            discount_percent = 0.0

        return {
            "current_price": current,
            "original_price": original,
            "discount_price": discount_price,
            "discount_percent": discount_percent,
        }

    async def extract_reviews(self, page: Page) -> dict[str, Any]:
        rating_text = await first_text(page, ["#acrPopover", 'span[data-hook="rating-out-of-text"]'])
        review_count_text = await first_text(page, ["#acrCustomerReviewText"])
        soup = BeautifulSoup(await page.content(), "lxml")

        return {
            "rating": parse_rating(rating_text),
            "review_count": parse_int(review_count_text),
            "review_summary": await self.extract_review_summary(page),
            "star_distribution": parse_star_distribution(soup),
            "review_details": parse_review_details(soup),
        }

    async def extract_review_summary(self, page: Page) -> Optional[str]:
        soup = BeautifulSoup(await page.content(), "lxml")
        summary = parse_review_summary(soup)
        if summary:
            return summary

        text = await first_text(
            page,
            [
                "#product-summary-review-card_feature_div",
                '[data-hook="cr-insights-widget"]',
                "#cr-dp-review-list",
            ],
        )
        return clean_text(text) or None

    async def detect_captcha(self, page: Page, raise_on_block: bool = False) -> bool:
        content = (await page.content()).lower()
        blocked = (
            "enter the characters you see below" in content
            or "type the characters you see in this image" in content
            or "/errors/validatecaptcha" in page.url.lower()
            or "sorry, we just need to make sure you're not a robot" in content
        )
        if blocked and raise_on_block:
            raise CaptchaDetected(page.url)
        return blocked

    async def scroll_to_bottom(self, page: Page) -> None:
        previous_height = 0
        for _ in range(8):
            height = await page.evaluate("document.body.scrollHeight")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(random.randint(350, 800))
            if height == previous_height:
                break
            previous_height = height

    async def polite_delay(self) -> None:
        await asyncio.sleep(random.uniform(settings.scraper_delay_min, settings.scraper_delay_max))

    def _progress(self, total: int, desc: str):
        if not tqdm:
            return None
        return tqdm(total=total, desc=desc, ncols=90, leave=True)


class AmazonScraper(AmazonMensTshirtsScraper):
    """Backward-compatible name for imports that expect AmazonScraper."""

    def __init__(self, config: Optional[ScrapeConfig] = None):
        super().__init__(config or ScrapeConfig())


class CaptchaDetected(RuntimeError):
    pass


async def first_text(page: Page, selectors: list[str]) -> str:
    for selector in selectors:
        try:
            locator = page.locator(selector)
            count = await locator.count()
            for index in range(count):
                node = locator.nth(index)
                if not await node.is_visible(timeout=1000):
                    continue
                text = await node.inner_text(timeout=5000)
                if clean_text(text):
                    return text
        except Exception:
            continue
    return ""


async def all_visible_texts(page: Page, selectors: list[str]) -> list[str]:
    texts: list[str] = []
    for selector in selectors:
        try:
            locator = page.locator(selector)
            count = await locator.count()
            for index in range(count):
                node = locator.nth(index)
                if not await node.is_visible(timeout=1000):
                    continue
                text = clean_text(await node.inner_text(timeout=3000))
                if text:
                    texts.append(text)
        except Exception:
            continue
    return texts


async def option_name(item) -> str:
    for selector in ["img[alt]", ".a-button-text", "button", "span"]:
        try:
            node = item.locator(selector).first
            if await node.count() == 0:
                continue
            alt = await node.get_attribute("alt")
            if alt:
                return alt
            text = await node.inner_text(timeout=2000)
            if clean_text(text):
                return text
        except Exception:
            continue
    return ""


async def selected_dimension_text(page: Page, dimension: str) -> Optional[str]:
    candidates = {
        "color_name": ["#variation_color_name .selection", "#inline-twister-expanded-dimension-text-color_name"],
        "size_name": ["#variation_size_name .selection", "#inline-twister-expanded-dimension-text-size_name"],
    }
    text = await first_text(page, candidates.get(dimension, []))
    return clean_text(text) or None


def dimension_selectors(dimension: str) -> list[str]:
    if dimension == "color_name":
        return [
            'ul[data-a-button-group*="color_name"] li',
            "#variation_color_name li",
            "li.dimension-value-list-item-square-image",
            'li[data-asin]:has(img[alt])',
        ]
    if dimension == "size_name":
        return [
            'ul[data-a-button-group*="size_name"] li',
            "#variation_size_name li",
            "li.dimension-value-list-item",
        ]
    return [f'ul[data-a-button-group*="{dimension}"] li']


async def safe_close(page: Page) -> None:
    try:
        await page.close()
    except Exception:
        pass


def listing_page_url(page_number: int) -> str:
    parsed = urlparse(LISTING_URL)
    params = parse_qs(parsed.query)
    params["page"] = [str(page_number)]
    params["ref"] = [f"sr_pg_{page_number}"]
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{urlencode(params, doseq=True)}"


def canonicalize_amazon_url(href: str | None, fallback_asin: str | None = None) -> Optional[str]:
    asin = asin_from_url(href or "") or fallback_asin
    if valid_asin(asin):
        return CANONICAL_DP.format(asin=asin)
    return None


def asin_from_url(url: str) -> Optional[str]:
    if not url:
        return None
    absolute = urljoin("https://www.amazon.com", url)
    patterns = [
        r"/dp/([A-Z0-9]{10})",
        r"/gp/product/([A-Z0-9]{10})",
        r"/product/([A-Z0-9]{10})",
    ]
    for pattern in patterns:
        match = re.search(pattern, absolute)
        if match:
            return match.group(1)
    query_asin = parse_qs(urlparse(absolute).query).get("asin", [None])[0]
    return query_asin if valid_asin(query_asin) else None


def valid_asin(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Z0-9]{10}", value.strip()))


def is_sponsored_card(card) -> bool:
    text = normalize_space(card.get_text(" ")).lower()
    return "sponsored" in text[:300]


def normalize_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u200e", "").strip().lower())


def clean_text(value: Any) -> str:
    return normalize_space(str(value)) if value is not None else ""


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def split_attribute_value(value: str) -> Any:
    value = clean_text(value)
    parts = [part.strip() for part in re.split(r",|;", value) if part.strip()]
    return parts if len(parts) > 1 else value


def best_original_price(texts: list[str], current: Optional[float]) -> Optional[float]:
    candidates = [price for price in (parse_price(text) for text in texts) if price is not None]
    if current is not None:
        candidates = [price for price in candidates if price > current]
    return round_money(min(candidates)) if candidates else None


def parse_review_summary(soup: BeautifulSoup) -> Optional[str]:
    candidates: list[str] = []
    for node in soup.select("span, div, p"):
        text = clean_text(node.get_text(" ", strip=True))
        if len(text) < 120:
            continue
        if not re.search(r"\bcustomers?\b", text, re.I):
            continue
        if re.search(r"\d+\s+percent\s+of\s+reviews|[1-5]\s+star", text, re.I):
            continue
        candidates.append(text)

    if not candidates:
        return None

    candidates.sort(key=lambda value: (value.lower().startswith("customers "), len(value)), reverse=True)
    return candidates[0]


def parse_star_distribution(soup: BeautifulSoup) -> dict[str, int]:
    distribution: dict[str, int] = {}
    histogram = soup.select_one("#histogramTable, table#histogramTable")
    rows = histogram.select("li, tr, a[aria-label]") if histogram else soup.select("tr.a-histogram-row, a[aria-label]")

    for row in rows:
        label = normalize_space(row.get("aria-label") or row.get_text(" "))
        match = re.search(r"(\d+)\s*percent\s+of\s+reviews\s+have\s+([1-5])\s+stars?", label, re.I)
        if match:
            distribution[match.group(2)] = int(match.group(1))
            continue

        star_match = re.search(r"([1-5])\s*star", label, re.I)
        pct_match = re.search(r"(\d+)%", label)
        if star_match and pct_match and star_match.group(1) not in distribution:
            distribution[star_match.group(1)] = int(pct_match.group(1))

    return {str(star): distribution[str(star)] for star in range(5, 0, -1) if str(star) in distribution}


def parse_review_details(soup: BeautifulSoup) -> dict[str, int]:
    details: dict[str, int] = {}
    for node in soup.select('[aria-label*="aspect"]'):
        label = normalize_space(node.get("aria-label") or "")
        match = re.search(r"aspect,\s*([^,]+),\s*([0-9,]+)\s+mentions?", label, re.I)
        if not match:
            continue
        topic = normalize_key(match.group(1)).replace(" ", "_")
        details[topic] = int(match.group(2).replace(",", ""))
    return details


def parse_price(value: str | None) -> Optional[float]:
    if not value:
        return None
    match = re.search(r"\$?\s*([0-9,]+(?:\.[0-9]{1,2})?)", value)
    if not match:
        return None
    return round_money(float(Decimal(match.group(1).replace(",", ""))))


def round_money(value: Optional[float]) -> Optional[float]:
    return round(value, 2) if value is not None else None


def format_money(value: Optional[float]) -> Optional[str]:
    return f"{value:.2f}" if value is not None else None


def parse_rating(value: str | None) -> Optional[float]:
    if not value:
        return None
    match = re.search(r"([0-5](?:\.[0-9])?)", value)
    return float(match.group(1)) if match else None


def parse_int(value: str | None) -> int:
    if not value:
        return 0
    match = re.search(r"([0-9][0-9,]*)", value)
    return int(match.group(1).replace(",", "")) if match else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Amazon Men's T-Shirts into PostgreSQL.")
    parser.add_argument("--max-products", type=int, default=None, help="Limit product pages processed.")
    parser.add_argument("--max-pages", type=int, default=None, help="Limit listing pages scanned.")
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    config = ScrapeConfig(
        max_products=args.max_products,
        max_pages=args.max_pages,
        headless=not args.headed if args.headed else settings.scraper_headless,
    )
    async with AmazonMensTshirtsScraper(config) as scraper:
        summary = await scraper.run()
    logger.info(f"[DONE] {summary}")


if __name__ == "__main__":
    asyncio.run(main())
