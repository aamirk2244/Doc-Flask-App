"""Playwright KIBOR helpers (moved from playwright_kibor).

Provides:
- `start_scrape()`, `scrape_status()`, `list_files()`, `download_top_for(year, month)`
"""
import asyncio
import re
import threading
from datetime import datetime, date
from pathlib import Path
import requests
from bs4 import BeautifulSoup
from typing import List


BASE_URL = "https://www.sbp.org.pk/ecodata/kibor_index.asp"
SAVE_DIR = Path("static/data/kibor_files")
START_YEAR = 2025
START_MONTH = 1
HEADLESS = True
PAGE_WAIT = 3

# scraper state
_scraper_state = {"running": False, "log": [], "error": None}


def month_name(month_num: int) -> str:
    from datetime import datetime as _dt
    return _dt(2000, month_num, 1).strftime("%b")


def months_to_scrape():
    today = date.today()
    result = []
    year, month = START_YEAR, START_MONTH
    while (year, month) <= (today.year, today.month):
        result.append((year, month))
        month += 1
        if month > 12:
            month, year = 1, year + 1
    return result


def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "", name).strip()


def log(msg: str) -> None:
    print(msg)
    _scraper_state["log"].append(msg)


def file_for_month_exists(year: int, month: int):
    """Return an existing PDF filename for the given year/month, or None.

    This uses heuristics (year, year-month, month name, 'kibor-YYYY-M') to
    avoid hitting the network when a likely filename is already present.
    """
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    mon_abbr = month_name(month).lower()
    mon_full = datetime(2000, month, 1).strftime("%B").lower()
    y = str(year)
    pats = [y, f"{year}-{month}", f"{year}-{month:02d}", mon_abbr, mon_full, f"kibor-{year}-{month}"]
    for p in SAVE_DIR.glob("*.pdf"):
        nm = p.name.lower()
        for pat in pats:
            if pat in nm:
                return p.name
    return None


def download_pdf(url: str, dest_path: Path, session: requests.Session) -> bool:
    try:
        resp = session.get(url, timeout=30, stream=True)
        resp.raise_for_status()
        dest_path.write_bytes(resp.content)
        log(f"    ✓ Saved → {dest_path.name}  ({len(resp.content):,} bytes)")
        return True
    except Exception as e:
        log(f"    ✗ Download failed: {e}")
        return False


async def _scrape_async() -> None:
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    periods = months_to_scrape()
    log(f"Months to process: {len(periods)}  ({periods[0]} → {periods[-1]})")

    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )

    try:
        from playwright.async_api import async_playwright
    except Exception as e:
        raise RuntimeError("playwright not installed; install 'playwright' and run 'playwright install'") from e

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=HEADLESS)
        context = await browser.new_context(accept_downloads=True, user_agent=session.headers["User-Agent"]) 
        page = await context.new_page()

        log(f"Opening {BASE_URL} …")
        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30_000)
        await asyncio.sleep(PAGE_WAIT)

        for year, month in periods:
            yr_str, mon_str = str(year), month_name(month)
            log(f"\n── {mon_str} {yr_str} ─────────────────────────")

            # Fast-path: if a likely file for this month already exists, skip network/page work
            existing = file_for_month_exists(year, month)
            if existing:
                log(f"  ⏭  Already downloaded ({existing}) — skipping without network.")
                continue

            # Select year
            try:
                await page.locator("select").first.select_option(yr_str)
                await asyncio.sleep(1)
            except Exception as e:
                log(f"  Could not select year {yr_str}: {e}"); continue

            # Select month
            try:
                selects = await page.locator("select").all()
                if len(selects) < 2:
                    log("  Expected 2 dropdowns, found fewer — skipping"); continue
                await selects[1].select_option(mon_str)
                await asyncio.sleep(PAGE_WAIT)
            except Exception as e:
                log(f"  Could not select month {mon_str}: {e}"); continue

            # Get topmost link
            try:
                links = await page.locator("a").filter(has_text=re.compile(r"Daily Kibor Rates", re.I)).all()
                if not links:
                    log("  No links found for this period."); continue

                link_text = (await links[0].inner_text()).strip()
                href      = (await links[0].get_attribute("href")) or ""
                log(f"  Top link : {link_text}")
            except Exception as e:
                log(f"  Failed to retrieve links: {e}"); continue

            # Build PDF URL
            if href.startswith("http"):
                pdf_url = href
            elif href.startswith("/"):
                pdf_url = f"https://www.sbp.org.pk{href}"
            else:
                pdf_url = f"{BASE_URL.rsplit('/', 1)[0]}/{href}"

            # Filename
            url_filename = pdf_url.split("/")[-1].split("?")[0]
            if not url_filename.lower().endswith(".pdf"):
                url_filename = sanitize_filename(link_text) + ".pdf"

            dest_path = SAVE_DIR / url_filename
            if dest_path.exists():
                log(f"  ⏭  Already downloaded — skipping."); continue

            # Share cookies with requests session
            for c in await context.cookies():
                session.cookies.set(c["name"], c["value"], domain=c.get("domain", ""))

            download_pdf(pdf_url, dest_path, session)
            await asyncio.sleep(1)

        await browser.close()

    total = len(list(SAVE_DIR.glob("*.pdf")))
    log(f"\nDone! {total} PDFs in {SAVE_DIR.resolve()}")


def _run_in_thread() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_scrape_async())
        _scraper_state["error"] = None
    except Exception as e:
        _scraper_state["error"] = str(e)
        log(f"Scraper error: {e}")
    finally:
        loop.close()
        _scraper_state["running"] = False


def start_scrape() -> dict:
    if _scraper_state["running"]:
        return {"status": "already_running"}
    _scraper_state["running"] = True
    _scraper_state["log"] = []
    _scraper_state["error"] = None
    thread = threading.Thread(target=_run_in_thread, daemon=True)
    thread.start()
    return {"status": "started"}


def scrape_status() -> dict:
    return {"running": _scraper_state["running"], "error": _scraper_state["error"], "log": list(_scraper_state["log"]) }


def list_files() -> List[str]:
    return sorted(p.name for p in SAVE_DIR.glob("*.pdf")) if SAVE_DIR.exists() else []


async def _download_top_for_async(year: int, month: int) -> dict:
    """Async helper: navigate the site for a single year/month and download the top 'Daily Kibor Rates' link."""
    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )

    # Fast-path: skip if file already present
    existing = file_for_month_exists(year, month)
    if existing:
        return {"ok": True, "skipped": True, "saved": existing, "pdf_url": None}

    try:
        from playwright.async_api import async_playwright
    except Exception as e:
        return {"ok": False, "error": "playwright not installed"}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=HEADLESS)
        context = await browser.new_context(accept_downloads=True, user_agent=session.headers["User-Agent"]) 
        page = await context.new_page()

        await page.goto(BASE_URL, wait_until="domcontentloaded", timeout=30_000)
        await asyncio.sleep(PAGE_WAIT)

        yr_str, mon_str = str(year), month_name(month)
        # select year
        try:
            await page.locator("select").first.select_option(yr_str)
            await asyncio.sleep(1)
        except Exception as e:
            return {"ok": False, "error": f"Could not select year {year}: {e}"}

        # select month
        try:
            selects = await page.locator("select").all()
            if len(selects) < 2:
                return {"ok": False, "error": "Expected 2 dropdowns, found fewer"}
            await selects[1].select_option(mon_str)
            await asyncio.sleep(PAGE_WAIT)
        except Exception as e:
            return {"ok": False, "error": f"Could not select month {mon_str}: {e}"}

        # get topmost link
        try:
            links = await page.locator("a").filter(has_text=re.compile(r"Daily Kibor Rates", re.I)).all()
            if not links:
                return {"ok": False, "error": "No links found for this period"}
            link_text = (await links[0].inner_text()).strip()
            href = (await links[0].get_attribute("href")) or ""
        except Exception as e:
            return {"ok": False, "error": f"Failed to retrieve links: {e}"}

        # build pdf url
        if href.startswith("http"):
            pdf_url = href
        elif href.startswith("/"):
            pdf_url = f"https://www.sbp.org.pk{href}"
        else:
            pdf_url = f"{BASE_URL.rsplit('/', 1)[0]}/{href}"

        url_filename = pdf_url.split("/")[-1].split("?")[0]
        if not url_filename.lower().endswith(".pdf"):
            url_filename = sanitize_filename(link_text) + ".pdf"

        dest_path = SAVE_DIR / url_filename
        if dest_path.exists():
            await browser.close()
            return {"ok": True, "skipped": True, "saved": dest_path.name, "pdf_url": pdf_url}

        # share cookies
        for c in await context.cookies():
            session.cookies.set(c["name"], c["value"], domain=c.get("domain", ""))

        success = download_pdf(pdf_url, dest_path, session)
        await browser.close()
        if success:
            return {"ok": True, "skipped": False, "saved": dest_path.name, "pdf_url": pdf_url}
        else:
            return {"ok": False, "error": "download_failed", "pdf_url": pdf_url}


def download_top_for(year: int, month: int) -> dict:
    """Synchronous wrapper to download top PDF for given year/month."""
    # Try a lightweight requests + BeautifulSoup approach first (no Playwright)
    try:
        res = _download_top_for_requests(year, month)
        # if we found something (ok True or skipped), return it
        if res.get('ok'):
            return res
        # otherwise continue to Playwright fallback
    except Exception as e:
        # keep going to Playwright fallback
        pass

    # Playwright fallback (may require playwright installed)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        res = loop.run_until_complete(_download_top_for_async(year, month))
        return res
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        loop.close()


def _download_top_for_requests(year: int, month: int) -> dict:
    """Request-based downloader for a single year/month. Returns same dict shape as async variant.

    This is a best-effort approach that looks for anchors mentioning 'Daily Kibor Rates' or
    direct PDF links on the index page. It avoids Playwright and works when the page is static.
    """
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )

    # Fast-path: skip if file already present
    existing = file_for_month_exists(year, month)
    if existing:
        return {"ok": True, "skipped": True, "saved": existing, "pdf_url": None}

    try:
        resp = session.get(BASE_URL, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        return {"ok": False, "error": f"network_error: {e}"}

    soup = BeautifulSoup(resp.text, "html.parser")
    # prefer anchors containing 'Daily Kibor Rates' or direct pdf links
    anchors = soup.find_all('a')

    candidates = []
    text_re = re.compile(r"Daily\s+Kibor Rates", re.I)
    mon_name = month_name(month)
    yr_str = str(year)

    for a in anchors:
        href = a.get('href') or ''
        text = (a.get_text() or '').strip()
        # prefer anchors that contain 'Daily Kibor Rates'
        score = 0
        if text_re.search(text):
            score += 10
        if href.lower().endswith('.pdf'):
            score += 5
        # prefer anchors mentioning month/year
        if mon_name.lower() in text.lower() or yr_str in text:
            score += 2
        if href and score > 0:
            candidates.append((score, text, href))

    if not candidates:
        # fallback: pick first PDF link on page
        for a in anchors:
            href = a.get('href') or ''
            if href.lower().endswith('.pdf'):
                candidates.append((1, a.get_text() or '', href))
                break

    if not candidates:
        return {"ok": False, "error": "no_link_found"}

    # pick best candidate by score
    candidates.sort(key=lambda x: -x[0])
    _, link_text, href = candidates[0]

    if href.startswith('http'):
        pdf_url = href
    elif href.startswith('/'):
        pdf_url = f"https://www.sbp.org.pk{href}"
    else:
        pdf_url = f"{BASE_URL.rsplit('/', 1)[0]}/{href}"

    url_filename = pdf_url.split("/")[-1].split("?")[0]
    if not url_filename.lower().endswith('.pdf'):
        url_filename = sanitize_filename(link_text or f"kibor-{year}-{month}") + '.pdf'

    dest_path = SAVE_DIR / url_filename
    if dest_path.exists():
        return {"ok": True, "skipped": True, "saved": dest_path.name, "pdf_url": pdf_url}

    success = download_pdf(pdf_url, dest_path, session)
    if success:
        return {"ok": True, "skipped": False, "saved": dest_path.name, "pdf_url": pdf_url}
    else:
        return {"ok": False, "error": "download_failed", "pdf_url": pdf_url}
