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
            feed = feedparser.parse(url, agent="Mozilla/5.0 (digest-bot)")
        except Exception as e:
            print(f"Failed to read {url}: {e}")
            continue
        for entry in feed.entries[:8]:
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
    prompt = f"""You are my personal research assistant. Here is my profile:
{PROFILE}

Below are new articles. Judge each one against my profile using this scoring:
- 9-10: directly advances a top goal and I can act on it this week
- 7-8: clearly useful for one of my goals
- 0-6: general interest, trivia, news, hype, or off-topic. Discard.

Rules:
- Include ONLY articles scoring 7 or higher, at most 6 in total. Never pad the list.
- Prefer evidence-based, practical, free resources. Reject motivational content and shallow listicles.
- Use only what the article text says. If you only have a title, say "judged by title only".
- If nothing scores 7+, reply only: "Nothing relevant today."

Group the results under these headings (skip a heading if it has nothing):
FITNESS | AUTOMATION | CALCULUS | PROGRAMMING | READING & COMMUNICATION | STUDY ABROAD

For each article write:
- Headline
- Why it matters to me (one sentence tied to a specific goal or course)
- Do this: one concrete action with a time estimate (e.g. "Read in the evening, 15 min" or "Try during morning workout")
- Link

End with:
- DEADLINES: any dates mentioned, soonest first (skip if none)
- TODAY'S ONE THING: the single most valuable action from this digest

Plain text only, no markdown, no emojis.

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
