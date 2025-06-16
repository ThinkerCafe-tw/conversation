"""
測試生產環境的笑話功能
"""

import os
import logging
from dotenv import load_dotenv
from google.cloud import firestore
from community_features import CommunityFeatures

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_production_joke():
    """測試生產環境的笑話功能"""
    try:
        # 初始化 Firestore
        db = firestore.Client()
        logger.info("Firestore 連接成功")
        
        # 初始化社群功能 (不需要 Redis)
        community = CommunityFeatures(
            redis_client=None,
            knowledge_graph=None,
            db=db
        )
        logger.info("CommunityFeatures 初始化成功")
        
        # 測試獲取笑話
        print("\n=== 測試獲取笑話 ===")
        result = community.get_random_joke(user_id_for_cache="test_user")
        
        print(f"成功: {result['success']}")
        print(f"訊息: {result['message']}")
        
        if result['success']:
            joke = result.get('joke', {})
            print(f"笑話ID: {joke.get('id')}")
            print(f"類別: {joke.get('category')}")
        
        # 列出資料庫中的笑話統計
        print("\n=== 資料庫統計 ===")
        jokes_count = len(list(db.collection('jokes').limit(1000).stream()))
        print(f"總笑話數: {jokes_count}")
        
        # 檢查前5則笑話的結構
        print("\n=== 前5則笑話結構 ===")
        for i, doc in enumerate(db.collection('jokes').limit(5).stream()):
            data = doc.to_dict()
            print(f"\n笑話 {i+1}:")
            print(f"  ID: {doc.id}")
            print(f"  欄位: {list(data.keys())}")
            print(f"  狀態: {data.get('status', 'N/A')}")
            print(f"  類別: {data.get('category', 'N/A')}")
            
    except Exception as e:
        logger.error(f"測試失敗: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_production_joke()