from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx

from ai_radio.models import ResearchItem
from ai_radio.timeutil import utc_now_iso


TAG_WORDS = {
    "ai": "AI",
    "artificial intelligence": "AI",
    "iphone": "スマホ",
    "android": "スマホ",
    "robot": "ロボット",
    "gpu": "GPU",
    "nvidia": "GPU",
    "security": "セキュリティ",
    "privacy": "プライバシー",
    "startup": "スタートアップ",
}


class Researcher:
    def __init__(self, searxng_url: str, max_candidates: int):
        self.searxng_url = searxng_url.rstrip("/")
        self.max_candidates = max_candidates

    async def collect(self, theme: str) -> list[ResearchItem]:
        queries = [
            f"{theme} latest technology news",
            f"{theme} gadgets news",
            "AI consumer tech trending news",
        ]
        seen: set[str] = set()
        items: list[ResearchItem] = []
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            for query in queries:
                for result in await self._search(client, query):
                    url = result.get("url")
                    title = self._clean(result.get("title") or "")
                    if not url or not title or url in seen:
                        continue
                    seen.add(url)
                    text_excerpt = await self._fetch_excerpt(client, url)
                    snippet = self._clean(result.get("content") or "")
                    tags = self._tags_for(" ".join([title, snippet, text_excerpt]))
                    items.append(
                        ResearchItem(
                            title=title,
                            url=url,
                            snippet=snippet,
                            fetched_at=utc_now_iso(),
                            published_at=result.get("publishedDate"),
                            text_excerpt=text_excerpt,
                            tags=tags,
                        )
                    )
                    if len(items) >= self.max_candidates:
                        return items
        return items

    async def _search(self, client: httpx.AsyncClient, query: str) -> list[dict]:
        resp = await client.get(
            f"{self.searxng_url}/search",
            params={"q": query, "format": "json", "language": "all"},
            headers={"User-Agent": "ai-radio-mvp/0.1", "X-Real-IP": "127.0.0.1"},
        )
        resp.raise_for_status()
        payload = resp.json()
        return list(payload.get("results") or [])

    async def _fetch_excerpt(self, client: httpx.AsyncClient, url: str) -> str:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return ""
        try:
            resp = await client.get(url, headers={"User-Agent": "ai-radio-mvp/0.1"})
            if "text/html" not in resp.headers.get("content-type", ""):
                return ""
            text = re.sub(r"<(script|style).*?</\1>", " ", resp.text, flags=re.I | re.S)
            text = re.sub(r"<[^>]+>", " ", text)
            return self._clean(text)[:4000]
        except httpx.HTTPError:
            return ""

    @staticmethod
    def _clean(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _tags_for(text: str) -> list[str]:
        lower = text.lower()
        tags = [label for key, label in TAG_WORDS.items() if key in lower]
        return sorted(set(tags))[:6] or ["テック"]
