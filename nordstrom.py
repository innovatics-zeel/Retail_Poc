"""
nordstrom_poc_v2.py  —  Stealth bypass for siteclosed.nordstrom.com

WHY THE OLD VERSION FAILED:
  Nordstrom uses Akamai Bot Manager which detects bots via:
    1. TLS fingerprint  (JA3/JA4) — Playwright Chromium has a unique signature
    2. HTTP/2 fingerprint          — header order / pseudo-header order differs from real Chrome
    3. navigator.webdriver         — CDP flag not fully erased in old code
    4. Canvas / WebGL fingerprint  — headless Chromium has a distinct GPU fingerprint

FIX STRATEGY (layered):
  Layer 1 → camoufox  : patched Firefox that randomises TLS + canvas fingerprints
  Layer 2 → playwright-stealth : patches remaining JS tells
  Layer 3 → real delays + mouse movement : behavioural signals

INSTALL:
    pip install camoufox[geoip] playwright-stealth beautifulsoup4 lxml
    python -m camoufox fetch          # downloads patched Firefox binary (~100 MB)
    
    # If camoufox install fails, fallback to system Chrome:
    pip install playwright-stealth beautifulsoup4 lxml
    playwright install chrome          # installs Google Chrome channel
"""

import re
import json
import asyncio
import random
import time
from typing import Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# ── Try camoufox first, fall back to patchright, then plain playwright ────────
try:
    from camoufox.async_api import AsyncCamoufox
    USE_CAMOUFOX = True
    print("[INIT] ✓ camoufox found — using patched Firefox (best stealth)")
except ImportError:
    USE_CAMOUFOX = False
    print("[INIT] camoufox not installed — pip install camoufox[geoip] && python -m camoufox fetch")

try:
    from patchright.async_api import async_playwright as patchright_playwright
    USE_PATCHRIGHT = True
    print("[INIT] ✓ patchright found — using CDP-patched Chrome")
except ImportError:
    USE_PATCHRIGHT = False
    print("[INIT] patchright not found — pip install patchright && patchright install chrome")

try:
    from playwright.async_api import async_playwright
    from playwright_stealth import stealth_async
    HAS_STEALTH = True
    print("[INIT] ✓ playwright-stealth found")
except ImportError:
    HAS_STEALTH = False
    print("[INIT] playwright-stealth not found: pip install playwright-stealth")

# ── Config ────────────────────────────────────────────────────────────────────

MAX_PRODUCTS = 10
HEADLESS     = T    # KEEP False — visible browser is harder to fingerprint
DELAY_MIN    = 3.5
DELAY_MAX    = 6.0

SUBCATEGORIES = [
    ("crewneck", "https://www.nordstrom.com/browse/men/clothing/shirts/tshirts/crewneck"
                 "?breadcrumb=Home%2FMen%2FClothing%2FT-Shirts"),
    ("graphic",  "https://www.nordstrom.com/browse/men/clothing/shirts/tshirts/graphic"
                 "?breadcrumb=Home%2FMen%2FClothing%2FT-Shirts"),
]

_FIT_KEYWORDS = ["slim", "regular", "relaxed", "classic", "athletic", "loose", "tailored", "oversized"]
_MATERIAL_PAT = re.compile(r"\d+%\s*\w+(?:\s*[,/&]\s*\d+%\s*\w+)*", re.I)
_NECK_MAP = {
    "crewneck": "crewneck", "crew neck": "crewneck", "crew-neck": "crewneck",
    "v-neck": "v-neck",     "vneck": "v-neck",       "v neck": "v-neck",
    "polo": "polo",         "henley": "henley",
    "mock neck": "mock neck", "quarter zip": "quarter zip",
}


# ── Stealth JS patches ────────────────────────────────────────────────────────
# Applied via add_init_script — patches CDP/webdriver tells that Akamai checks

STEALTH_SCRIPT = """
// 1. Erase webdriver flag completely
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined,
    configurable: true
});

// 2. Spoof plugins (headless Chrome has 0 plugins)
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const arr = [{ name: 'Chrome PDF Plugin' }, { name: 'Chrome PDF Viewer' }, { name: 'Native Client' }];
        Object.defineProperty(arr, 'length', { value: 3 });
        return arr;
    }
});

// 3. Spoof languages
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });

// 4. Fix broken chrome runtime (headless has window.chrome === undefined)
window.chrome = {
    app: { isInstalled: false },
    runtime: {
        onConnect: { addListener: () => {} },
        onMessage: { addListener: () => {} }
    }
};

// 5. Spoof permissions API (headless returns 'denied' for notifications)
const originalQuery = window.navigator.permissions && window.navigator.permissions.query;
if (originalQuery) {
    window.navigator.permissions.query = (params) =>
        params.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(params);
}

// 6. Hide automation-related properties
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;

// 7. Fix hairline feature (headless returns wrong value)
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


# ── Human-like helpers ────────────────────────────────────────────────────────

async def human_mouse_move(page):
    """Random mouse movements to look human."""
    print("[MOUSE] Simulating human mouse movement...")
    for _ in range(random.randint(2, 4)):
        x = random.randint(200, 1100)
        y = random.randint(200, 600)
        await page.mouse.move(x, y, steps=random.randint(5, 15))
        await asyncio.sleep(random.uniform(0.1, 0.4))


def human_delay(label: str = ""):
    secs = random.uniform(DELAY_MIN, DELAY_MAX)
    print(f"[DELAY] {label} → {secs:.1f}s...")
    time.sleep(secs)


async def scroll_to_load(page):
    print("[SCROLL] Starting human-like scroll...")
    # Randomise scroll chunk size and timing (not robotic fixed increments)
    scroll_steps = random.randint(6, 10)
    for i in range(scroll_steps):
        scroll_px = random.randint(300, 700)
        await page.evaluate(f"window.scrollBy(0, {scroll_px})")
        await asyncio.sleep(random.uniform(0.4, 1.1))
        print(f"[SCROLL]   step {i+1}/{scroll_steps} (+{scroll_px}px)")
    await asyncio.sleep(random.uniform(0.5, 1.5))
    await page.evaluate("window.scrollTo(0, 0)")
    print("[SCROLL] ✓ Done")


# ── Block detection ───────────────────────────────────────────────────────────

async def is_blocked(page) -> bool:
    url = page.url
    print(f"[BLOCK-CHECK] Current URL: {url}")
    if "siteclosed.nordstrom.com" in url:
        print("[BLOCK-CHECK] ❌ siteclosed redirect — TLS/fingerprint block")
        return True
    try:
        body = await page.locator("body").inner_text(timeout=5000)
        if "unidentified, automated traffic" in body.lower():
            print("[BLOCK-CHECK] ❌ Bot message in body")
            return True
        if "access denied" in body.lower():
            print("[BLOCK-CHECK] ❌ Access denied in body")
            return True
    except Exception as e:
        print(f"[BLOCK-CHECK] Could not read body: {e}")
    print("[BLOCK-CHECK] ✓ Not blocked")
    return False


async def safe_goto(page, url: str) -> bool:
    print(f"[NAV] → {url}")
    try:
        resp = await page.goto(url, timeout=60_000, wait_until="domcontentloaded")
        code = resp.status if resp else "?"
        print(f"[NAV] Status: {code} | Final URL: {page.url}")
        if resp and resp.status >= 400:
            print(f"[NAV] ❌ HTTP {code}")
            return False
        await asyncio.sleep(random.uniform(1.5, 2.5))
        return True
    except Exception as e:
        print(f"[NAV] ❌ Failed: {e}")
        return False


# ── Camoufox page factory ─────────────────────────────────────────────────────

async def get_camoufox_page(browser):
    """Create a new page from camoufox browser with stealth init script."""
    print("[PAGE] Creating new camoufox page...")
    page = await browser.new_page()
    await page.add_init_script(STEALTH_SCRIPT)
    print("[PAGE] ✓ Page ready (camoufox)")
    return page


# ── Playwright + system Chrome page factory ───────────────────────────────────

async def get_playwright_page(context):
    """Create a new Playwright page with stealth patches."""
    print("[PAGE] Creating new playwright page...")
    page = await context.new_page()
    await page.add_init_script(STEALTH_SCRIPT)
    if HAS_STEALTH:
        await stealth_async(page)
        print("[PAGE] playwright-stealth applied ✓")
    print("[PAGE] ✓ Page ready (playwright + chrome)")
    return page


# ── Parsers (unchanged from v1) ───────────────────────────────────────────────

def extract_product_links(soup: BeautifulSoup) -> list[str]:
    print("[LINKS] Extracting product links...")
    seen: set[str] = set()
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        path = urlparse(a["href"]).path
        if path.startswith("/s/") and path not in seen:
            seen.add(path)
            links.append(urljoin("https://www.nordstrom.com", path))
    print(f"[LINKS] Found {len(links)} unique product links")
    return links


def extract_json_ld(soup: BeautifulSoup) -> Optional[dict]:
    print("[JSON-LD] Searching for Product JSON-LD...")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") == "Product":
                    print("[JSON-LD] ✓ Found")
                    return item
        except Exception as e:
            print(f"[JSON-LD] Parse error: {e}")
    print("[JSON-LD] Not found, using DOM fallbacks")
    return None


def parse_price(text: str) -> Optional[float]:
    m = re.search(r"[\d]+\.?\d*", text.replace(",", ""))
    try:
        return float(m.group(0)) if m else None
    except (ValueError, AttributeError):
        return None


def parse_product(soup: BeautifulSoup, url: str, neck_type_hint: str) -> Optional[dict]:
    print(f"\n[PARSE] === {url}")
    try:
        ld = extract_json_ld(soup)

        print("[PARSE] title...")
        title = (ld or {}).get("name", "")
        if not title:
            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else ""
        print(f"[PARSE] title → '{title}'")
        if not title:
            print("[PARSE] ❌ No title, skipping")
            return None

        print("[PARSE] brand...")
        brand = ""
        if ld and "brand" in ld:
            b = ld["brand"]
            brand = b.get("name", "") if isinstance(b, dict) else str(b)
        if not brand:
            el = soup.select_one("span[itemprop='name']")
            brand = el.get_text(strip=True) if el else ""
        print(f"[PARSE] brand → '{brand}'")

        print("[PARSE] price...")
        price = None
        if ld and "offers" in ld:
            offers = ld["offers"]
            if isinstance(offers, list): offers = offers[0]
            try:
                price = float(offers.get("price") or 0) or None
            except (TypeError, ValueError):
                pass
        if price is None:
            el = soup.select_one("[data-botify-lu='current-price']")
            if el:
                price = parse_price(el.get_text(strip=True))
        print(f"[PARSE] price → {price}")

        print("[PARSE] colors...")
        colors = []
        for img in soup.select("ul#product-page-color-swatches img.EgvtC"):
            alt = img.get("alt", "").replace("selected", "").strip()
            if alt:
                colors.append(alt)
        if not colors:
            strong = soup.select_one("div.Mv4wF strong")
            if strong:
                colors.append(strong.get_text(strip=True))
        color = ", ".join(colors) if colors else None
        print(f"[PARSE] color → '{color}'")

        print("[PARSE] sizes...")
        sizes = []
        for li in soup.select("ul#size-filter-product-page-option-list li"):
            span = li.select_one("span.G75tb")
            if span:
                s = span.get_text(strip=True)
                if s: sizes.append(s)
        size = ", ".join(sizes) if sizes else None
        print(f"[PARSE] sizes → {sizes}")

        print("[PARSE] details text...")
        details_el = (
            soup.find("div", {"data-botify-lu": "product-addtl-details"})
            or soup.find("div", {"data-testid": "product-details"})
        )
        details_text = details_el.get_text(" ", strip=True) if details_el else ""
        print(f"[PARSE] details (first 120): '{details_text[:120]}'")
        full_lower = f"{title} {details_text}".lower()

        neck_type = "crewneck" if neck_type_hint in ("crewneck", "graphic") else None
        if not neck_type:
            for kw, val in _NECK_MAP.items():
                if kw in full_lower:
                    neck_type = val
                    break
        print(f"[PARSE] neck_type → '{neck_type}'")

        fit = None
        for kw in _FIT_KEYWORDS:
            if kw in full_lower:
                fit = kw
                break
        print(f"[PARSE] fit → '{fit}'")

        material = None
        m = _MATERIAL_PAT.search(details_text)
        if m:
            material = m.group(0)
        if not material:
            for label in ["Fabric:", "Material:", "Content:", "Fabric Content:"]:
                idx = details_text.find(label)
                if idx != -1:
                    material = details_text[idx + len(label): idx + 80].split(".")[0].strip()
                    break
        print(f"[PARSE] material → '{material}'")

        rating, review_count = None, 0
        if ld and "aggregateRating" in ld:
            ar = ld["aggregateRating"]
            try:
                rating = float(ar.get("ratingValue") or 0) or None
                review_count = int(ar.get("reviewCount") or ar.get("ratingCount") or 0)
            except (TypeError, ValueError):
                pass
        print(f"[PARSE] rating → {rating} ({review_count} reviews)")

        print(f"[PARSE] ✓ Done: '{title}'")
        return {
            "platform": "nordstrom", "url": url,
            "title": title, "brand": brand or None, "price": price,
            "size": size, "color": color, "neck_type": neck_type,
            "fit": fit, "material": material,
            "rating": rating, "review_count": review_count,
        }
    except Exception as e:
        import traceback
        print(f"[PARSE] ❌ Error: {e}")
        traceback.print_exc()
        return None


# ── Core scrape loop ──────────────────────────────────────────────────────────

async def run_scrape_loop(get_page_fn, max_products: int) -> list[dict]:
    """
    Shared scrape loop — works with both camoufox and playwright page factories.
    get_page_fn: async callable that returns a fresh page with stealth applied.
    """
    collected: list[tuple[str, str]] = []
    all_results: list[dict] = []

    # Phase 1 — collect URLs
    print("\n--- PHASE 1: Collecting product URLs ---")
    for neck_hint, sub_url in SUBCATEGORIES:
        if len(collected) >= max_products:
            break
        print(f"\n[COLLECT] [{neck_hint}] → {sub_url}")
        page = await get_page_fn()

        ok = await safe_goto(page, sub_url)
        if not ok:
            print(f"[COLLECT] ❌ Nav failed for [{neck_hint}]")
            await page.close()
            continue

        if await is_blocked(page):
            print(f"[COLLECT] ❌ Blocked on [{neck_hint}]")
            await page.close()
            human_delay("post-block cooldown")
            continue

        await human_mouse_move(page)
        await scroll_to_load(page)

        soup = BeautifulSoup(await page.content(), "lxml")
        links = extract_product_links(soup)

        existing = {u for u, _ in collected}
        added = 0
        for link in links:
            if link not in existing:
                collected.append((link, neck_hint))
                existing.add(link)
                added += 1
        print(f"[COLLECT] Added {added} links (total so far: {len(collected)})")
        await page.close()
        human_delay(f"after [{neck_hint}]")

    to_scrape = collected[:max_products]
    print(f"\n[COLLECT] Total: {len(collected)} found → scraping {len(to_scrape)}")

    # Phase 2 — scrape each product
    print("\n--- PHASE 2: Scraping product pages ---")
    for i, (url, neck_hint) in enumerate(to_scrape):
        print(f"\n[PRODUCT {i+1}/{len(to_scrape)}] {url}")
        page = await get_page_fn()

        ok = await safe_goto(page, url)
        if not ok:
            print(f"[PRODUCT {i+1}] ❌ Nav failed, skipping")
            await page.close()
            continue

        if await is_blocked(page):
            print(f"[PRODUCT {i+1}] ❌ Blocked, skipping")
            await page.close()
            human_delay("post-block cooldown")
            continue

        await human_mouse_move(page)
        await scroll_to_load(page)

        print("[PRODUCT] Clicking size dropdown...")
        try:
            await page.click("#size-filter-product-page-anchor", timeout=3000)
            await asyncio.sleep(random.uniform(0.5, 1.0))
            print("[PRODUCT] Size dropdown clicked ✓")
        except Exception as e:
            print(f"[PRODUCT] Size dropdown not found / click failed: {e}")

        soup = BeautifulSoup(await page.content(), "lxml")
        data = parse_product(soup, url, neck_hint)
        if data:
            all_results.append(data)
            print(f"[PRODUCT {i+1}] ✓ {data['title']} | ${data['price']} | {data['brand']}")
        else:
            print(f"[PRODUCT {i+1}] ❌ parse returned None")

        await page.close()
        if i < len(to_scrape) - 1:
            human_delay(f"after product {i+1}")

    return all_results


# ── Main ──────────────────────────────────────────────────────────────────────

async def scrape_nordstrom(max_products: int = MAX_PRODUCTS):
    print("\n" + "="*60)
    print("  NORDSTROM POC v2 — STEALTH BYPASS")
    print("="*60)

    all_results = []

    if USE_CAMOUFOX:
        # ── Best option: camoufox (patched Firefox, randomised TLS fingerprint) ──
        print("\n[MODE] Using camoufox (patched Firefox) — best anti-fingerprint")
        async with AsyncCamoufox(headless=HEADLESS, geoip=True) as browser:
            async def get_page():
                return await get_camoufox_page(browser)
            all_results = await run_scrape_loop(get_page, max_products)

    else:
        # ── Fallback: Playwright + system Google Chrome + playwright-stealth ───
        print("\n[MODE] Using Playwright + system Chrome channel")
        print("[MODE] TIP: install camoufox for stronger bypass: pip install camoufox[geoip]")
        async with async_playwright() as pw:
            print("[BROWSER] Launching system Chrome (channel='chrome')...")
            # 'chrome' channel = your real installed Google Chrome, not Playwright's Chromium.
            # Real Chrome has a legitimate TLS fingerprint that passes Akamai checks.
            browser = await pw.chromium.launch(
                channel="chrome",      # <-- KEY: uses system Chrome, not bundled Chromium
                headless=HEADLESS,
                slow_mo=60,
                args=[
                    "--disable-blink-features=AutomationControlled",   # hides CDP flag
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ],
            )
            print("[BROWSER] Chrome launched ✓")
            context = await browser.new_context(
                viewport={"width": 1366, "height": 768},
                locale="en-US",
                timezone_id="America/New_York",
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "DNT": "1",
                },
            )
            await context.add_init_script(STEALTH_SCRIPT)

            async def get_page():
                return await get_playwright_page(context)

            all_results = await run_scrape_loop(get_page, max_products)

            await context.close()
            await browser.close()

    # ── Output ────────────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print(f"  DONE — {len(all_results)} products scraped")
    print("="*60)

    for idx, p in enumerate(all_results, 1):
        print(f"\n  [{idx}] {p['title']}")
        print(f"       Brand    : {p['brand']}")
        print(f"       Price    : ${p['price']}")
        print(f"       Color    : {p['color']}")
        print(f"       Size     : {p['size']}")
        print(f"       Neck     : {p['neck_type']}")
        print(f"       Fit      : {p['fit']}")
        print(f"       Material : {p['material']}")
        print(f"       Rating   : {p['rating']} ({p['review_count']} reviews)")

    out_file = "nordstrom_results.json"
    print(f"\n[OUTPUT] Saving to {out_file}...")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"[OUTPUT] ✓ {len(all_results)} products saved")
    return all_results


if __name__ == "__main__":
    asyncio.run(scrape_nordstrom(max_products=MAX_PRODUCTS))