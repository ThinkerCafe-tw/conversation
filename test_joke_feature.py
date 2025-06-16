"""
測試笑話功能
"""

import os
import logging
from google.cloud import firestore
from community_features import CommunityFeatures
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_joke_feature():
    """測試笑話功能"""
    # 初始化 Firestore
    db = firestore.Client()
    
    # 初始化社群功能
    community = CommunityFeatures(
        redis_client=None,  # 我們只測試笑話功能，不需要 Redis
        knowledge_graph=None,
        db=db
    )
    
    print("=== 測試笑話功能 ===\n")
    
    # 測試 1: 檢查資料庫中的笑話數量
    print("1. 檢查資料庫中的笑話數量")
    all_jokes = list(db.collection('jokes').stream())
    print(f"   總笑話數: {len(all_jokes)}")
    
    approved_jokes = list(db.collection('jokes').where('status', '==', 'approved').stream())
    print(f"   已批准笑話數: {len(approved_jokes)}")
    
    # 顯示一些笑話的結構
    if approved_jokes:
        sample = approved_jokes[0].to_dict()
        print(f"   笑話範例結構: {list(sample.keys())}")
    
    print("\n2. 測試獲取隨機笑話")
    # 測試獲取笑話多次，看是否真的隨機
    seen_jokes = set()
    categories_seen = set()
    
    for i in range(10):
        print(f"\n   第 {i+1} 次測試:")
        result = community.get_random_joke(user_id_for_cache="test_user")
        
        if result['success']:
            joke = result.get('joke', {})
            joke_id = joke.get('id', 'unknown')
            joke_text = joke.get('text', '')[:50] + "..."
            
            print(f"   ✅ 成功獲取笑話")
            print(f"   ID: {joke_id}")
            print(f"   內容: {joke_text}")
            
            # 檢查分類
            if 'category' in result.get('joke', {}):
                category = result['joke']['category']
                categories_seen.add(category)
                print(f"   類別: {category}")
            
            seen_jokes.add(joke_id)
        else:
            print(f"   ❌ 失敗: {result['message']}")
    
    print(f"\n3. 隨機性測試結果")
    print(f"   10次測試中看到了 {len(seen_jokes)} 個不同的笑話")
    print(f"   涵蓋了 {len(categories_seen)} 個類別: {', '.join(categories_seen)}")
    
    # 測試 3: 測試添加新笑話
    print("\n4. 測試添加新笑話")
    test_joke = "測試笑話：為什麼測試工程師不喜歡戶外活動？因為外面沒有 console.log！"
    add_result = community.add_joke("test_user", test_joke)
    
    if add_result['success']:
        print(f"   ✅ 成功添加笑話")
    else:
        print(f"   ❌ 添加失敗: {add_result['message']}")
    
    # 測試 4: 再次檢查數量
    print("\n5. 再次檢查笑話數量")
    new_count = len(list(db.collection('jokes').stream()))
    print(f"   現在的笑話總數: {new_count}")
    
    print("\n=== 測試完成 ===")


if __name__ == "__main__":
    try:
        test_joke_feature()
    except Exception as e:
        logger.error(f"測試失敗: {e}")
        import traceback
        traceback.print_exc()