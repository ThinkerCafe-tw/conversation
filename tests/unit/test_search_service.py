import unittest
from unittest.mock import patch, MagicMock
import os
import requests # For requests.exceptions.RequestException
from search_service import CustomSearchService
# Assuming search_service.py is in the root directory or accessible via PYTHONPATH

class TestCustomSearchService(unittest.TestCase):

    @patch.dict(os.environ, {"CUSTOM_SEARCH_API_KEY": "test_api_key"})
    def test_init_success(self):
        mock_redis_client = MagicMock()
        service = CustomSearchService(redis_client=mock_redis_client)
        self.assertEqual(service.api_key, "test_api_key")
        self.assertEqual(service.cx_id, "f4bbd246ef2324d78")
        self.assertEqual(service.base_url, "https://www.googleapis.com/customsearch/v1")
        self.assertEqual(service.redis, mock_redis_client)
        self.assertEqual(service.daily_limit, 100)
        self.assertEqual(service.redis_usage_key_prefix, "custom_search_api:usage:")

    @patch.dict(os.environ, {}, clear=True) # Ensure CUSTOM_SEARCH_API_KEY is not set
    def test_init_no_api_key(self):
        with patch.object(CustomSearchService, 'logger') as mock_logger:
            service = CustomSearchService(redis_client=None)
            self.assertIsNone(service.api_key)
            mock_logger.warning.assert_called_with("CUSTOM_SEARCH_API_KEY environment variable not found. Search functionality will be disabled.")

    def test_init_no_redis_client(self):
        with patch.object(CustomSearchService, 'logger') as mock_logger:
            service = CustomSearchService(redis_client=None)
            self.assertIsNone(service.redis)
            mock_logger.warning.assert_called_with("Redis client not provided to CustomSearchService. Rate limiting will be disabled (fail open).")

    # --- Test _check_and_increment_usage ---
    @patch.dict(os.environ, {"CUSTOM_SEARCH_API_KEY": "test_api_key"})
    def test_check_usage_redis_unavailable(self):
        service = CustomSearchService(redis_client=None) # No Redis
        with patch.object(service, 'logger') as mock_logger:
            self.assertTrue(service._check_and_increment_usage())
            mock_logger.warning.assert_called_with("Rate limiting disabled: Redis client not available.")

    @patch.dict(os.environ, {"CUSTOM_SEARCH_API_KEY": "test_api_key"})
    def test_check_usage_first_use_of_day(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None # First use
        mock_redis.incr.return_value = 1   # incr returns new value
        service = CustomSearchService(redis_client=mock_redis)

        self.assertTrue(service._check_and_increment_usage())

        mock_redis.get.assert_called_once()
        mock_redis.incr.assert_called_once()
        mock_redis.expire.assert_called_once_with(mock_redis.incr.call_args[0][0], 86400) # Check key and timeout

    @patch.dict(os.environ, {"CUSTOM_SEARCH_API_KEY": "test_api_key"})
    def test_check_usage_under_limit(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "50"
        mock_redis.incr.return_value = 51
        service = CustomSearchService(redis_client=mock_redis)

        self.assertTrue(service._check_and_increment_usage())
        mock_redis.expire.assert_not_called() # Expire only on first increment

    @patch.dict(os.environ, {"CUSTOM_SEARCH_API_KEY": "test_api_key"})
    def test_check_usage_at_limit(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "100" # At daily_limit
        service = CustomSearchService(redis_client=mock_redis)

        with patch.object(service, 'logger') as mock_logger:
            self.assertFalse(service._check_and_increment_usage())
            mock_logger.warning.assert_called()
        mock_redis.incr.assert_not_called()

    @patch.dict(os.environ, {"CUSTOM_SEARCH_API_KEY": "test_api_key"})
    def test_check_usage_redis_exception(self):
        mock_redis = MagicMock()
        mock_redis.get.side_effect = Exception("Redis down")
        service = CustomSearchService(redis_client=mock_redis)
        with patch.object(service, 'logger') as mock_logger:
            self.assertTrue(service._check_and_increment_usage()) # Should fail open
            mock_logger.error.assert_called_with("Redis error during API usage check: Redis down. Allowing request (fail open).")

    # --- Test perform_search ---
    @patch.dict(os.environ, {"CUSTOM_SEARCH_API_KEY": "test_api_key"})
    @patch('search_service.requests.get')
    def test_perform_search_success_with_items(self, mock_requests_get):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "1" # Under limit
        mock_redis.incr.return_value = 2

        service = CustomSearchService(redis_client=mock_redis)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {"title": "Title 1", "link": "link1.com", "snippet": "Snippet 1"},
                {"title": "Title 2", "link": "link2.com", "snippet": "Snippet 2"},
            ],
            "searchInformation": {"totalResults": "12345"}
        }
        mock_requests_get.return_value = mock_response

        result = service.perform_search("test query", num_results=2)
        self.assertTrue(result['success'])
        self.assertEqual(result['query'], "test query")
        self.assertEqual(len(result['results']), 2)
        self.assertEqual(result['results'][0]['title'], "Title 1")
        self.assertEqual(result['total_results_available'], "12345")
        mock_requests_get.assert_called_once()
        call_args = mock_requests_get.call_args[1]['params']
        self.assertEqual(call_args['q'], "test query")
        self.assertEqual(call_args['num'], 2)

    @patch.dict(os.environ, {"CUSTOM_SEARCH_API_KEY": "test_api_key"})
    @patch('search_service.requests.get')
    def test_perform_search_success_no_items(self, mock_requests_get):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "10"
        mock_redis.incr.return_value = 11
        service = CustomSearchService(redis_client=mock_redis)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"searchInformation": {"totalResults": "0"}} # No items
        mock_requests_get.return_value = mock_response

        result = service.perform_search("rare query")
        self.assertTrue(result['success'])
        self.assertEqual(len(result['results']), 0)
        self.assertEqual(result['total_results_available'], "0")

    @patch.dict(os.environ, {"CUSTOM_SEARCH_API_KEY": "test_api_key"})
    def test_perform_search_rate_limit_reached(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = "100" # Limit reached
        service = CustomSearchService(redis_client=mock_redis)

        result = service.perform_search("any query")
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'API daily limit reached.')
        self.assertEqual(result['message'], '抱歉，今日的網路搜尋次數已達上限，請明日再試。')

    @patch.dict(os.environ, {"CUSTOM_SEARCH_API_KEY": "test_api_key"})
    @patch('search_service.requests.get')
    def test_perform_search_http_error(self, mock_requests_get):
        service = CustomSearchService(redis_client=MagicMock()) # Assume rate limit check passes
        service.redis.get.return_value = "5"
        service.redis.incr.return_value = 6

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("403 Client Error")
        mock_response.text = "Forbidden"
        mock_requests_get.return_value = mock_response

        result = service.perform_search("test http error")
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'API request failed (HTTP error)')
        self.assertIn("403 Client Error", result['details'])

    @patch.dict(os.environ, {"CUSTOM_SEARCH_API_KEY": "test_api_key"})
    @patch('search_service.requests.get')
    def test_perform_search_request_exception(self, mock_requests_get):
        service = CustomSearchService(redis_client=MagicMock())
        service.redis.get.return_value = "5"
        service.redis.incr.return_value = 6

        mock_requests_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        result = service.perform_search("test request exception")
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'API request failed (Request exception)')
        self.assertIn("Connection timed out", result['details'])

    @patch.dict(os.environ, {"CUSTOM_SEARCH_API_KEY": "test_api_key"})
    @patch('search_service.requests.get')
    def test_perform_search_api_error_in_json(self, mock_requests_get):
        service = CustomSearchService(redis_client=MagicMock())
        service.redis.get.return_value = "5"
        service.redis.incr.return_value = 6

        mock_response = MagicMock()
        mock_response.status_code = 200 # API might return 200 but still have an error in body
        mock_response.json.return_value = {"error": {"message": "Daily Limit Exceeded"}}
        mock_requests_get.return_value = mock_response

        result = service.perform_search("test api error in json")
        self.assertFalse(result['success'])
        self.assertEqual(result['error'], 'Custom Search API error')
        self.assertEqual(result['details'], "Daily Limit Exceeded")

    def test_perform_search_no_api_key(self):
        with patch.dict(os.environ, {}, clear=True): # No API key
            service = CustomSearchService(redis_client=None)
            result = service.perform_search("query")
            self.assertFalse(result['success'])
            self.assertEqual(result['error'], 'API key or CX ID is not configured.')

if __name__ == '__main__':
    unittest.main()
