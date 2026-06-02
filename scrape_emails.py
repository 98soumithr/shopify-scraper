"""
Shopify Store Email Scraper — Step 1
=====================================
Scrapes ALL publicly visible emails from Shopify stores.
Fast, no API calls, no AI. Just collect everything.

Step 2 (enrich.py) will filter + find founder emails.

Usage:    python scrape_emails.py
Input:    domains.txt  (one domain per line)
Output:   raw_leads.csv (saved live as it runs — crash safe)
"""

import re
import csv
import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ── Config ─────────────────────────────────────────────────────────────────────

INPUT_FILE  = "domains.txt"
OUTPUT_FILE = "raw_leads.csv"
DELAY_MIN   = 1.5
DELAY_MAX   = 3.0
TIMEOUT     = 10

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

# ── Pages to check on every store ─────────────────────────────────────────────

PAGES = [
    "/pages/about-us",
    "/pages/about",
    "/pages/our-story",
    "/pages/team",
    "/pages/meet-the-team",
    "/pages/founders",
    "/pages/contact",
    "/contact",
    "/pages/contact-us",
    "",              # homepage — checks footer
]

# ── User agents ────────────────────────────────────────────────────────────────

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# ── Junk email filters ─────────────────────────────────────────────────────────

JUNK_EMAIL_DOMAINS = {
    "shopify.com", "example.com", "sentry.io", "wixpress.com",
    "googletagmanager.com", "google.com", "schema.org",
    "cloudflare.com", "fastly.net", "cloudfront.net",
    "klaviyo.com", "sendgrid.net", "mailchimp.com",
    "mandrillapp.com", "sparkpostmail.com", "amazonaws.com",
    "intercom.io", "zendesk.com", "gorgias.com",
    "tidio.com", "crisp.chat", "drift.com",
    "facebook.com", "instagram.com", "twitter.com",
    "apple.com", "microsoft.com", "w3.org",
}

JUNK_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".svg",
    ".css", ".js", ".woff", ".ttf", ".ico"
}

EMAIL_PATTERN = re.compile(
    r"\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b"
)

# ── CSV columns ────────────────────────────────────────────────────────────────

FIELDS = [
    "domain",
    "store_name",
    "niche",
    "product_count",
    "all_emails",
    "email_count",
    "email_sources",
    "pages_checked",
    "scraped_at",
    "enriched",
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_headers():
    return {
        "User-Agent":      random.choice(USER_AGENTS),
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection":      "keep-alive",
    }


def fetch(url: str) -> str | None:
    try:
        r = requests.get(
            url,
            headers=get_headers(),
            timeout=TIMEOUT,
            allow_redirects=True
        )
        return r.text if r.status_code == 200 else None
    except requests.exceptions.Timeout:
        log.debug(f"    timeout: {url}")
        return None
    except requests.exceptions.ConnectionError:
        log.debug(f"    connection error: {url}")
        return None
    except Exception as e:
        log.debug(f"    fetch error {url}: {e}")
        return None


def pause():
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


def clean_domain(raw: str) -> str:
    d = raw.strip().lower()
    for prefix in ["https://", "http://", "www."]:
        d = d.replace(prefix, "")
    return d.split("/")[0]


def is_junk_email(email: str) -> bool:
    if any(email.endswith(ext) for ext in JUNK_EXTENSIONS):
        return True
    domain_part = email.split("@")[-1].lower()
    if any(domain_part == j or domain_part.endswith("." + j)
           for j in JUNK_EMAIL_DOMAINS):
        return True
    if len(email) > 80:
        return True
    tld = domain_part.split(".")[-1]
    if len(tld) < 2:
        return True
    return False


def extract_emails(html: str) -> list:
    raw = EMAIL_PATTERN.findall(html)
    seen = set()
    result = []
    for email in raw:
        email = email.lower().rstrip(".,;:)>\"'")
        if email in seen:
            continue
        seen.add(email)
        if not is_junk_email(email):
            result.append(email)
    return result


# ── Shopify confirmation ───────────────────────────────────────────────────────

def confirm_shopify(domain: str) -> dict | None:
    url = f"https://{domain}/products.json?limit=5"
    try:
        r = requests.get(url, headers=get_headers(), timeout=TIMEOUT)
        if r.status_code != 200:
            return None

        data = r.json()
        products = data.get("products", [])
        if not products:
            return {"store_name": domain, "niche": "unknown", "product_count": 0}

        vendors = [p.get("vendor", "") for p in products if p.get("vendor")]
        store_name = vendors[0].strip() if vendors else domain

        types = list({
            p.get("product_type", "").strip()
            for p in products
            if p.get("product_type", "").strip()
        })

        all_tags = []
        for p in products:
            tags = p.get("tags", "")
            if isinstance(tags, str):
                all_tags += [t.strip() for t in tags.split(",") if t.strip()]
            elif isinstance(tags, list):
                all_tags += [str(t).strip() for t in tags]

        niche = types[0] if types else (all_tags[0] if all_tags else "general")

        return {
            "store_name":    store_name[:60],
            "niche":         niche[:40],
            "product_count": len(products),
        }

    except (ValueError, KeyError):
        return None
    except Exception as e:
        log.debug(f"  products.json error for {domain}: {e}")
        return None


# ── Main store scraper ─────────────────────────────────────────────────────────

def scrape_store(domain: str) -> dict | None:
    domain = clean_domain(domain)
    if not domain or "." not in domain:
        return None

    # Confirm Shopify
    shopify_info = confirm_shopify(domain)
    if shopify_info is None:
        log.info(f"  ✗ skip  {domain}  (not Shopify)")
        return None
    pause()

    store_name    = shopify_info["store_name"]
    niche         = shopify_info["niche"]
    product_count = shopify_info["product_count"]

    # Visit pages and collect emails
    found_emails  = {}
    pages_checked = 0

    for path in PAGES:
        url  = f"https://{domain}{path}"
        html = fetch(url)
        if not html:
            pause()
            continue

        pages_checked += 1
        emails = extract_emails(html)

        for email in emails:
            if email not in found_emails:
                found_emails[email] = path if path else "homepage"

        pause()

    # Build output
    emails_list  = list(found_emails.keys())
    sources_list = [found_emails[e] for e in emails_list]

    if emails_list:
        log.info(
            f"  ✓ found  {domain}  ({store_name[:30]})  "
            f"— {len(emails_list)} email(s): {', '.join(emails_list[:3])}"
        )
    else:
        log.info(f"  ○ none   {domain}  ({store_name[:30]})")

    return {
        "domain":        domain,
        "store_name":    store_name,
        "niche":         niche,
        "product_count": product_count,
        "all_emails":    " | ".join(emails_list),
        "email_count":   len(emails_list),
        "email_sources": " | ".join(sources_list),
        "pages_checked": pages_checked,
        "scraped_at":    datetime.now().strftime("%Y-%m-%d %H:%M"),
        "enriched":      "no",
    }


# ── Domain loader ──────────────────────────────────────────────────────────────

def load_domains(path: str) -> list:
    try:
        with open(path, encoding="utf-8") as f:
            return [
                line.strip()
                for line in f
                if line.strip() and not line.startswith("#")
            ]
    except FileNotFoundError:
        log.warning(f"{path} not found — creating sample file")
        with open(path, "w") as f:
            f.write("# Add Shopify store domains here, one per line\n")
            f.write("# Run find_domains.py first to generate this list\n")
        return []


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("  Shopify Email Scraper  —  Step 1 of 2")
    log.info("  Collects all public emails from Shopify stores")
    log.info("  Results saved live — safe to stop and restart")
    log.info("=" * 60)

    domains = load_domains(INPUT_FILE)
    if not domains:
        log.error(f"No domains in {INPUT_FILE} — add some and retry")
        return

    log.info(f"Loaded {len(domains)} domains\n")

    total       = len(domains)
    confirmed   = 0
    with_emails = 0
    no_emails   = 0
    skipped     = 0

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDS)
        writer.writeheader()
        csvfile.flush()

        for i, raw_domain in enumerate(domains, 1):
            log.info(f"\n[{i}/{total}]  {raw_domain.strip()}")
            try:
                row = scrape_store(raw_domain)
            except KeyboardInterrupt:
                log.info("\nStopped — progress saved to CSV")
                break
            except Exception as e:
                log.error(f"  Unexpected error: {e}")
                skipped += 1
                continue

            if row is None:
                skipped += 1
                continue

            confirmed += 1
            if row["email_count"] > 0:
                with_emails += 1
            else:
                no_emails += 1

            writer.writerow(row)
            csvfile.flush()

    log.info("\n" + "=" * 60)
    log.info("  SUMMARY")
    log.info("=" * 60)
    log.info(f"  Total domains:          {total}")
    log.info(f"  Confirmed Shopify:      {confirmed}")
    log.info(f"  Stores with emails:     {with_emails}")
    log.info(f"  Stores with no email:   {no_emails}")
    log.info(f"  Skipped / not Shopify:  {skipped}")
    log.info(f"\n  Saved to: {OUTPUT_FILE}")
    log.info(f"\n  Next: run  python enrich.py  to find founder emails")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
