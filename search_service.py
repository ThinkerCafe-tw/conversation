import os
import requests
import json
import logging
from datetime import datetime # Added for rate limiting

logger = logging.getLogger(__name__)

class CustomSearchService:
    def __init__(self, redis_client=None): # Added redis_client
        """
        Initializes the Custom Search Service.
        API Key is read from the CUSTOM_SEARCH_API_KEY environment variable.
        CX ID is hardcoded for a specific search engine.
        Redis client is used for rate limiting.
        """
        self.api_key = os.getenv('CUSTOM_SEARCH_API_KEY')
        self.cx_id = "f4bbd246ef2324d78"  # Predefined CX ID
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        self.redis = redis_client
        self.daily_limit = 100 # As per plan
        self.redis_usage_key_prefix = "custom_search_api:usage:"

        if not self.api_key:
            logger.warning("CUSTOM_SEARCH_API_KEY environment variable not found. Search functionality will be disabled.")
        if not self.redis:
            logger.warning("Redis client not provided to CustomSearchService. Rate limiting will be disabled (fail open).")

    def _check_and_increment_usage(self) -> bool:
        """
        Checks if the API usage is within the daily limit and increments the count.
        Returns True if the request can proceed, False otherwise.
        Fails open (returns True) if Redis is unavailable.
        """
        if not self.redis:
            logger.warning("Rate limiting disabled: Redis client not available.")
            return True # Fail open

        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            usage_key = f"{self.redis_usage_key_prefix}{today_str}"

            current_usage_str = self.redis.get(usage_key)
            current_usage = int(current_usage_str) if current_usage_str else 0

            if current_usage >= self.daily_limit:
                logger.warning(f"Custom Search API daily limit of {self.daily_limit} reached for key {usage_key}.")
                return False # Limit exceeded

            new_count = self.redis.incr(usage_key)
            if new_count == 1: # First increment for the day
                self.redis.expire(usage_key, 86400) # Set expiry for 24 hours

            logger.info(f"Custom Search API usage for {today_str}: {new_count}/{self.daily_limit}")
            return True # Request allowed

        except Exception as e:
            logger.error(f"Redis error during API usage check: {e}. Allowing request (fail open).")
            return True # Fail open if Redis operations fail

    def perform_search(self, query: str, num_results: int = 5) -> dict:
        """
        Performs a search using the Google Custom Search JSON API, with rate limiting and caching.

        Args:
            query (str): The search query.
            num_results (int): The number of search results to return (default is 5).

        Returns:
            dict: A dictionary containing the search results or an error message.
        """
        if not self.api_key or not self.cx_id:
            logger.error("Custom Search API key or CX ID is not configured.")
            return {'success': False, 'error': 'API key or CX ID is not configured.'}

        # 檢查快取
        cache_key = f"search:{query}:{num_results}"
        if self.redis:
            try:
                cached_result = self.redis.get(cache_key)
                if cached_result:
                    logger.info(f"Search cache hit for query: '{query}'")
                    result = json.loads(cached_result)
                    result['from_cache'] = True
                    return result
            except Exception as e:
                logger.warning(f"Cache retrieval failed: {e}")

        # Check rate limit before proceeding
        if not self._check_and_increment_usage():
            return {
                'success': False,
                'error': 'API daily limit reached.',
                'message': '抱歉，今日的網路搜尋次數已達上限，請明日再試。'
            }

        params = {
            'key': self.api_key,
            'cx': self.cx_id,
            'q': query,
            'num': num_results
        }

        try:
            logger.info(f"Performing custom search for query: '{query}' with {num_results} results.")
            response = requests.get(self.base_url, params=params, timeout=10) # Added timeout
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)

            response_json = response.json()

            # Check for API-level errors if raise_for_status didn't catch them
            if 'error' in response_json:
                error_details = response_json['error'].get('message', 'Unknown API error')
                logger.error(f"Custom Search API returned an error: {error_details} - Response: {response_json}")
                return {'success': False, 'error': 'Custom Search API error', 'details': error_details}

            search_items = response_json.get('items', [])
            results = []
            for item in search_items:
                results.append({
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet")
                })

            total_results_available = response_json.get('searchInformation', {}).get('totalResults', '0')
            logger.info(f"Search successful for query '{query}'. Found {len(results)} results. Total available: {total_results_available}")

            search_result = {
                "success": True,
                "query": query,
                "results": results,
                "total_results_available": total_results_available
            }

            # 快取結果 (15分鐘)
            if self.redis and results:
                try:
                    self.redis.setex(cache_key, 900, json.dumps(search_result))
                    logger.info(f"Search results cached for query: '{query}'")
                except Exception as e:
                    logger.warning(f"Failed to cache search results: {e}")

            return search_result

        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred during custom search: {http_err} - Response: {response.text}")
            return {'success': False, 'error': 'API request failed (HTTP error)', 'details': str(http_err)}
        except requests.exceptions.RequestException as req_err:
            logger.error(f"Request exception occurred during custom search: {req_err}")
            return {'success': False, 'error': 'API request failed (Request exception)', 'details': str(req_err)}
        except json.JSONDecodeError as json_err:
            logger.error(f"Failed to decode JSON response from custom search: {json_err} - Response: {response.text}")
            return {'success': False, 'error': 'API response JSON decode error', 'details': str(json_err)}
        except Exception as e:
            logger.error(f"An unexpected error occurred during custom search: {e}")
            return {'success': False, 'error': 'An unexpected error occurred', 'details': str(e)}

if __name__ == '__main__':
    # Example Usage (requires CUSTOM_SEARCH_API_KEY to be set in environment)
    # This part is for testing and will not run when imported.
    logging.basicConfig(level=logging.INFO)

    # Example Usage (requires CUSTOM_SEARCH_API_KEY and Redis connection for full test)
    print("Attempting to perform a test search...")
    if not os.getenv('CUSTOM_SEARCH_API_KEY'):
        print("Please set the CUSTOM_SEARCH_API_KEY environment variable to test.")
    else:
        # For local testing, you might need a mock Redis or a real Redis instance.
        # For this example, we'll proceed without Redis for the __main__ block,
        # which means rate limiting will be effectively off here.
        print("Note: For __main__ test, Redis client is not provided, so rate limiting is off.")
        search_service = CustomSearchService(redis_client=None)
        if search_service.api_key:
            test_query = "Python programming"
            print(f"Testing with query: '{test_query}'")
            results = search_service.perform_search(test_query, num_results=2)

            if results['success']:
                print(f"Search successful for query: {results['query']}")
                print(f"Total results available (approximate): {results['total_results_available']}")
                for i, item in enumerate(results['results']):
                    print(f"--- Result {i+1} ---")
                    print(f"  Title: {item['title']}")
                    print(f"  Link: {item['link']}")
                    print(f"  Snippet: {item['snippet']}")
            else:
                print(f"Search failed: {results['error']}")
                if 'details' in results:
                    print(f"Details: {results['details']}")
        else:
            print("Search service could not be initialized due to missing API key.")
    print("Test search finished.")
