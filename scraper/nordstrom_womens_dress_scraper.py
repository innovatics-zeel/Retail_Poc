"""
nordstrom_womens_dress_scraper.py
Scrapes Nordstrom women's dresses from the main dresses category.

Output design:
- stock_price_json: color-wise variants with size availability and price display info
- attributes_json: dress attributes like neck_type, material, fit, length, occasion, care, etc.
- review_json: rating, review count, review fit, stars, pros, cons
- raw_product_json: one clean managed JSON object containing product + variants + attributes + reviews
- Also writes one JSON file containing all scraped products.
"""
import re
import json
import asyncio
import random
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode, urljoin, urlparse

from bs4 import BeautifulSoup
from loguru import logger

from scraper.base_scraper import BaseScraper
from scraper.schemas import WomensDressData
from database.models import NordstromWomensDress

try:
    from camoufox.async_api import AsyncCamoufox
    USE_CAMOUFOX = True
    logger.info("[INIT] camoufox found — using patched Firefox")
except ImportError:
    USE_CAMOUFOX = False
    logger.warning("[INIT] camoufox not installed")

try:
    from patchright.async_api import async_playwright as patchright_playwright
    USE_PATCHRIGHT = True
    logger.info("[INIT] patchright found")
except ImportError:
    USE_PATCHRIGHT = False
    logger.warning("[INIT] patchright not found")

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
    logger.warning("[INIT] playwright-stealth not found")


STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined, configurable: true });
Object.defineProperty(navigator, 'plugins', { get: () => {
    const arr = [{ name: 'Chrome PDF Plugin' }, { name: 'Chrome PDF Viewer' }, { name: 'Native Client' }];
    Object.defineProperty(arr, 'length', { value: 3 });
    return arr;
}});
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
window.chrome = { app: { isInstalled: false }, runtime: { onConnect: { addListener: () => {} }, onMessage: { addListener: () => {} } } };
const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
if (originalQuery) {
    window.navigator.permissions.query = (params) =>
        params.name === 'notifications' ? Promise.resolve({ state: Notification.permission }) : originalQuery(params);
}
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
"""

WOMENS_DRESS_BASE = "https://www.nordstrom.com/browse/women/clothing/dresses"
INR_TO_USD = 0.012

_MATERIAL_PAT = re.compile(r"\d+%\s*[\w\-]+(?:\s*[,/&]\s*\d+%\s*[\w\-]+)*", re.I)

_DRESS_NECK_MAP = {
    "strapless": "strapless",
    "halter": "halter",
    "v-neck": "v-neck",
    "v neck": "v-neck",
    "square neck": "square neck",
    "scoop neck": "scoop neck",
    "crewneck": "crewneck",
    "crew neck": "crewneck",
    "one-shoulder": "one-shoulder",
    "one shoulder": "one-shoulder",
    "off-the-shoulder": "off-the-shoulder",
    "off the shoulder": "off-the-shoulder",
    "mock neck": "mock neck",
    "collared": "collared",
}

_DRESS_LENGTH_MAP = {
    "mini": "mini",
    "midi": "midi",
    "maxi": "maxi",
    "floor-length": "floor-length",
    "floor length": "floor-length",
    "knee-length": "knee-length",
    "knee length": "knee-length",
}

_OCCASION_MAP = {
    "vacation": "vacation",
    "casual": "casual",
    "cocktail": "cocktail",
    "party": "party",
    "wedding": "wedding",
    "evening": "evening",
    "work": "work",
    "formal": "formal",
}

_FIT_KEYWORDS = ["slim", "regular", "relaxed", "body-con", "bodycon", "fitted", "loose", "oversized", "a-line", "shift", "sheath"]
_PATTERN_MAP = {
    "floral": "floral",
    "striped": "striped",
    "stripe": "striped",
    "solid": "solid",
    "plain": "solid",
    "printed": "printed",
    "print": "printed",
    "plaid": "plaid",
    "polka dot": "polka dot",
    "lace": "lace",
    "embroidered": "embroidered",
}
_CLOSURE_MAP = {
    "zip closure": "zip",
    "back zip": "zip",
    "hidden zip": "zip",
    "button closure": "button",
    "button-front": "button",
    "tie closure": "tie",
    "pullover": "pullover",
    "pull-on": "pull-on",
}


class NordstromWomensDressScraper(BaseScraper):
    PLATFORM = "nordstrom"
    CATEGORY = "womens_dresses"
    SCHEMA_CLASS = WomensDressData
    DB_MODEL = NordstromWomensDress

    @staticmethod
    def to_db_values(data: WomensDressData) -> dict:
        return {
            "platform":          data.platform,
            "platform_id":       data.platform_id,
            "url":               str(data.url),
            "title":             data.title,
            "brand":             data.brand,
            "description":       data.description,
            "category":          data.category,
            "gender":            data.gender,
            "currency":          data.currency,
            "stock_price_json":  data.stock_price_json,
            "attributes_json":   data.attributes_json,
            "review_json":       data.review_json,
            "raw_product_json":  data.raw_product_json,
            "json_file_path":    data.json_file_path,
            "data_label":        data.data_label,
            "poc_run_id":        data.poc_run_id,
        }

    def __init__(self, json_output_path: str = "data/nordstrom_womens_dresses.json"):
        super().__init__()
        self._mode = None
        self._camoufox_mgr = None
        self.json_output_path = Path(json_output_path)

    async def start(self):
        if USE_CAMOUFOX:
            await self._start_camoufox()
        elif USE_PATCHRIGHT:
            await self._start_patchright()
        else:
            await self._start_playwright()

    async def _start_camoufox(self):
        logger.info("[BROWSER] Starting camoufox")
        self._camoufox_mgr = AsyncCamoufox(headless=False)
        self.browser = await self._camoufox_mgr.__aenter__()
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
        await self.context.clear_cookies()
        await self.context.add_init_script(STEALTH_SCRIPT)
        self._mode = "camoufox"

    async def _start_patchright(self):
        logger.info("[BROWSER] Starting patchright")
        self.playwright = await patchright_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox"],
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
        await self.context.clear_cookies()
        await self.context.add_init_script(STEALTH_SCRIPT)
        self._mode = "patchright"

    async def _start_playwright(self):
        logger.info("[BROWSER] Starting playwright + Chrome")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            channel="chrome",
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox"],
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
        await self.context.clear_cookies()
        await self.context.add_init_script(STEALTH_SCRIPT)
        self._mode = "playwright"

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
        logger.info("[BROWSER] stopped")

    async def new_page(self):
        page = await self.context.new_page()
        if HAS_STEALTH and self._mode == "playwright":
            await stealth_async(page)
        return page

    async def search_category(self, category: str = "womens_dresses", max_products: int = 10) -> list[dict]:
        if category != "womens_dresses":
            raise ValueError(f"Only womens_dresses supported, got: {category}")

        collected: list[str] = []
        seen_urls: set[str] = set()
        page = await self.new_page()

        page_num = 1
        last_page = None
        while len(collected) < max_products:
            category_url = self._category_url(page_num)
            logger.info(f"Women dresses page {page_num} -> {category_url}")

            if not await self.safe_goto(page, category_url):
                break
            if await self._is_blocked(page):
                logger.error(f"Nordstrom blocked automated traffic, redirected to {page.url}")
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
                    collected.append(link)
                    new_links += 1
                    if len(collected) >= max_products:
                        break

            if last_page is None:
                last_page = self._extract_last_page(soup)
            if new_links == 0:
                break
            if last_page is not None and page_num >= last_page:
                break
            if page_num > 200:
                logger.warning("Stopping pagination at 200 pages")
                break

            page_num += 1
            await self.polite_delay()

        await page.close()

        results = []
        for i, url in enumerate(collected[:max_products]):
            logger.info(f"[{i + 1}/{min(len(collected), max_products)}] {url}")
            data = await self.scrape_listing(url)
            if data:
                results.append(data)
            await self.polite_delay()

        self._write_products_json(results)
        logger.info(f"Nordstrom womens_dresses: {len(results)} products scraped")
        return results

    def _category_url(self, page_num: int) -> str:
        query = {"breadcrumb": "Home/Women/Clothing/Dresses"}
        if page_num > 1:
            query["page"] = str(page_num)
        return f"{WOMENS_DRESS_BASE}?{urlencode(query)}"

    async def scrape_listing(self, url: str, category: str = "womens_dresses") -> Optional[dict]:
        page = await self.new_page()
        try:
            if not await self.safe_goto(page, url):
                return None
            if await self._is_blocked(page):
                logger.error(f"Nordstrom blocked product page {url}; redirected to {page.url}")
                return None

            await self._human_mouse_move(page)
            stock_price = await self._collect_variant_stock_price(page)
            if not stock_price:
                await self._scroll_to_load(page)
                stock_price = await self._collect_variant_stock_price(page)

            soup = BeautifulSoup(await page.content(), "lxml")
            return self._parse_product(soup, url, stock_price)
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None
        finally:
            await page.close()

    def _parse_product(self, soup: BeautifulSoup, url: str, stock_price: Optional[list[dict]] = None) -> Optional[dict]:
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

            details = self._extract_details(soup)
            details_text = details["details_text"]
            description = details["description"] or self._clean_text(details_text) or None
            attributes = self._parse_attributes(title, details_text)
            review = self._parse_review_details(soup, ld)

            colors = [v.get("color") for v in (stock_price or []) if v.get("color")]
            sizes = []
            for variant in stock_price or []:
                for size in variant.get("sizes") or []:
                    if size.get("size") and size["size"] not in sizes:
                        sizes.append(size["size"])

            raw_product = {
                "platform": "nordstrom",
                "platform_id": 2,
                "url": url,
                "title": title,
                "brand": brand or None,
                "description": description,
                "category": "womens_dresses",
                "gender": "women",
                "currency": "USD",
                "colors": colors,
                "sizes": sizes,
                "stock_price": stock_price or [],
                "attributes": attributes,
                "review": review,
            }

            return {
                "platform": "nordstrom",
                "platform_id": 2,
                "url": url,
                "title": title,
                "brand": brand or None,
                "description": description,
                "category": "womens_dresses",
                "gender": "women",
                "currency": "USD",
                "stock_price_json": json.dumps(stock_price or [], ensure_ascii=False),
                "attributes_json": json.dumps(attributes, ensure_ascii=False),
                "review_json": json.dumps(review, ensure_ascii=False),
                "raw_product_json": json.dumps(raw_product, ensure_ascii=False),
                "json_file_path": str(self.json_output_path),
                "data_label": "demonstration_data",
            }
        except Exception as e:
            logger.error(f"Parse error for {url}: {e}")
            return None

    async def _collect_variant_stock_price(self, page) -> list[dict]:
        colors = await self._get_color_controls(page)

        if not colors:
            price = await self._read_price_from_page(page)
            sizes = await self._get_size_controls(page)
            return [{"color": None, "sizes": [{**s, **price} for s in sizes]}] if sizes else []

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
                variants.append({"color": color_name, "sizes": [{**s, **price} for s in sizes]})
            except Exception as e:
                logger.debug(f"Could not collect variant for color {color_name}: {e}")
                continue
        return variants

    async def _get_color_controls(self, page) -> list[dict]:
        controls = []
        candidates = page.locator("ul#product-page-color-swatches button")
        count = await candidates.count()
        for i in range(count):
            btn = candidates.nth(i)
            try:
                img = btn.locator("img.EgvtC")
                name = await img.get_attribute("alt")
                name = self._clean_text((name or "").replace("selected", ""))
                if name:
                    controls.append({"name": name, "locator": btn})
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
                name_span = li.locator("span.G75tb").first
                size_name = self._clean_text(await name_span.inner_text(timeout=800))
                if not size_name or size_name.lower() in {"size", "select a size"}:
                    continue

                aria_disabled = await li.get_attribute("aria-disabled")
                class_name = await li.get_attribute("class") or ""
                full_text = self._clean_text(await li.inner_text(timeout=800))
                lower_text = full_text.lower()

                unavailable = (
                    aria_disabled == "true"
                    or "unavailable" in class_name.lower()
                    or "disabled" in class_name.lower()
                    or "not available" in lower_text
                    or "sold out" in lower_text
                    or "out of stock" in lower_text
                    or "unavailable" in lower_text
                )

                key = size_name.lower()
                if key not in seen:
                    seen.add(key)
                    sizes.append({
                        "size": size_name,
                        "available": not unavailable,
                        "stock_text": full_text,
                    })
            except Exception:
                continue
        return sizes

    async def _read_price_from_page(self, page) -> dict:
        soup = BeautifulSoup(await page.content(), "lxml")
        current_el = soup.select_one(
            "[data-botify-lu='current-price'], [data-testid='current-price'], "
            "[class*='current-price'], [aria-label*='Current price']"
        )
        original_el = soup.select_one(
            "[data-botify-lu='initial-price'], [data-botify-lu='original-price'], "
            "[data-testid='original-price'], [data-testid='strikethrough-price'], "
            "[class*='original-price'], [class*='strikethrough'], s"
        )
        discount_el = soup.select_one(
            "[data-botify-lu='percent-discount'], [data-testid='percent-off'], [class*='discount']"
        )

        price_text_raw = self._clean_text(current_el.get_text(" ", strip=True)) if current_el else None
        original_text_raw = self._clean_text(original_el.get_text(" ", strip=True)) if original_el else None
        discount_text = self._clean_text(discount_el.get_text(" ", strip=True)) if discount_el else None

        current_price = self._parse_price(price_text_raw or "")
        original_price = self._parse_price(original_text_raw or "")
        discount_percent = None
        if current_price and original_price and original_price > current_price:
            discount_percent = round((original_price - current_price) / original_price * 100, 2)
        if discount_percent is None and discount_text:
            discount_percent = self._parse_discount_percent(discount_text)

        # No numeric price fields here; only display text + discount info.
        return {
            "price_text": f"${current_price}" if current_price is not None else price_text_raw,
            "original_price_text": f"${original_price}" if original_price is not None else original_text_raw,
            "discount_text": discount_text,
            "discount_percent": discount_percent,
            "currency": "USD",
        }

    def _parse_attributes(self, title: str, details_text: str) -> dict:
        full_lower = f"{title} {details_text}".lower()

        def find_from_map(mapping: dict[str, str]) -> Optional[str]:
            for kw, val in mapping.items():
                if kw in full_lower:
                    return val
            return None

        material = None
        m = _MATERIAL_PAT.search(details_text)
        if m:
            material = m.group(0)
        if not material:
            for label in ["Fabric:", "Material:", "Content:", "Fabric Content:"]:
                idx = details_text.find(label)
                if idx != -1:
                    material = details_text[idx + len(label): idx + 100].split(".")[0].strip()
                    break

        fit = None
        for kw in _FIT_KEYWORDS:
            if kw in full_lower:
                fit = "bodycon" if kw == "body-con" else kw
                break

        return {
            "neck_type": find_from_map(_DRESS_NECK_MAP),
            "dress_length": find_from_map(_DRESS_LENGTH_MAP),
            "occasion": find_from_map(_OCCASION_MAP),
            "fit": fit,
            "pattern": find_from_map(_PATTERN_MAP),
            "closure_type": find_from_map(_CLOSURE_MAP),
            "material": material,
            "care_instructions": self._extract_care_instructions(details_text),
            "sleeve_type": self._extract_sleeve_type(full_lower),
            "details_text": self._clean_text(details_text) or None,
        }

    def _extract_sleeve_type(self, full_lower: str) -> Optional[str]:
        for kw in ["sleeveless", "short sleeve", "long sleeve", "cap sleeve", "puff sleeve", "spaghetti strap", "strapless"]:
            if kw in full_lower:
                return kw
        return None

    def _extract_details(self, soup: BeautifulSoup) -> dict:
        description = None
        details_parts = []

        # Nordstrom details block, including user-provided PIu5W/d13vj HTML pattern.
        details_block = (
            soup.select_one("div.PIu5W")
            or soup.find("div", {"data-botify-lu": "product-addtl-details"})
            or soup.find("div", {"data-testid": "product-details"})
        )
        if details_block:
            p = details_block.find("p")
            if p:
                description = self._clean_text(p.get_text(" ", strip=True))
            for li in details_block.select("li span, li"):
                text = self._clean_text(li.get_text(" ", strip=True))
                if text and text not in details_parts:
                    details_parts.append(text)

        if not details_parts:
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
                        details_parts.append(re.sub(r"^Details\s*&\s*care\s*", "", text, flags=re.I))
                        break
                    container = container.find_parent("div")

        details_text = self._clean_text(" ".join(details_parts))
        return {"description": description, "details_text": details_text}

    def _parse_review_details(self, soup: BeautifulSoup, ld: Optional[dict] = None) -> dict:
        details = {
            "rating": None,
            "review_count": 0,
            "fit": None,
            "star_distribution": {},
            "pros": [],
            "cons": [],
        }

        if ld and "aggregateRating" in ld:
            ar = ld["aggregateRating"]
            try:
                details["rating"] = float(ar.get("ratingValue") or 0) or None
            except (TypeError, ValueError):
                pass
            try:
                details["review_count"] = int(ar.get("reviewCount") or ar.get("ratingCount") or 0)
            except (TypeError, ValueError):
                pass

        if details["rating"] is None:
            rating_text = soup.find(string=re.compile(r"\d+(?:\.\d+)?\s+out of 5", re.I))
            if rating_text:
                m = re.search(r"(\d+(?:\.\d+)?)\s+out of 5", str(rating_text), re.I)
                if m:
                    details["rating"] = float(m.group(1))

        if details["review_count"] == 0:
            count_el = soup.select_one(".RHpZP")
            if count_el:
                try:
                    details["review_count"] = int(re.sub(r"[^\d]", "", count_el.get_text(" ", strip=True)))
                except ValueError:
                    pass

        fit_label = soup.find(string=re.compile(r"^\s*Fit:\s*$", re.I))
        if fit_label:
            container = fit_label.find_parent("div") or fit_label.find_parent()
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

    def _write_products_json(self, rows: list[dict]) -> None:
        try:
            self.json_output_path.parent.mkdir(parents=True, exist_ok=True)
            products = []
            for row in rows:
                raw = row.get("raw_product_json")
                if raw:
                    products.append(json.loads(raw))
            self.json_output_path.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
            logger.info(f"Wrote product JSON file: {self.json_output_path}")
        except Exception as e:
            logger.warning(f"Could not write product JSON file: {e}")

    async def _human_mouse_move(self, page):
        for _ in range(random.randint(2, 4)):
            await page.mouse.move(random.randint(200, 1100), random.randint(200, 600), steps=random.randint(5, 15))
            await asyncio.sleep(random.uniform(0.1, 0.4))

    async def _scroll_to_load(self, page):
        for _ in range(random.randint(6, 10)):
            await page.evaluate(f"window.scrollBy(0, {random.randint(300, 700)})")
            await asyncio.sleep(random.uniform(0.4, 1.1))
        await asyncio.sleep(random.uniform(0.5, 1.5))
        await page.evaluate("window.scrollTo(0, 0)")

    async def _is_blocked(self, page) -> bool:
        if "siteclosed.nordstrom.com" in page.url:
            return True
        try:
            lower = (await page.locator("body").inner_text(timeout=5000)).lower()
            return "unidentified, automated traffic" in lower or "access denied" in lower
        except Exception:
            return False

    def _extract_product_links(self, soup: BeautifulSoup) -> list[str]:
        seen = set()
        links = []
        for a in soup.find_all("a", href=True):
            path = urlparse(a["href"]).path
            if path.startswith("/s/") and path not in seen:
                seen.add(path)
                links.append(urljoin("https://www.nordstrom.com", path))
        return links

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

    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[dict]:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("@type") == "Product":
                            return item
                elif isinstance(data, dict) and data.get("@type") == "Product":
                    return data
            except Exception:
                continue
        return None

    def _extract_care_instructions(self, details_text: str) -> Optional[str]:
        for part in re.split(r"\s{2,}|(?<=[a-z]) (?=[A-Z])", details_text):
            cleaned = self._clean_text(part)
            if re.search(r"\b(machine wash|hand wash|dry clean|tumble dry|dry flat|line dry)\b", cleaned, re.I):
                return cleaned
        m = re.search(r"((?:machine|hand)\s+wash[^.]*|dry clean[^.]*)", details_text, re.I)
        return self._clean_text(m.group(1)) if m else None

    def _parse_price(self, text: str) -> Optional[float]:
        raw = (text or "").replace(",", "")
        m = re.search(r"[\d]+\.?\d*", raw)
        if not m:
            return None
        price = float(m.group(0))
        if "₹" in raw or "INR" in raw.upper() or "RS" in raw.upper():
            return round(price * INR_TO_USD, 2)
        return round(price, 2)

    def _parse_discount_percent(self, text: str) -> Optional[float]:
        m = re.search(r"(\d+(?:\.\d+)?)\s*%", text or "")
        try:
            return float(m.group(1)) if m else None
        except (ValueError, AttributeError):
            return None

    def _clean_text(self, text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()
