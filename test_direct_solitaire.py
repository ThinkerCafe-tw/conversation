#!/usr/bin/env python3
"""
直接測試接龍功能，不通過 webhook
"""

import os
import sys
import redis
from dotenv import load_dotenv

# 添加當前目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from community_features import CommunityFeatures
from word_chain_formatter import (
    format_word_chain_display, 
    format_chain_complete,
    format_chain_error,
    format_chain_status
)

# 載入環境變數
if os.path.exists('.env'):
    load_dotenv()

def main():
    print("=== 直接測試接龍功能 ===\n")
    
    # 連接 Redis
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
        redis_client.ping()
        print("✅ Redis 連接成功")
    except Exception as e:
        print(f"❌ Redis 連接失敗: {e}")
        return
    
    # 初始化社群功能
    community = CommunityFeatures(redis_client)
    print(f"✅ 社群功能初始化成功")
    print(f"✅ community.connected = {community.connected}\n")
    
    # 測試場景
    test_users = ["用戶0001", "用戶0002", "用戶0003"]
    
    print("1. 開始新接龍:")
    result = community.start_word_chain("蘋果", test_users[0])
    print(result['message'])
    print()
    
    print("2. 查看接龍狀態:")
    result = community.get_word_chain_status()
    print(result['message'])
    print()
    
    print("3. 正確接龍 (果汁):")
    result = community.continue_word_chain("果汁", test_users[1])
    print(result['message'])
    print()
    
    print("4. 錯誤接龍 (蘋果):")
    result = community.continue_word_chain("蘋果", test_users[2])
    print(result['message'])
    print()
    
    print("5. 正確接龍 (汁液):")
    result = community.continue_word_chain("汁液", test_users[2])
    print(result['message'])
    print()
    
    print("6. 測試單個字詞 (液):")
    result = community.continue_word_chain("液", test_users[0])
    print(result['message'])
    print()
    
    print("7. 正確接龍 (液體):")
    result = community.continue_word_chain("液體", test_users[0])
    print(result['message'])
    print()
    
    # 清理
    redis_client.delete("word_chain:current")
    print("\n✅ 測試完成，已清理測試資料")

if __name__ == "__main__":
    main()