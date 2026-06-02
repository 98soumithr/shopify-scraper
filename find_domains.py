"""
Shopify Store Domain Finder — Step 0
======================================
Uses Serper.dev (2,500 free searches on signup, no card needed)
to find Shopify store domains by niche and country.

Run this first to build domains.txt, then run scrape_emails.py.

Usage:    python find_domains.py
Output:   domains.txt
Sign up:  serper.dev
"""

import re
import time
import logging
import requests

# ── Config ─────────────────────────────────────────────────────────────────────

SERPER_API_KEY = "YOUR_SERPER_API_KEY"   # free at serper.dev
OUTPUT_FILE    = "domains.txt"
DELAY_SECONDS  = 1.5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

# ── Search queries ─────────────────────────────────────────────────────────────
# Each returns up to 10 store domains.
# 2,500 free searches = up to 25,000 domains.
# Edit these to target your preferred niche + country.

SEARCH_QUERIES = [
    # USA — fashion
    'site:myshopify.com "women\'s fashion" "United States"',
    'site:myshopify.com "clothing boutique" USA',
    'site:myshopify.com "streetwear" "United States"',
    'site:myshopify.com "activewear" "United States"',

    # USA — beauty
    'site:myshopify.com "skincare" "United States"',
    'site:myshopify.com "beauty products" USA',
    'site:myshopify.com "cosmetics" "United States"',

    # USA — pets
    'site:myshopify.com "pet products" "United States"',
    'site:myshopify.com "dog accessories" USA',
    'site:myshopify.com "pet supplies" "United States"',

    # USA — fitness
    'site:myshopify.com "fitness supplements" "United States"',
    'site:myshopify.com "gym wear" "United States"',

    # USA — home
    'site:myshopify.com "home decor" "United States"',
    'site:myshopify.com "kitchen accessories" USA',

    # USA — subscription
    'site:myshopify.com "subscription box" "United States"',

    # UK
    'site:myshopify.com "women\'s fashion" "United Kingdom"',
    'site:myshopify.com "skincare" "United Kingdom"',
    'site:myshopify.com "pet products" UK',
    'site:myshopify.com "home decor" "United Kingdom"',

    # Australia
    'site:myshopify.com "fashion" Australia',
    'site:myshopify.com "skincare" Australia',
    'site:myshopify.com "activewear" Australia',
    'site:myshopify.com "pet supplies" Australia',

    # New Zealand
    'site:myshopify.com "clothing" "New Zealand"',
    'site:myshopify.com "beauty" "New Zealand"',

    # UAE
    'site:myshopify.com "fashion" "UAE"',
    'site:myshopify.com "beauty" "Dubai"',
    'site:myshopify.com "clothing" "United Arab Emirates"',
]


# ── Serper API ─────────────────────────────────────────────────────────────────

def search_serper(query: str) -> list:
    """Run one search query, return list of domains found."""
    headers = {
        "X-API-KEY":    SERPER_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {"q": query, "num": 10}

    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers=headers,
            json=payload,
            timeout=10
        )
        if resp.status_code != 200:
            log.warning(f"  Serper {resp.status_code}: {resp.text[:80]}")
            return []

        domains = []
        for result in resp.json().get("organic", []):
            link = result.get("link", "")
            match = re.search(r"https?://(?:www\.)?([^/]+)", link)
            if match:
                domain = match.group(1).lower()
                if domain and domain not in domains:
                    domains.append(domain)
        return domains

    except Exception as e:
        log.error(f"  Serper error: {e}")
        return []


# ── Fallback starter list ──────────────────────────────────────────────────────
# Used if no Serper API key — gives you something to test with immediately

STARTER_DOMAINS = [
    "gymshark.com",
    "allbirds.com",
    "tentree.com",
    "chubbiesshorts.com",
    "beardbrand.com",
    "ugmonk.com",
    "huckberry.com",
    "colourpopcosmetics.com",
    "ruggable.com",
    "alphalete.com",
]


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 55)
    log.info("  Shopify Domain Finder")
    log.info("=" * 55)

    all_domains = set()

    if SERPER_API_KEY == "YOUR_SERPER_API_KEY":
        log.warning("No Serper key set — using starter list to test")
        log.warning("Sign up free at serper.dev for 2,500 real searches")
        all_domains.update(STARTER_DOMAINS)
    else:
        log.info(f"Running {len(SEARCH_QUERIES)} queries via Serper...\n")

        for i, query in enumerate(SEARCH_QUERIES, 1):
            log.info(f"[{i}/{len(SEARCH_QUERIES)}]  {query[:65]}...")
            found = search_serper(query)
            new   = [d for d in found if d not in all_domains]
            all_domains.update(found)
            log.info(f"  → {len(found)} found | {len(new)} new | {len(all_domains)} total")
            time.sleep(DELAY_SECONDS)

    # Write output
    sorted_domains = sorted(all_domains)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# Shopify store domains — generated by find_domains.py\n")
        f.write(f"# Total: {len(sorted_domains)}\n")
        f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M')}\n\n")
        for d in sorted_domains:
            f.write(d + "\n")

    log.info(f"\n✓ Saved {len(sorted_domains)} domains to {OUTPUT_FILE}")
    log.info("→ Now run: python scrape_emails.py")


if __name__ == "__main__":
    main()
