#!/usr/bin/env python3
"""
Full automated lead pipeline for Olympus:
1. Scrape leads from Google Maps via Outscraper (full data)
2. Save new leads via Base44 saveLeads function (deduplicates automatically)
3. Enrich with emails via Base44 enrichLeads function (Hunter.io)
"""

import os
import sys
import json
import requests
import time

OUTSCRAPER_API_KEY = os.environ.get("OUTSCRAPER_API_KEY")
APP_URL = "https://super-dave-b523dd32.base44.app"

SEARCHES = [
    "dental office Vancouver BC",
    "medical spa Vancouver BC",
    "cosmetic clinic Vancouver BC",
    "dermatology clinic Vancouver BC"
]

def scrape_google_maps(query, limit=50):
    print(f"  🔍 {query}")
    url = "https://api.app.outscraper.com/maps/search-v3"
    params = {
        "query": query,
        "limit": limit,
        "async": False
        # No fields filter — get everything
    }
    headers = {"X-API-KEY": OUTSCRAPER_API_KEY}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=90)
        if response.status_code != 200:
            print(f"    ❌ Error {response.status_code}: {response.text[:200]}")
            return []
        data = response.json()
        results = []
        if isinstance(data, dict) and "data" in data:
            for item_list in data["data"]:
                if isinstance(item_list, list):
                    results.extend(item_list)
                else:
                    results.append(item_list)
        elif isinstance(data, list):
            results = data
        print(f"    ✅ {len(results)} results")
        return results
    except Exception as e:
        print(f"    ❌ Exception: {e}")
        return []

def call_function(name, payload):
    url = f"{APP_URL}/functions/{name}"
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        return resp.json()
    except Exception as e:
        print(f"  ❌ Function {name} error: {e}")
        return {}

def clean_website(url):
    """Extract clean domain from messy URL"""
    if not url:
        return ""
    # Remove UTM params and tracking
    clean = url.split("?")[0].split("%3F")[0]
    # Ensure it has scheme
    if not clean.startswith("http"):
        clean = "https://" + clean
    return clean

def main():
    print("🚀 OLYMPUS LEAD PIPELINE")
    print("=" * 40)

    if not OUTSCRAPER_API_KEY:
        print("❌ OUTSCRAPER_API_KEY missing")
        sys.exit(1)

    # Phase 1: Scrape
    print("\n📍 PHASE 1: Scraping Google Maps...")
    all_results = []
    for query in SEARCHES:
        results = scrape_google_maps(query, limit=50)
        all_results.extend(results)
        time.sleep(1)

    print(f"\n  Total scraped: {len(all_results)}")

    # Format for saving — use correct field names from Outscraper
    leads_to_save = []
    for item in all_results:
        name = (item.get("name") or "").strip()
        if not name:
            continue

        website = clean_website(item.get("website") or "")
        address = item.get("address") or item.get("full_address") or ""
        city = item.get("city") or "Vancouver"
        phone = item.get("phone") or ""
        rating = str(item.get("rating") or "")
        category = item.get("category") or item.get("type") or ""

        leads_to_save.append({
            "business_name": name,
            "phone": phone,
            "website": website,
            "address": address,
            "city": city,
            "rating": rating,
            "category": category,
            "source": "outscraper"
        })

    # Phase 2: Save
    print(f"\n📍 PHASE 2: Saving {len(leads_to_save)} leads to database...")
    save_result = call_function("saveLeads", {"leads": leads_to_save})
    saved = save_result.get("saved", 0)
    skipped = save_result.get("skipped", 0)
    print(f"  ✅ Saved: {saved} new | Skipped: {skipped} duplicates")

    # Phase 3: Enrich
    print("\n📍 PHASE 3: Enriching with Hunter.io emails...")
    enrich_result = call_function("enrichLeads", {})
    found = enrich_result.get("found", 0)
    guessed = enrich_result.get("guessed", 0)
    remaining = enrich_result.get("remaining", 0)
    msg = enrich_result.get("message", "")
    if msg:
        print(f"  ℹ️  {msg}")
    else:
        print(f"  ✅ Emails found: {found} | Guessed: {guessed} | Still pending: {remaining}")

    print("\n" + "=" * 40)
    print("✅ PIPELINE COMPLETE")
    print(f"   New leads added:  {saved}")
    print(f"   Emails found:     {found}")
    print(f"   Emails guessed:   {guessed}")
    if remaining > 0:
        print(f"   ⚠️  {remaining} leads still pending (will enrich on next run)")
    print("=" * 40)

    return saved, found, guessed

if __name__ == "__main__":
    main()
