from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from time import mktime

import feedparser


FEEDS: dict[str, str] = {
    "ITmedia AI+": "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml",
    "Publickey": "https://www.publickey1.jp/atom.xml",
    "Zenn AIタグ": "https://zenn.dev/topics/ai/feed",
    "はてブTech": "https://b.hatena.ne.jp/hotentry/it.rss",
    "TechCrunch Japan": "https://jp.techcrunch.com/feed/",
}


@dataclass
class Entry:
    title: str
    link: str
    summary: str
    source: str
    published: datetime | None


def _parse_published(entry) -> datetime | None:
    struct = getattr(entry, "published_parsed", None) or getattr(entry, "updated_parsed", None)
    if not struct:
        return None
    return datetime.fromtimestamp(mktime(struct), tz=timezone.utc)


def fetch_all() -> list[Entry]:
    entries: list[Entry] = []
    for source, url in FEEDS.items():
        parsed = feedparser.parse(url)
        for item in parsed.entries:
            entries.append(
                Entry(
                    title=getattr(item, "title", "").strip(),
                    link=getattr(item, "link", ""),
                    summary=getattr(item, "summary", "").strip(),
                    source=source,
                    published=_parse_published(item),
                )
            )
    return entries


def recent(limit: int = 30) -> list[Entry]:
    all_entries = fetch_all()
    seen_links: set[str] = set()
    deduped: list[Entry] = []
    for e in all_entries:
        if not e.link or e.link in seen_links:
            continue
        seen_links.add(e.link)
        deduped.append(e)
    deduped.sort(key=lambda e: e.published or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return deduped[:limit]
