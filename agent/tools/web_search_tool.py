"""
Web Search Tool using Google Custom Search API
"""
import os
import json
import requests
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def web_search(query: str, num_results: int = 5) -> str:
    """
    Search the web using Google Custom Search API.

    This tool searches the web for current information, research papers,
    and latest developments in geology and mineral exploration.

    Args:
        query: Search query string
        num_results: Number of results to return (default: 5)

    Returns:
        Formatted search results with title, link, and snippet for each result
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")

    if not api_key or not search_engine_id:
        return "Error: Google API key or Search Engine ID not configured"

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": search_engine_id,
        "q": query,
        "num": min(num_results, 10)  # API limit is 10
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        results = response.json()

        if "items" not in results:
            return "No results found"

        formatted = []
        for item in results["items"]:
            result = {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", "")
            }
            formatted.append(result)

        return json.dumps(formatted, ensure_ascii=False, indent=2)

    except requests.exceptions.Timeout:
        return "Error: Search request timed out"
    except requests.exceptions.RequestException as e:
        return f"Error: {str(e)}"
    except json.JSONDecodeError:
        return "Error: Failed to parse search results"
