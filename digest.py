import os
import time
import calendar
import smtplib
from email.mime.text import MIMEText

import feedparser
from google import genai

# ---------- Settings you can change ----------
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")  # check AI Studio for current free models
INTERESTS = "computer science, AI, Polymath Topics, Philosphy, Pakistan news"
HOURS = 24          # how far back to look for new articles
MAX_ITEMS = 60      # cap on articles sent to the AI
# ---------------------------------------------


def fetch_items():
    cutoff = time.time() - HOURS * 3600
    items = []
    with open("feeds.txt") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    for url in urls:
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"Failed to read {url}: {e}")
            continue
        for entry in feed.entries:
            t = entry.get("published_parsed") or entry.get("updated_parsed")
            if t and calendar.timegm(t) < cutoff:
                continue
            title = entry.get("title", "").strip()
            summary = entry.get("summary", "")[:300].strip()
            link = entry.get("link", "")
            items.append(f"- {title} | {summary} | {link}")
    return items[:MAX_ITEMS]


def summarize(items):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = f"""You are my news assistant. I'm a university student interested in: {INTERESTS}.
From the articles below, write a daily digest:
1. Pick the 5-8 most relevant and important stories.
2. For each: a one-line headline, a 1-2 sentence summary, and the link.
3. Ignore duplicates, ads, and fluff.
4. At the end, add a short "Deadlines & opportunities" section if any article mentions one.
Use plain text only, no markdown.

Articles:
""" + "\n".join(items)

    # Retry a few times in case of rate limits (429)
    for attempt in range(3):
        try:
            return client.models.generate_content(model=MODEL, contents=prompt).text
        except Exception as e:
            print(f"Gemini error (attempt {attempt + 1}): {e}")
            time.sleep(30 * (attempt + 1))
    raise RuntimeError("Gemini failed after 3 attempts")


def send_email(text):
    address = os.environ["EMAIL_ADDRESS"]
    msg = MIMEText(text, "plain", "utf-8")
    msg["Subject"] = "Your Daily Digest"
    msg["From"] = address
    msg["To"] = address
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(address, os.environ["EMAIL_APP_PASSWORD"])
        server.send_message(msg)


if __name__ == "__main__":
    items = fetch_items()
    print(f"Found {len(items)} recent articles")
    if not items:
        send_email("No new articles in the last 24 hours.")
    else:
        send_email(summarize(items))
    print("Digest sent.")
