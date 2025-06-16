"""
測試搜尋功能
"""

import os
from dotenv import load_dotenv
from search_service import CustomSearchService
import logging

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_search():
    """測試搜尋功能"""
    # 初始化搜尋服務
    search_service = CustomSearchService(redis_client=None)
    
    if not search_service.api_key:
        print("❌ CUSTOM_SEARCH_API_KEY 未設定")
        return
        
    print(f"✅ API Key 已設定: {search_service.api_key[:10]}...")
    print(f"✅ Search Engine ID: {search_service.cx_id}")
    
    # 測試搜尋
    test_queries = [
        "台灣天氣",
        "Python tutorial",
        "LINE Bot 開發"
    ]
    
    for query in test_queries:
        print(f"\n=== 搜尋: {query} ===")
        result = search_service.perform_search(query, num_results=3)
        
        if result['success']:
            print(f"找到 {len(result['results'])} 筆結果：")
            for i, item in enumerate(result['results'], 1):
                print(f"\n{i}. {item['title']}")
                print(f"   {item['snippet'][:80]}...")
                print(f"   🔗 {item['link']}")
        else:
            print(f"❌ 錯誤: {result['message']}")
            
        print("-" * 50)


if __name__ == "__main__":
    test_search()