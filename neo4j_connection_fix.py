"""
修復 Neo4j 連接問題的補丁
"""

import os
import sys

def patch_knowledge_graph():
    """修補 knowledge_graph.py 中的所有方法"""
    
    # 讀取檔案
    with open('knowledge_graph.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 需要加入連接檢查的方法
    methods_to_patch = [
        'add_message',
        'link_message_to_feature', 
        'add_topic',
        'get_user_preferences',
        'get_conversation_context',
        'find_similar_intents',
        'get_social_recommendations',
        'get_community_insights',
        'analyze_message_flow'
    ]
    
    # 對每個方法加入檢查
    for method in methods_to_patch:
        # 找到方法定義
        method_pattern = f'def {method}(self'
        if method_pattern in content:
            # 找到方法開始的位置
            start_idx = content.find(method_pattern)
            # 找到下一個 with self.driver.session() 的位置
            session_pattern = 'with self.driver.session()'
            session_idx = content.find(session_pattern, start_idx)
            
            if session_idx > start_idx:
                # 找到適當的插入點（函數文檔字串之後）
                doc_end_idx = content.find('"""', content.find('"""', start_idx) + 3) + 3
                newline_idx = content.find('\n', doc_end_idx)
                
                # 插入連接檢查
                check_code = '''
        if not self.connected or not self.driver:
            logger.warning(f"Neo4j not connected, skipping {method}")
            return {{}}
            '''
                
                # 只有在還沒有檢查的情況下才插入
                if 'if not self.connected' not in content[doc_end_idx:session_idx]:
                    content = content[:newline_idx] + check_code.replace('{method}', method) + content[newline_idx:]
    
    # 寫回檔案
    with open('knowledge_graph.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 已修補 knowledge_graph.py")

def add_connection_status_endpoint():
    """在 app.py 加入 Neo4j 狀態端點"""
    
    endpoint_code = '''
@app.route("/neo4j/status")
def neo4j_status():
    """檢查 Neo4j 連接狀態和資料統計"""
    if not knowledge_graph:
        return jsonify({
            "status": "not_initialized",
            "message": "Knowledge graph not initialized"
        })
    
    if not knowledge_graph.connected:
        return jsonify({
            "status": "disconnected", 
            "message": "Neo4j connection failed",
            "uri": knowledge_graph.uri if knowledge_graph else None
        })
    
    try:
        # 獲取統計資料
        stats = knowledge_graph.get_community_insights()
        return jsonify({
            "status": "connected",
            "statistics": stats['statistics'],
            "message": "Neo4j is working properly"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })
'''
    
    # 讀取 app.py
    with open('app.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 在健康檢查端點後面加入
    insert_point = content.find('}, 200') + 6
    if '/neo4j/status' not in content:
        content = content[:insert_point] + '\n' + endpoint_code + content[insert_point:]
        
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 已加入 /neo4j/status 端點")

def create_data_seeder():
    """建立資料填充腳本"""
    
    seeder_code = '''"""
自動填充 Neo4j 測試資料
"""

import os
import time
from knowledge_graph import KnowledgeGraph
from collective_memory import CollectiveMemorySystem

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
    print("\\n新增用戶...")
    for user_id, name in test_users:
        result = graph.add_user(user_id, name)
        print(f"✅ 新增用戶: {name} ({user_id})")
    
    # 新增訊息
    print("\\n新增訊息...")
    for i, (user_id, content) in enumerate(test_messages):
        # 使用集體記憶系統處理訊息
        result = memory_system.process_message(user_id, content)
        print(f"✅ 處理訊息 {i+1}: [{user_id}] {content[:20]}...")
        time.sleep(0.1)  # 避免過快
    
    # 顯示統計
    print("\\n=== Neo4j 資料統計 ===")
    insights = graph.get_community_insights()
    stats = insights['statistics']
    print(f"總用戶數: {stats['total_users']}")
    print(f"總訊息數: {stats['total_messages']}")
    print(f"總功能數: {stats['total_features']}")
    print(f"總話題數: {stats['total_topics']}")
    
    print("\\n✅ 資料填充完成！")
    print("\\n您可以到 Neo4j Browser 查看：")
    print("1. 查看所有節點: MATCH (n) RETURN n LIMIT 50")
    print("2. 查看用戶關係: MATCH (u:User)-[r]->(m) RETURN u,r,m")
    print("3. 查看功能使用: MATCH (m:Message)-[:TRIGGERS]->(f:Feature) RETURN m,f")
    
    graph.close()

if __name__ == "__main__":
    seed_neo4j()
'''
    
    with open('seed_neo4j.py', 'w', encoding='utf-8') as f:
        f.write(seeder_code)
    
    print("✅ 已建立 seed_neo4j.py")

if __name__ == "__main__":
    print("🔧 開始修復 Neo4j 連接問題...\n")
    
    # 1. 修補 knowledge_graph.py
    patch_knowledge_graph()
    
    # 2. 加入狀態檢查端點
    add_connection_status_endpoint()
    
    # 3. 建立資料填充腳本
    create_data_seeder()
    
    print("\n✅ 修復完成！")
    print("\n下一步：")
    print("1. 執行 python seed_neo4j.py 填充測試資料")
    print("2. 訪問 /neo4j/status 檢查連接狀態")
    print("3. 重新部署到 Cloud Run")