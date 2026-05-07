#!/usr/bin/env python3
"""
Olympus Cold Outreach — Daily Email Drip
Pulls cosmetic/derm leads, generates personalized emails via Hugging Face, sends via Gmail.
Sends 5 emails per run to stay under spam thresholds.
"""

import os
import json
import requests
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── Config ──────────────────────────────────────────────────────────────────
BASE44_APP_ID        = os.environ.get("VITE_BASE44_APP_ID", "69b54834a5db0026b523dd32")
BASE44_SERVICE_TOKEN = os.environ.get("BASE44_SERVICE_TOKEN")
BASE44_API_URL       = os.environ.get("VITE_BASE44_BACKEND_URL", "https://base44.app")
HF_ACCESS_TOKEN      = os.environ.get("HUGGING_FACE_ACCESS_TOKEN")
GMAIL_ACCESS_TOKEN   = os.environ.get("GMAIL_ACCESS_TOKEN")

SENDER_EMAIL = "thedc.bookings@gmail.com"
SENDER_NAME  = "Derek | Olympus AI"
DAILY_LIMIT  = 5

TARGET_CATEGORIES = [
    "Dermatologist", "Skin care clinic", "Medical spa",
    "Cosmetic surgeon", "Plastic surgeon", "Plastic surgery clinic",
    "Specialized clinic", "Facial spa"
]

# ── Fetch leads ──────────────────────────────────────────────────────────────
def fetch_leads():
    headers = {
        "app-id": BASE44_APP_ID,
        "Authorization": f"Bearer {BASE44_SERVICE_TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"{BASE44_API_URL}/api/apps/{BASE44_APP_ID}/entities/Lead"
    params = {"status": "new", "limit": 100}
    r = requests.get(url, headers=headers, params=params)
    r.raise_for_status()
    all_leads = r.json()

    # Filter: has email + is in target category
    qualified = [
        l for l in all_leads
        if l.get("email") and l.get("category") in TARGET_CATEGORIES
    ]
    return qualified[:DAILY_LIMIT]

# ── Generate email via Hugging Face ─────────────────────────────────────────
def generate_email(lead):
    name     = lead.get("first_name") or "there"
    business = lead["business_name"]
    category = lead["category"]

    label_map = {
        "Dermatologist": "dermatology clinic",
        "Skin care clinic": "skin care clinic",
        "Medical spa": "medical spa",
        "Cosmetic surgeon": "cosmetic surgery practice",
        "Plastic surgeon": "plastic surgery practice",
        "Plastic surgery clinic": "plastic surgery clinic",
        "Specialized clinic": "aesthetic clinic",
        "Facial spa": "facial spa"
    }
    clinic_type = label_map.get(category, "clinic")

    prompt = f"""Write a short, friendly cold outreach email from Derek at Olympus AI to {name} at {business}, a {clinic_type} in Vancouver.

The email should:
- Be 3-4 short paragraphs max
- Mention that Olympus AI helps {clinic_type}s automate patient follow-ups, appointment reminders, and reactivation campaigns using AI
- Sound human and conversational, not salesy
- End with a soft CTA asking for a free 20-minute call
- Sign off as: Derek | Olympus AI

Write only the email body, no subject line, no extra commentary."""

    response = requests.post(
        "https://router.huggingface.co/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {HF_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "model": "meta-llama/Llama-3.1-8B-Instruct",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 350,
            "temperature": 0.7
        }
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()

# ── Send via Gmail ───────────────────────────────────────────────────────────
def send_email(to_email, business_name, body):
    subject = f"Quick idea for {business_name}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"{SENDER_NAME} <{SENDER_EMAIL}>"
    msg["To"]      = to_email

    msg.attach(MIMEText(body, "plain"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    r = requests.post(
        "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
        headers={
            "Authorization": f"Bearer {GMAIL_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        },
        json={"raw": raw}
    )
    r.raise_for_status()
    return r.json()

# ── Mark lead as contacted ───────────────────────────────────────────────────
def mark_contacted(lead_id):
    headers = {
        "app-id": BASE44_APP_ID,
        "Authorization": f"Bearer {BASE44_SERVICE_TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"{BASE44_API_URL}/api/apps/{BASE44_APP_ID}/entities/Lead/{lead_id}"
    requests.put(url, headers=headers, json={"status": "contacted"})

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("🚀 Olympus Outreach — starting daily drip...")

    leads = fetch_leads()
    if not leads:
        print("✅ No new leads to contact today.")
        return

    print(f"📋 Found {len(leads)} leads to contact today")

    results = []
    for lead in leads:
        business = lead["business_name"]
        email    = lead["email"]
        print(f"\n✉️  Generating email for {business} ({email})...")

        try:
            body = generate_email(lead)
            send_email(email, business, body)
            mark_contacted(lead["id"])
            print(f"   ✅ Sent to {email}")
            results.append({"business": business, "email": email, "status": "sent"})
        except Exception as e:
            print(f"   ❌ Failed for {business}: {e}")
            results.append({"business": business, "email": email, "status": f"failed: {e}"})

    print(f"\n📊 Done — {len([r for r in results if r['status'] == 'sent'])}/{len(results)} emails sent")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
