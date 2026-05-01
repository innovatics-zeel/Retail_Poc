"""
amazon_womens_dress_scraper.py
Standalone Amazon scraper for Women's Dresses.
Writes to the normalized schema (products, product_variants, reviews).
"""
from __future__ import annotations

import asyncio
import json
import random
import re
import sys
from typing import Optional
from urllib.parse import unquote

from bs4 import BeautifulSoup
from loguru import logger

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from scraper.base_scraper import BaseScraper
from scraper.schemas import RawAmazonWomensDressPayload
from scraper.attribute_parser import (
    parse_price, parse_rating, parse_review_count,
    parse_pattern, parse_fit, parse_neck_type, parse_sleeve_type,
)
from database.models import GENDER_ID
from config.settings import settings

try:
    from camoufox.async_api import AsyncCamoufox
    _HAS_CAMOUFOX = True
except ImportError:
    _HAS_CAMOUFOX = False

AMAZON_HOME = "https://www.amazon.com"
# Women's Dresses — Amazon Fashion > Women > Clothing > Dresses (node 1045024)
LISTING_URL = (
    "https://www.amazon.com/s?"
    "i=fashion-womens-clothing&bbn=1045024"
    "&rh=n%3A7147440011%2Cn%3A1045024"
    "&s=review-rank&dc"
)
ZIP_CODE = "60601"

_EXCLUDE_KEYWORDS = [
    "patch", "sticker", "decal", "mug", "hat", "cap", "phone case",
    "poster", "pillow", "bag", "backpack", "keychain", "magnet",
    "water bottle", "tumbler", "accessory", "jewelry", "watch",
]

_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined, configurable: true });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
window.chrome = { app: { isInstalled: false }, runtime: {} };
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
"""


class AmazonWomensDressScraper(BaseScraper):
    PLATFORM = "amazon"
    CATEGORY = "womens_dresses"
    SCHEMA_CLASS = RawAmazonWomensDressPayload

    def __init__(self):
        super().__init__()
        self._camoufox_mgr = None

    # ── Browser lifecycle ─────────────────────────────────────────────────────

    async def start(self):
        if _HAS_CAMOUFOX:
            logger.info("[AMZ-WD] Starting camoufox")
            self._camoufox_mgr = AsyncCamoufox(headless=settings.scraper_headless)
            self.browser = await self._camoufox_mgr.__aenter__()
            self.context = await self.browser.new_context(
                locale="en-US",
                timezone_id="America/New_York",
                geolocation={"latitude": 40.7128, "longitude": -74.0060},
                permissions=["geolocation"],
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9", "DNT": "1"},
            )
            await self.context.add_init_script(_STEALTH_JS)
            logger.info("[AMZ-WD] camoufox ready")
        else:
            await super().start()

    async def stop(self):
        try:
            if self._camoufox_mgr:
                await self._camoufox_mgr.__aexit__(None, None, None)
            else:
                await super().stop()
        except Exception as e:
            logger.debug(f"[AMZ-WD] stop error: {e}")
        logger.info("[AMZ-WD] stopped")

    # ── Main entry point ──────────────────────────────────────────────────────

    async def search_category(self, category: str = "womens_dresses", max_products: int = 40) -> list[dict]:
        logger.info(f"[AMZ-WD] search_category max_products={max_products}")
        page = await self.new_page()
        product_urls: list[tuple[str, str]] = []

        try:
            # Step 1: Load homepage to establish a real browser session
            logger.info("[AMZ-WD] Loading homepage to establish session...")
            await self.safe_goto(page, AMAZON_HOME)
            await asyncio.sleep(random.uniform(2, 4))

            # Step 2: Set US delivery region while nav header is available
            await self._set_region(page)
            await asyncio.sleep(random.uniform(1, 2))

            # Step 3: Navigate to search results
            logger.info("[AMZ-WD] Navigating to search URL...")
            if not await self.safe_goto(page, LISTING_URL):
                logger.error("[AMZ-WD] Could not load search results")
                return []
            await asyncio.sleep(random.uniform(1, 2))

            page_num = 1
            while len(product_urls) < max_products:
                if page_num > 1:
                    url = f"{LISTING_URL}&page={page_num}"
                    if not await self.safe_goto(page, url):
                        break
                await self._scroll(page)
                html = await page.content()
                logger.debug(f"[AMZ-WD] page {page_num} HTML={len(html)} title={await page.title()!r}")
                links = self._extract_links(html)
                logger.info(f"[AMZ-WD] page {page_num} → {len(links)} links")
                if not links:
                    self._save_debug_html(html, page_num)
                    break
                product_urls.extend(links)
                page_num += 1
                await self.polite_delay()
        finally:
            await page.close()

        product_urls = product_urls[:max_products]
        logger.info(f"[AMZ-WD] {len(product_urls)} URLs to scrape")

        results = []
        for i, (asin, url) in enumerate(product_urls):
            logger.info(f"[AMZ-WD] product {i+1}/{len(product_urls)}: {asin}")
            data = await self._scrape_product(url, asin)
            if data:
                results.append(data)
            await self.polite_delay()

        logger.info(f"[AMZ-WD] done — {len(results)} products scraped")
        return results

    # ── Region setup ──────────────────────────────────────────────────────────

    async def _set_region(self, page) -> None:
        try:
            loc = page.locator("#nav-global-location-popover-link")
            await loc.click(timeout=10000)
            inp = page.locator("#GLUXZipUpdateInput")
            await inp.wait_for(state="visible", timeout=10000)
            await inp.fill(ZIP_CODE)
            await page.locator("#GLUXZipUpdate").click(timeout=8000)
            await asyncio.sleep(1)
            for sel in ['button:has-text("Continue")', 'input[type="submit"][value="Continue"]']:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=1500):
                        await btn.click(timeout=3000)
                        break
                except Exception:
                    pass
            try:
                done = page.locator('button[name="glowDoneButton"]')
                if await done.is_visible(timeout=3000):
                    await done.click(timeout=5000)
            except Exception:
                pass
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
            logger.info(f"[AMZ-WD] region set to ZIP {ZIP_CODE}")
        except Exception as e:
            logger.warning(f"[AMZ-WD] region setup failed (continuing anyway): {e}")

    # ── Link extraction ───────────────────────────────────────────────────────

    def _extract_links(self, html: str) -> list[tuple[str, str]]:
        soup = BeautifulSoup(html, "lxml")
        results: list[tuple[str, str]] = []
        seen: set[str] = set()
        for div in soup.select("div[data-asin]"):
            asin = div.get("data-asin", "").strip()
            if not asin or len(asin) != 10 or asin in seen:
                continue
            link = (
                div.select_one("a.a-link-normal[href*='/dp/']")
                or div.select_one("a[href*='/dp/']")
                or div.select_one("h2 a[href]")
                or div.select_one("a[href*='/sspa/click']")
            )
            if not link:
                continue
            href = link.get("href", "")
            if "sspa/click" in href:
                m = re.search(r"url=(%2F[^&]+)", href)
                if m:
                    href = unquote(m.group(1))
            m = re.search(r"/dp/([A-Z0-9]{10})", href)
            if m:
                seen.add(asin)
                results.append((asin, f"https://www.amazon.com/dp/{m.group(1)}"))
        return results

    # ── Browser restart ───────────────────────────────────────────────────────

    async def _restart_browser(self) -> bool:
        logger.warning("[AMZ-WD] Browser crashed — restarting...")
        try:
            await self.stop()
        except Exception:
            pass
        try:
            await self.start()
            logger.info("[AMZ-WD] Browser restarted OK")
            return True
        except Exception as e:
            logger.error(f"[AMZ-WD] Browser restart failed: {e}")
            return False

    # ── Product scraping ──────────────────────────────────────────────────────

    async def _scrape_product(self, url: str, asin: str) -> Optional[dict]:
        for attempt in range(2):
            page = None
            try:
                page = await self.new_page()
                if not await self.safe_goto(page, url):
                    return None
                try:
                    await page.wait_for_selector("span#productTitle", timeout=10000)
                except Exception:
                    pass
                await asyncio.sleep(1.5)
                html = await page.content()
                soup = BeautifulSoup(html, "lxml")
                return self._parse_page(soup, url, asin)
            except Exception as e:
                err = str(e).lower()
                logger.error(f"[AMZ-WD] scrape error {url} (attempt {attempt + 1}): {e}")
                if page:
                    try:
                        await page.close()
                    except Exception:
                        pass
                    page = None
                if attempt == 0 and ("closed" in err or "disconnected" in err or "target" in err):
                    if not await self._restart_browser():
                        return None
                    await asyncio.sleep(2)
                    continue
                return None
            finally:
                if page:
                    try:
                        await page.close()
                    except Exception:
                        pass
        return None

    def _parse_page(self, soup: BeautifulSoup, url: str, asin: str) -> Optional[dict]:
        title_el = soup.find("span", id="productTitle")
        title = title_el.get_text(strip=True) if title_el else ""
        logger.debug(f"[AMZ-WD] title={title[:60]!r}")
        if not title:
            logger.warning(f"[AMZ-WD] no title at {url}")
            return None

        # Skip non-clothing items
        title_lower = title.lower()
        if any(kw in title_lower for kw in _EXCLUDE_KEYWORDS):
            logger.warning(f"[AMZ-WD] skipping non-clothing item: {title[:60]}")
            return None

        brand = self._brand(soup)
        logger.debug(f"[AMZ-WD] brand={brand!r}")

        current_price, original_price = self._prices(soup)
        discount_pct = None
        if current_price and original_price and original_price > current_price:
            discount_pct = round((original_price - current_price) / original_price * 100, 1)
        logger.debug(f"[AMZ-WD] price={current_price}, orig={original_price}")

        rating = self._rating(soup)
        review_count = self._review_count(soup)
        star_dist = self._star_dist(soup)
        logger.debug(f"[AMZ-WD] rating={rating}, reviews={review_count}")

        detail = self._detail_table(soup)
        logger.debug(f"[AMZ-WD] detail keys: {list(detail.keys())}")

        bullets = soup.find("div", id="feature-bullets")
        full_text = f"{title} {bullets.get_text(' ', strip=True) if bullets else ''}"

        material     = detail.get("Fabric Type") or detail.get("Material") or detail.get("Fabric") or detail.get("Material Type")
        pattern      = detail.get("Pattern") or detail.get("Pattern Type") or parse_pattern(full_text)
        fit          = detail.get("Fit Type") or detail.get("Fit") or parse_fit(full_text)
        neck_type    = detail.get("Neck Style") or detail.get("Collar Style") or detail.get("Neckline") or parse_neck_type(full_text)
        sleeve       = detail.get("Sleeve Type") or detail.get("Sleeve Length") or parse_sleeve_type(full_text)
        occasion     = detail.get("Occasion Type") or detail.get("Occasion")
        care         = detail.get("Care Instructions") or detail.get("Wash Care")
        dress_length = detail.get("Dress Length") or detail.get("Length")
        waist_style  = detail.get("Waist Style") or detail.get("Waist")
        closure      = detail.get("Closure Type") or detail.get("Closure")
        silhouette   = detail.get("Apparel Silhouette") or detail.get("Silhouette")
        logger.debug(f"[AMZ-WD] mat={material!r} pat={pattern!r} length={dress_length!r}")

        colors = self._colors(soup)
        sizes  = self._sizes(soup)
        logger.debug(f"[AMZ-WD] colors={colors} sizes={sizes}")

        size_str = ",".join(sizes) if sizes else None
        variants = [
            {
                "color": c or None,
                "size": size_str,
                "current_price":  float(current_price) if current_price else None,
                "original_price": float(original_price) if original_price else None,
                "discount_percent": discount_pct,
                "currency": "USD",
            }
            for c in (colors or [None])
        ]
        logger.debug(f"[AMZ-WD] {len(variants)} variants built")

        return {
            "platform": "amazon",
            "url": url,
            "title": title,
            "brand": brand,
            "category": "womens_dresses",
            "gender": "women",
            "asin": asin,
            "variants": variants,
            "attributes": {
                "neck_style":         neck_type,
                "sleeve_type":        sleeve,
                "pattern":            pattern,
                "fit_type":           fit,
                "material_type":      material,
                "occasion":           occasion,
                "dress_length":       dress_length,
                "waist_style":        waist_style,
                "closure":            closure,
                "apparel_silhouette": silhouette,
                "care":               care,
            },
            "review": {
                "rating":            float(rating) if rating else None,
                "review_count":      review_count or 0,
                "star_distribution": star_dist,
            },
        }

    # ── HTML helpers ──────────────────────────────────────────────────────────

    def _detail_table(self, soup: BeautifulSoup) -> dict:
        result = {}
        for sel in [
            "table.prodDetTable tr",
            "#productDetails_techSpec_section_1 tr",
            "#productDetails_detailBullets_sections1 tr",
            ".a-expander-content tr",
            "tr[class^='po-']",
        ]:
            for row in soup.select(sel):
                th = row.find("th") or row.find("td", class_="a-color-secondary")
                tds = row.find_all("td")
                td = tds[-1] if tds else None
                if th and td:
                    k = re.sub(r"\s+", " ", th.get_text(" ", strip=True))
                    v = re.sub(r"\s+", " ", td.get_text(" ", strip=True))
                    if k and v and k.lower() != v.lower():
                        result[k] = v
        for li in soup.select("#detailBullets_feature_div li"):
            spans = li.find_all("span", recursive=False)
            if len(spans) >= 2:
                k = spans[0].get_text(" ", strip=True).rstrip(":").strip()
                v = spans[-1].get_text(" ", strip=True)
                if k and v:
                    result[k] = v
        return result

    def _brand(self, soup: BeautifulSoup) -> Optional[str]:
        el = soup.find("a", id="bylineInfo")
        if el:
            txt = re.sub(r"^(Visit the |Brand: )", "", el.get_text(strip=True), flags=re.I)
            txt = re.sub(r"\s+[Ss]tore$", "", txt).strip()
            if txt:
                return txt
        tbl = self._detail_table(soup)
        return tbl.get("Brand") or tbl.get("Brand Name")

    def _prices(self, soup: BeautifulSoup) -> tuple[Optional[float], Optional[float]]:
        current = None
        for sel in [
            "span.apex-pricetopay-value span.a-offscreen",
            "#corePriceDisplay_desktop_feature_div span.a-price span.a-offscreen",
            "#corePrice_feature_div span.a-offscreen",
            "span.a-price span.a-offscreen",
            "span.a-price-whole",
        ]:
            el = soup.select_one(sel)
            if el:
                val = parse_price(el.get_text(strip=True))
                if val:
                    current = val
                    logger.debug(f"[AMZ-WD] price via {sel}: {val}")
                    break
        original = None
        for sel in [
            "span.priceBlockStrikePriceString",
            "#corePriceDisplay_desktop_feature_div span.a-text-price span.a-offscreen",
            "span.a-text-price span.a-offscreen",
        ]:
            for el in soup.select(sel):
                val = parse_price(el.get_text(strip=True))
                if val and (current is None or val > current):
                    original = val
                    break
            if original:
                break
        return current, original

    def _rating(self, soup: BeautifulSoup) -> Optional[float]:
        el = soup.select_one("#acrPopover")
        if el:
            return parse_rating(el.get("title", "") or el.get_text())
        el = soup.find("span", {"class": "a-icon-alt"})
        return parse_rating(el.get_text()) if el else None

    def _review_count(self, soup: BeautifulSoup) -> int:
        el = soup.find("span", id="acrCustomerReviewText")
        return parse_review_count(el.get_text()) if el else 0

    def _star_dist(self, soup: BeautifulSoup) -> dict:
        dist = {}
        for el in soup.select("tr.a-histogram-row a[aria-label], a[aria-label*='star']"):
            label = el.get("aria-label", "")
            m = re.search(r"(\d+)\s*percent.*?([1-5])\s*star", label, re.I)
            if m:
                dist[m.group(2)] = int(m.group(1))
        return dist

    def _colors(self, soup: BeautifulSoup) -> list[str]:
        seen: set[str] = set()
        colors: list[str] = []
        for img in soup.select("li[data-asin] img[alt], #variation_color_name li img[alt]"):
            alt = img.get("alt", "").strip()
            if alt and alt.lower() not in seen:
                seen.add(alt.lower()); colors.append(alt)
        if not colors:
            for el in soup.select("#variation_color_name .selection, span[id*='color_name']"):
                txt = el.get_text(strip=True)
                if txt and txt.lower() not in seen:
                    seen.add(txt.lower()); colors.append(txt)
        return colors

    def _sizes(self, soup: BeautifulSoup) -> list[str]:
        seen: set[str] = set()
        sizes: list[str] = []
        for btn in soup.select("li.swatch-list-item-text .swatch-title-text-display"):
            s = btn.get_text(strip=True)
            if s and s.lower() not in seen:
                seen.add(s.lower()); sizes.append(s)
        if not sizes:
            for btn in soup.select(
                "#variation_size_name li .a-button-text, "
                "#native_dropdown_selected_size_name option"
            ):
                s = btn.get_text(strip=True)
                if s and s.lower() not in seen and s.lower() not in ("select", "choose", "-"):
                    seen.add(s.lower()); sizes.append(s)
        return sizes

    async def _scroll(self, page) -> None:
        for _ in range(4):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(0.4, 0.8))

    def _save_debug_html(self, html: str, page_num: int) -> None:
        import os
        try:
            os.makedirs("data", exist_ok=True)
            with open(f"data/amazon_wd_debug_p{page_num}.html", "w", encoding="utf-8") as f:
                f.write(html)
            logger.warning(f"[AMZ-WD] 0 links — debug HTML saved to data/amazon_wd_debug_p{page_num}.html")
        except Exception:
            pass

    async def scrape_listing(self, url: str, **kwargs) -> Optional[dict]:
        return await self._scrape_product(url, kwargs.get("asin", ""))

    @staticmethod
    def to_db_values(data: RawAmazonWomensDressPayload) -> dict:
        attrs    = data.attributes.model_dump()
        variants = [v.model_dump() for v in data.variants]
        review   = data.review.model_dump()
        return {
            "platform_id":         1,
            "gender_id":           GENDER_ID.get("women", 2),
            "category":            data.category,
            "url":                 data.url,
            "title":               data.title,
            "brand":               data.brand,
            "material":            attrs.get("material_type"),
            "neck_type":           attrs.get("neck_style"),
            "sleeve_type":         attrs.get("sleeve_type"),
            "fit":                 attrs.get("fit_type"),
            "pattern":             attrs.get("pattern"),
            "care_instructions":   attrs.get("care"),
            "stock_variants_json": json.dumps(variants),
            "review_json": json.dumps({
                "rating":            review.get("rating"),
                "review_count":      review.get("review_count", 0),
                "star_distribution": review.get("star_distribution", {}),
            }),
        }
