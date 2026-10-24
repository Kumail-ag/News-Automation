import time
import feedparser

urls = [l.strip() for l in open("feeds.txt") if l.strip() and not l.startswith("#")]
for url in urls:
    f = feedparser.parse(url, agent="Mozilla/5.0 (feed-check)")
    if not f.entries:
        print(f"FAIL  {url}  (status: {getattr(f, 'status', 'no response')})")
    else:
        t = f.entries[0].get("published_parsed") or f.entries[0].get("updated_parsed")
        date = time.strftime("%Y-%m-%d", t) if t else "no date"
        print(f"OK    {url}  items={len(f.entries)} latest={date}")
