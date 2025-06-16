"""
測試 Neo4j 連接腳本
"""

import os
from dotenv import load_dotenv
from knowledge_graph import KnowledgeGraph
from intent_analyzer import IntentAnalyzer

# 載入環境變數
if os.path.exists('.env'):
    load_dotenv()

def test_connection():
    """測試 Neo4j 連接"""
    print("=== Neo4j 連接測試 ===\n")
    
    # 檢查環境變數
    print("1. 檢查環境變數:")
    neo4j_uri = os.getenv('NEO4J_URI')
    neo4j_user = os.getenv('NEO4J_USER')
    neo4j_password = os.getenv('NEO4J_PASSWORD')
    
    print(f"   NEO4J_URI: {'已設定' if neo4j_uri else '未設定'}")
    print(f"   NEO4J_USER: {'已設定' if neo4j_user else '未設定'}")
    print(f"   NEO4J_PASSWORD: {'已設定' if neo4j_password else '未設定'}")
    
    if not all([neo4j_uri, neo4j_user, neo4j_password]):
        print("\n❌ 缺少必要的環境變數！")
        print("\n請在 .env 檔案中設定以下變數:")
        print("NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io")
        print("NEO4J_USER=neo4j")
        print("NEO4J_PASSWORD=your-password")
        return
    
    # 測試連接
    print("\n2. 測試資料庫連接:")
    try:
        kg = KnowledgeGraph()
        print("   ✅ 連接成功！")
        
        # 測試基本操作
        print("\n3. 測試基本操作:")
        
        # 新增測試用戶
        user = kg.add_user("test_user_001", "測試用戶")
        print(f"   ✅ 新增用戶: {user}")
        
        # 新增測試訊息
        msg = kg.add_message(
            message_id=None,
            content="這是一個測試訊息",
            user_id="test_user_001",
            embedding=[0.1, 0.2, 0.3]  # 簡化的嵌入向量
        )
        print(f"   ✅ 新增訊息: {msg['message']['id']}")
        
        # 建立功能關聯
        kg.link_message_to_feature(msg['message']['id'], "測試功能")
        print("   ✅ 建立功能關聯")
        
        # 查詢用戶偏好
        prefs = kg.get_user_preferences("test_user_001")
        print(f"   ✅ 查詢用戶偏好: {prefs}")
        
        # 獲取社群洞察
        insights = kg.get_community_insights()
        print(f"   ✅ 社群統計: {insights['statistics']}")
        
        kg.close()
        
    except Exception as e:
        print(f"   ❌ 連接失敗: {e}")
        return
    
    # 測試意圖分析器
    print("\n4. 測試意圖分析器:")
    try:
        analyzer = IntentAnalyzer()
        
        # 測試幾個範例訊息
        test_messages = [
            "我想玩接龍",
            "查看統計",
            "3",
            "今天天氣真好"
        ]
        
        for msg in test_messages:
            result = analyzer.analyze(msg, "test_user_001")
            print(f"   訊息: '{msg}'")
            print(f"   → 意圖: {result.get('intent')}, 功能: {result.get('feature')}, 信心度: {result.get('confidence'):.2f}")
        
        print("   ✅ 意圖分析器運作正常")
        
    except Exception as e:
        print(f"   ❌ 意圖分析器錯誤: {e}")
    
    print("\n=== 測試完成 ===")

if __name__ == "__main__":
    test_connection()