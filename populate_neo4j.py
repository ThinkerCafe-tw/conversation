"""
填充 Neo4j 資料庫以展示系統功能
"""

import os
import time
from dotenv import load_dotenv
from knowledge_graph import KnowledgeGraph
from collective_memory import CollectiveMemorySystem

# 載入環境變數
load_dotenv()

def populate_neo4j_with_sample_data():
    """填充範例資料到 Neo4j"""
    print("開始填充 Neo4j 資料庫...")
    
    # 初始化
    graph = KnowledgeGraph()
    memory_system = CollectiveMemorySystem(graph)
    
    # 模擬一天的對話資料
    conversations = [
        # 早上時段 (8-10am)
        ("用戶0001", "早安大家！今天天氣真好", "08:15"),
        ("用戶0002", "早安～昨晚睡得好嗎", "08:20"),
        ("用戶0003", "剛起床，準備上班了", "08:25"),
        ("用戶0001", "統計", "08:30"),  # 查看統計
        ("用戶0004", "有人要一起訂早餐嗎", "08:35"),
        ("用戶0002", "投票 早餐吃什麼/三明治/漢堡/蛋餅/飯糰", "08:40"),
        ("用戶0005", "1", "08:41"),  # 投票
        ("用戶0003", "3", "08:42"),  # 投票
        
        # 中午時段 (12-2pm)
        ("用戶0006", "午休時間到！", "12:00"),
        ("用戶0007", "好餓喔，附近有什麼好吃的", "12:10"),
        ("用戶0008", "我知道一家不錯的拉麵店", "12:15"),
        ("用戶0001", "接龍 拉麵", "12:20"),  # 開始接龍
        ("用戶0009", "麵包", "12:21"),
        ("用戶0010", "包子", "12:22"),
        ("用戶0002", "子彈", "12:23"),
        
        # 下午時段 (3-5pm)
        ("用戶0011", "下午茶時間～", "15:00"),
        ("用戶0012", "好累喔，需要咖啡", "15:30"),
        ("用戶0013", "我也是，一起團購咖啡？", "15:35"),
        ("用戶0012", "統計", "15:40"),  # 查看統計
        
        # 晚上時段 (7-10pm)
        ("用戶0014", "終於下班了！", "19:00"),
        ("用戶0015", "今天好累，想放鬆一下", "19:30"),
        ("用戶0016", "有人要打電動嗎", "19:45"),
        ("用戶0017", "防空 信義區某大樓 地下停車場 200", "20:00"),  # 防災資訊
        ("用戶0018", "今晚的月亮真美", "20:30"),
        ("用戶0019", "是啊，今天是滿月", "20:35"),
        ("用戶0020", "時間過得真快", "21:00"),
        ("用戶0001", "廣播", "21:30"),  # 查看廣播
        
        # 深夜時段 (10pm-12am)
        ("用戶0021", "準備睡覺了，晚安大家", "22:00"),
        ("用戶0022", "我還在加班QQ", "22:30"),
        ("用戶0023", "辛苦了，早點休息", "22:35"),
        ("用戶0024", "明天見！", "23:00"),
        ("用戶0025", "做個好夢～", "23:30"),
    ]
    
    # 處理每條訊息
    for i, (user_id, message, time_str) in enumerate(conversations):
        print(f"處理訊息 {i+1}/{len(conversations)}: [{user_id}] {message[:20]}...")
        
        # 加入集體記憶
        try:
            result = memory_system.process_message(user_id, message)
            
            # 模擬時間延遲
            time.sleep(0.1)
            
        except Exception as e:
            print(f"  錯誤: {e}")
    
    print("\n資料填充完成！")
    
    # 顯示統計
    print("\n=== Neo4j 資料庫統計 ===")
    insights = graph.get_community_insights()
    print(f"總用戶數: {insights['statistics']['total_users']}")
    print(f"總訊息數: {insights['statistics']['total_messages']}")
    print(f"總功能數: {insights['statistics']['total_features']}")
    print(f"總話題數: {insights['statistics']['total_topics']}")
    
    print("\n熱門功能:")
    for feature in insights['popular_features']:
        print(f"  - {feature['feature']}: 使用 {feature['count']} 次")
    
    print("\n活躍用戶:")
    for user in insights['active_users']:
        print(f"  - {user['user_id']}: {user['count']} 則訊息")
    
    # 測試一些查詢
    print("\n=== 測試查詢 ===")
    
    # 查詢用戶偏好
    print("\n用戶0001的偏好:")
    prefs = graph.get_user_preferences("用戶0001")
    print(f"  常用功能: {[f['name'] for f in prefs['preferred_features']]}")
    print(f"  關注話題: {[t['name'] for t in prefs['interested_topics']]}")
    
    # 分析訊息流動
    print("\n訊息流動模式:")
    flow = graph.analyze_message_flow(hours=24)
    if flow['topic_transitions']:
        print("  話題轉換:")
        for trans in flow['topic_transitions'][:3]:
            print(f"    {trans['from_topic']} → {trans['to_topic']}")
    
    graph.close()
    print("\n完成！現在可以在 Neo4j Browser 中查看資料了。")

def test_collective_memory_broadcast():
    """測試集體記憶廣播生成"""
    print("\n=== 測試集體記憶廣播 ===")
    
    graph = KnowledgeGraph()
    memory_system = CollectiveMemorySystem(graph)
    
    # 生成廣播提示詞
    current_hour = int(time.time() // 3600)
    prompt = memory_system.generate_broadcast_prompt(current_hour)
    
    print(f"\n生成的提示詞長度: {len(prompt)} 字")
    print("\n提示詞預覽:")
    print("-" * 50)
    print(prompt[:800] + "...")
    print("-" * 50)
    
    graph.close()

if __name__ == "__main__":
    populate_neo4j_with_sample_data()
    test_collective_memory_broadcast()