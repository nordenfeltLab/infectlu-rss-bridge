#!/usr/bin/env python3
"""Fetch the Infect@LU RDF/RSS feed and render a readable public HTML snapshot."""
from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

RSS_URL = "https://lup.lub.lu.se/search/feed/monthly?q=department+exact+v1001765"
OUT_DIR = Path(__file__).resolve().parents[1] / "docs"
MAX_ENTRIES = 100

class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)
    def handle_starttag(self, tag, attrs):
        if tag in ("p", "br", "li"):
            self.parts.append(" ")

def clean_text(s: str, limit: int = 750) -> str:
    parser = PlainText()
    parser.feed(unescape(s or ""))
    text = re.sub(r"\s+", " ", "".join(parser.parts)).strip()
    return text[:limit].rstrip() + ("..." if len(text) > limit else "")

def child_text(item: ET.Element, name: str) -> str:
    # ET's wildcard namespace syntax works for namespaced RDF/RSS 1.0 and RSS 2.0.
    el = item.find("{*}" + name)
    return (el.text or "").strip() if el is not None else ""

def parse_feed(payload: bytes) -> list[dict]:
    root = ET.fromstring(payload)
    entries = []
    seen = set()
    for item in root.findall(".//{*}item"):
        title = child_text(item, "title")
        link = child_text(item, "link")
        if not link:
            link = next((v for k, v in item.attrib.items() if k.endswith("}about")), "")
        if not title or not link or not link.startswith(("https://", "http://")):
            continue
        if link in seen:
            continue
        seen.add(link)
        entries.append({
            "title": clean_text(title, 350),
            "link": link,
            "published": child_text(item, "date") or child_text(item, "pubDate"),
            "summary": clean_text(child_text(item, "description"), 450),
        })
    return entries[:MAX_ENTRIES]

def fetch() -> bytes:
    req = urllib.request.Request(
        RSS_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; InfectLU-Publications-Feed/1.0)",
            "Accept": "application/rss+xml, application/rdf+xml, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=35) as res:
        data = res.read(5_000_000)
        print(f"Downloaded {len(data)} bytes from {res.url} (HTTP {res.status})")
        return data

def render(entries: list[dict], checked: str) -> str:
    blocks = []
    for p in entries:
        date = f'<span class="date">{escape(p["published"])}</span>' if p["published"] else ""
        summ = f'<p>{escape(p["summary"])}</p>' if p["summary"] else ""
        blocks.append(f'<article>{date}<h2><a href="{escape(p["link"], quote=True)}">{escape(p["title"])}</a></h2>{summ}</article>')
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Infect@LU publications – recent RSS entries</title>
<style>body{font:16px/1.55 system-ui, sans-serif;max-width:850px;margin:3rem auto;padding:0 1.2rem;color:#182b32}h1{font-size:1.8rem}h2{font-size:1.15rem;margin:.2rem 0}a{color:#075a8d}article{padding:1rem 0;border-top:1px solid #ddd}.date,small{color:#52646e}.date{font-size:.85rem}p{margin:.5rem 0 0}</style>
</head><body><h1>Infect@LU – recent publications</h1>
<p>Automatically collected from the official Lund University Publications RSS feed. Entries indicate feed updates, which may differ from original publication dates.</p>
<p><small>Last successful fetch (UTC): """+escape(checked)+""" · Entries: """+str(len(entries))+"""<br>Source: <a href="""+'"'+escape(RSS_URL,quote=True)+'"'+""">Official Infect@LU RSS</a> · <a href="feed.json">Machine-readable JSON</a></small></p>
"""+"\n".join(blocks)+"\n</body></html>\n"

def main() -> None:
    raw = Path(os.environ["RSS_SAMPLE_FILE"]).read_bytes() if os.environ.get("RSS_SAMPLE_FILE") else fetch()
    entries = parse_feed(raw)
    if not entries:
        raise RuntimeError("RSS parsed but contained zero valid items. Existing published snapshot will be kept.")
    checked = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = {"source": RSS_URL, "last_successful_fetch_utc": checked, "count": len(entries), "items": entries}
    (OUT_DIR / "feed.json").write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    (OUT_DIR / "index.html").write_text(render(entries, checked), encoding="utf-8")
    print(f"Wrote {len(entries)} entries to {OUT_DIR}")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
