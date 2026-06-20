"""Fetch news articles related to a breeding facility."""
import logging
import time
import urllib.parse
import xml.etree.ElementTree as ET

import requests

logger = logging.getLogger(__name__)


def fetch_news(name: str, city: str = '', state: str = '') -> list[dict]:
    """Search Google News RSS for articles about a facility."""
    location = ' '.join(p for p in [city, state] if p)
    query = f'"{name}" puppy mill OR dog breeder {location}'.strip()
    url = (
        'https://news.google.com/rss/search?q='
        + urllib.parse.quote(query)
        + '&hl=en-US&gl=US&ceid=US:en'
    )

    articles = []
    try:
        time.sleep(0.5)
        res = requests.get(url, timeout=15, headers={'User-Agent': "Ben's Breads Dog Watch"})
        root = ET.fromstring(res.content)
        for item in root.findall('.//item')[:5]:
            title = item.findtext('title', '')
            link = item.findtext('link', '')
            pub_date = item.findtext('pubDate', '')
            source_el = item.find('source')
            source = source_el.text if source_el is not None else ''
            if title and link:
                articles.append({
                    'title': title,
                    'url': link,
                    'published': pub_date,
                    'source': source,
                })
    except (requests.RequestException, ET.ParseError) as exc:
        logger.warning('News fetch failed for %s: %s', name, exc)
    return articles
