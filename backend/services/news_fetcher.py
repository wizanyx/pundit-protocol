import os
from typing import Any, Dict, List
import json

import requests

NEWS_API_URL = os.getenv("NEWS_API_URL", "https://newsapi.org/v2/everything")


def _get_newsapi_key() -> str:
    key = os.getenv("NEWSAPI_KEY") or os.getenv("NEWS_API_KEY")
    if not key:
        raise ValueError(
            "Missing NewsAPI key. Set NEWSAPI_KEY or NEWS_API_KEY in your environment."
        )
    return key


def search_news(topic: str, limit: int = 5, language: str = "en") -> List[Dict[str, Any]]:
    """Search NewsAPI for a topic and return normalized results."""
    if not topic.strip():
        raise ValueError("The 'topic' parameter cannot be empty.")

    if not isinstance(limit, int) or limit <= 0:
        raise ValueError("The 'limit' parameter must be a positive integer.")

    if not isinstance(language, str) or len(language) != 2:
        raise ValueError("The 'language' parameter must be a valid ISO 639-1 code (e.g., 'en').")

    api_key = _get_newsapi_key()

    params = {
        "q": topic,
        "language": language,
        "sortBy": "relevancy",
        "pageSize": limit,
        "apiKey": api_key,
    }

    try:
        resp = requests.get(NEWS_API_URL, params=params, timeout=15)
        resp.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
    except requests.exceptions.Timeout:
        raise RuntimeError("NewsAPI request timed out")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"NewsAPI request failed: {str(e)}")

    try:
        payload = resp.json()
    except json.JSONDecodeError:
        raise RuntimeError("Failed to decode NewsAPI response as JSON")

    articles = payload.get("articles")
    if not isinstance(articles, list):
        raise RuntimeError("Invalid NewsAPI response: 'articles' is missing or not a list")

    results: List[Dict[str, Any]] = []
    for item in articles[:limit]:
        source = item.get("source") or {}
        results.append(
            {
                "title": item.get("title") or "No title available",
                "url": item.get("url") or "No URL available",
                "source": source.get("name") or "Unknown source",
                "published_at": item.get("publishedAt"),
                "snippet": item.get("description") or item.get("content") or "No content available",
            }
        )

    if not results:
        raise RuntimeError("No articles found in NewsAPI response")

    return results
