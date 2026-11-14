#!/usr/bin/env python3
"""Fetch RSS/Atom feeds from sources.json, group matching stories, write docs/news.json.

Uses only the Python standard library, so there is nothing to install.
Run:  python scripts/fetch_news.py
"""
import html
import json
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
SOURCES_FILE = ROOT / "sources.json"
OUT_FILE = ROOT / "docs" / "news.json"

MAX_AGE_HOURS = {"australia": 36, "world": 36, "factcheck": 24 * 14}
MAX_PER_SOURCE = 25
MAX_CLUSTERS = {"australia": 80, "world": 80, "factcheck": 30}
RELIABILITY_RANK = {"very-high": 4, "high": 3, "mostly-factual": 2, "mixed": 1}
LEAN_BUCKET = {"left": "left", "left-centre": "left", "centre": "centre",
               "right-centre": "right", "right": "right"}
USER_AGENT = "Mozilla/5.0 (compatible; OpenNewsAU/1.0; +https://github.com/)"

STOPWORDS = set("""a an the and or but of to in on at for from by with as is are was were be been
has have had it its this that these those after over into about says say said new more than
up out not no will can could would should may his her their our your they we you he she who
what when where why how amid against under amid off live updates news latest""".split())


def local(tag):
    return tag.rsplit("}", 1)[-1].lower() if isinstance(tag, str) else ""


def child_text(el, *names):
    for c in el:
        if local(c.tag) in names and (c.text or "").strip():
            return c.text.strip()
    return ""


def clean_text(s, limit=None):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    if limit and len(s) > limit:
        s = s[:limit].rsplit(" ", 1)[0] + "…"
    return s


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError, IndexError):
        d = None
    if d is None:
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def entry_link(el):
    for c in el:
        if local(c.tag) == "link":
            href = c.get("href")
            if href and c.get("rel", "alternate") == "alternate":
                return href.strip()
            if c.text and c.text.strip():
                return c.text.strip()
    for c in el:  # fallback: any atom link, or guid that is a URL
        if local(c.tag) == "link" and c.get("href"):
            return c.get("href").strip()
        if local(c.tag) == "guid" and (c.text or "").startswith("http"):
            return c.text.strip()
    return ""


def parse_xml(xml_bytes):
    try:
        return ET.fromstring(xml_bytes)
    except ET.ParseError:
        # Some publishers ship slightly broken XML (stray control characters or
        # bare "&"). Clean those up and try once more.
        text = xml_bytes.decode("utf-8", "replace")
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        text = re.sub(r"&(?!(?:[a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);)", "&amp;", text)
        text = re.sub(r"^\s*<\?xml[^>]*\?>", "", text)
        return ET.fromstring(text)


def parse_feed(xml_bytes, source):
    root = parse_xml(xml_bytes)
    items = []
    for el in root.iter():
        if local(el.tag) not in ("item", "entry"):
            continue
        title = clean_text(child_text(el, "title"))
        link = entry_link(el)
        if not title or not link:
            continue
        # Google News appends " - Publisher" to titles; strip it.
        title = re.sub(r"\s+[-–|]\s+[^-–|]{2,40}$", "", title) if "news.google." in source["url"] else title
        published = parse_date(child_text(el, "pubdate", "published", "updated", "date", "issued"))
        summary = clean_text(child_text(el, "description", "summary", "content", "encoded"), 280)
        if "news.google." in source["url"]:
            summary = ""  # Google News summaries just repeat the headline
        items.append({
            "title": title,
            "link": link,
            "published": published,
            "summary": summary,
            "source": source["name"],
            "lean": source["lean"],
            "reliability": source["reliability"],
        })
    return items


def fetch(source):
    req = urllib.request.Request(source["url"], headers={"User-Agent": USER_AGENT,
                                                         "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read()


def tokens(title):
    words = re.findall(r"[a-z0-9']+", title.lower())
    return {w.strip("'") for w in words if len(w) > 2 and w not in STOPWORDS}


def similar(a, b):
    shared = a & b
    if len(shared) < 3:
        return False
    return len(shared) / len(a | b) >= 0.34 or len(shared) / min(len(a), len(b)) >= 0.6


def cluster(items):
    clusters = []
    for it in sorted(items, key=lambda x: x["published"], reverse=True):
        t = tokens(it["title"])
        for c in clusters:
            if it["source"] not in c["_sources"] and similar(t, c["_tokens"]):
                c["stories"].append(it)
                c["_sources"].add(it["source"])
                c["_tokens"] |= t
                break
        else:
            clusters.append({"stories": [it], "_sources": {it["source"]}, "_tokens": set(t)})

    out = []
    for c in clusters:
        stories = sorted(c["stories"], key=lambda s: (-RELIABILITY_RANK.get(s["reliability"], 0), s["published"]))
        leans = {"left": 0, "centre": 0, "right": 0}
        for s in stories:
            leans[LEAN_BUCKET.get(s["lean"], "centre")] += 1
        out.append({
            "headline": stories[0]["title"],
            "summary": next((s["summary"] for s in stories if s["summary"]), ""),
            "latest": max(s["published"] for s in stories).isoformat(),
            "source_count": len(stories),
            "leans": leans,
            "stories": [{**s, "published": s["published"].isoformat()} for s in stories],
        })
    # Stories covered by more outlets first, then newest.
    out.sort(key=lambda c: (min(c["source_count"], 5), c["latest"]), reverse=True)
    return out


def build(sources, fetcher=fetch, now=None):
    now = now or datetime.now(timezone.utc)
    by_region = {"australia": [], "world": [], "factcheck": []}
    status = []

    def work(src):
        try:
            items = parse_feed(fetcher(src), src)
            return src, items, None
        except Exception as e:  # one bad feed must never break the whole run
            return src, [], f"{type(e).__name__}: {e}"[:200]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(work, sources))

    for src, items, err in results:
        region = src.get("region", "world")
        cutoff = now - timedelta(hours=MAX_AGE_HOURS.get(region, 36))
        fresh = []
        seen = set()
        for it in items:
            if it["published"] is None:
                it["published"] = now
            if it["published"] < cutoff or it["published"] > now + timedelta(hours=2):
                continue
            key = it["title"].lower()
            if key in seen:
                continue
            seen.add(key)
            fresh.append(it)
        fresh.sort(key=lambda x: x["published"], reverse=True)
        fresh = fresh[:MAX_PER_SOURCE]
        by_region.setdefault(region, []).extend(fresh)
        status.append({"name": src["name"], "region": region, "lean": src["lean"],
                       "reliability": src["reliability"], "ok": err is None,
                       "count": len(fresh), "error": err})

    return {
        "generated": now.isoformat(),
        "regions": {r: cluster(items)[:MAX_CLUSTERS.get(r, 80)] for r, items in by_region.items()},
        "sources": status,
    }


def main():
    sources = json.loads(SOURCES_FILE.read_text())["sources"]
    data = build(sources)
    ok = sum(s["ok"] for s in data["sources"])
    for s in data["sources"]:
        mark = "ok " if s["ok"] else "ERR"
        print(f"[{mark}] {s['name']:<28} {s['count']:>3} stories  {s['error'] or ''}")
    if ok == 0:
        print("Every feed failed; keeping the previous news.json.", file=sys.stderr)
        sys.exit(1)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"Wrote {OUT_FILE} — {ok}/{len(data['sources'])} feeds ok")


if __name__ == "__main__":
    main()
