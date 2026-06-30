import asyncio

import httpx

from ai_radio.research import Researcher


def test_search_requests_json_with_client_ip_header():
    async def run_search():
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.params["format"] == "json"
            assert request.url.params["language"] == "all"
            assert request.headers["X-Real-IP"] == "127.0.0.1"
            return httpx.Response(200, json={"results": [{"title": "Test"}]})

        researcher = Researcher("http://searxng:8080", max_candidates=20)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await researcher._search(client, "AI news")

    assert asyncio.run(run_search()) == [{"title": "Test"}]
