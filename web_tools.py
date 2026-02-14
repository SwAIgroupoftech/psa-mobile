"""
web_tools.py - Bulletproof DuckDuckGo HTML Scraping
Works reliably in both dev and PyInstaller packaged apps
No external search libraries needed - just requests + BeautifulSoup
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict
import urllib.parse
import re
import time


# ---------------------------------------------------------------------------
#   WEB SEARCH - DuckDuckGo HTML (Primary Method)
# ---------------------------------------------------------------------------
def search_web(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """
    Search the web using DuckDuckGo HTML version.
    Most reliable method - works in packaged apps.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (default 5)
    
    Returns:
        List of dicts with keys: 'title', 'url', 'snippet'
    """
    print(f"🔍 Searching DuckDuckGo for: '{query}'")
    
    # Try Method 1: DuckDuckGo HTML
    results = _search_ddg_html(query, max_results)
    if results:
        return results
    
    print("⚠️ DuckDuckGo HTML failed, trying Lite version...")
    
    # Try Method 2: DuckDuckGo Lite (fallback)
    results = _search_ddg_lite(query, max_results)
    if results:
        return results
    
    print("⚠️ DuckDuckGo Lite failed, trying API...")
    
    # Try Method 3: DuckDuckGo Instant Answer API (fallback)
    results = _search_ddg_api(query, max_results)
    if results:
        return results
    
    print("❌ All search methods failed")
    
    # Return error message
    return [{
        'title': '⚠️ Web Search Unavailable',
        'url': '',
        'snippet': f'Unable to search for "{query}". Please check your internet connection and try again.'
    }]


# ---------------------------------------------------------------------------
#   METHOD 1: DuckDuckGo HTML (Most Reliable)
# ---------------------------------------------------------------------------
def _search_ddg_html(query: str, max_results: int) -> List[Dict[str, str]]:
    """
    Search using DuckDuckGo HTML version WITH DEBUG LOGGING.
    """
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # DEBUG: Save HTML to file
        
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # DEBUG: Try different selectors
        result_divs = soup.find_all('div', class_='result')
        
        
        # Try alternative selectors
        if not result_divs:
            result_divs = soup.find_all('div', class_='results')
           
        
        if not result_divs:
            all_divs = soup.find_all('div')
            
            # Print classes of first 10 divs
            for i, div in enumerate(all_divs[:10]):
                classes = div.get('class', [])
                print(f"    Div {i}: classes={classes}")
        
        results = []
        
        for div in result_divs[:max_results]:
            try:
                title_tag = div.find('a', class_='result__a')
                if not title_tag:
                    
                    continue
                
                title = title_tag.get_text(strip=True)
                
                url_tag = div.find('a', class_='result__url')
                result_url = url_tag.get('href', '') if url_tag else ''
                
                # Unwrap DuckDuckGo URL
                if 'duckduckgo.com/l/' in result_url:
                    try:
                        parsed = urllib.parse.urlparse(result_url)
                        params = urllib.parse.parse_qs(parsed.query)
                        if 'uddg' in params:
                            result_url = urllib.parse.unquote(params['uddg'][0])
                    except:
                        pass
                
                if result_url.startswith('//'):
                    result_url = 'https:' + result_url
                
                snippet_tag = div.find('a', class_='result__snippet')
                snippet = snippet_tag.get_text(strip=True) if snippet_tag else 'No description'
                
                if title and result_url and result_url.startswith('http'):
                    results.append({
                        'title': title,
                        'url': result_url,
                        'snippet': snippet
                    })
                    print(f"    ✓ Added: {title}")
                    
            except Exception as e:
                print(f"  ⚠️ Error parsing result: {e}")
                continue
        
        if results:
            print(f"  ✅ DuckDuckGo HTML: Found {len(results)} results")
        else:
            print(f"  ⚠️ DuckDuckGo HTML: No results found")
        
        return results
        
    except Exception as e:
        print(f"  ❌ DuckDuckGo HTML error: {e}")
        import traceback
        traceback.print_exc()
        return []

# ---------------------------------------------------------------------------
#   METHOD 2: DuckDuckGo Lite (Fallback)
# ---------------------------------------------------------------------------
def _search_ddg_lite(query: str, max_results: int) -> List[Dict[str, str]]:
    """
    Search using DuckDuckGo Lite version.
    Even simpler HTML structure.
    """
    try:
        # Encode query
        encoded_query = urllib.parse.quote(query)
        url = f"https://lite.duckduckgo.com/lite/?q={encoded_query}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        results = []
        
        # Find all result rows (Lite uses table layout)
        result_tables = soup.find_all('table', class_='result-table')
        
        for table in result_tables[:max_results]:
            try:
                # Find link
                link = table.find('a', class_='result-link')
                if not link:
                    continue
                
                title = link.get_text(strip=True)
                result_url = link.get('href', '')
                
                # Find snippet
                snippet_td = table.find('td', class_='result-snippet')
                snippet = snippet_td.get_text(strip=True) if snippet_td else 'No description'
                
                if title and result_url:
                    results.append({
                        'title': title,
                        'url': result_url,
                        'snippet': snippet
                    })
                    
            except Exception as e:
                print(f"  ⚠️ Error parsing Lite result: {e}")
                continue
        
        if results:
            print(f"  ✅ DuckDuckGo Lite: Found {len(results)} results")
        else:
            print(f"  ⚠️ DuckDuckGo Lite: No results found")
        
        return results
        
    except Exception as e:
        print(f"  ❌ DuckDuckGo Lite error: {e}")
        return []


# ---------------------------------------------------------------------------
#   METHOD 3: DuckDuckGo Instant Answer API (Fallback)
# ---------------------------------------------------------------------------
def _search_ddg_api(query: str, max_results: int) -> List[Dict[str, str]]:
    """
    Use DuckDuckGo Instant Answer API.
    Good for factual queries, definitions, etc.
    """
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded_query}&format=json"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        
        # Extract related topics
        for topic in data.get('RelatedTopics', [])[:max_results]:
            if isinstance(topic, dict) and 'Text' in topic:
                # Get first 100 chars for title
                text = topic.get('Text', '')
                title = text[:100] + '...' if len(text) > 100 else text
                
                results.append({
                    'title': title,
                    'url': topic.get('FirstURL', ''),
                    'snippet': text
                })
        
        # If no related topics, use abstract
        if not results and data.get('Abstract'):
            results.append({
                'title': data.get('Heading', query.title()),
                'url': data.get('AbstractURL', ''),
                'snippet': data.get('Abstract', '')
            })
        
        if results:
            print(f"  ✅ DuckDuckGo API: Found {len(results)} results")
        else:
            print(f"  ⚠️ DuckDuckGo API: No results found")
        
        return results
        
    except Exception as e:
        print(f"  ❌ DuckDuckGo API error: {e}")
        return []


# ---------------------------------------------------------------------------
#   PAGE FETCHING - Extract clean text from URLs
# ---------------------------------------------------------------------------
def fetch_page_content(url: str, max_length: int = 3000) -> str:
    """
    Fetch and extract clean text content from a URL.
    
    Args:
        url: URL to fetch
        max_length: Maximum characters to return (default 3000)
    
    Returns:
        Clean text content from the page
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for script in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            script.decompose()
        
        # Get text
        text = soup.get_text(separator=' ', strip=True)
        
        # Clean whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        # Truncate if needed
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        return text
        
    except requests.exceptions.Timeout:
        return f"Error: Timeout fetching {url}"
    except requests.exceptions.RequestException as e:
        return f"Error fetching page: {str(e)}"
    except Exception as e:
        return f"Error parsing page: {str(e)}"


# ---------------------------------------------------------------------------
#   COMBINED SEARCH + FETCH
# ---------------------------------------------------------------------------
def search_and_fetch(query: str, fetch_top: int = 2) -> Dict[str, any]:
    """
    Search web and fetch content from top results.
    
    Args:
        query: Search query
        fetch_top: Number of top results to fetch content from (default 2)
    
    Returns:
        Dict with 'results' (search results) and 'fetched' (fetched content)
    """
    # Search first
    search_results = search_web(query, max_results=5)
    
    # Fetch content from top results
    fetched_content = []
    for result in search_results[:fetch_top]:
        url = result.get('url', '')
        if url and url.startswith('http'):
            print(f"  📄 Fetching content from: {url}")
            content = fetch_page_content(url)
            fetched_content.append({
                'url': url,
                'title': result.get('title', ''),
                'content': content
            })
    
    return {
        'results': search_results,
        'fetched': fetched_content
    }


# ---------------------------------------------------------------------------
#   FORMAT RESULTS FOR LLM
# ---------------------------------------------------------------------------
def format_search_results_for_llm(results: List[Dict[str, str]]) -> str:
    """Format search results into a clean string for LLM context."""
    if not results:
        return "No search results found."
    
    formatted = "Web Search Results:\n\n"
    
    for i, result in enumerate(results, 1):
        formatted += f"{i}. {result['title']}\n"
        formatted += f"   URL: {result['url']}\n"
        formatted += f"   {result['snippet']}\n\n"
    
    return formatted.strip()


def format_fetched_content_for_llm(fetched: List[Dict[str, str]]) -> str:
    """Format fetched page content for LLM context."""
    if not fetched:
        return ""
    
    formatted = "\n\nFetched Page Content:\n\n"
    
    for item in fetched:
        formatted += f"From: {item['title']}\n"
        formatted += f"URL: {item['url']}\n"
        formatted += f"Content: {item['content']}\n\n"
        formatted += "-" * 80 + "\n\n"
    
    return formatted.strip()


# ---------------------------------------------------------------------------
#   INTELLIGENT WEB SEARCH DETECTION
# ---------------------------------------------------------------------------
def should_search_web(user_input: str) -> bool:
    """
    Intelligently detect if user input requires web search.
    
    Args:
        user_input: User's message
    
    Returns:
        True if web search is needed, False otherwise
    """
    user_lower = user_input.lower()
    
    # Explicit search triggers
    explicit_triggers = [
        'search for', 'look up', 'find information about',
        'google', 'search the web', 'search about',
        'can you search', 'please search', 'look online',
        'check online', 'find me', 'research'
    ]
    
    if any(trigger in user_lower for trigger in explicit_triggers):
        return True
    
    # Temporal indicators (current information)
    temporal_patterns = [
        r'\b(today|tonight|this (week|month|year|morning|evening))\b',
        r'\b(currently|right now|at the moment|as of now)\b',
        r'\b(recent|latest|newest|updated|current)\b',
        r'\b(yesterday|last (night|week|month|year))\b',
    ]
    
    for pattern in temporal_patterns:
        if re.search(pattern, user_lower):
            return True
    
    # Real-time data keywords
    realtime_keywords = [
        'weather', 'forecast', 'temperature',
        'stock price', 'stock market', 'trading at',
        'score', 'match result', 'game score',
        'exchange rate', 'currency', 'bitcoin', 'crypto',
        'news', 'breaking', 'headline',
        'price of', 'cost of', 'how much is',
    ]
    
    if any(keyword in user_lower for keyword in realtime_keywords):
        return True
    
    # Question words about current state
    question_patterns = [
        r'\bwhat is (the )?(current|latest|today\'?s)\b',
        r'\bwho is (the )?(current|new|latest)\b',
        r'\bwhen (is|was|did)\b',
        r'\bwhere (is|can i|are)\b',
    ]
    
    for pattern in question_patterns:
        if re.search(pattern, user_lower):
            return True
    
    return False


def extract_search_query(user_input: str) -> str:
    """
    Extract the actual search query from user input.
    
    Args:
        user_input: User's message
    
    Returns:
        Cleaned search query
    """
    query = user_input.strip()
    
    # Remove common prefixes
    prefixes_to_remove = [
        'search for ', 'look up ', 'find information about ',
        'search the web for ', 'google ', 'find out about ',
        'research ', 'tell me about ', 'search about ',
        'can you search for ', 'please search for ',
    ]
    
    query_lower = query.lower()
    for prefix in prefixes_to_remove:
        if query_lower.startswith(prefix):
            query = query[len(prefix):].strip()
            break
    
    # Remove question words if still present
    if query.lower().startswith(('what is ', 'what\'s ', 'who is ', 'where is ')):
        words = query.split()
        if len(words) > 2:
            query = ' '.join(words[2:])
    
    return query.strip()


# ---------------------------------------------------------------------------
#   TEST BLOCK
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print("=" * 80)
    print("WEB SEARCH TEST - DuckDuckGo HTML Scraping")
    print("=" * 80)
    print()
    
    # Test 1: Simple search
    print("📌 TEST 1: Simple Query")
    print("-" * 80)
    test_query_1 = "Python programming"
    results_1 = search_web(test_query_1, max_results=3)
    
    print(f"\nResults for '{test_query_1}':")
    for i, result in enumerate(results_1, 1):
        print(f"\n{i}. {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   Snippet: {result['snippet'][:100]}...")
    
    print("\n" + "=" * 80)
    time.sleep(2)  # Be nice to DuckDuckGo
    
    # Test 2: Current event
    print("\n📌 TEST 2: Current Event Query")
    print("-" * 80)
    test_query_2 = "latest AI news"
    results_2 = search_web(test_query_2, max_results=3)
    
    print(f"\nResults for '{test_query_2}':")
    for i, result in enumerate(results_2, 1):
        print(f"\n{i}. {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   Snippet: {result['snippet'][:100]}...")
    
    print("\n" + "=" * 80)
    time.sleep(2)
    
    # Test 3: Search detection
    print("\n📌 TEST 3: Search Detection")
    print("-" * 80)
    test_inputs = [
        "What's the weather today?",
        "Explain recursion in programming",
        "Who is the current president of USA?",
        "How to make a for loop in Python?",
        "Latest news on AI",
    ]
    
    for test_input in test_inputs:
        should_search = should_search_web(test_input)
        status = "🔍 SEARCH" if should_search else "💭 NO SEARCH"
        print(f"{status}: {test_input}")
    
    print("\n" + "=" * 80)
    time.sleep(2)
    
    # Test 4: Search and fetch
    print("\n📌 TEST 4: Search + Fetch Content")
    print("-" * 80)
    test_query_4 = "Virat Kohli centuries"
    print(f"Query: '{test_query_4}'")
    print("Searching and fetching top 2 results...\n")
    
    combined_results = search_and_fetch(test_query_4, fetch_top=2)
    
    print("\n--- Search Results ---")
    formatted_results = format_search_results_for_llm(combined_results['results'])
    print(formatted_results)
    
    print("\n--- Fetched Content (First 500 chars) ---")
    for item in combined_results['fetched']:
        print(f"\nFrom: {item['title']}")
        print(f"Content preview: {item['content'][:500]}...")
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS COMPLETE!")
    print("=" * 80)