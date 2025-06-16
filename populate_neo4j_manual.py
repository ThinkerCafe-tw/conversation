"""
手動填充 Neo4j 展示資料
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
import time
import random

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv('NEO4J_URI'),
    auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
)

def populate_demo_data():
    """填充展示用資料"""
    
    with driver.session() as session:
        print("清理現有資料...")
        # 清理現有資料（可選）
        # session.run("MATCH (n) DETACH DELETE n")
        
        print("創建用戶...")
        # 創建一批用戶
        users = [
            ("user_alice", "Alice"),
            ("user_bob", "Bob"),
            ("user_charlie", "Charlie"),
            ("user_diana", "Diana"),
            ("user_evan", "Evan"),
            ("user_fiona", "Fiona"),
            ("user_george", "George"),
            ("user_helen", "Helen"),
            ("user_ivan", "Ivan"),
            ("user_julia", "Julia")
        ]
        
        for user_id, name in users:
            session.run("""
                MERGE (u:User {id: $user_id})
                ON CREATE SET 
                    u.name = $name,
                    u.joined_at = datetime(),
                    u.message_count = 0
            """, user_id=user_id, name=name)
        
        print("創建訊息和互動...")
        
        # 早晨對話場景
        morning_messages = [
            ("user_alice", "早安！今天天氣真不錯呢☀️"),
            ("user_bob", "早安Alice！是啊，陽光明媚"),
            ("user_charlie", "大家早！準備開始新的一天"),
            ("user_diana", "早安各位～昨晚睡得好嗎？"),
            ("user_alice", "統計"),  # 查看統計
            ("user_evan", "有人要一起訂早餐嗎？"),
            ("user_fiona", "我想要！投票決定吧"),
            ("user_evan", "投票 早餐選擇/麥當勞/美而美/永和豆漿/7-11"),
            ("user_alice", "1"),  # 投票麥當勞
            ("user_bob", "3"),    # 投票永和豆漿
            ("user_charlie", "3"), # 投票永和豆漿
            ("user_diana", "2"),  # 投票美而美
        ]
        
        # 中午遊戲場景
        noon_messages = [
            ("user_george", "午休時間！來玩接龍吧"),
            ("user_helen", "接龍 開始"),
            ("user_ivan", "始終"),
            ("user_julia", "終點"),
            ("user_alice", "點心"),
            ("user_bob", "心情"),
            ("user_charlie", "情緒"),
            ("user_diana", "緒論"),
            ("user_evan", "論文"),
            ("user_fiona", "文章"),
            ("user_george", "太棒了！我們完成了10個詞"),
        ]
        
        # 晚上深度對話場景
        evening_messages = [
            ("user_helen", "今天好累啊...工作壓力好大"),
            ("user_ivan", "我也是，最近專案deadline一直在趕"),
            ("user_julia", "大家都辛苦了，要記得照顧自己"),
            ("user_alice", "是啊，健康最重要"),
            ("user_bob", "說到健康，最近有在運動嗎？"),
            ("user_charlie", "我每週會去跑步三次"),
            ("user_diana", "防空 信義區體育館 室內空間 500"),  # 防災資訊
            ("user_evan", "物資 飲用水 100箱 大安區 0912345678"),  # 物資分享
            ("user_fiona", "今晚的月亮真的很美"),
            ("user_george", "夏目漱石的梗XD"),
            ("user_helen", "哈哈，你懂的"),
            ("user_ivan", "廣播"),  # 查看廣播
            ("user_julia", "時間過得真快，又到晚上了"),
            ("user_alice", "是啊，感覺一天咻一下就過去了"),
            ("user_bob", "大家晚安，明天見！"),
            ("user_charlie", "晚安～做個好夢"),
        ]
        
        # 處理所有訊息
        all_messages = morning_messages + noon_messages + evening_messages
        base_time = time.time() - 86400  # 從昨天開始
        
        for i, (user_id, content) in enumerate(all_messages):
            msg_time = base_time + (i * 300)  # 每5分鐘一則
            msg_id = f"msg_{int(msg_time)}_{i}"
            
            # 創建訊息
            session.run("""
                MATCH (u:User {id: $user_id})
                CREATE (m:Message {
                    id: $msg_id,
                    content: $content,
                    timestamp: datetime($timestamp)
                })
                CREATE (u)-[:SENT {time: datetime($timestamp)}]->(m)
                SET u.message_count = u.message_count + 1
            """, user_id=user_id, msg_id=msg_id, content=content, timestamp=msg_time)
            
            # 偵測功能使用
            if "統計" in content:
                add_feature(session, msg_id, "統計")
            elif "投票" in content and "/" in content:
                add_feature(session, msg_id, "投票")
            elif content.isdigit():
                add_feature(session, msg_id, "投票")
            elif "接龍" in content:
                add_feature(session, msg_id, "接龍")
            elif "防空" in content:
                add_feature(session, msg_id, "防災")
            elif "物資" in content:
                add_feature(session, msg_id, "防災")
            elif "廣播" in content:
                add_feature(session, msg_id, "廣播")
            
            # 提取話題
            topics = extract_topics(content)
            for topic in topics:
                add_topic(session, msg_id, topic)
            
            print(f"處理: [{user_id}] {content[:30]}...")
        
        # 建立一些訊息序列關聯
        print("\n建立對話流關聯...")
        session.run("""
            MATCH (m1:Message), (m2:Message)
            WHERE m1.timestamp < m2.timestamp
            WITH m1, m2, m2.timestamp - m1.timestamp as time_diff
            WHERE time_diff > 0 AND time_diff < 600  // 10分鐘內
            WITH m1, m2
            ORDER BY m1.timestamp, m2.timestamp
            LIMIT 20
            CREATE (m1)-[:FOLLOWED_BY {time_diff: m2.timestamp - m1.timestamp}]->(m2)
        """)
        
        print("\n資料填充完成！")

def add_feature(session, msg_id, feature_name):
    """添加功能使用關聯"""
    session.run("""
        MATCH (m:Message {id: $msg_id})
        MERGE (f:Feature {name: $feature_name})
        ON CREATE SET 
            f.category = $category,
            f.usage_count = 0,
            f.created_at = datetime()
        CREATE (m)-[:TRIGGERS]->(f)
        SET f.usage_count = f.usage_count + 1
    """, msg_id=msg_id, feature_name=feature_name, category=get_category(feature_name))

def add_topic(session, msg_id, topic):
    """添加話題關聯"""
    session.run("""
        MATCH (m:Message {id: $msg_id})
        MERGE (t:Topic {name: $topic})
        ON CREATE SET t.frequency = 0
        CREATE (m)-[:MENTIONS]->(t)
        SET t.frequency = t.frequency + 1
    """, msg_id=msg_id, topic=topic)

def extract_topics(content):
    """簡單的話題提取"""
    topics = []
    keywords = ["天氣", "早安", "晚安", "工作", "健康", "運動", "月亮", "時間", "壓力", "專案"]
    for keyword in keywords:
        if keyword in content:
            topics.append(keyword)
    return topics[:3]  # 最多3個話題

def get_category(feature_name):
    """獲取功能分類"""
    categories = {
        "接龍": "遊戲",
        "投票": "互動",
        "統計": "資訊",
        "廣播": "資訊",
        "防災": "防災"
    }
    return categories.get(feature_name, "其他")

def show_statistics():
    """顯示統計資訊"""
    with driver.session() as session:
        print("\n=== Neo4j 資料庫統計 ===")
        
        # 總計
        result = session.run("""
            MATCH (u:User) WITH count(u) as users
            MATCH (m:Message) WITH users, count(m) as messages
            MATCH (f:Feature) WITH users, messages, count(f) as features
            MATCH (t:Topic) WITH users, messages, features, count(t) as topics
            RETURN users, messages, features, topics
        """).single()
        
        print(f"用戶總數: {result['users']}")
        print(f"訊息總數: {result['messages']}")
        print(f"功能總數: {result['features']}")
        print(f"話題總數: {result['topics']}")
        
        # 活躍用戶
        print("\n最活躍用戶:")
        result = session.run("""
            MATCH (u:User)
            RETURN u.id as user, u.name as name, u.message_count as count
            ORDER BY u.message_count DESC
            LIMIT 5
        """)
        for record in result:
            print(f"  {record['name']} ({record['user']}): {record['count']} 則")
        
        # 熱門功能
        print("\n熱門功能:")
        result = session.run("""
            MATCH (f:Feature)
            RETURN f.name as feature, f.category as category, f.usage_count as count
            ORDER BY f.usage_count DESC
        """)
        for record in result:
            print(f"  {record['feature']} [{record['category']}]: {record['count']} 次")
        
        # 熱門話題
        print("\n熱門話題:")
        result = session.run("""
            MATCH (t:Topic)
            WHERE t.frequency > 0
            RETURN t.name as topic, t.frequency as freq
            ORDER BY t.frequency DESC
            LIMIT 10
        """)
        for record in result:
            print(f"  {record['topic']}: {record['freq']} 次")

if __name__ == "__main__":
    populate_demo_data()
    show_statistics()
    driver.close()
    
    print("\n✅ 完成！現在您可以在 Neo4j Browser 中看到豐富的資料了。")
    print("\n建議查詢:")
    print("1. 查看用戶網絡:")
    print("   MATCH (u:User)-[:SENT]->(m:Message) RETURN u, m LIMIT 50")
    print("\n2. 查看功能使用:")
    print("   MATCH (m:Message)-[:TRIGGERS]->(f:Feature) RETURN m, f")
    print("\n3. 查看話題網絡:")
    print("   MATCH (m:Message)-[:MENTIONS]->(t:Topic) RETURN m, t")