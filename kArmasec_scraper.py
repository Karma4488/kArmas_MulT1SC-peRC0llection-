#!/usr/bin/env python3
"""
-------------------------------------------------------------
kArmasec Ultimate Web Scraper - Termux Edition v1.3-fixed
Professional scraper (requests + BeautifulSoup)
Made by kArmasec → fixed & hardened for Termux ~2026
-------------------------------------------------------------
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import logging
import sys
import os

# ─── Colors for Termux ───────────────────────────────────────
class Colors:
    BLUE   = '\033[94m'
    GREEN  = '\033[92m'
    YELLOW = '\033[93m'
    RED    = '\033[91m'
    BOLD   = '\033[1m'
    END    = '\033[0m'


# ─── Configuration ────────────────────────────────────────────
MADE_BY        = "kArmasec"
SCRIPT_NAME    = "kArmasec_Ultimate_WebScraper"
SCRIPT_VERSION = "1.3-termux-fixed"
# ──────────────────────────────── VERY IMPORTANT ─────────────
# Never scrape Facebook without official API / huge risk of ban
# Use your own test site or public page for learning!
# ─────────────────────────────────────────────────────────────
BASE_URL       = "https://example.com/"               # ← CHANGE THIS
OUTPUT_DIR     = "scraped_pages"
USER_AGENT     = (
    "Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36"
)
RATE_DELAY     = 8     # seconds – be polite
MAX_PAGES      = 15
MAX_RETRIES    = 3
RETRY_BACKOFF  = 2.5


def termux_setup():
    print(f"{Colors.GREEN}{Colors.BOLD}🚀 {SCRIPT_NAME} v{SCRIPT_VERSION}{Colors.END}")
    print(f"{Colors.BLUE}📱 Termux 0.118.x – Android{Colors.END}\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)


# ─── Better colored logging ──────────────────────────────────
class ColoredFormatter(logging.Formatter):
    LEVEL_COLORS = {
        'INFO': Colors.GREEN,
        'WARNING': Colors.YELLOW,
        'ERROR': Colors.RED,
        'DEBUG': Colors.BLUE
    }

    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelname, '')
        record.levelname = f"{color}{record.levelname}{Colors.END}"
        return super().format(record)


logging.basicConfig(
    level=logging.INFO,
    format=f"{Colors.BOLD}%(asctime)s{Colors.END} %(levelname)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

for h in logging.getLogger().handlers:
    h.setFormatter(ColoredFormatter("%(asctime)s %(levelname)s: %(message)s"))

logging.info(f"Started. Developed by {MADE_BY}")


# ─── Session ──────────────────────────────────────────────────
session = requests.Session()
session.headers.update({
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml; q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
})


# Optional auth (most sites → don't use)
# SCRAPE_USER  = os.getenv("SCRAPE_USER")
# SCRAPE_PASS  = os.getenv("SCRAPE_PASS")
# if SCRAPE_USER and SCRAPE_PASS:
#     session.auth = requests.auth.HTTPBasicAuth(SCRAPE_USER, SCRAPE_PASS)
#     logging.info("Basic auth configured")


def print_banner():
    print(f"{Colors.BLUE}{Colors.BOLD}"
          "╔══════════════════════════════════════╗\n"
          "║    kArmasec Web Scraper v1.3-fixed   ║\n"
          "║      Termux Edition – 2026 ready     ║\n"
          "╚══════════════════════════════════════╝"
          f"{Colors.END}\n")


def allowed_by_robots(base_url: str) -> bool:
    print(f"{Colors.BLUE}🤖 Checking robots.txt...{Colors.END}")
    try:
        r = session.get(urljoin(base_url, "/robots.txt"), timeout=10)
        if r.status_code != 200:
            logging.warning(f"robots.txt not found ({r.status_code}) → continuing anyway")
            return True
        # Very naive check – real parser is better but overkill here
        if "Disallow: /" in r.text:
            logging.error("robots.txt says Disallow: / → aborting")
            return False
        return True
    except Exception as e:
        logging.warning(f"robots.txt check failed: {e} → continuing")
        return True


def fetch(url: str) -> str | None:
    print(f"{Colors.GREEN}📥 Fetching: {Colors.BOLD}{url}{Colors.END}")
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = session.get(url, timeout=20, allow_redirects=True)
            if r.status_code in (401, 403, 429):
                logging.error(f"❌ {r.status_code} – access denied / rate limit")
                return None
            if r.status_code >= 400:
                logging.error(f"❌ Client error {r.status_code}")
                return None
            r.raise_for_status()
            print(f"{Colors.GREEN}✅ OK ({len(r.text):,} bytes){Colors.END}")
            return r.text
        except requests.RequestException as e:
            msg = str(e)[:60] + "…" if len(str(e)) > 60 else str(e)
            if attempt < MAX_RETRIES:
                print(f"{Colors.YELLOW}↻ Retry {attempt}/{MAX_RETRIES}: {msg}{Colors.END}")
                time.sleep(RETRY_BACKOFF ** attempt)
            else:
                logging.error(f"💥 Gave up after {MAX_RETRIES} tries")
                return None


def save_html(url: str, html: str) -> bool:
    parsed = urlparse(url)
    path = (parsed.path.strip("/") or "index").replace("/", "_").replace("?", "_").replace("=", "_")
    path = path[:80]                           # prevent too long names
    if not path.endswith(".html"):
        path += ".html"

    outpath = os.path.join(OUTPUT_DIR, path)
    header = f"<!-- Scraped by {MADE_BY} v{SCRIPT_VERSION} from {url} -->\n"

    try:
        with open(outpath, "w", encoding="utf-8") as f:
            f.write(header)
            f.write(html)
        print(f"{Colors.GREEN}💾 Saved → {Colors.BOLD}{outpath}{Colors.END}")
        return True
    except Exception as e:
        logging.error(f"Save failed: {e}")
        return False


def extract_links(base_url: str, html: str) -> set[str]:
    try:
        soup = BeautifulSoup(html, "html.parser")           # safe & works without lxml
        links = set()
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            full = urljoin(base_url, href)
            if urlparse(full).netloc == urlparse(base_url).netloc:
                links.add(full.split("#")[0])
        print(f"{Colors.BLUE}🔗 Found {len(links)} internal link(s){Colors.END}")
        return links
    except Exception as e:
        logging.error(f"Link extraction crashed: {e}")
        return set()


def main():
    termux_setup()
    print_banner()

    if not allowed_by_robots(BASE_URL):
        print(f"{Colors.RED}Aborting – robots.txt blocks us.{Colors.END}")
        return

    to_visit = [BASE_URL]
    visited = set()
    count = 0
    start = time.time()

    print(f"{Colors.BLUE}🎯 Target → {BASE_URL}{Colors.END}")
    print(f"{Colors.YELLOW}Limits → {MAX_PAGES} pages max | {RATE_DELAY}s delay{Colors.END}\n")

    while to_visit and count < MAX_PAGES:
        url = to_visit.pop(0)
        if url in visited:
            continue

        html = fetch(url)
        if not html:
            visited.add(url)
            continue

        if save_html(url, html):
            visited.add(url)
            count += 1

            new_links = 0
            for link in extract_links(BASE_URL, html):
                if link not in visited and link not in to_visit:
                    if count + len(to_visit) < MAX_PAGES:
                        to_visit.append(link)
                        new_links += 1

            print(f"{Colors.BLUE}Progress → {count}/{MAX_PAGES} | Queue: {len(to_visit)} | New: {new_links}{Colors.END}")

        if to_visit:
            print(f"{Colors.YELLOW}Waiting {RATE_DELAY}s …{Colors.END}")
            time.sleep(RATE_DELAY)

    elapsed = time.time() - start
    print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 FINISHED !{Colors.END}")
    print(f"Scraped {count} page(s) in {elapsed:.1f} s")
    print(f"Files → {Colors.BLUE}{OUTPUT_DIR}/{Colors.END}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}⏹ Stopped by user{Colors.END}")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Fatal crash: {e}")
        sys.exit(1)
