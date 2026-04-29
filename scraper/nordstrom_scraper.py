"""
nordstrom_scraper.py
Scrapes Nordstrom Men's T-shirts — Crewneck and Graphic Tees subcategories.

Anti-detection strategy (mirrors nordstrom.py POC):
  Layer 1 → camoufox  : patched Firefox, randomised TLS + canvas fingerprints
  Layer 2 → patchright : CDP-patched Chrome with legitimate TLS fingerprint
  Layer 3 → playwright + system Chrome channel + playwright-stealth (fallback)

INSTALL:
    pip install camoufox[geoip] patchright playwright-stealth beautifulsoup4 lxml
    python -m camoufox fetch          # downloads patched Firefox binary
    patchright install chrome         # installs patchright Chrome
    playwright install chrome         # fallback system Chrome
"""
import re
import json
import asyncio
import random
from typing import Optional
from urllib.parse import urlencode, urljoin, urlparse
from bs4 import BeautifulSoup
from loguru import logger

from scraper.base_scraper import BaseScraper

# ── Try stealth backends in priority order ────────────────────────────────────

try:
    from camoufox.async_api import AsyncCamoufox
    USE_CAMOUFOX = True
    logger.info("[INIT] camoufox found — using patched Firefox (best stealth)")
except ImportError:
    USE_CAMOUFOX = False
    logger.warning("[INIT] camoufox not installed — pip install camoufox[geoip] && python -m camoufox fetch")

try:
    from patchright.async_api import async_playwright as patchright_playwright
    USE_PATCHRIGHT = True
    logger.info("[INIT] patchright found — using CDP-patched Chrome")
except ImportError:
    USE_PATCHRIGHT = False
    logger.warning("[INIT] patchright not found — pip install patchright && patchright install chrome")

try:
    from playwright.async_api import async_playwright
    from playwright_stealth import stealth_async
    HAS_STEALTH = True
    logger.info("[INIT] playwright-stealth found")
except ImportError:
    try:
        from playwright.async_api import async_playwright
        HAS_STEALTH = False
    except ImportError:
        pass
    logger.warning("[INIT] playwright-stealth not found — pip install playwright-stealth")

# ── Stealth JS injected before every page load ────────────────────────────────
# Erases CDP/webdriver signals that Akamai Bot Manager checks

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true
});

Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const arr = [{ name: 'Chrome PDF Plugin' }, { name: 'Chrome PDF Viewer' }, { name: 'Native Client' }];
        Object.defineProperty(arr, 'length', { value: 3 });
        return arr;
    }
});

Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });

window.chrome = {
    app: { isInstalled: false },
    runtime: {
        onConnect: { addListener: () => {} },
        onMessage: { addListener: () => {} }
    }
};

const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
if (originalQuery) {
    window.navigator.permissions.query = (params) =>
        params.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(params);
}

delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;

const elementDescriptor = Object.getOwnPropertyDescriptor(HTMLElement.prototype, 'offsetHeight');
if (elementDescriptor && elementDescriptor.configurable) {
    Object.defineProperty(HTMLDivElement.prototype, 'offsetHeight', {
        ...elementDescriptor,
        get: function() {
            if (this.id === 'modernizr') return 1;
            return elementDescriptor.get.apply(this);
        }
    });
}
"""

MENS_TSHIRT_BASE = "https://www.nordstrom.com/browse/men/clothing/shirts/tshirts"

MENS_SUBCATEGORIES = [
    ("crewneck", "/browse/men/clothing/shirts/tshirts/crewneck"),
    ("graphic",  "/browse/men/clothing/shirts/tshirts/graphic"),
]

_FIT_KEYWORDS = ["slim", "regular", "relaxed", "classic", "athletic", "loose", "tailored", "oversized"]

_MATERIAL_PAT = re.compile(r"\d+%\s*\w+(?:\s*[,/&]\s*\d+%\s*\w+)*", re.I)

_NECK_MAP = {
    "crewneck":    "crewneck",   "crew neck":   "crewneck",  "crew-neck":   "crewneck",
    "v-neck":      "v-neck",     "vneck":       "v-neck",    "v neck":      "v-neck",
    "polo":        "polo",       "henley":      "henley",
    "mock neck":   "mock neck",  "quarter zip": "quarter zip",
}

_PATTERN_MAP = {
    "graphic":  "graphic",
    "striped":  "striped",  "stripe":  "striped",
    "plaid":    "plaid",
    "floral":   "floral",
    "printed":  "printed",  "print":   "printed",
    "solid":    "solid",    "plain":   "solid",
    "tie-dye":  "tie-dye",  "tie dye": "tie-dye",
    "camo":     "camo",     "camouflage": "camo",
}


class NordstromScraper(BaseScraper):
    PLATFORM = "nordstrom"

    def __init__(self):
        super().__init__()
        self._mode = None          # "camoufox" | "patchright" | "playwright"
        self._camoufox_mgr = None  # holds AsyncCamoufox context manager for cleanup

    # ── Browser lifecycle — overrides BaseScraper to add stealth ─────────────

    async def start(self):
        if USE_CAMOUFOX:
            await self._start_camoufox()
        elif USE_PATCHRIGHT:
            await self._start_patchright()
        else:
            await self._start_playwright()

    async def _start_camoufox(self):
        logger.info("[BROWSER] Starting camoufox (patched Firefox) — best anti-fingerprint")
        # Only pass headless — camoufox 0.4.x forwards all kwargs to Firefox launch()
        # and rejects anything Playwright doesn't know (locale, geolocation, timezone).
        self._camoufox_mgr = AsyncCamoufox(headless=False)
        self.browser = await self._camoufox_mgr.__aenter__()
        # Create a context so US locale/geolocation are set the same way as other modes
        self.context = await self.browser.new_context(
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
        await self.context.add_init_script(STEALTH_SCRIPT)
        self._mode = "camoufox"
        logger.info("[BROWSER] camoufox ready")

    async def _start_patchright(self):
        logger.info("[BROWSER] Starting patchright (CDP-patched Chrome)")
        self.playwright = await patchright_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1366, "height": 768},
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
        await self.context.add_init_script(STEALTH_SCRIPT)
        self._mode = "patchright"
        logger.info("[BROWSER] patchright ready")

    async def _start_playwright(self):
        # channel="chrome" uses your real system Google Chrome — its TLS fingerprint
        # passes Akamai checks unlike Playwright's bundled Chromium build.
        logger.info("[BROWSER] Starting playwright + system Chrome channel (fallback)")
        logger.warning("[BROWSER] TIP: install camoufox for stronger bypass: pip install camoufox[geoip]")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-features=IsolateOrigins,site-per-process",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )
        self.context = await self.browser.new_context(
            viewport={"width": 1366, "height": 768},
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
        await self.context.add_init_script(STEALTH_SCRIPT)
        self._mode = "playwright"
        logger.info("[BROWSER] playwright + Chrome ready")

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
            logger.debug(f"Browser cleanup error (safe to ignore on Ctrl+C): {e}")
        logger.info("[BROWSER] stopped")

    async def new_page(self):
        page = await self.context.new_page()
        if HAS_STEALTH and self._mode == "playwright":
            await stealth_async(page)
        return page

    # ── Category entry point ─────────────────────────────────────────────────

    async def search_category(self, category: str, max_products: int = 1) -> list[dict]:
        if category != "mens_tshirts":
            raise ValueError(f"Only mens_tshirts supported currently, got: {category}")

        collected: list[tuple[str, str]] = []
        seen_urls: set[str] = set()
        page = await self.new_page()

        for neck_hint, sub_path in MENS_SUBCATEGORIES:
            if len(collected) >= max_products:
                break

            page_num = 1
            last_page = None
            while len(collected) < max_products:
                sub_url = self._category_url(sub_path, page_num)
                logger.info(f"Subcategory [{neck_hint}] page {page_num} -> {sub_url}")

                if not await self.safe_goto(page, sub_url):
                    break
                if await self._is_blocked(page):
                    logger.error(
                        f"Nordstrom blocked automated traffic on [{neck_hint}], "
                        f"redirected to {page.url}"
                    )
                    await self.polite_delay()
                    break

                await self._human_mouse_move(page)
                await self._scroll_to_load(page)
                soup = BeautifulSoup(await page.content(), "lxml")
                links = self._extract_product_links(soup)
                logger.info(f"  Found {len(links)} product links")

                new_links = 0
                for link in links:
                    if link not in seen_urls:
                        seen_urls.add(link)
                        collected.append((link, neck_hint))
                        new_links += 1
                        if len(collected) >= max_products:
                            break

                if last_page is None:
                    last_page = self._extract_last_page(soup)
                if new_links == 0:
                    logger.info(f"  No new product links on page {page_num}; stopping [{neck_hint}]")
                    break
                if last_page is not None and page_num >= last_page:
                    break

                page_num += 1
                await self.polite_delay()

                # A guardrail for accidental huge runs when max_products is very high.
                if page_num > 200:
                    logger.warning("Stopping pagination at 200 pages")
                    break

        await page.close()

        results = []
        for i, (url, neck_hint) in enumerate(collected[:max_products]):
            logger.info(f"[{i + 1}/{min(len(collected), max_products)}] {url}")
            data = await self.scrape_listing(url, neck_type_hint=neck_hint)
            if data:
                results.append(data)
            await self.polite_delay()

        logger.info(f"Nordstrom mens_tshirts: {len(results)} products scraped")
        return results

    def _category_url(self, sub_path: str, page_num: int) -> str:
        query = {
            "breadcrumb": "Home/Men/Clothing/T-Shirts",
        }
        if page_num > 1:
            query["page"] = str(page_num)
        return f"https://www.nordstrom.com{sub_path}?{urlencode(query)}"

    def _extract_last_page(self, soup: BeautifulSoup) -> Optional[int]:
        pages = []
        for a in soup.select("ul.supUd a[href*='page=']"):
            href = a.get("href", "")
            m = re.search(r"[?&]page=(\d+)", href)
            if m:
                pages.append(int(m.group(1)))
            else:
                text = a.get_text(strip=True)
                if text.isdigit():
                    pages.append(int(text))
        return max(pages) if pages else None

    # ── Single product page ──────────────────────────────────────────────────

    async def scrape_listing(self, url: str, category: str = "", neck_type_hint: str = "") -> Optional[dict]:
        page = await self.new_page()
        try:
            if not await self.safe_goto(page, url):
                return None
            if await self._is_blocked(page):
                logger.error(
                    f"Nordstrom blocked automated traffic on product page "
                    f"{url}; redirected to {page.url}"
                )
                return None

            await self._human_mouse_move(page)

            variant_stock = await self._collect_variant_stock(page)
            # Only scroll if __NEXT_DATA__ failed and we need DOM-rendered content
            if not variant_stock:
                await self._scroll_to_load(page)
                variant_stock = await self._collect_variant_stock(page)

            soup = BeautifulSoup(await page.content(), "lxml")
            return self._parse_product(soup, url, neck_type_hint, variant_stock)

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None
        finally:
            await page.close()

    # ── Parse product page HTML ──────────────────────────────────────────────

    def _parse_product(
        self,
        soup: BeautifulSoup,
        url: str,
        neck_type_hint: str,
        variant_stock: Optional[list[dict]] = None,
    ) -> Optional[dict]:
        try:
            ld = self._extract_json_ld(soup)

            title = (ld or {}).get("name", "")
            if not title:
                h1 = soup.find("h1")
                title = h1.get_text(strip=True) if h1 else ""
            if not title:
                return None

            brand = ""
            if ld and "brand" in ld:
                b = ld["brand"]
                brand = b.get("name", "") if isinstance(b, dict) else str(b)
            if not brand:
                el = soup.select_one("span[itemprop='name']")
                brand = el.get_text(strip=True) if el else ""

            current_price = None
            original_price = None
            price_text = None
            discount_text = None
            if ld and "offers" in ld:
                offers = ld["offers"]
                if isinstance(offers, list):
                    offers = offers[0]
                try:
                    current_price = float(offers.get("price") or 0) or None
                except (TypeError, ValueError):
                    pass
            el = soup.select_one("[data-botify-lu='current-price']")
            if el:
                price_text = el.get_text(" ", strip=True)
            dom_price = self._parse_price(price_text or "")
            if dom_price is not None:
                current_price = dom_price
            el = soup.select_one("[data-botify-lu='initial-price'], [data-botify-lu='original-price']")
            if el:
                original_price = self._parse_price(el.get_text(" ", strip=True))
            el = soup.select_one("[data-botify-lu='percent-discount']")
            if el:
                discount_text = el.get_text(" ", strip=True)

            colors = []
            for img in soup.select("ul#product-page-color-swatches img.EgvtC"):
                alt = img.get("alt", "").replace("selected", "").strip()
                if alt:
                    colors.append(alt)
            if not colors:
                strong = soup.select_one("div.Mv4wF strong")
                if strong:
                    colors.append(strong.get_text(strip=True))
            if variant_stock:
                variant_colors = [item.get("color") for item in variant_stock if item.get("color")]
                if variant_colors:
                    colors = variant_colors
            color = ", ".join(colors) if colors else None

            sizes = []
            for li in soup.select("ul#size-filter-product-page-option-list li"):
                span = li.select_one("span.G75tb")
                if span:
                    s = span.get_text(strip=True)
                    if s:
                        sizes.append(s)
            if variant_stock:
                variant_sizes = []
                for variant in variant_stock:
                    for item in variant.get("sizes") or []:
                        if item.get("size") and item["size"] not in variant_sizes:
                            variant_sizes.append(item["size"])
                if variant_sizes:
                    sizes = variant_sizes
            size = ", ".join(sizes) if sizes else None

            details_text = self._extract_details_text(soup)
            description = self._clean_text(details_text) or None
            full_lower = f"{title} {details_text}".lower()

            neck_type = None
            if neck_type_hint in ("crewneck", "graphic"):
                neck_type = "crewneck"
            if not neck_type:
                for kw, val in _NECK_MAP.items():
                    if kw in full_lower:
                        neck_type = val
                        break

            fit = None
            for kw in _FIT_KEYWORDS:
                if kw in full_lower:
                    fit = kw
                    break

            pattern = None
            for kw, val in _PATTERN_MAP.items():
                if kw in full_lower:
                    pattern = val
                    break
            if pattern is None and neck_type_hint == "graphic":
                pattern = "graphic"

            material = None
            m = _MATERIAL_PAT.search(details_text)
            if m:
                material = m.group(0)
            if not material:
                for label in ["Fabric:", "Material:", "Content:", "Fabric Content:"]:
                    idx = details_text.find(label)
                    if idx != -1:
                        snippet = details_text[idx + len(label): idx + 80]
                        material = snippet.split(".")[0].strip()
                        break
            care_instructions = self._extract_care_instructions(details_text)

            rating, review_count = None, 0
            review_details = self._parse_review_details(soup)
            if ld and "aggregateRating" in ld:
                ar = ld["aggregateRating"]
                try:
                    rating = float(ar.get("ratingValue") or 0) or None
                except (TypeError, ValueError):
                    pass
                try:
                    review_count = int(ar.get("reviewCount") or ar.get("ratingCount") or 0)
                except (TypeError, ValueError):
                    pass
            if rating is None:
                el = soup.find("span", {"itemprop": "ratingValue"})
                if el:
                    try:
                        rating = float(el.get_text(strip=True))
                    except ValueError:
                        pass
            if review_count == 0:
                el = soup.find("span", {"itemprop": "reviewCount"})
                if el:
                    try:
                        review_count = int(re.sub(r"[^\d]", "", el.get_text()))
                    except ValueError:
                        pass
            if rating is None:
                rating = review_details.get("rating")
            if review_count == 0:
                review_count = review_details.get("review_count") or 0

            discount_percent = None
            if current_price and original_price and original_price > current_price:
                discount_percent = round((original_price - current_price) / original_price * 100, 2)
            if discount_percent is None and discount_text:
                discount_percent = self._parse_discount_percent(discount_text)

            return {
                # ── SkuListing fields ──────────────────────────────────────
                "platform":       "nordstrom",
                "platform_id":    2,
                "url":            url,
                "title":          title,
                "brand":          brand or None,
                "description":    description,
                "category":       "mens_tshirts",
                "gender":         "men",
                "sub_category":   neck_type_hint or None,
                "current_price":  current_price,
                "currency":       "USD",
                "rating":         rating,
                "review_count":   review_count,
                "data_label":     "demonstration_data",
                # ── SkuAttribute fields ────────────────────────────────────
                "size":           size,
                "color":          color,
                "pattern":        pattern,
                "material":       material,
                "neck_type":      neck_type,
                "sleeve_type":    "short sleeve",
                "fit":            fit,
                "care_instructions": care_instructions,
                "stock_json":     json.dumps(variant_stock or [], ensure_ascii=True),
                # ── PriceSnapshot extras ───────────────────────────────────
                "original_price":    original_price,
                "discount_percent":  discount_percent,
                "price_text":         price_text,
                "discount_text":      discount_text,
                "review_details_json": json.dumps(review_details, ensure_ascii=True),
            }

        except Exception as e:
            logger.error(f"Parse error for {url}: {e}")
            return None

    # ── Helpers ──────────────────────────────────────────────────────────────

    async def _collect_variant_stock(self, page) -> list[dict]:
        """
        Collect color × size availability with minimal DOM interactions.
        Price is read once per color (T-shirt prices don't vary by size).
        """
        colors = await self._get_color_controls(page)

        if not colors:
            price = await self._read_price_from_page(page)
            sizes = await self._get_size_controls(page)
            return [{"color": None, "sizes": [
                {"size": s["size"], "available": s["available"], **price}
                for s in sizes
            ]}] if sizes else []

        variants = []
        for idx, color in enumerate(colors):
            color_name = color.get("name")
            try:
                if idx > 0:
                    try:
                        await color["locator"].evaluate("el => el.click()")
                    except Exception:
                        await color["locator"].click(timeout=2000, force=True)
                    await asyncio.sleep(random.uniform(0.5, 1.0))

                price = await self._read_price_from_page(page)
                sizes = await self._get_size_controls(page)
                variants.append({"color": color_name, "sizes": [
                    {"size": s["size"], "available": s["available"], **price}
                    for s in sizes
                ]})
            except Exception as e:
                logger.debug(f"Could not collect stock for color {color_name}: {e}")
                continue

        return variants

    async def _get_color_controls(self, page) -> list[dict]:
        controls = []

        # Nordstrom swatches are clickable on <button>, not <img>
        candidates = page.locator("ul#product-page-color-swatches button")
        count = await candidates.count()

        for i in range(count):
            btn = candidates.nth(i)

            try:
                img = btn.locator("img.EgvtC")
                name = await img.get_attribute("alt")
                name = self._clean_text((name or "").replace("selected", ""))

                if not name:
                    continue

                controls.append({
                    "name": name,
                    "locator": btn,
                })

            except Exception:
                continue

        return controls
    async def _get_size_controls(self, page) -> list[dict]:
        ul = page.locator("ul#size-filter-product-page-option-list")
        try:
            is_visible = await ul.is_visible(timeout=500)
        except Exception:
            is_visible = False

        if not is_visible:
            try:
                await page.locator("#size-filter-product-page-anchor").evaluate("el => el.click()")
                await asyncio.sleep(random.uniform(0.2, 0.4))
            except Exception:
                pass

        try:
            await ul.wait_for(state="visible", timeout=4000)
        except Exception:
            return []

        sizes = []
        seen = set()
        items = ul.locator("li[role='option']")
        count = await items.count()

        for i in range(count):
            li = items.nth(i)
            try:
                # Read only the first span (size name), ignoring "Only N left" sibling span
                name_span = li.locator("span.G75tb").first
                size_name = self._clean_text(await name_span.inner_text(timeout=800))
                if not size_name or size_name.lower() in {"size", "select a size"}:
                    continue

                aria_disabled = await li.get_attribute("aria-disabled")
                class_name = await li.get_attribute("class") or ""
                unavailable = (
                    aria_disabled == "true"
                    or "unavailable" in class_name.lower()
                    or "disabled" in class_name.lower()
                )

                key = size_name.lower()
                if key not in seen:
                    seen.add(key)
                    sizes.append({"size": size_name, "available": not unavailable})
            except Exception:
                continue

        return sizes

    async def _read_price_from_page(self, page) -> dict:
        soup = BeautifulSoup(await page.content(), "lxml")
        current_el = soup.select_one("[data-botify-lu='current-price']")
        original_el = soup.select_one("[data-botify-lu='initial-price'], [data-botify-lu='original-price']")
        discount_el = soup.select_one("[data-botify-lu='percent-discount']")

        price_text = self._clean_text(current_el.get_text(" ", strip=True)) if current_el else None
        original_text = self._clean_text(original_el.get_text(" ", strip=True)) if original_el else None
        discount_text = self._clean_text(discount_el.get_text(" ", strip=True)) if discount_el else None

        discounted_price = self._parse_price(price_text or "")
        original_price = self._parse_price(original_text or "")
        discount_percent = None
        if discounted_price and original_price and original_price > discounted_price:
            discount_percent = round((original_price - discounted_price) / original_price * 100, 2)
        if discount_percent is None and discount_text:
            discount_percent = self._parse_discount_percent(discount_text)

        return {
            "discounted_price": discounted_price,
            "original_price": original_price,
            "price_text": price_text,
            "original_price_text": original_text,
            "discount_text": discount_text,
            "discount_percent": discount_percent,
            "currency": "USD",
        }

    async def _human_mouse_move(self, page):
        """Random mouse movements — behavioural signal that Akamai checks."""
        for _ in range(random.randint(2, 4)):
            x = random.randint(200, 1100)
            y = random.randint(200, 600)
            await page.mouse.move(x, y, steps=random.randint(5, 15))
            await asyncio.sleep(random.uniform(0.1, 0.4))

    async def _scroll_to_load(self, page):
        """Randomised scroll to trigger lazy-load and look human."""
        steps = random.randint(6, 10)
        for _ in range(steps):
            scroll_px = random.randint(300, 700)
            await page.evaluate(f"window.scrollBy(0, {scroll_px})")
            await asyncio.sleep(random.uniform(0.4, 1.1))
        await asyncio.sleep(random.uniform(0.5, 1.5))
        await page.evaluate("window.scrollTo(0, 0)")

    async def _is_blocked(self, page) -> bool:
        """Detect Nordstrom's Akamai bot-block redirect or inline message."""
        if "siteclosed.nordstrom.com" in page.url:
            return True
        try:
            body_text = await page.locator("body").inner_text(timeout=5000)
            lower = body_text.lower()
            if "unidentified, automated traffic" in lower:
                return True
            if "access denied" in lower:
                return True
        except Exception:
            pass
        return False

    def _extract_product_links(self, soup: BeautifulSoup) -> list[str]:
        seen: set[str] = set()
        links: list[str] = []
        for a in soup.find_all("a", href=True):
            path = urlparse(a["href"]).path
            if path.startswith("/s/") and path not in seen:
                seen.add(path)
                links.append(urljoin("https://www.nordstrom.com", path))
        return links

    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[dict]:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    for item in data:
                        if item.get("@type") == "Product":
                            return item
                elif data.get("@type") == "Product":
                    return data
            except Exception:
                continue
        return None

    def _extract_details_text(self, soup: BeautifulSoup) -> str:
        heading = soup.find(
            lambda tag: tag.name in {"h2", "h3"}
            and "details" in tag.get_text(" ", strip=True).lower()
            and "care" in tag.get_text(" ", strip=True).lower()
        )
        if heading:
            container = heading.find_parent("div")
            while container and container.name == "div":
                text = self._clean_text(container.get_text(" ", strip=True))
                if "details" in text.lower() and len(text) > 40:
                    return re.sub(r"^Details\s*&\s*care\s*", "", text, flags=re.I)
                container = container.find_parent("div")

        details_el = (
            soup.find("div", {"data-botify-lu": "product-addtl-details"})
            or soup.find("div", {"data-testid": "product-details"})
        )
        return details_el.get_text(" ", strip=True) if details_el else ""

    def _extract_care_instructions(self, details_text: str) -> Optional[str]:
        for part in re.split(r"\s{2,}|(?<=[a-z]) (?=[A-Z])", details_text):
            cleaned = self._clean_text(part)
            if re.search(r"\b(machine wash|hand wash|dry clean|tumble dry|line dry)\b", cleaned, re.I):
                return cleaned
        m = re.search(r"((?:machine|hand)\s+wash[^.]*|dry clean[^.]*)", details_text, re.I)
        return self._clean_text(m.group(1)) if m else None

    def _parse_price(self, text: str) -> Optional[float]:
        m = re.search(r"[\d]+\.?\d*", (text or "").replace(",", ""))
        try:
            return float(m.group(0)) if m else None
        except (ValueError, AttributeError):
            return None

    def _parse_discount_percent(self, text: str) -> Optional[float]:
        m = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        try:
            return float(m.group(1)) if m else None
        except (ValueError, AttributeError):
            return None

    def _parse_review_details(self, soup: BeautifulSoup) -> dict:
        details = {
            "rating": None,
            "review_count": 0,
            "fit": None,
            "star_distribution": {},
            "pros": [],
            "cons": [],
        }

        rating_text = soup.find(string=re.compile(r"\d+(?:\.\d+)?\s+out of 5", re.I))
        if rating_text:
            m = re.search(r"(\d+(?:\.\d+)?)\s+out of 5", str(rating_text), re.I)
            if m:
                details["rating"] = float(m.group(1))

        count_el = soup.select_one(".RHpZP")
        if count_el:
            try:
                details["review_count"] = int(re.sub(r"[^\d]", "", count_el.get_text(" ", strip=True)))
            except ValueError:
                pass
        if details["review_count"] == 0:
            counts = []
            for text in soup.find_all(string=re.compile(r"\(\s*[\d,]+\s*\)")):
                try:
                    counts.append(int(re.sub(r"[^\d]", "", str(text))))
                except ValueError:
                    pass
            if counts:
                details["review_count"] = max(counts)

        fit_label = soup.find(string=re.compile(r"^\s*Fit:\s*$", re.I))
        if fit_label:
            container = fit_label.find_parent("div")
            if not container:
                parent = fit_label.find_parent()
                container = parent.find_parent("div") if parent else None
            if container:
                text = self._clean_text(container.get_text(" ", strip=True))
                details["fit"] = re.sub(r"^Fit:\s*", "", text, flags=re.I) or None

        for row in soup.select("[data-qm-element-id='pdp-review-star-filter'] .COStO"):
            text = self._clean_text(row.get_text(" ", strip=True))
            m = re.search(r"([1-5])\s+stars?\s+(\d+)%", text, re.I)
            if m:
                details["star_distribution"][m.group(1)] = int(m.group(2))

        for selector, key in [
            ("[data-qm-element-id='pdp-review-pro-button'] span", "pros"),
            ("[data-qm-element-id='pdp-review-con-button'] span", "cons"),
        ]:
            for el in soup.select(selector):
                text = self._clean_text(el.get_text(" ", strip=True))
                if text:
                    details[key].append(text)

        return details

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()
