"""
檢查 Neo4j 資料和關聯
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

def check_neo4j_data():
    """檢查 Neo4j 中的資料狀態"""
    
    # 連接 Neo4j
    uri = os.getenv('NEO4J_URI')
    user = os.getenv('NEO4J_USER', 'neo4j')
    password = os.getenv('NEO4J_PASSWORD')
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session() as session:
        print("=== Neo4j 資料檢查 ===\n")
        
        # 1. 節點統計
        print("1. 節點統計：")
        result = session.run("""
            MATCH (n)
            RETURN labels(n)[0] as label, count(n) as count
            ORDER BY count DESC
        """)
        for record in result:
            print(f"   {record['label']}: {record['count']}")
        
        # 2. 關係統計
        print("\n2. 關係統計：")
        result = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) as type, count(r) as count
            ORDER BY count DESC
        """)
        relationships = list(result)
        if relationships:
            for record in relationships:
                print(f"   {record['type']}: {record['count']}")
        else:
            print("   ❌ 沒有找到任何關係！")
        
        # 3. 用戶和訊息的關聯
        print("\n3. 用戶-訊息關聯：")
        result = session.run("""
            MATCH (u:User)-[r:SENT]->(m:Message)
            RETURN u.id as user, count(m) as messages
            ORDER BY messages DESC
            LIMIT 5
        """)
        sent_relationships = list(result)
        if sent_relationships:
            for record in sent_relationships:
                print(f"   {record['user']}: {record['messages']} 則訊息")
        else:
            print("   ❌ 沒有 SENT 關係！")
        
        # 4. 訊息和功能的關聯
        print("\n4. 訊息-功能關聯：")
        result = session.run("""
            MATCH (m:Message)-[r:TRIGGERS]->(f:Feature)
            RETURN f.name as feature, count(m) as count
            ORDER BY count DESC
        """)
        feature_relationships = list(result)
        if feature_relationships:
            for record in feature_relationships:
                print(f"   {record['feature']}: {record['count']} 次")
        else:
            print("   ❌ 沒有 TRIGGERS 關係！")
        
        # 5. 訊息序列關聯
        print("\n5. 訊息序列關聯：")
        result = session.run("""
            MATCH (m1:Message)-[r:FOLLOWED_BY]->(m2:Message)
            RETURN count(r) as count
        """)
        follow_count = result.single()['count']
        print(f"   FOLLOWED_BY 關係數量: {follow_count}")
        
        # 6. 話題關聯
        print("\n6. 話題關聯：")
        result = session.run("""
            MATCH (m:Message)-[r:MENTIONS]->(t:Topic)
            RETURN t.name as topic, count(m) as count
            ORDER BY count DESC
            LIMIT 5
        """)
        topic_relationships = list(result)
        if topic_relationships:
            for record in topic_relationships:
                print(f"   {record['topic']}: {record['count']} 次")
        else:
            print("   ❌ 沒有 MENTIONS 關係！")
        
        # 7. 診斷問題
        print("\n=== 問題診斷 ===")
        
        # 檢查是否有孤立的訊息
        result = session.run("""
            MATCH (m:Message)
            WHERE NOT (m)<-[:SENT]-(:User)
            RETURN count(m) as orphan_messages
        """)
        orphans = result.single()['orphan_messages']
        if orphans > 0:
            print(f"⚠️  發現 {orphans} 個沒有用戶關聯的訊息")
        
        # 檢查用戶是否有 ID
        result = session.run("""
            MATCH (u:User)
            WHERE u.id IS NULL
            RETURN count(u) as users_without_id
        """)
        no_id = result.single()['users_without_id']
        if no_id > 0:
            print(f"⚠️  發現 {no_id} 個沒有 ID 的用戶")
        
        # 建議
        print("\n=== 建議 ===")
        if not relationships:
            print("❌ 資料庫中完全沒有關係！可能的原因：")
            print("   1. process_message 方法沒有正確執行")
            print("   2. 關係建立的程式碼有錯誤")
            print("   3. 交易沒有正確提交")
            print("\n建議重新執行 seed_neo4j.py 並檢查錯誤日誌")
        else:
            print("✅ 資料庫中有關係存在")
            if not sent_relationships:
                print("⚠️  但是缺少 User->Message 的 SENT 關係")
            if not feature_relationships:
                print("⚠️  但是缺少 Message->Feature 的 TRIGGERS 關係")
    
    driver.close()

if __name__ == "__main__":
    check_neo4j_data()