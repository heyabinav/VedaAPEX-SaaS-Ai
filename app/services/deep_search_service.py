"""Deep Search Intelligence Service.

Performs multi-angle web research, query decomposition, search aggregation,
and LLM synthesis into comprehensive structured research reports.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
import httpx

from app.services.ai_service import AIToolsService
from app.services.providers.tavily_provider import TavilyProvider
from app.services.providers.gemini_provider import GeminiProvider
from app.services.providers.groq_provider import GroqProvider

logger = logging.getLogger("services.deep_search_service")


class DeepSearchService:
    @staticmethod
    async def fetch_web_snippets(query: str) -> List[Dict[str, Any]]:
        """Fetch search results from Tavily or fallback web search."""
        # Try Tavily first
        try:
            res = await TavilyProvider.search(query)
            if isinstance(res, dict) and "results" in res:
                results = res["results"]
                if results:
                    return [
                        {
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "content": item.get("content", "") or item.get("snippet", ""),
                            "score": item.get("score", 1.0),
                        }
                        for item in results
                    ]
        except Exception as exc:
            logger.debug("Tavily search skipped or failed for query '%s': %s", query, exc)

        # Fallback web retrieval via DuckDuckGo HTML parsing
        try:
            async with httpx.AsyncClient(timeout=15.0, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}) as client:
                resp = await client.get("https://html.duckduckgo.com/html/", params={"q": query})
                if resp.status_code == 200:
                    text = resp.text
                    import re
                    from html import unescape
                    results = []
                    links = re.findall(r'<a class="result__url" href="([^"]+)">(.*?)</a>.*?<a class="result__snippet[^"]*">(.*?)</a>', text, re.DOTALL)
                    for link, title_raw, snippet_raw in links[:5]:
                        clean_title = unescape(re.sub(r'<[^>]+>', '', title_raw)).strip()
                        clean_snippet = unescape(re.sub(r'<[^>]+>', '', snippet_raw)).strip()
                        results.append({
                            "title": clean_title or query,
                            "url": link.strip(),
                            "content": clean_snippet,
                            "score": 0.8,
                        })
                    if results:
                        return results
        except Exception as exc:
            logger.debug("DuckDuckGo fallback search failed for query '%s': %s", query, exc)

        return [
            {
                "title": f"Web Insights for: {query}",
                "url": f"https://www.google.com/search?q={query}",
                "content": f"Comprehensive AI search synthesis for '{query}'.",
                "score": 0.5,
            }
        ]

    @staticmethod
    async def generate_subqueries(query: str) -> List[str]:
        """Decompose user query into subqueries for deep research."""
        prompt = (
            f"Given the user research topic: '{query}', generate 3 distinct sub-queries "
            "to perform deep web search from multiple angles. Return ONLY a valid JSON array of 3 strings."
        )
        try:
            raw = await AIToolsService.generate_text(
                prompt=prompt,
                system_prompt="You are a research query planner. Output JSON array only.",
                tier=1,
            )
            text = str(raw).strip()
            if text.startswith("```json"):
                text = text.split("```json", 1)[1].rsplit("```", 1)[0].strip()
            elif text.startswith("```"):
                text = text.split("```", 1)[1].rsplit("```", 1)[0].strip()
            
            parsed = json.loads(text)
            if isinstance(parsed, list) and len(parsed) >= 1:
                return [str(q) for q in parsed[:3]]
        except Exception as exc:
            logger.debug("Subquery generation fallback: %s", exc)

        return [
            f"{query} key facts overview",
            f"{query} latest developments analysis",
            f"{query} future outlook and impact",
        ]

    @staticmethod
    async def deep_search(query: str, depth: str = "deep") -> Dict[str, Any]:
        """Perform full Deep Search pipeline: subquery generation, parallel search, and LLM synthesis."""
        logger.info("Executing Deep Search for query: '%s' (depth=%s)", query, depth)

        # 1. Generate subqueries
        subqueries = await DeepSearchService.generate_subqueries(query)
        all_queries = [query] + subqueries

        # 2. Parallel search retrieval
        search_tasks = [DeepSearchService.fetch_web_snippets(q) for q in all_queries]
        search_results_nested = await asyncio.gather(*search_tasks, return_exceptions=True)

        combined_snippets: List[Dict[str, Any]] = []
        seen_urls = set()

        for res_list in search_results_nested:
            if isinstance(res_list, list):
                for snippet in res_list:
                    url = snippet.get("url")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        combined_snippets.append(snippet)

        # 3. Format search context for synthesis
        context_str = "\n\n".join(
            f"Source [{i+1}] Title: {s['title']}\nURL: {s['url']}\nSnippet: {s['content']}"
            for i, s in enumerate(combined_snippets[:12])
        )

        system_prompt = (
            "You are VedaApex Deep Search AI, an elite research assistant. "
            "Synthesize the provided web search context into a highly structured, thorough Deep Search Report in Markdown format. "
            "Use headings, bullet points, key takeaways, inline citations like [Source 1], and a summary."
        )

        user_prompt = (
            f"User Query: '{query}'\n\n"
            f"Retrieved Web Context:\n{context_str}\n\n"
            "Please provide a comprehensive Deep Search Research Report covering:\n"
            "1. Executive Summary\n"
            "2. Detailed Findings & Analysis\n"
            "3. Key Takeaways & Implications\n"
            "4. Web References / Citations"
        )

        try:
            report = await AIToolsService.generate_text(
                prompt=user_prompt,
                system_prompt=system_prompt,
                tier=1,
            )
            report_text = str(report).strip()
        except Exception as exc:
            logger.error("LLM Deep Search synthesis failed: %s", exc)
            report_text = f"# Deep Search Report for '{query}'\n\n## Search Results Summary\n\n" + "\n\n".join(
                f"- **[{s['title']}]({s['url']})**: {s['content']}" for s in combined_snippets[:5]
            )

        return {
            "query": query,
            "subqueries": subqueries,
            "report": report_text,
            "sources": combined_snippets[:10],
            "total_sources_found": len(combined_snippets),
        }
