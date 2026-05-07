#!/usr/bin/env python3
"""
Scrape local business leads from Google Maps using Outscraper API.
Outputs JSON to stdout for the agent to process.
Usage: python scrape_leads.py
"""

import os
import sys
import json
import requests
import time

OUTSCRAPER_API_KEY = os.environ.get("OUTSCRAPER_API_KEY")

SEARCHES = [
    "dental office Vancouver BC",
    "medical spa Vancouver BC",
    "cosmetic clinic Vancouver BC",
    "dermatology clinic Vancouver BC"
]

def scrape_google_maps(query, limit=50):
    print(f"Scraping: {query}", file=sys.stderr)
    url = "https://api.app.outscraper.com/maps/search-v3"
    params = {
        "query": query,
        "limit": limit,
        "async": False
    }
    headers = {"X-API-KEY": OUTSCRAPER_API_KEY}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=60)
        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text[:200]}", file=sys.stderr)
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
        print(f"Got {len(results)} results", file=sys.stderr)
        return results
    except Exception as e:
        print(f"Exception: {e}", file=sys.stderr)
        return []

def main():
    if not OUTSCRAPER_API_KEY:
        print("ERROR: OUTSCRAPER_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    all_results = []
    for query in SEARCHES:
        results = scrape_google_maps(query, limit=50)
        all_results.extend(results)
        time.sleep(1)

    print(f"Total scraped: {len(all_results)}", file=sys.stderr)

    # Deduplicate and clean
    seen = set()
    output = []
    for item in all_results:
        name = (item.get("name") or "").strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        output.append({
            "business_name": name,
            "phone": item.get("phone") or "",
            "website": item.get("website") or "",
            "address": item.get("full_address") or item.get("address") or "",
            "city": item.get("city") or "Vancouver",
            "rating": str(item.get("rating") or ""),
            "category": item.get("category") or "",
            "email_status": "pending",
            "status": "new",
            "source": "outscraper"
        })

    print(f"Unique leads: {len(output)}", file=sys.stderr)
    print(json.dumps(output))

if __name__ == "__main__":
    main()
