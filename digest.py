import os
import time
import calendar
import smtplib
from email.mime.text import MIMEText

import feedparser
from google import genai

# ---------- Settings you can change ----------
MODELS = ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash-lite"]  # check AI Studio for current free models
INTERESTS = """Degree and year: BSCS, FAST-NUCES, first semester.
Courses and weak areas: Programming Fundamentals, Calculus, Functional English, Ideology and Constitution of Pakistan, ICT. Weak: programming (stopped Python before OOP).
Goals for the next 12 months (ranked by priority): 1) Fitness: lean muscle gain via home workouts. 2) Free-tool automation. 3) Calculus mastery. Also: communication, reading.
Target countries/regions: Germany, US, Australia for postgraduate study after BSCS.
Current skills and levels: Beginner Python, C++, HTML/CSS. Strong reader.
Skills I want to build: Automation, calculus, communication, Urdu and English articulateness.
Time available per week: About 7 hours for automation; evenings 6-10pm for reading and study; mornings 5:25-6:20 for exercise.
Topics I want to see: Free automation tools, learning programming, calculus, muscle-gain nutrition, study-abroad requirements, analytically rich history.
Topics to ignore completely: Trivia about countries or the world; history without analysis.
What makes information useful to me: Free, actionable, evidence-based, analytical; no motivational fluff."""
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

    for model in MODELS:
        for attempt in range(2):
            try:
                print(f"Trying {model} (attempt {attempt + 1})")
                return client.models.generate_content(model=model, contents=prompt).text
            except Exception as e:
                print(f"{model} error: {e}")
                time.sleep(20)
    raise RuntimeError("All Gemini models failed")


def send_email(text):
    address = os.environ["EMAIL_ADDRESS"]
    password = os.environ["EMAIL_APP_PASSWORD"]
    msg = MIMEText(text, "plain", "utf-8")
    msg["Subject"] = "Your Daily Digest"
    msg["From"] = address
    msg["To"] = address

    for attempt in range(3):
        # Method 1: port 465 (SSL)
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
                server.login(address, password)
                server.send_message(msg)
            return
        except Exception as e:
            print(f"SSL 465 failed (attempt {attempt + 1}): {e}")
        # Method 2: port 587 (STARTTLS)
        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
                server.starttls()
                server.login(address, password)
                server.send_message(msg)
            return
        except Exception as e:
            print(f"STARTTLS 587 failed (attempt {attempt + 1}): {e}")
        time.sleep(15)
    raise RuntimeError("Could not send email after several attempts")

if __name__ == "__main__":
    items = fetch_items()
    print(f"Found {len(items)} recent articles")
    if not items:
        send_email("No new articles in the last 24 hours.")
    else:
        send_email(summarize(items))
    print("Digest sent.")
