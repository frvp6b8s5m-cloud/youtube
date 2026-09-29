import re
import xml.etree.ElementTree as ET

import requests

TRENDS_RSS = "https://trends.google.com/trending/rss"
USER_AGENT = "CloudShortsFactory/1.0"


def _clean(value):
    return re.sub(r"\s+", " ", (value or "").strip())


def fetch_trends(config):
    cfg = config.get("trends", {})
    if not cfg.get("enabled", True):
        return []

    response = requests.get(
        TRENDS_RSS,
        params={"geo": cfg.get("geo", "US"), "hl": cfg.get("language", "en-US")},
        headers={"User-Agent": USER_AGENT},
        timeout=20,
    )
    response.raise_for_status()

    root = ET.fromstring(response.content)
    results = []
    limit = int(cfg.get("max_candidates", 20))

    for item in root.findall(".//item"):
        title = _clean(item.findtext("title"))
        if not title:
            continue
        results.append({
            "query": title,
            "traffic": _clean(item.findtext("{*}approx_traffic")),
            "published": _clean(item.findtext("pubDate")),
            "url": _clean(item.findtext("link")),
        })
        if len(results) >= limit:
            break

    return results
