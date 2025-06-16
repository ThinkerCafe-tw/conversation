"""
自動填充 Neo4j 測試資料
"""

import os
import time
from dotenv import load_dotenv
from knowledge_graph import KnowledgeGraph
from collective_memory import CollectiveMemorySystem

# 載入環境變數
load_dotenv()

def seed_neo4j():
    """填充測試資料到 Neo4j"""
    print("開始填充 Neo4j 資料...")
    
    # 初始化
    graph = KnowledgeGraph()
    
    if not graph.connected:
        print("❌ Neo4j 未連接，請檢查環境變數：")
        print(f"   NEO4J_URI: {os.getenv('NEO4J_URI', 'Not set')}")
        print(f"   NEO4J_USER: {os.getenv('NEO4J_USER', 'Not set')}")
        print(f"   NEO4J_PASSWORD: {'Set' if os.getenv('NEO4J_PASSWORD') else 'Not set'}")
        return
    
    memory_system = CollectiveMemorySystem(graph)
    
    # 測試資料
    test_users = [
        ("user_001", "Alice"),
        ("user_002", "Bob"),
        ("user_003", "Charlie"),
        ("user_004", "David"),
        ("user_005", "Eve")
    ]
    
    test_messages = [
        ("user_001", "早安大家！今天天氣真好"),
        ("user_002", "早安～準備開始新的一天"),
        ("user_003", "我想玩遊戲"),
        ("user_001", "接龍 蘋果"),
        ("user_002", "果汁"),
        ("user_003", "汁液"),
        ("user_004", "統計"),
        ("user_005", "投票 午餐吃什麼/便當/麵/飯"),
        ("user_001", "1"),
        ("user_002", "2"),
        ("user_003", "1"),
        ("user_004", "廣播"),
        ("user_005", "晚安大家～")
    ]
    
    # 新增用戶
    print("\n新增用戶...")
    for user_id, name in test_users:
        result = graph.add_user(user_id, name)
        print(f"✅ 新增用戶: {name} ({user_id})")
    
    # 新增訊息
    print("\n新增訊息...")
    for i, (user_id, content) in enumerate(test_messages):
        # 使用集體記憶系統處理訊息
        result = memory_system.process_message(user_id, content)
        print(f"✅ 處理訊息 {i+1}: [{user_id}] {content[:20]}...")
        time.sleep(0.1)  # 避免過快
    
    # 顯示統計
    print("\n=== Neo4j 資料統計 ===")
    insights = graph.get_community_insights()
    stats = insights['statistics']
    print(f"總用戶數: {stats['total_users']}")
    print(f"總訊息數: {stats['total_messages']}")
    print(f"總功能數: {stats['total_features']}")
    print(f"總話題數: {stats['total_topics']}")
    
    print("\n✅ 資料填充完成！")
    print("\n您可以到 Neo4j Browser 查看：")
    print("1. 查看所有節點: MATCH (n) RETURN n LIMIT 50")
    print("2. 查看用戶關係: MATCH (u:User)-[r]->(m) RETURN u,r,m")
    print("3. 查看功能使用: MATCH (m:Message)-[:TRIGGERS]->(f:Feature) RETURN m,f")
    
    graph.close()

if __name__ == "__main__":
    seed_neo4j()
