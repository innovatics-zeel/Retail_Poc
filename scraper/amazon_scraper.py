"""
amazon_scraper.py
Scrapes Amazon US for Men's T-shirts and Women's Casual Dresses.
Extracts: listing, attributes, price, reviews from product pages.
"""
import sys
import re
from typing import Optional
from bs4 import BeautifulSoup
from loguru import logger

sys.path.append("..")
from scraper.base_scraper import BaseScraper
from scraper.attribute_parser import (
    parse_price, parse_rating, parse_review_count,
    parse_pattern, parse_fit, parse_neck_type, parse_sleeve_type,
    get_color_family, get_material_family,
)
from config.settings import settings


# ── Amazon Search URLs ────────────────────────────────────────
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
    """Scrapes Amazon product listings for apparel categories."""

    PLATFORM = "amazon"

    # ─── Category Search ──────────────────────────────────────

    async def search_category(self, category: str, max_products: int = 40) -> list[dict]:
        """
        Scrape search results page(s) to collect product URLs + ASINs.
        Returns list of raw product dicts (full detail scraped per listing).
        """
        if category not in AMAZON_SEARCH_URLS:
            raise ValueError(f"Unknown category: {category}. Use: {list(AMAZON_SEARCH_URLS)}")

        base_url = AMAZON_SEARCH_URLS[category]
        product_urls = []
        page_num = 1

        page = await self.new_page()

        while len(product_urls) < max_products:
            url = f"{base_url}&page={page_num}"
            logger.info(f"🔍 Searching Amazon [{category}] page {page_num} — {url}")

            if not await self.safe_goto(page, url):
                break

            # Check for CAPTCHA / robot check
            if await self._is_blocked(page):
                logger.warning("⚠️  Amazon bot check detected — stopping search")
                break

            soup = BeautifulSoup(await page.content(), "lxml")
            links = self._extract_search_result_links(soup)

            if not links:
                logger.info(f"No more results on page {page_num}")
                break

            product_urls.extend(links)
            logger.info(f"  Found {len(links)} links on page {page_num} (total: {len(product_urls)})")

            page_num += 1
            await self.polite_delay()

        await page.close()

        # Scrape each product page
        results = []
        for i, (asin, url) in enumerate(product_urls[:max_products]):
            logger.info(f"📦 Scraping product {i+1}/{min(len(product_urls), max_products)}: {asin}")
            data = await self.scrape_listing(url, category=category, asin=asin)
            if data:
                results.append(data)
            await self.polite_delay()

        logger.info(f"✅ Amazon [{category}]: scraped {len(results)} products")
        return results

    # ─── Single Listing ───────────────────────────────────────

    async def scrape_listing(self, url: str, category: str = "", asin: str = "") -> Optional[dict]:
        """Scrape a single Amazon product page."""
        page = await self.new_page()
        try:
            if not await self.safe_goto(page, url):
                return None

            if await self._is_blocked(page):
                logger.warning(f"⚠️  Bot check on listing: {url}")
                return None

            soup = BeautifulSoup(await page.content(), "lxml")
            return self._parse_product_page(soup, url, category, asin)

        except Exception as e:
            logger.error(f"❌ Error scraping {url}: {e}")
            return None
        finally:
            await page.close()

    # ─── Parsers ──────────────────────────────────────────────

    def _parse_product_page(self, soup: BeautifulSoup, url: str, category: str, asin: str) -> Optional[dict]:
        """Extract all fields from a parsed Amazon product page."""
        try:
            # ── Title ──────────────────────────────────────────
            title_el = soup.find("span", id="productTitle")
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                return None

            # ── Brand ──────────────────────────────────────────
            brand = ""
            brand_el = soup.find("a", id="bylineInfo")
            if brand_el:
                brand = re.sub(r"^(Visit the |Brand: )", "", brand_el.get_text(strip=True))

            # ── Price ──────────────────────────────────────────
            price_raw = ""
            for selector in [
                ("span", {"class": "a-price-whole"}),
                ("span", {"id": "priceblock_ourprice"}),
                ("span", {"class": "a-offscreen"}),
            ]:
                el = soup.find(*selector)
                if el:
                    price_raw = el.get_text(strip=True)
                    break

            original_price_raw = ""
            orig_el = soup.find("span", {"class": "a-text-price"})
            if orig_el:
                original_price_raw = orig_el.get_text(strip=True)

            price = parse_price(price_raw)
            original_price = parse_price(original_price_raw)
            discount_pct = None
            if price and original_price and original_price > price:
                discount_pct = round((1 - price / original_price) * 100, 1)

            # ── Rating & Reviews ───────────────────────────────
            rating_el = soup.find("span", {"class": "a-icon-alt"})
            rating = parse_rating(rating_el.get_text() if rating_el else "")

            review_el = soup.find("span", id="acrCustomerReviewText")
            review_count = parse_review_count(review_el.get_text() if review_el else "")

            # ── Attributes from feature bullets + title ────────
            bullets = soup.find("div", id="feature-bullets")
            bullet_text = bullets.get_text(" ", strip=True) if bullets else ""
            full_text = f"{title} {bullet_text}"

            # Color from variation selector
            color = self._parse_color(soup)
            color_family = get_color_family(color)

            # Material
            material = self._extract_detail(soup, ["Fabric Type", "Material", "Fabric"])
            material_family = get_material_family(material)

            # Pattern, Fit, Neck, Sleeve
            pattern    = parse_pattern(full_text)
            fit        = parse_fit(full_text) or self._extract_detail(soup, ["Fit Type"])
            neck_type  = parse_neck_type(full_text) or self._extract_detail(soup, ["Collar Style", "Neckline"])
            sleeve     = parse_sleeve_type(full_text) or self._extract_detail(soup, ["Sleeve Type"])

            # Size range
            size_range = self._parse_sizes(soup)

            return {
                "platform":     "amazon",
                "sku_id":       asin or self._extract_asin(url),
                "url":          url,
                "title":        title,
                "brand":        brand,
                "category":     category or "mens_tshirts",
                "is_available": True,
                "color":        color,
                "color_family": color_family,
                "pattern":      pattern,
                "material":     material,
                "material_family": material_family,
                "fit":          fit,
                "neck_type":    neck_type,
                "sleeve_type":  sleeve,
                "gender":       "Men" if "mens" in category else "Women",
                "size_range":   size_range,
                "price":        price,
                "original_price": original_price,
                "discount_pct": discount_pct,
                "currency":     "USD",
                "rating":       rating,
                "review_count": review_count,
            }

        except Exception as e:
            logger.error(f"❌ Parse error: {e}")
            return None

    def _extract_search_result_links(self, soup: BeautifulSoup) -> list[tuple[str, str]]:
        """Extract (ASIN, URL) pairs from search results page."""
        results = []
        for div in soup.select("div[data-asin]"):
            asin = div.get("data-asin", "").strip()
            if not asin:
                continue
            link_el = div.select_one("a.a-link-normal[href*='/dp/']")
            if link_el:
                href = link_el.get("href", "")
                if "/dp/" in href:
                    clean_url = f"https://www.amazon.com{href.split('?')[0]}"
                    results.append((asin, clean_url))
        return results

    def _extract_detail(self, soup: BeautifulSoup, labels: list[str]) -> Optional[str]:
        """Extract product detail row by label (from product details table)."""
        for row in soup.select("tr.po-fabric_type, tr.po-material, .a-expander-content tr"):
            label_el = row.find("td", {"class": "a-span3"})
            value_el = row.find("td", {"class": "a-span9"})
            if label_el and value_el:
                if any(l.lower() in label_el.get_text().lower() for l in labels):
                    return value_el.get_text(strip=True)

        # Fallback: product description table
        for el in soup.select(".prodDetAttrValue"):
            prev = el.find_previous_sibling()
            if prev and any(l.lower() in prev.get_text().lower() for l in labels):
                return el.get_text(strip=True)
        return None

    def _parse_color(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract selected color from variation selector."""
        color_el = soup.find("span", id=re.compile(r"color_name_\d+"))
        if color_el:
            return color_el.get_text(strip=True)
        # Fallback: variation label
        for el in soup.select(".selection"):
            return el.get_text(strip=True)
        return None

    def _parse_sizes(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract available sizes from size selector."""
        sizes = []
        for btn in soup.select("li.swatch-list-item-text .swatch-title-text-display"):
            s = btn.get_text(strip=True)
            if s and len(s) <= 6:
                sizes.append(s)
        return ",".join(sizes) if sizes else None

    def _extract_asin(self, url: str) -> str:
        match = re.search(r"/dp/([A-Z0-9]{10})", url)
        return match.group(1) if match else url.split("/")[-1]

    async def _is_blocked(self, page) -> bool:
        """Detect Amazon bot/CAPTCHA page."""
        content = await page.content()
        blocked_signals = [
            "Enter the characters you see below",
            "Sorry, we just need to make sure you're not a robot",
            "api-services-support@amazon.com",
            "Type the characters you see in this image",
        ]
        return any(s in content for s in blocked_signals)
