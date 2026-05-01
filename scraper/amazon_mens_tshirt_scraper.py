"""
amazon_mens_tshirt_scraper.py
Standalone Amazon scraper for Men's T-Shirts.
Writes to the normalized schema (products, product_variants, reviews).
"""
from __future__ import annotations

import asyncio
import json
import random
import re
import sys
from typing import Any, Optional
from urllib.parse import parse_qs, unquote, urlencode, urljoin, urlparse

from bs4 import BeautifulSoup
from loguru import logger

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from scraper.base_scraper import BaseScraper
from scraper.schemas import RawAmazonMensTshirtPayload
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
CANONICAL_DP = "https://www.amazon.com/dp/{asin}"

# Men's T-Shirts — same scoped Amazon Fashion URL used by the original scraper.
LISTING_URL = (
    "https://www.amazon.com/s?k=men+tshirt&i=fashion-mens"
    "&rh=n%3A7141123011%2Cn%3A7147441011%2Cn%3A1040658%2Cn%3A15697821011"
    "&dc&ds=v1%3A%2BxTPWgCBnr0P2o83YbUJ5lGxLw4xkap2i8w1D6fHlNs"
    "&crid=1615ED0Q0I2CX&qid=1777382089&rnid=1040658"
    "&sprefix=men+tshirt%2Cfashion-mens%2C391&ref=sr_nr_n_14"
)
ZIP_CODE = "60601"

# Keywords that indicate non-clothing / wrong category items.
_EXCLUDE_KEYWORDS = [
    "patch", "sticker", "decal", "mug", "hat", "cap", "phone case",
    "poster", "pillow", "bag", "backpack", "keychain", "magnet",
    "water bottle", "tumbler", "accessory", "jewelry", "watch",
    "dress", "blouse", "skirt", "pants", "shorts", "shoes", "socks",
    "hoodie", "sweatshirt", "sweater", "jacket", "coat", "costume",
    "women's", "womens", "girls", "boys", "kids", "toddler", "baby",
]

_TSHIRT_KEYWORDS = [
    "t-shirt", "t shirt", "tee", "tees", "shirt", "crewneck", "crew neck",
    "v-neck", "v neck", "henley", "polo",
]

_STEALTH_JS = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined, configurable: true });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
window.chrome = { app: { isInstalled: false }, runtime: {} };
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
"""


class AmazonMensTshirtScraper(BaseScraper):
    PLATFORM = "amazon"
    CATEGORY = "mens_tshirts"
    SCHEMA_CLASS = RawAmazonMensTshirtPayload

    def __init__(self):
        super().__init__()
        self._camoufox_mgr = None

    # ── Browser lifecycle ─────────────────────────────────────────────────────

    async def start(self):
        if _HAS_CAMOUFOX:
            logger.info("[AMZ-MT] Starting camoufox")
            self._camoufox_mgr = AsyncCamoufox(headless=settings.scraper_headless)
            self.browser = await self._camoufox_mgr.__aenter__()
            self.context = await self.browser.new_context(
                viewport={"width": 1440, "height": 950},
                locale="en-US",
                timezone_id="America/New_York",
                geolocation={"latitude": 40.7128, "longitude": -74.0060},
                permissions=["geolocation"],
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "DNT": "1",
                },
            )
            await self.context.add_init_script(_STEALTH_JS)
            await self.context.route(
                "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,otf}",
                lambda route: route.abort(),
            )
            logger.info("[AMZ-MT] camoufox ready")
        else:
            await super().start()

    async def stop(self):
        try:
            if self._camoufox_mgr:
                await self._camoufox_mgr.__aexit__(None, None, None)
            else:
                await super().stop()
        except Exception as e:
            logger.debug(f"[AMZ-MT] stop error: {e}")
        finally:
            self.browser = None
            self.context = None
            self._camoufox_mgr = None
        logger.info("[AMZ-MT] stopped")

    async def new_page(self):
        if not self.context:
            raise RuntimeError("Browser context is not started")
        page = await self.context.new_page()
        page.set_default_timeout(settings.scraper_timeout)
        return page

    # ── Main entry point ──────────────────────────────────────────────────────

    async def search_category(self, category: str = "mens_tshirts", max_products: int = 40) -> list[dict]:
        logger.info(f"[AMZ-MT] search_category max_products={max_products}")
        if max_products <= 0:
            return []

        product_urls: list[tuple[str, str]] = []
        seen_asins: set[str] = set()
        candidate_target = max(max_products * 4, max_products + 15)
        max_listing_pages = 3
        page_num = 1
        page_restarts = 0
        max_page_restarts = max(2, settings.scraper_max_retries)
        page = await self.new_page()

        try:
            # Step 1: Load homepage to establish a real browser session
            logger.info("[AMZ-MT] Loading homepage to establish session...")
            try:
                if await self.safe_goto(page, AMAZON_HOME):
                    await asyncio.sleep(random.uniform(2, 4))
                    # Region setup is useful, but Amazon often hides the header on error pages.
                    await self._set_region(page)
                    await asyncio.sleep(random.uniform(1, 2))
            except Exception as exc:
                logger.warning(f"[AMZ-MT] homepage/session warmup failed; continuing with search: {exc}")

            logger.info("[AMZ-MT] Navigating to search URL...")
            while len(product_urls) < candidate_target and page_num <= max_listing_pages:
                target_url = LISTING_URL if page_num == 1 else listing_page_url(page_num)
                try:
                    if not page or page.is_closed():
                        raise RuntimeError("search page is closed")
                    if not await self.safe_goto(page, target_url):
                        raise RuntimeError(f"could not load search page {page_num}")

                    html = await page.content()
                    if self._is_blocked_html(html, page.url):
                        self._save_debug_html(html, page_num)
                        logger.warning(f"[AMZ-MT] blocked/search error page at page {page_num}")
                        break

                    logger.debug(f"[AMZ-MT] page {page_num} HTML={len(html)} title={await page.title()!r}")
                    links = self._extract_links(html)
                    logger.info(f"[AMZ-MT] page {page_num} → {len(links)} links")
                    if not links:
                        await self._light_scroll(page)
                        html = await page.content()
                        links = self._extract_links(html)
                        logger.info(f"[AMZ-MT] page {page_num} after light scroll → {len(links)} links")
                        if not links:
                            self._save_debug_html(html, page_num)
                            break

                    added_this_page = 0
                    for asin, url in links:
                        if asin in seen_asins:
                            continue
                        seen_asins.add(asin)
                        product_urls.append((asin, url))
                        added_this_page += 1
                        if len(product_urls) >= candidate_target:
                            break
                    if added_this_page == 0:
                        logger.info(f"[AMZ-MT] page {page_num} added no new ASINs; stopping collection")
                        break

                    page_restarts = 0
                    page_num += 1
                    await self.polite_delay()
                except Exception as exc:
                    logger.warning(f"[AMZ-MT] search page {page_num} failed: {exc}")
                    if not self._is_recoverable_browser_error(exc) or page_restarts >= max_page_restarts:
                        logger.error(f"[AMZ-MT] giving up search page {page_num} after browser/page failures")
                        break
                    page_restarts += 1
                    await safe_close(page)
                    if not await self._restart_browser():
                        break
                    page = await self.new_page()
                    await asyncio.sleep(2 * page_restarts)
        finally:
            await safe_close(page)

        logger.info(f"[AMZ-MT] {len(product_urls)} candidate URLs queued for {max_products} products")

        results = []
        for i, (asin, url) in enumerate(product_urls):
            if len(results) >= max_products:
                break
            logger.info(f"[AMZ-MT] product {i+1}/{len(product_urls)}: {asin}")
            data = await self._scrape_product(url, asin)
            if data:
                results.append(data)
            await self.polite_delay()

        logger.info(f"[AMZ-MT] done — {len(results)} products scraped")
        return results

    # ── Region setup ──────────────────────────────────────────────────────────

    async def _set_region(self, page) -> None:
        """Set Amazon delivery ZIP to 60601 (Chicago) so results are correct."""
        try:
            loc = page.locator("#nav-global-location-popover-link")
            await loc.click(timeout=10000)
            inp = page.locator("#GLUXZipUpdateInput")
            await inp.wait_for(state="visible", timeout=10000)
            await inp.fill(ZIP_CODE)
            await page.locator("#GLUXZipUpdate").click(timeout=8000)
            await asyncio.sleep(1)
            # Click "Continue" modal if it appears
            for sel in ['button:has-text("Continue")', 'input[type="submit"][value="Continue"]']:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=1500):
                        await btn.click(timeout=3000)
                        break
                except Exception:
                    pass
            # Done button
            try:
                done = page.locator('button[name="glowDoneButton"]')
                if await done.is_visible(timeout=3000):
                    await done.click(timeout=5000)
            except Exception:
                pass
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
            logger.info(f"[AMZ-MT] region set to ZIP {ZIP_CODE}")
        except Exception as e:
            logger.warning(f"[AMZ-MT] region setup failed (continuing anyway): {e}")

    # ── Link extraction ───────────────────────────────────────────────────────

    def _extract_links(self, html: str) -> list[tuple[str, str]]:
        soup = BeautifulSoup(html, "lxml")
        results: list[tuple[str, str]] = []
        seen: set[str] = set()
        cards = soup.select(
            'div[data-component-type="s-search-result"][data-asin], '
            'div.s-result-item[data-asin]'
        )
        for card in cards:
            asin = (card.get("data-asin") or "").strip()
            if not valid_asin(asin) or asin in seen:
                continue
            if is_sponsored_card(card):
                continue
            link = (
                card.select_one("h2 a.a-link-normal[href]")
                or card.select_one("a.a-link-normal.s-link-style.a-text-normal[href]")
                or card.select_one("a[href*='/dp/']")
            )
            if not link:
                continue
            href = link.get("href", "")
            if "sspa/click" in href:
                m = re.search(r"url=(%2F[^&]+)", href)
                if m:
                    href = unquote(m.group(1))
            canonical = canonicalize_amazon_url(href, fallback_asin=asin)
            canonical_asin = asin_from_url(canonical or "")
            if canonical and canonical_asin:
                if canonical_asin in seen:
                    continue
                seen.add(canonical_asin)
                results.append((canonical_asin, canonical))
        return results

    # ── Browser restart ───────────────────────────────────────────────────────

    async def _restart_browser(self) -> bool:
        logger.warning("[AMZ-MT] Browser crashed — restarting...")
        try:
            await self.stop()
        except Exception:
            pass
        try:
            await self.start()
            logger.info("[AMZ-MT] Browser restarted OK")
            return True
        except Exception as e:
            logger.error(f"[AMZ-MT] Browser restart failed: {e}")
            return False

    # ── Product scraping ──────────────────────────────────────────────────────

    async def _scrape_product(self, url: str, asin: str) -> Optional[dict]:
        max_attempts = max(2, settings.scraper_max_retries)
        for attempt in range(max_attempts):
            page = None
            try:
                page = await self.new_page()
                if not await self.safe_goto(page, url):
                    raise RuntimeError("navigation failed")
                await asyncio.sleep(random.uniform(0.5, 1.0))
                html = await page.content()
                soup = BeautifulSoup(html, "lxml")
                if self._product_title(soup) and not self._is_blocked_html(html, page.url):
                    return self._parse_page(soup, url, asin)

                try:
                    await page.wait_for_selector("span#productTitle", timeout=4000)
                except Exception:
                    pass
                html = await page.content()
                if self._is_blocked_html(html, page.url):
                    self._save_debug_html(html, f"product_{asin}_blocked_a{attempt + 1}")
                    logger.warning(f"[AMZ-MT] blocked page while scraping {url}")
                    raise RuntimeError("blocked product page")
                soup = BeautifulSoup(html, "lxml")
                if not self._product_title(soup):
                    self._save_debug_html(html, f"product_{asin}_missing_title_a{attempt + 1}")
                    raise RuntimeError("missing product title")
                return self._parse_page(soup, url, asin)
            except Exception as e:
                err = str(e).lower()
                logger.error(f"[AMZ-MT] scrape error {url} (attempt {attempt + 1}/{max_attempts}): {e}")
                if page:
                    await safe_close(page)
                    page = None
                recoverable = any(
                    token in err
                    for token in (
                        "closed",
                        "disconnected",
                        "target",
                        "browser",
                        "context",
                        "navigation failed",
                        "blocked product page",
                        "missing product title",
                    )
                )
                if attempt < max_attempts - 1 and recoverable:
                    if not await self._restart_browser():
                        return None
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                return None
            finally:
                if page:
                    await safe_close(page)
        return None

    def _parse_page(self, soup: BeautifulSoup, url: str, asin: str) -> Optional[dict]:
        title = self._product_title(soup)
        logger.debug(f"[AMZ-MT] title={title[:60]!r}")
        if not title:
            logger.warning(f"[AMZ-MT] no title at {url}")
            return None

        detail = self._detail_table(soup)
        if not self._looks_like_mens_tshirt(title, soup, detail):
            logger.warning(f"[AMZ-MT] skipping non men's T-shirt item: {title[:80]}")
            return None

        brand = self._brand(soup)
        logger.debug(f"[AMZ-MT] brand={brand!r}")

        current_price, original_price = self._prices(soup)
        discount_pct = None
        if current_price and original_price and original_price > current_price:
            discount_pct = round((original_price - current_price) / original_price * 100, 1)
        logger.debug(f"[AMZ-MT] price={current_price}, orig={original_price}, disc={discount_pct}")

        rating = self._rating(soup)
        review_count = self._review_count(soup)
        star_dist = self._star_dist(soup)
        logger.debug(f"[AMZ-MT] rating={rating}, reviews={review_count}, stars={star_dist}")

        logger.debug(f"[AMZ-MT] detail keys: {list(detail.keys())}")

        bullets = soup.find("div", id="feature-bullets")
        full_text = f"{title} {bullets.get_text(' ', strip=True) if bullets else ''}"

        material  = detail.get("Fabric Type") or detail.get("Material") or detail.get("Fabric") or detail.get("Material Type")
        pattern   = detail.get("Pattern") or detail.get("Pattern Type") or parse_pattern(full_text)
        fit       = detail.get("Fit Type") or detail.get("Fit") or parse_fit(full_text)
        neck_type = detail.get("Neck Style") or detail.get("Collar Style") or detail.get("Neckline") or parse_neck_type(full_text)
        sleeve    = detail.get("Sleeve Type") or detail.get("Sleeve Length") or parse_sleeve_type(full_text)
        occasion  = detail.get("Occasion Type") or detail.get("Occasion")
        care      = detail.get("Care Instructions") or detail.get("Wash Care")
        logger.debug(f"[AMZ-MT] mat={material!r} pat={pattern!r} fit={fit!r} neck={neck_type!r} sleeve={sleeve!r}")

        colors = self._colors(soup)
        sizes  = self._sizes(soup)
        logger.debug(f"[AMZ-MT] colors={colors} sizes={sizes}")

        size_str = ",".join(sizes) if sizes else None
        variants = [
            {
                "color": c or None,
                "size": size_str,
                "current_price": float(current_price) if current_price else None,
                "original_price": float(original_price) if original_price else None,
                "discount_percent": discount_pct,
                "currency": "USD",
            }
            for c in (colors or [None])
        ]
        logger.debug(f"[AMZ-MT] {len(variants)} variants built")

        return {
            "platform": "amazon",
            "url": url,
            "title": title,
            "brand": brand,
            "category": "mens_tshirts",
            "gender": "men",
            "asin": asin,
            "variants": variants,
            "attributes": {
                "neck_style": neck_type,
                "sleeve_type": sleeve,
                "pattern": pattern,
                "fit_type": fit,
                "material_type": material,
                "occasion": occasion,
                "care": care,
            },
            "review": {
                "rating": float(rating) if rating else None,
                "review_count": review_count or 0,
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
                    logger.debug(f"[AMZ-MT] price via {sel}: {val}")
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
            if page.is_closed():
                raise RuntimeError("page closed during scroll")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(0.4, 0.8))

    async def _light_scroll(self, page) -> None:
        if page.is_closed():
            raise RuntimeError("page closed during light scroll")
        try:
            await page.mouse.wheel(0, 900)
            await asyncio.sleep(random.uniform(0.4, 0.8))
        except Exception as exc:
            raise RuntimeError(f"light scroll failed: {exc}") from exc

    def _product_title(self, soup: BeautifulSoup) -> str:
        title_el = soup.find("span", id="productTitle")
        if title_el:
            return re.sub(r"\s+", " ", title_el.get_text(" ", strip=True)).strip()
        meta = soup.select_one('meta[name="title"], meta[property="og:title"]')
        if meta and meta.get("content"):
            title = re.sub(r"\s+", " ", meta["content"]).strip()
            if not title.lower().startswith("amazon.com"):
                return title
        return ""

    def _is_recoverable_browser_error(self, exc: Exception) -> bool:
        text = str(exc).lower()
        return any(
            token in text
            for token in (
                "closed",
                "disconnected",
                "target",
                "browser",
                "context",
                "page",
                "navigation failed",
                "could not load search page",
                "blocked product page",
                "missing product title",
            )
        )

    def _looks_like_mens_tshirt(self, title: str, soup: BeautifulSoup, detail: dict) -> bool:
        bullets = soup.find("div", id="feature-bullets")
        text = " ".join(
            part
            for part in [
                title,
                bullets.get_text(" ", strip=True) if bullets else "",
                " ".join(str(value) for value in detail.values()),
            ]
            if part
        ).lower()
        if text_has_any_keyword(text, _EXCLUDE_KEYWORDS):
            return False
        return text_has_any_keyword(text, _TSHIRT_KEYWORDS)

    def _is_blocked_html(self, html: str, url: str = "") -> bool:
        text = html.lower()
        return (
            "enter the characters you see below" in text
            or "type the characters you see in this image" in text
            or "sorry, we just need to make sure you're not a robot" in text
            or "something went wrong on our end" in text
            or "500_503.png" in text
            or "api-services-support@amazon.com" in text
            or "automated access" in text
            or "validatecaptcha" in text
            or "captcha" in text
            or "amazon.com/errors/" in url.lower()
            or "/errors/validatecaptcha" in url.lower()
        )

    def _save_debug_html(self, html: str, page_num: int | str) -> None:
        import os
        try:
            os.makedirs("data", exist_ok=True)
            safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(page_num))
            path = f"data/amazon_mt_debug_p{safe_name}.html"
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            logger.warning(f"[AMZ-MT] debug HTML saved to {path}")
        except Exception:
            pass

    # ── scrape_listing (satisfies BaseScraper abstract) ───────────────────────

    async def scrape_listing(self, url: str, **kwargs) -> Optional[dict]:
        return await self._scrape_product(url, kwargs.get("asin", ""))

    # ── to_db_values — maps to normalized schema ──────────────────────────────

    @staticmethod
    def to_db_values(data: RawAmazonMensTshirtPayload) -> dict:
        attrs    = data.attributes.model_dump()
        variants = [v.model_dump() for v in data.variants]
        review   = data.review.model_dump()
        return {
            "platform_id":         1,
            "gender_id":           GENDER_ID.get("men", 1),
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


async def safe_close(page) -> None:
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
    absolute = urljoin(AMAZON_HOME, url)
    for pattern in [
        r"/dp/([A-Z0-9]{10})",
        r"/gp/product/([A-Z0-9]{10})",
        r"/product/([A-Z0-9]{10})",
    ]:
        match = re.search(pattern, absolute)
        if match:
            return match.group(1)
    query_asin = parse_qs(urlparse(absolute).query).get("asin", [None])[0]
    return query_asin if valid_asin(query_asin) else None


def valid_asin(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Z0-9]{10}", value.strip()))


def is_sponsored_card(card) -> bool:
    text = re.sub(r"\s+", " ", card.get_text(" ")).strip().lower()
    return "sponsored" in text[:300]


def text_has_any_keyword(text: str, keywords: list[str]) -> bool:
    for keyword in keywords:
        pattern = r"(?<![a-z0-9])" + re.escape(keyword.lower()) + r"(?![a-z0-9])"
        if re.search(pattern, text):
            return True
    return False
