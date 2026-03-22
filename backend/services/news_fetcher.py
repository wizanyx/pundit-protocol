import os
import json
from typing import Any, Dict, List
from pathlib import Path

import requests
from dotenv import load_dotenv

# Force load the .env file from the current directory
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

NEWS_API_URL = os.getenv("NEWS_API_URL", "https://newsapi.org/v2/everything")

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