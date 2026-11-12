#!/usr/bin/env python3
"""Fetch the Infect@LU RSS feed and render a readable HTML/JSON snapshot.

A persistent ID/signature manifest lets successive scheduled runs distinguish
newly appearing RSS records from records already seen by the bridge. RSS dates
are retained as source metadata and are not treated as LUP registration dates.
"""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

RSS_URL = "https://lup.lub.lu.se/search/feed/monthly?q=department+exact+v1001765"
OUT_DIR = Path(__file__).resolve().parents[1] / "docs"
STATE_FILE = Path(__file__).resolve().parents[1] / ".state" / "seen_publications.json"
MAX_ENTRIES = 1000

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
    el = item.find("{*}" + name)
    return (el.text or "").strip() if el is not None else ""


def item_id(item: dict) -> str:
    # LUP publication links contain a stable record identifier. Keep the full
    # link as a fallback so IDs remain stable if a feed item has no explicit ID.
    return item.get("link", "").strip()


def signature(item: dict) -> str:
    value = "\n".join(item.get(k, "") for k in ("title", "link", "published", "summary"))
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_feed(payload: bytes) -> list[dict]:
    root = ET.fromstring(payload)
    entries = []
    seen = set()
    for node in root.findall(".//{*}item"):
        title = child_text(node, "title")
        link = child_text(node, "link")
        if not link:
            link = next((v for k, v in node.attrib.items() if k.endswith("}about")), "")
        if not title or not link or not link.startswith(("https://", "http://")):
            continue
        if link in seen:
            continue
        seen.add(link)
        entries.append({
            "id": link,
            "title": clean_text(title, 350),
            "link": link,
            "published": child_text(node, "date") or child_text(node, "pubDate"),
            "summary": clean_text(child_text(node, "description"), 450),
        })
    return entries[:MAX_ENTRIES]


def fetch(url: str, label: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; InfectLU-Publications-Feed/1.0)",
            "Accept": "application/rss+xml, application/rdf+xml, application/json, application/xml, text/xml, */*",
        },
    )
    with urllib.request.urlopen(req, timeout=35) as res:
        data = res.read(5_000_000)
        print(f"Downloaded {len(data)} bytes from {res.url} (HTTP {res.status}; {label})")
        return data


def read_json(url: str) -> dict | None:
    try:
        return json.loads(fetch(url, "previous bridge snapshot").decode("utf-8"))
    except Exception as exc:
        print(f"Previous snapshot unavailable; will establish a baseline: {exc}")
        return None


def load_previous_state() -> tuple[dict[str, str], str | None, str]:
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            seen = state.get("seen", {})
            if isinstance(seen, dict):
                return seen, state.get("last_successful_fetch_utc"), "tracked"
        except Exception as exc:
            print(f"Saved tracking state could not be read: {exc}")

    # On upgrade, compare against the currently published bridge snapshot so
    # the first tracked run does not label the entire existing feed as new.
    previous_url = os.environ.get("PREVIOUS_FEED_URL", "").strip()
    if previous_url:
        previous = read_json(previous_url)
        if previous and isinstance(previous.get("items"), list):
            seen = {}
            for item in previous["items"]:
                if isinstance(item, dict) and item.get("link"):
                    seen[item_id(item)] = signature(item)
            return seen, previous.get("last_successful_fetch_utc"), "bootstrapped"

    return {}, None, "baseline"


def render(entries: list[dict], checked: str, previous_checked: str | None,
           new_items: list[dict], changed_items: list[dict], tracking_status: str) -> str:
    blocks = []
    for p in entries:
        date = f'<span class="date">RSS date: {escape(p["published"])}</span>' if p["published"] else ""
        summ = f'<p>{escape(p["summary"])}</p>' if p["summary"] else ""
        blocks.append(f'<article>{date}<h2><a href="{escape(p["link"], quote=True)}">{escape(p["title"])}</a></h2>{summ}</article>')
    new_block = "".join(
        f'<li><a href="{escape(p["link"], quote=True)}">{escape(p["title"])}</a></li>'
        for p in new_items
    ) or "<li>None</li>"
    changed_block = "".join(
        f'<li><a href="{escape(p["link"], quote=True)}">{escape(p["title"])}</a></li>'
        for p in changed_items
    ) or "<li>None</li>"
    prior = escape(previous_checked or "not available")
    status_note = (
        "The bridge is comparing against its previous successful snapshot."
        if tracking_status in ("tracked", "bootstrapped")
        else "This is the initial baseline; new entries will be identified on the next successful run."
    )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Infect@LU publications – recent RSS entries</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;max-width:850px;margin:3rem auto;padding:0 1.2rem;color:#182b32}}h1{{font-size:1.8rem}}h2{{font-size:1.15rem;margin:.2rem 0}}a{{color:#075a8d}}article{{padding:1rem 0;border-top:1px solid #ddd}}.date,small{{color:#52646e}}.date{{font-size:.85rem}}p{{margin:.5rem 0 0}}section{{padding:.5rem 1rem;background:#f4f7f8;margin:1rem 0}}</style>
</head><body><h1>Infect@LU – recent publications</h1>
<p>Automatically collected from the official Lund University Publications RSS feed. RSS dates may differ from original publication dates and from the date a record was added to LUP.</p>
<p><small>Last successful fetch (UTC): {escape(checked)} · Entries: {len(entries)} · New since previous snapshot: {len(new_items)} · Changed records: {len(changed_items)}<br>Previous snapshot (UTC): {prior}<br>{escape(status_note)}<br>Source: <a href="{escape(RSS_URL, quote=True)}">Official Infect@LU RSS</a> · <a href="feed.json">Machine-readable JSON</a></small></p>
<section><h2>New since previous successful snapshot ({len(new_items)})</h2><ul>{new_block}</ul><h2>Changed since previous successful snapshot ({len(changed_items)})</h2><ul>{changed_block}</ul></section>
<h2>Current feed entries</h2>
{"\n".join(blocks)}
</body></html>
'''


def main() -> None:
    raw = Path(os.environ["RSS_SAMPLE_FILE"]).read_bytes() if os.environ.get("RSS_SAMPLE_FILE") else fetch(RSS_URL, "official RSS")
    entries = parse_feed(raw)
    if not entries:
        raise RuntimeError("RSS parsed but contained zero valid items. Existing published snapshot and tracking state will be kept.")

    previous_seen, previous_checked, tracking_status = load_previous_state()
    new_items = []
    changed_items = []
    current_signatures = {}
    for entry in entries:
        key = item_id(entry)
        sig = signature(entry)
        current_signatures[key] = sig
        if key not in previous_seen:
            new_items.append(entry)
        elif previous_seen[key] != sig:
            changed_items.append(entry)

    checked = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    # Keep all IDs ever observed, even after entries roll out of the monthly feed.
    merged_seen = dict(previous_seen)
    merged_seen.update(current_signatures)
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    state = {"version": 1, "last_successful_fetch_utc": checked, "seen": merged_seen}
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = {
        "source": RSS_URL,
        "last_successful_fetch_utc": checked,
        "previous_successful_fetch_utc": previous_checked,
        "tracking_status": tracking_status,
        "count": len(entries),
        "new_count": len(new_items),
        "new_items": new_items,
        "changed_count": len(changed_items),
        "changed_items": changed_items,
        "items": entries,
    }
    (OUT_DIR / "feed.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR / "index.html").write_text(render(entries, checked, previous_checked, new_items, changed_items, tracking_status), encoding="utf-8")
    print(f"Wrote {len(entries)} entries; {len(new_items)} new and {len(changed_items)} changed to {OUT_DIR}")

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
