"""
amazon_scraper.py
Base scraper for Amazon US — anti-detection browser setup + shared HTML parsers.
Subclassed by amazon_mt_scraper (mens_tshirts) and amazon_wd_scraper (womens_dresses).

Anti-detection mirrors the Nordstrom scraper:
  Layer 1 → camoufox  : patched Firefox, randomised TLS + canvas fingerprints
  Layer 2 → patchright : CDP-patched Chrome
  Layer 3 → playwright + system Chrome (fallback)
"""
import re
import sys
from typing import Optional

from bs4 import BeautifulSoup
from loguru import logger

sys.path.append("..")
from scraper.base_scraper import BaseScraper
from scraper.attribute_parser import (
    parse_price, parse_rating, parse_review_count,
)
from config.settings import settings

# ── Try stealth backends in priority order ────────────────────────────────────

try:
    from camoufox.async_api import AsyncCamoufox
    USE_CAMOUFOX = True
    logger.info("[AMAZON] camoufox found — using patched Firefox")
except ImportError:
    USE_CAMOUFOX = False
    logger.warning("[AMAZON] camoufox not installed — pip install camoufox[geoip] && python -m camoufox fetch")

try:
    from patchright.async_api import async_playwright as patchright_playwright
    USE_PATCHRIGHT = True
    logger.info("[AMAZON] patchright found")
except ImportError:
    USE_PATCHRIGHT = False
    logger.warning("[AMAZON] patchright not found")

try:
    from playwright.async_api import async_playwright
    try:
        from playwright_stealth import stealth_async
        HAS_STEALTH = True
    except ImportError:
        HAS_STEALTH = False
except ImportError:
    pass

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined, configurable: true });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
window.chrome = { app: { isInstalled: false }, runtime: { onConnect: { addListener: () => {} }, onMessage: { addListener: () => {} } } };
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
"""

AMAZON_SEARCH_URLS = {
    "mens_tshirts": (
        "https://www.amazon.com/s?k=mens+t+shirts"
        "&rh=n%3A1040660%2Cn%3A9057119011"
        "&s=review-rank&i=fashion"
    ),
    "womens_casual_dresses": (
        "https://www.amazon.com/s?k=womens+casual+dresses"
        "&rh=n%3A1040660%2Cn%3A7147443011"
        "&s=review-rank&i=fashion"
    ),
}


class AmazonScraper(BaseScraper):
    """Base Amazon scraper — stealth browser setup + shared HTML parsers."""

    PLATFORM = "amazon"

    def __init__(self):
        super().__init__()
        self._mode = None
        self._camoufox_mgr = None

    # ── Browser lifecycle — stealth setup ─────────────────────────────────────

    async def start(self):
        # camoufox (Firefox) resolves DNS correctly in WSL2 — use it first.
        # Patchright (Chrome) has ERR_NAME_NOT_RESOLVED in WSL2 despite /etc/resolv.conf fix.
        if USE_CAMOUFOX:
            await self._start_camoufox()
        elif USE_PATCHRIGHT:
            await self._start_patchright()
        else:
            await self._start_playwright()

    async def _start_camoufox(self):
        logger.info("[AMAZON BROWSER] Starting camoufox")
        self._camoufox_mgr = AsyncCamoufox(headless=settings.scraper_headless)
        self.browser = await self._camoufox_mgr.__aenter__()
        self.context = await self.browser.new_context(
            locale="en-US",
            timezone_id="America/New_York",
            geolocation={"latitude": 40.7128, "longitude": -74.0060},
            permissions=["geolocation"],
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9", "DNT": "1"},
        )
        await self.context.add_init_script(STEALTH_SCRIPT)
        self._mode = "camoufox"
        logger.info("[AMAZON BROWSER] camoufox ready")

    async def _start_patchright(self):
        logger.info("[AMAZON BROWSER] Starting patchright")
        self.playwright = await patchright_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",   # required for WSL2 / Linux containers
                "--disable-gpu",
                "--no-first-run",
                "--no-zygote",
                "--dns-servers=8.8.8.8,8.8.4.4",  # WSL2: Chromium ignores /etc/resolv.conf
            ],
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9", "DNT": "1"},
        )
        await self.context.add_init_script(STEALTH_SCRIPT)
        self._mode = "patchright"
        logger.info("[AMAZON BROWSER] patchright ready")

    async def _start_playwright(self):
        logger.info("[AMAZON BROWSER] Starting playwright + system Chrome (fallback)")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--no-first-run",
                "--no-zygote",
            ],
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9", "DNT": "1"},
        )
        await self.context.add_init_script(STEALTH_SCRIPT)
        self._mode = "playwright"
        logger.info("[AMAZON BROWSER] playwright ready")

    async def stop(self):
        try:
            if self._mode == "camoufox" and self._camoufox_mgr:
                await self._camoufox_mgr.__aexit__(None, None, None)
            else:
                if self.browser:
                    await self.browser.close()
                if self.playwright:
                    await self.playwright.stop()
        except Exception as e:
            logger.debug(f"Browser cleanup error: {e}")
        logger.info("[AMAZON BROWSER] stopped")

    # ── Category search ───────────────────────────────────────────────────────

    async def search_category(self, category: str, max_products: int = 40) -> list[dict]:
        logger.info(f"[AMAZON] search_category called: category={category!r} max_products={max_products} mode={self._mode!r}")
        if category not in AMAZON_SEARCH_URLS:
            logger.error(f"[AMAZON] Unknown category {category!r}. Available: {list(AMAZON_SEARCH_URLS)}")
            raise ValueError(f"Unknown Amazon category: {category}. Use: {list(AMAZON_SEARCH_URLS)}")

        base_url = AMAZON_SEARCH_URLS[category]
        logger.debug(f"[AMAZON] base_url={base_url}")
        product_urls = []
        page_num = 1
        page = await self.new_page()
        logger.debug(f"[AMAZON] new_page created, is_closed={page.is_closed()}")

        while len(product_urls) < max_products:
            url = f"{base_url}&page={page_num}"
            logger.info(f"🔍 Amazon [{category}] page {page_num} — {url}")
            nav_ok = await self.safe_goto(page, url)
            logger.debug(f"[AMAZON] safe_goto returned={nav_ok}, current_url={page.url!r}")
            if not nav_ok:
                logger.error(f"[AMAZON] Navigation failed for page {page_num}, aborting search loop")
                break
            blocked = await self._is_blocked(page)
            logger.debug(f"[AMAZON] _is_blocked={blocked}")
            if blocked:
                logger.warning("⚠️  Amazon bot check detected on search page")
                break
            html = await page.content()
            logger.debug(f"[AMAZON] page HTML length={len(html)}, title={await page.title()!r}")
            soup = BeautifulSoup(html, "lxml")

            # Count all divs with data-asin before link extraction
            all_asin_divs = soup.select("div[data-asin]")
            logger.debug(f"[AMAZON] div[data-asin] total on page: {len(all_asin_divs)}")
            for i, d in enumerate(all_asin_divs[:5]):
                logger.debug(f"  [div {i}] asin={d.get('data-asin')!r} class={d.get('class')!r}")
                a = d.find("a", href=True)
                logger.debug(f"  [div {i}] first <a> href={a.get('href','none')[:80] if a else 'NO_LINK'!r}")

            links = self._extract_search_result_links(soup)
            logger.debug(f"[AMAZON] _extract_search_result_links returned {len(links)} links")
            if not links:
                dump_path = f"data/amazon_debug_page{page_num}.html"
                try:
                    import os; os.makedirs("data", exist_ok=True)
                    with open(dump_path, "w", encoding="utf-8") as f:
                        f.write(html)
                    logger.warning(f"⚠️  0 links found — HTML saved to {dump_path}")
                except Exception as de:
                    logger.warning(f"[AMAZON] Could not save debug HTML: {de}")
                logger.info(f"No more results on page {page_num}")
                break
            product_urls.extend(links)
            logger.info(f"  Found {len(links)} links on page {page_num} (total: {len(product_urls)})")
            page_num += 1
            await self.polite_delay()

        await page.close()

        results = []
        for i, (asin, url) in enumerate(product_urls[:max_products]):
            logger.info(f"📦 Scraping product {i+1}/{min(len(product_urls), max_products)}: {asin}")

            # Proactively restart if context died from previous iteration
            if not await self._is_context_alive():
                logger.warning("⚠️  Browser context dead — restarting before next product...")
                await self._restart_browser()

            try:
                data = await self.scrape_listing(url, category=category, asin=asin)
            except Exception as e:
                logger.warning(f"⚠️  Browser crashed scraping {asin}: {e} — restarting...")
                await self._restart_browser()
                try:
                    data = await self.scrape_listing(url, category=category, asin=asin)
                except Exception as e2:
                    logger.error(f"❌ Retry after restart also failed ({asin}): {e2}")
                    data = None

            if data:
                results.append(data)
            await self.polite_delay()

        logger.info(f"✅ Amazon [{category}]: scraped {len(results)} products")
        return results

    async def _is_context_alive(self) -> bool:
        try:
            if self.context is None:
                return False
            _ = self.context.pages  # raises if context is closed
            return True
        except Exception:
            return False

    async def _restart_browser(self) -> None:
        try:
            await self.stop()
        except Exception:
            pass
        try:
            await self.start()
            logger.info("✅ Browser restarted successfully")
        except Exception as e:
            logger.error(f"❌ Browser restart failed: {e}")

    # ── Single listing ────────────────────────────────────────────────────────

    async def scrape_listing(self, url: str, category: str = "", asin: str = "") -> Optional[dict]:
        page = None
        try:
            page = await self.new_page()

            # Page closed immediately after creation — context is already dead
            if page.is_closed():
                raise RuntimeError("Browser context closed before navigation")

            if not await self.safe_goto(page, url):
                return None

            # Page may have been closed by Amazon JS / redirect during navigation
            if page.is_closed():
                raise RuntimeError("Page closed during navigation — browser likely crashed")

            if await self._is_blocked(page):
                logger.warning(f"⚠️  Bot check on: {url}")
                return None

            soup = BeautifulSoup(await page.content(), "lxml")
            result = self._parse_product_page(soup, url, category, asin)
            if not result:
                logger.warning(f"  ⚠️  Could not parse: {url}")
            return result

        except Exception as e:
            err = str(e).lower()
            # Re-raise browser/context closed errors — caller will restart browser
            if "closed" in err and any(w in err for w in ("context", "browser", "target")):
                raise
            logger.error(f"❌ Error scraping {url}: {e}")
            return None
        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass

    # ── Shared HTML helpers ───────────────────────────────────────────────────

    def _parse_product_page(self, soup: BeautifulSoup, url: str, category: str, asin: str) -> Optional[dict]:
        """Base implementation — subclasses override this to produce structured output."""
        title_el = soup.find("span", id="productTitle")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            return None

        brand_el = soup.find("a", id="bylineInfo")
        brand = re.sub(r"^(Visit the |Brand: )", "", brand_el.get_text(strip=True)) if brand_el else ""

        price_raw = ""
        for sel in [("span", {"class": "a-price-whole"}), ("span", {"id": "priceblock_ourprice"}), ("span", {"class": "a-offscreen"})]:
            el = soup.find(*sel)
            if el:
                price_raw = el.get_text(strip=True)
                break
        price = parse_price(price_raw)

        rating_el = soup.find("span", {"class": "a-icon-alt"})
        rating = parse_rating(rating_el.get_text() if rating_el else "")
        review_el = soup.find("span", id="acrCustomerReviewText")
        review_count = parse_review_count(review_el.get_text() if review_el else "")

        return {
            "platform": "amazon", "url": url, "title": title, "brand": brand,
            "category": category, "gender": "men" if "mens" in category else "women",
            "asin": asin, "price": price, "currency": "USD",
            "rating": rating, "review_count": review_count,
        }

    def _extract_search_result_links(self, soup: BeautifulSoup) -> list[tuple[str, str]]:
        from urllib.parse import unquote
        results: list[tuple[str, str]] = []
        seen_asins: set[str] = set()

        for div in soup.select("div[data-asin]"):
            asin = div.get("data-asin", "").strip()
            # Valid ASINs are exactly 10 alphanumeric characters
            if not asin or len(asin) != 10 or asin in seen_asins:
                continue

            # Try selectors in priority order — Amazon changes classes frequently
            link_el = (
                div.select_one("a.a-link-normal[href*='/dp/']")
                or div.select_one("a[href*='/dp/']")
                or div.select_one("h2 a[href]")
                or div.select_one("a[href*='/sspa/click']")
            )
            if not link_el:
                continue

            href = link_el.get("href", "")

            # Decode SSPA (sponsored) wrapper URLs: /sspa/click?...&url=%2Fdp%2F...
            if "sspa/click" in href:
                m = re.search(r"url=(%2F[^&]+)", href)
                if m:
                    href = unquote(m.group(1))

            dp_match = re.search(r"/dp/([A-Z0-9]{10})", href)
            if dp_match:
                canonical = f"https://www.amazon.com/dp/{dp_match.group(1)}"
                seen_asins.add(asin)
                results.append((asin, canonical))

        return results

    def _extract_detail(self, soup: BeautifulSoup, labels: list[str]) -> Optional[str]:
        tbl = self._extract_product_detail_table(soup)
        for label in labels:
            for key, val in tbl.items():
                if label.lower() in key.lower():
                    return val
        return None

    def _parse_color(self, soup: BeautifulSoup) -> Optional[str]:
        colors = self._extract_colors(soup)
        return colors[0] if colors else None

    def _parse_sizes(self, soup: BeautifulSoup) -> Optional[str]:
        sizes = self._extract_sizes(soup)
        return ",".join(sizes) if sizes else None

    def _extract_asin(self, url: str) -> str:
        match = re.search(r"/dp/([A-Z0-9]{10})", url)
        return match.group(1) if match else url.split("/")[-1]

    # ── Rich HTML extraction helpers (used by subclass _parse_product_page) ─────

    def _extract_product_detail_table(self, soup: BeautifulSoup) -> dict:
        """Return all product-detail rows as {label: value}."""
        result = {}
        selectors = [
            "table.prodDetTable tr",
            "#productDetails_techSpec_section_1 tr",
            "#productDetails_detailBullets_sections1 tr",
            ".a-expander-content tr",
            "tr[class^='po-']",
        ]
        for sel in selectors:
            for row in soup.select(sel):
                th = row.find("th") or row.find("td", class_="a-color-secondary")
                tds = row.find_all("td")
                td = tds[-1] if tds else None
                if th and td:
                    key = re.sub(r"\s+", " ", th.get_text(" ", strip=True))
                    val = re.sub(r"\s+", " ", td.get_text(" ", strip=True))
                    if key and val and key.lower() != val.lower():
                        result[key] = val
        # Bullet-point style (#detailBullets)
        for li in soup.select("#detailBullets_feature_div li"):
            spans = li.find_all("span", recursive=False)
            if len(spans) >= 2:
                key = spans[0].get_text(" ", strip=True).rstrip(":").strip()
                val = spans[-1].get_text(" ", strip=True)
                if key and val:
                    result[key] = val
        return result

    def _extract_brand_text(self, soup: BeautifulSoup) -> Optional[str]:
        el = soup.find("a", id="bylineInfo")
        if el:
            txt = re.sub(r"^(Visit the |Brand: )", "", el.get_text(strip=True), flags=re.I)
            txt = re.sub(r"\s+[Ss]tore$", "", txt).strip()
            if txt:
                return txt
        tbl = self._extract_product_detail_table(soup)
        return tbl.get("Brand") or tbl.get("Brand Name")

    def _extract_prices(self, soup: BeautifulSoup) -> tuple[Optional[float], Optional[float]]:
        """Returns (current_price, original_price)."""
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
                    logger.debug(f"[AMAZON] price from selector {sel!r}: {val}")
                    break
        if current is None:
            logger.debug("[AMAZON] current_price NOT found — all price selectors missed")

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

    def _extract_rating(self, soup: BeautifulSoup) -> Optional[float]:
        el = soup.select_one("#acrPopover")
        if el:
            return parse_rating(el.get("title", "") or el.get_text())
        el = soup.find("span", {"class": "a-icon-alt"})
        return parse_rating(el.get_text()) if el else None

    def _extract_review_count(self, soup: BeautifulSoup) -> int:
        el = soup.find("span", id="acrCustomerReviewText")
        return parse_review_count(el.get_text()) if el else 0

    def _extract_star_distribution(self, soup: BeautifulSoup) -> dict:
        dist = {}
        for el in soup.select("tr.a-histogram-row a[aria-label], a[aria-label*='star']"):
            label = el.get("aria-label", "")
            m = re.search(r"(\d+)\s*percent.*?([1-5])\s*star", label, re.I)
            if m:
                dist[m.group(2)] = int(m.group(1))
                continue
            m2 = re.search(r"([1-5])\s*star.*?(\d+)\s*percent", label, re.I)
            if m2:
                dist[m2.group(1)] = int(m2.group(2))
        return dist

    def _extract_colors(self, soup: BeautifulSoup) -> list[str]:
        colors: list[str] = []
        seen: set[str] = set()
        for img in soup.select("li[data-asin] img[alt], #variation_color_name li img[alt]"):
            alt = img.get("alt", "").strip()
            if alt and alt.lower() not in seen:
                seen.add(alt.lower()); colors.append(alt)
        if not colors:
            for el in soup.select("#variation_color_name .selection, span[id*='color_name']"):
                txt = el.get_text(strip=True)
                if txt and txt.lower() not in seen:
                    seen.add(txt.lower()); colors.append(txt)
        logger.debug(f"[AMAZON] colors extracted: {colors}")
        return colors

    def _extract_sizes(self, soup: BeautifulSoup) -> list[str]:
        sizes: list[str] = []
        seen: set[str] = set()
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
        logger.debug(f"[AMAZON] sizes extracted: {sizes}")
        return sizes

    async def _is_blocked(self, page) -> bool:
        url = page.url
        if any(x in url for x in ["amazon.com/errors/", "amazon.com/captcha", "/ap/signin"]):
            logger.debug(f"[AMAZON] blocked by URL pattern: {url}")
            return True
        content = await page.content()
        blocked_signals = [
            "Enter the characters you see below",
            "Sorry, we just need to make sure you're not a robot",
            "api-services-support@amazon.com",
            "Type the characters you see in this image",
            "Robot Check",
            "automated access",
            "To discuss automated access",
        ]
        hit = next((s for s in blocked_signals if s in content), None)
        if hit:
            logger.warning(f"[AMAZON] bot-block signal: {hit!r}")
        return hit is not None
