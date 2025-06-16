"""
Smoke Tests - 部署後立即執行的快速測試
確保服務基本運作正常
"""

import sys
import time
import requests
import argparse
from typing import Dict, Tuple

class SmokeTestRunner:
    def __init__(self, service_url: str):
        self.service_url = service_url.rstrip('/')
        self.results = []
        
    def test_health_endpoint(self) -> Tuple[bool, str]:
        """測試健康檢查端點"""
        try:
            response = requests.get(f"{self.service_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    return True, "Health check passed"
                else:
                    return False, f"Service unhealthy: {data}"
            else:
                return False, f"Health check failed: HTTP {response.status_code}"
        except Exception as e:
            return False, f"Health check error: {str(e)}"
    
    def test_neo4j_connection(self) -> Tuple[bool, str]:
        """測試 Neo4j 連接"""
        try:
            response = requests.get(f"{self.service_url}/neo4j/status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "connected":
                    return True, "Neo4j connected"
                else:
                    return False, f"Neo4j not connected: {data.get('message')}"
            else:
                return False, f"Neo4j status check failed: HTTP {response.status_code}"
        except Exception as e:
            return False, f"Neo4j check error: {str(e)}"
    
    def test_webhook_endpoint(self) -> Tuple[bool, str]:
        """測試 Webhook 端點（不實際處理，只確認端點存在）"""
        try:
            # 發送一個格式錯誤的請求，預期返回 400
            response = requests.post(
                f"{self.service_url}/webhook",
                json={},
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            # 沒有簽名應該返回 400
            if response.status_code == 400:
                return True, "Webhook endpoint exists and validates signature"
            else:
                return False, f"Unexpected webhook response: HTTP {response.status_code}"
        except Exception as e:
            return False, f"Webhook test error: {str(e)}"
    
    def test_root_endpoint(self) -> Tuple[bool, str]:
        """測試根路徑"""
        try:
            response = requests.get(self.service_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("service") == "frequency-bot":
                    return True, "Root endpoint working"
                else:
                    return False, "Root endpoint returns unexpected data"
            else:
                return False, f"Root endpoint failed: HTTP {response.status_code}"
        except Exception as e:
            return False, f"Root endpoint error: {str(e)}"
    
    def run_all_tests(self) -> bool:
        """執行所有 Smoke Tests"""
        print(f"🔥 Running Smoke Tests for: {self.service_url}")
        print("=" * 60)
        
        tests = [
            ("Root Endpoint", self.test_root_endpoint),
            ("Health Check", self.test_health_endpoint),
            ("Neo4j Connection", self.test_neo4j_connection),
            ("Webhook Endpoint", self.test_webhook_endpoint)
        ]
        
        all_passed = True
        
        for test_name, test_func in tests:
            print(f"\n📍 Testing: {test_name}")
            passed, message = test_func()
            
            if passed:
                print(f"   ✅ PASSED: {message}")
            else:
                print(f"   ❌ FAILED: {message}")
                all_passed = False
            
            self.results.append({
                "test": test_name,
                "passed": passed,
                "message": message
            })
            
            # 避免過快的請求
            time.sleep(0.5)
        
        # 總結
        print("\n" + "=" * 60)
        passed_count = sum(1 for r in self.results if r["passed"])
        total_count = len(self.results)
        
        print(f"📊 Results: {passed_count}/{total_count} tests passed")
        
        if not all_passed:
            print("\n❌ Some tests failed:")
            for result in self.results:
                if not result["passed"]:
                    print(f"   - {result['test']}: {result['message']}")
        else:
            print("\n✅ All smoke tests passed!")
        
        return all_passed


def main():
    parser = argparse.ArgumentParser(description='Run smoke tests on deployed service')
    parser.add_argument('--url', required=True, help='Service URL to test')
    parser.add_argument('--timeout', type=int, default=30, help='Overall timeout in seconds')
    args = parser.parse_args()
    
    # 等待服務完全啟動
    print(f"⏳ Waiting 5 seconds for service to stabilize...")
    time.sleep(5)
    
    # 執行測試
    runner = SmokeTestRunner(args.url)
    
    try:
        passed = runner.run_all_tests()
        sys.exit(0 if passed else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()