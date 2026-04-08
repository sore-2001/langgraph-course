"""
Web Search Tool using DuckDuckGo Search (ddgs package)

This tool searches the web using DuckDuckGo for current information,
research papers, and latest developments in geology and mineral exploration.
"""
import os
from typing import List, Dict
from dotenv import load_dotenv

try:
    from ddgs import DDGS
    HAS_DDGS = True
except ImportError:
    HAS_DDGS = False

# Load environment variables
load_dotenv()


def web_search(query: str, num_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo Search.

    Args:
        query: Search query string
        num_results: Number of results to return (default: 5)

    Returns:
        Formatted search results with title, link, and snippet for each result
    """
    if not HAS_DDGS:
        return "Error: ddgs package not installed. Run: pip install ddgs"

    try:
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=num_results))

        if not results:
            return "No results found"

        formatted = []
        for item in results:
            title = item.get('title', 'N/A')
            link = item.get('href', 'N/A')
            snippet = item.get('body', 'N/A')
            formatted.append(f"标题：{title}\n链接：{link}\n摘要：{snippet}")

        return "\n\n".join(formatted)

    except Exception as e:
        return f"Error: {str(e)}"
