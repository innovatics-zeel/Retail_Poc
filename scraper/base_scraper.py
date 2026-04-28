"""
base_scraper.py
Shared async Playwright session with retry logic and polite delays.
No proxies — uses realistic browser headers and slow_mo to avoid blocks.
"""
import asyncio
import random
import sys
from abc import ABC, abstractmethod
from typing import Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

sys.path.append("..")
from config.settings import settings


class BaseScraper(ABC):
    """
    Abstract base — handles browser lifecycle, delays, and retries.
    Subclass and implement `scrape_listing()` and `search_category()`.
    """

    HEADERS = {
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }

    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, *args):
        await self.stop()

    async def start(self):
        """Launch Playwright browser."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=settings.scraper_headless,
            slow_mo=settings.scraper_slow_mo,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        self.context = await self.browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1440, "height": 900},
            locale="en-US",
            timezone_id="America/New_York",
            extra_http_headers=self.HEADERS,
        )
        # Block images/fonts to speed up scraping
        await self.context.route(
            "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,otf}",
            lambda route: route.abort()
        )
        logger.info(f"✅ Browser started — headless={settings.scraper_headless}")

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("🛑 Browser stopped")

    async def new_page(self) -> Page:
        return await self.context.new_page()

    async def polite_delay(self):
        """Random delay between requests — be a good citizen."""
        delay = random.uniform(settings.scraper_delay_min, settings.scraper_delay_max)
        logger.debug(f"⏳ Waiting {delay:.1f}s...")
        await asyncio.sleep(delay)

    async def safe_goto(self, page: Page, url: str) -> bool:
        """Navigate with retry on timeout/network errors."""
        for attempt in range(1, settings.scraper_max_retries + 1):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=settings.scraper_timeout)
                return True
            except Exception as e:
                logger.warning(f"Attempt {attempt}/{settings.scraper_max_retries} failed for {url}: {e}")
                if attempt < settings.scraper_max_retries:
                    await asyncio.sleep(3 * attempt)
        logger.error(f"❌ Failed to load: {url}")
        return False

    @abstractmethod
    async def scrape_listing(self, url: str) -> Optional[dict]:
        """Scrape a single product listing page. Returns raw dict."""
        ...

    @abstractmethod
    async def search_category(self, category: str, max_products: int) -> list[dict]:
        """Search a category and return list of raw product dicts."""
        ...
