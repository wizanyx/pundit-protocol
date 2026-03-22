import os
import json
from typing import Any, Dict, List
from pathlib import Path

import re
import requests
from dotenv import load_dotenv

# Load backend/.env (one level above services/)
BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=BASE_DIR / ".env")

NEWS_API_URL = os.getenv("NEWS_API_URL", "https://newsapi.org/v2/everything")

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then", "so", "of", "to", "in", "on",
    "for", "with", "by", "about", "as", "at", "is", "are", "was", "were", "be", "been",
    "being", "it", "this", "that", "these", "those", "from", "my", "your", "our", "their",
    "his", "her", "its", "i", "you", "we", "they", "he", "she", "them", "me", "us",
}


def _topic_keywords(topic: str) -> list[str]:
    words = re.findall(r"[a-zA-Z0-9']+", (topic or "").lower())
    return [w for w in words if len(w) >= 3 and w not in STOPWORDS]


def _matches_topic(item: Dict[str, Any], keywords: list[str]) -> bool:
    if not keywords:
        return True
    hay = " ".join(
        [
            item.get("title") or "",
            item.get("description") or "",
            item.get("content") or "",
        ]
    ).lower()
    return any(k in hay for k in keywords)

def _get_newsapi_key() -> str:
    # Check both common naming conventions
    key = os.getenv("NEWSAPI_KEY") or os.getenv("NEWS_API_KEY")
    if not key:
        raise ValueError(
            "Missing NewsAPI key. Set NEWSAPI_KEY in your .env file."
        )
    return key

def search_news(topic: str, limit: int = 5, language: str = "en") -> List[Dict[str, Any]]:
    """Search NewsAPI for a topic and return normalized results."""
    
    # 1. Validation
    if not topic.strip():
        return [] # Return empty instead of crashing the whole engine

    api_key = _get_newsapi_key()

    params = {
        "q": topic,
        "language": language,
        "sortBy": "relevancy",
        "pageSize": limit,
        "apiKey": api_key,
    }

    # 2. Network Request
    try:
        resp = requests.get(NEWS_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        payload = resp.json()
    except requests.exceptions.RequestException as e:
        print(f"NewsAPI Warning: Request failed ({e})")
        return []
    except json.JSONDecodeError:
        print("NewsAPI Warning: Failed to decode JSON")
        return []

    # 3. Data Normalization
    articles = payload.get("articles", [])
    if not isinstance(articles, list):
        return []

    # 3.5 Topic filter to avoid irrelevant headlines
    keywords = _topic_keywords(topic)
    if keywords:
        filtered = [item for item in articles if _matches_topic(item, keywords)]
        if filtered:
            articles = filtered
        else:
            return []

    results: List[Dict[str, Any]] = []
    for item in articles[:limit]:
        # Clean the snippet: Prefer description, fallback to content, remove [...]
        raw_snippet = item.get("description") or item.get("content") or ""
        clean_snippet = raw_snippet.split(" [+")[0] # Removes the " [+123 chars]" suffix
        
        results.append({
            "title": item.get("title") or "No title",
            "url": item.get("url") or "#",
            "source": (item.get("source") or {}).get("name") or "Unknown",
            "published_at": item.get("publishedAt"),
            "snippet": clean_snippet or "No content available"
        })

    return results

if __name__ == "__main__":
    # Test block to verify it works independently
    try:
        test_results = search_news("Silicon Valley Bank", limit=2)
        print(f"Successfully fetched {len(test_results)} articles.")
        for r in test_results:
            print(f"- {r['title']} ({r['source']})")
    except Exception as e:
        print(f"Test Failed: {e}")
