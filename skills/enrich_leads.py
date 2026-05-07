#!/usr/bin/env python3
"""
Enrich leads with emails via Hunter.io.
Takes a JSON array of leads (with website field) via stdin or as argument.
Outputs enriched leads as JSON to stdout.
Usage: echo '[{"business_name":"...", "website":"..."}]' | python enrich_leads.py
"""

import os
import sys
import json
import requests
import time

HUNTER_API_KEY = os.environ.get("HUNTER_API_KEY")

def find_email_hunter(domain):
    domain = domain.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0].strip()
    if not domain or "." not in domain:
        return None, None, None

    try:
        r = requests.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": domain, "api_key": HUNTER_API_KEY, "limit": 1},
            timeout=10
        )
        if r.status_code == 200:
            data = r.json().get("data", {})
            emails = data.get("emails", [])
            if emails:
                email = emails[0].get("value")
                first = emails[0].get("first_name", "") or ""
                last = emails[0].get("last_name", "") or ""
                return email, first, last
    except Exception as e:
        print(f"Hunter error for {domain}: {e}", file=sys.stderr)

    return None, None, None

def main():
    if not HUNTER_API_KEY:
        print("ERROR: HUNTER_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    # Read leads from stdin
    raw = sys.stdin.read().strip()
    if not raw:
        print("No leads provided via stdin", file=sys.stderr)
        sys.exit(1)

    leads = json.loads(raw)
    print(f"Enriching {len(leads)} leads...", file=sys.stderr)

    enriched = []
    for lead in leads:
        website = lead.get("website", "")
        name = lead.get("business_name", "")

        if not website:
            lead["email_status"] = "not_found"
            enriched.append(lead)
            continue

        print(f"Looking up: {name[:40]}", file=sys.stderr)
        email, first, last = find_email_hunter(website)

        if email:
            lead["email"] = email
            lead["email_status"] = "found"
            lead["email_verified"] = True
            if first:
                lead["first_name"] = first
            if last:
                lead["last_name"] = last
            print(f"  Found: {email}", file=sys.stderr)
        else:
            domain = website.replace("https://", "").replace("http://", "").replace("www.", "").split("/")[0]
            if domain and "." in domain:
                lead["email"] = f"info@{domain}"
                lead["email_status"] = "guessed"
                lead["email_verified"] = False
                print(f"  Guessed: info@{domain}", file=sys.stderr)
            else:
                lead["email_status"] = "not_found"

        enriched.append(lead)
        time.sleep(0.4)

    print(json.dumps(enriched))

if __name__ == "__main__":
    main()
