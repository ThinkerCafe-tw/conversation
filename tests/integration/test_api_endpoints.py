"""
整合測試 - API 端點測試
測試部署後的服務端點是否正常運作
"""

import pytest
import requests
import time
import os
from typing import Dict, Optional


@pytest.fixture
def base_url():
    """獲取測試的基礎 URL"""
    # 從命令行參數或環境變數獲取
    url = pytest.config.getoption("--base-url", default=None)
    if not url:
        url = os.getenv('TEST_BASE_URL', 'http://localhost:8080')
    return url.rstrip('/')


@pytest.fixture
def headers():
    """默認請求頭"""
    return {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }


class TestHealthEndpoints:
    """健康檢查端點測試"""
    
    def test_root_endpoint(self, base_url: str):
        """測試根端點"""
        response = requests.get(f"{base_url}/")
        assert response.status_code == 200
        data = response.json()
        assert data['service'] == 'frequency-bot'
        assert data['status'] == 'running'
        
    def test_health_endpoint(self, base_url: str):
        """測試健康檢查端點"""
        response = requests.get(f"{base_url}/health")
        assert response.status_code in [200, 503]  # 503 表示部分服務降級
        data = response.json()
        assert 'status' in data
        assert 'connections' in data
        assert 'env_vars' in data
        
        # 檢查必要的環境變數
        assert data['env_vars']['LINE_TOKEN'] is True
        assert data['env_vars']['LINE_SECRET'] is True
        assert data['env_vars']['GEMINI_KEY'] is True
        
    def test_neo4j_status_endpoint(self, base_url: str):
        """測試 Neo4j 狀態端點"""
        response = requests.get(f"{base_url}/neo4j/status")
        assert response.status_code == 200
        data = response.json()
        assert 'status' in data
        assert data['status'] in ['connected', 'disconnected', 'not_configured']


class TestRateLimiting:
    """速率限制測試"""
    
    def test_rate_limit_headers(self, base_url: str):
        """測試速率限制響應頭"""
        response = requests.get(f"{base_url}/")
        assert 'X-RateLimit-Limit' in response.headers
        assert 'X-RateLimit-Remaining' in response.headers
        assert 'X-RateLimit-Reset' in response.headers
        
    def test_rate_limit_exceeded(self, base_url: str):
        """測試超過速率限制"""
        # 快速發送多個請求
        responses = []
        for _ in range(35):  # API_QUERY 限制是 30/分鐘
            response = requests.get(f"{base_url}/")
            responses.append(response)
            if response.status_code == 429:
                break
                
        # 應該有至少一個 429 響應
        status_codes = [r.status_code for r in responses]
        assert 429 in status_codes
        
        # 檢查 429 響應的內容
        rate_limited_response = next(r for r in responses if r.status_code == 429)
        assert 'Retry-After' in rate_limited_response.headers
        data = rate_limited_response.json()
        assert 'error' in data
        assert 'retry_after' in data


class TestWebhookEndpoint:
    """Webhook 端點測試"""
    
    def test_webhook_requires_signature(self, base_url: str, headers: Dict):
        """測試 webhook 需要簽名"""
        response = requests.post(
            f"{base_url}/webhook",
            json={"events": []},
            headers=headers
        )
        assert response.status_code == 400
        
    def test_webhook_invalid_signature(self, base_url: str, headers: Dict):
        """測試無效的簽名"""
        headers['X-Line-Signature'] = 'invalid_signature'
        response = requests.post(
            f"{base_url}/webhook",
            json={"events": []},
            headers=headers
        )
        assert response.status_code == 400


class TestSchedulerEndpoints:
    """排程器端點測試"""
    
    @pytest.mark.parametrize("endpoint", [
        "/scheduler/test",
        "/scheduler/broadcast",
        "/scheduler/cleanup"
    ])
    def test_scheduler_endpoints_require_post(self, base_url: str, endpoint: str):
        """測試排程器端點需要 POST 方法"""
        response = requests.get(f"{base_url}{endpoint}")
        assert response.status_code == 405  # Method Not Allowed
        
    def test_scheduler_test_endpoint(self, base_url: str, headers: Dict):
        """測試排程器測試端點"""
        # 添加 Cloud Scheduler 頭
        headers['X-Cloudscheduler'] = 'true'
        response = requests.post(
            f"{base_url}/scheduler/test",
            headers=headers
        )
        assert response.status_code in [200, 429]  # 可能受速率限制


class TestErrorHandling:
    """錯誤處理測試"""
    
    def test_404_error(self, base_url: str):
        """測試 404 錯誤"""
        response = requests.get(f"{base_url}/non-existent-endpoint")
        assert response.status_code == 404
        
    def test_sentry_integration(self, base_url: str):
        """測試 Sentry 整合（如果有測試端點）"""
        response = requests.get(f"{base_url}/test-sentry")
        # 如果端點存在，應該返回錯誤
        if response.status_code != 404:
            assert response.status_code == 500
            data = response.json()
            assert 'error' in data


class TestPerformance:
    """性能測試"""
    
    def test_response_time(self, base_url: str):
        """測試響應時間"""
        start_time = time.time()
        response = requests.get(f"{base_url}/health")
        end_time = time.time()
        
        response_time = end_time - start_time
        assert response_time < 2.0  # 響應時間應該小於 2 秒
        
    def test_concurrent_requests(self, base_url: str):
        """測試並發請求"""
        import concurrent.futures
        
        def make_request():
            return requests.get(f"{base_url}/health")
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            responses = [future.result() for future in concurrent.futures.as_completed(futures)]
            
        # 所有請求應該成功（或因速率限制而失敗）
        for response in responses:
            assert response.status_code in [200, 429, 503]


# Pytest 配置
def pytest_addoption(parser):
    """添加命令行選項"""
    parser.addoption(
        "--base-url",
        action="store",
        default=None,
        help="Base URL for the API tests"
    )


if __name__ == "__main__":
    # 本地測試運行
    pytest.main([__file__, "-v"])