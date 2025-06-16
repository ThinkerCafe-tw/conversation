#!/usr/bin/env python3
"""
測試接龍功能的腳本
"""

import os
import sys
import redis
from dotenv import load_dotenv
from community_features import CommunityFeatures

# 載入環境變數
if os.path.exists('.env'):
    load_dotenv()

def test_redis_connection():
    """測試 Redis 連接"""
    print("=== 測試 Redis 連接 ===")
    try:
        redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=os.getenv('REDIS_PASSWORD'),
            username=os.getenv('REDIS_USERNAME', 'default'),
            decode_responses=True,
            socket_keepalive=True,
            socket_connect_timeout=5
        )
        
        # 測試 ping
        redis_client.ping()
        print("✅ Redis 連接成功！")
        
        # 顯示連接資訊
        print(f"Host: {os.getenv('REDIS_HOST', 'localhost')}")
        print(f"Port: {os.getenv('REDIS_PORT', 6379)}")
        print(f"Username: {os.getenv('REDIS_USERNAME', 'default')}")
        print(f"Password: {'設定' if os.getenv('REDIS_PASSWORD') else '未設定'}")
        
        return redis_client
    except Exception as e:
        print(f"❌ Redis 連接失敗: {e}")
        print(f"錯誤類型: {type(e).__name__}")
        return None

def test_community_features(redis_client):
    """測試社群功能"""
    print("\n=== 測試社群功能 ===")
    
    if not redis_client:
        print("❌ 無法測試，Redis 未連接")
        return
    
    # 初始化社群功能
    community = CommunityFeatures(redis_client)
    
    # 測試 connected 屬性
    print(f"Community.connected: {community.connected}")
    
    # 測試接龍功能
    print("\n=== 測試接龍功能 ===")
    
    # 1. 開始新接龍
    result = community.start_word_chain("蘋果", "測試用戶1")
    print(f"開始接龍: {result}")
    
    # 2. 查看接龍狀態
    status = community.get_word_chain_status()
    print(f"接龍狀態: {status}")
    
    # 3. 繼續接龍
    result = community.continue_word_chain("果汁", "測試用戶2")
    print(f"繼續接龍: {result}")
    
    # 4. 錯誤測試 - 錯誤的開頭
    result = community.continue_word_chain("蘋果", "測試用戶3")
    print(f"錯誤測試: {result}")
    
    # 5. 清理測試資料
    redis_client.delete("word_chain:current")
    print("\n✅ 測試資料已清理")

def check_redis_data():
    """檢查 Redis 中的資料"""
    print("\n=== 檢查 Redis 資料 ===")
    
    redis_client = test_redis_connection()
    if not redis_client:
        return
    
    # 檢查接龍相關的 key
    print("\n接龍相關 keys:")
    keys = redis_client.keys("word_chain:*")
    for key in keys:
        value = redis_client.get(key)
        print(f"  {key}: {value}")
    
    # 檢查其他相關 keys
    print("\n其他相關 keys:")
    for pattern in ["votes:*", "api:*", "shelters:*", "supplies:*"]:
        keys = redis_client.keys(pattern)
        if keys:
            print(f"  {pattern}: {len(keys)} 個")

if __name__ == "__main__":
    # 測試 Redis 連接
    redis_client = test_redis_connection()
    
    # 測試社群功能
    test_community_features(redis_client)
    
    # 檢查資料
    check_redis_data()