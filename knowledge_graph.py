"""
知識圖譜模組
使用 Neo4j 儲存和查詢用戶訊息關聯性
"""

import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from neo4j import GraphDatabase
import hashlib
import json

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        """初始化 Neo4j 連接"""
        self.uri = uri or os.getenv('NEO4J_URI')
        self.user = user or os.getenv('NEO4J_USER', 'neo4j')
        self.password = password or os.getenv('NEO4J_PASSWORD')
        self.connected = False
        
        if not all([self.uri, self.user, self.password]):
            logger.warning("Neo4j connection parameters missing")
            self.driver = None
            return
            
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # 測試連接
            self.driver.verify_connectivity()
            self.connected = True
            logger.info("Neo4j 連接成功")
            self._init_schema()
        except Exception as e:
            logger.error(f"Neo4j 連接失敗: {e}")
            self.driver = None
            self.connected = False
        
    def _init_schema(self):
        """初始化資料庫 schema"""
        with self.driver.session() as session:
            # 創建索引
            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Message) REQUIRE m.id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (f:Feature) REQUIRE f.name IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (v:Vote) REQUIRE v.id IS UNIQUE", # Added in previous task, ensure it's here
                "CREATE CONSTRAINT IF NOT EXISTS FOR (j:Joke) REQUIRE j.id IS UNIQUE", # For new Joke nodes
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    logger.warning(f"Schema creation warning: {e}")
                    
    def close(self):
        """關閉連接"""
        self.driver.close()
        
    # ========== 基礎 CRUD 操作 ==========
    
    def add_user(self, user_id: str, name: str = None) -> Dict:
        """新增或更新用戶節點"""
        if not self.connected or not self.driver:
            logger.warning("Neo4j not connected, skipping add_user")
            return {"user": {"id": user_id}}
            
        with self.driver.session() as session:
            result = session.run("""
                MERGE (u:User {id: $user_id})
                ON CREATE SET 
                    u.name = $name,
                    u.joined_at = datetime(),
                    u.message_count = 0
                ON MATCH SET
                    u.last_active = datetime()
                RETURN u
            """, user_id=user_id, name=name or user_id)
            
            return result.single()["u"]
            
    def add_message(self, message_id: str, content: str, user_id: str, 
                   embedding: List[float] = None) -> Dict:
        """新增訊息節點並建立關聯"""
        if not self.connected or not self.driver:
            logger.warning(f"Neo4j not connected, skipping add_message")
            return {{}}
            
        with self.driver.session() as session:
            # 產生訊息 ID
            if not message_id:
                message_id = f"msg_{user_id}_{int(time.time() * 1000)}"
                
            result = session.run("""
                MATCH (u:User {id: $user_id})
                CREATE (m:Message {
                    id: $message_id,
                    content: $content,
                    timestamp: datetime(),
                    embedding: $embedding
                })
                CREATE (u)-[r:SENT {time: datetime()}]->(m)
                SET u.message_count = u.message_count + 1
                RETURN m, u
            """, message_id=message_id, content=content, 
                user_id=user_id, embedding=embedding)
            
            record = result.single()
            return {
                "message": record["m"],
                "user": record["u"]
            }
            
    def link_message_to_feature(self, message_id: str, feature_name: str):
        """建立訊息與功能的關聯"""
        if not self.connected or not self.driver:
            logger.warning(f"Neo4j not connected, skipping link_message_to_feature")
            return {{}}
            
        with self.driver.session() as session:
            session.run("""
                MATCH (m:Message {id: $message_id})
                MERGE (f:Feature {name: $feature_name})
                ON CREATE SET 
                    f.category = $category,
                    f.usage_count = 0,
                    f.created_at = datetime()
                CREATE (m)-[r:TRIGGERS]->(f)
                SET f.usage_count = f.usage_count + 1
            """, message_id=message_id, feature_name=feature_name,
                category=self._get_feature_category(feature_name))
                
    def add_topic(self, message_id: str, topics: List[str]):
        """為訊息加入主題標籤"""
        if not self.connected or not self.driver:
            logger.warning(f"Neo4j not connected, skipping add_topic")
            return {{}}
            
        with self.driver.session() as session:
            for topic in topics:
                session.run("""
                    MATCH (m:Message {id: $message_id})
                    MERGE (t:Topic {name: $topic})
                    ON CREATE SET t.frequency = 0
                    CREATE (m)-[r:MENTIONS]->(t)
                    SET t.frequency = t.frequency + 1
                """, message_id=message_id, topic=topic)
                
    def link_message_sequence(self, prev_message_id: str, curr_message_id: str):
        """建立訊息序列關聯（對話流）"""
        if not self.connected or not self.driver:
            logger.warning(f"Neo4j not connected, skipping link_message_sequence")
            return {}
            
        with self.driver.session() as session:
            session.run("""
                MATCH (m1:Message {id: $prev_id})
                MATCH (m2:Message {id: $curr_id})
                CREATE (m1)-[r:FOLLOWED_BY {time: datetime()}]->(m2)
            """, prev_id=prev_message_id, curr_id=curr_message_id)
            
    # ========== 查詢操作 ==========
    
    def find_similar_intents(self, user_id: str, embedding: List[float], 
                           limit: int = 5) -> List[Dict]:
        """找出相似的使用意圖"""
        if not self.connected or not self.driver:
            logger.warning(f"Neo4j not connected, skipping find_similar_intents")
            return {{}}
            
        with self.driver.session() as session:
            # 注意：Neo4j 的向量相似度功能需要企業版
            # 這裡使用簡化的查詢
            result = session.run("""
                MATCH (u:User {id: $user_id})-[:SENT]->(m:Message)
                -[:TRIGGERS]->(f:Feature)
                WITH f, count(m) as usage_count
                ORDER BY usage_count DESC
                LIMIT $limit
                RETURN f.name as feature, usage_count
            """, user_id=user_id, limit=limit)
            
            return [{"feature": r["feature"], "count": r["usage_count"]} 
                   for r in result]
                   
    def get_user_preferences(self, user_id: str) -> Dict:
        """獲取用戶偏好"""
        if not self.connected or not self.driver:
            logger.warning(f"Neo4j not connected, skipping get_user_preferences")
            return {{}}
            
        with self.driver.session() as session:
            # 最常用功能
            features = session.run("""
                MATCH (u:User {id: $user_id})-[:SENT]->(:Message)
                -[:TRIGGERS]->(f:Feature)
                RETURN f.name as feature, count(*) as count
                ORDER BY count DESC
                LIMIT 5
            """, user_id=user_id)
            
            # 最常提及主題
            topics = session.run("""
                MATCH (u:User {id: $user_id})-[:SENT]->(:Message)
                -[:MENTIONS]->(t:Topic)
                RETURN t.name as topic, count(*) as count
                ORDER BY count DESC
                LIMIT 5
            """, user_id=user_id)
            
            return {
                "preferred_features": [{"name": r["feature"], "count": r["count"]} 
                                     for r in features],
                "interested_topics": [{"name": r["topic"], "count": r["count"]} 
                                    for r in topics]
            }
            
    def get_social_recommendations(self, user_id: str) -> List[str]:
        """基於社交圖譜的功能推薦"""
        if not self.connected or not self.driver:
            logger.warning(f"Neo4j not connected, skipping get_social_recommendations")
            return {{}}
            
        with self.driver.session() as session:
            # 找出互動過的用戶常用的功能
            result = session.run("""
                MATCH (u1:User {id: $user_id})-[:SENT]->(:Message)<-[:SENT]-(u2:User)
                WHERE u1 <> u2
                WITH u2, count(*) as interaction_count
                ORDER BY interaction_count DESC
                LIMIT 10
                MATCH (u2)-[:SENT]->(:Message)-[:TRIGGERS]->(f:Feature)
                WHERE NOT EXISTS {
                    MATCH (u1)-[:SENT]->(:Message)-[:TRIGGERS]->(f)
                }
                RETURN f.name as feature, count(*) as popularity
                ORDER BY popularity DESC
                LIMIT 3
            """, user_id=user_id)
            
            return [r["feature"] for r in result]
            
    def get_conversation_context(self, user_id: str, limit: int = 5) -> List[Dict]:
        """獲取用戶最近的對話上下文"""
        if not self.connected or not self.driver:
            logger.warning(f"Neo4j not connected, skipping get_conversation_context")
            return {{}}
            
        with self.driver.session() as session:
            result = session.run("""
                MATCH (u:User {id: $user_id})-[:SENT]->(m:Message)
                RETURN m.id as id, m.content as content, m.timestamp as time
                ORDER BY m.timestamp DESC
                LIMIT $limit
            """, user_id=user_id, limit=limit)
            
            return [{"id": r["id"], "content": r["content"], "time": r["time"]} 
                   for r in result]
                   
    def analyze_message_flow(self, hours: int = 24) -> Dict:
        """分析訊息流動模式"""
        if not self.connected or not self.driver:
            logger.warning(f"Neo4j not connected, skipping analyze_message_flow")
            return {{}}
            
        with self.driver.session() as session:
            cutoff_time = datetime.now().timestamp() - (hours * 3600)
            
            # 熱門話題流
            topic_flow = session.run("""
                MATCH (m1:Message)-[:FOLLOWED_BY]->(m2:Message)
                WHERE m1.timestamp > datetime($cutoff)
                MATCH (m1)-[:MENTIONS]->(t1:Topic)
                MATCH (m2)-[:MENTIONS]->(t2:Topic)
                WHERE t1 <> t2
                RETURN t1.name as from_topic, t2.name as to_topic, 
                       count(*) as transitions
                ORDER BY transitions DESC
                LIMIT 10
            """, cutoff=cutoff_time)
            
            # 功能使用流
            feature_flow = session.run("""
                MATCH (m1:Message)-[:FOLLOWED_BY]->(m2:Message)
                WHERE m1.timestamp > datetime($cutoff)
                MATCH (m1)-[:TRIGGERS]->(f1:Feature)
                MATCH (m2)-[:TRIGGERS]->(f2:Feature)
                WHERE f1 <> f2
                RETURN f1.name as from_feature, f2.name as to_feature,
                       count(*) as transitions
                ORDER BY transitions DESC
                LIMIT 10
            """, cutoff=cutoff_time)
            
            return {
                "topic_transitions": [dict(r) for r in topic_flow],
                "feature_transitions": [dict(r) for r in feature_flow]
            }
            
    def get_community_insights(self) -> Dict:
        """獲取社群洞察"""
        if not self.connected or not self.driver:
            logger.warning(f"Neo4j not connected, skipping get_community_insights")
            return {{}}
            
        with self.driver.session() as session:
            stats = session.run("""
                MATCH (u:User)
                WITH count(u) as total_users
                MATCH (m:Message)
                WITH total_users, count(m) as total_messages
                MATCH (f:Feature)
                WITH total_users, total_messages, count(f) as total_features
                MATCH (t:Topic)
                RETURN total_users, total_messages, total_features,
                       count(t) as total_topics
            """).single()
            
            # 最活躍用戶
            active_users = session.run("""
                MATCH (u:User)
                RETURN u.id as user_id, u.message_count as count
                ORDER BY u.message_count DESC
                LIMIT 5
            """)
            
            # 熱門功能
            popular_features = session.run("""
                MATCH (f:Feature)
                RETURN f.name as feature, f.usage_count as count
                ORDER BY f.usage_count DESC
                LIMIT 5
            """)
            
            return {
                "statistics": dict(stats),
                "active_users": [dict(r) for r in active_users],
                "popular_features": [dict(r) for r in popular_features]
            }
            
    # ========== 工具方法 ==========
    
    def _get_feature_category(self, feature_name: str) -> str:
        """獲取功能分類"""
        categories = {
            "接龍": "遊戲",
            "投票": "互動",
            "統計": "資訊",
            "廣播": "資訊",
            "防空": "防災", # Assuming "防空" is mapped to "防災資訊" feature name
            "防災資訊": "防災", # Explicitly for "防災資訊" feature name
            "物資": "防災",
            "API統計": "系統",
            "笑話": "娛樂" # Added category for Joke feature
        }
        
        # Exact match preferred
        if feature_name in categories:
            return categories[feature_name]

        # Fallback to keyword based
        for keyword, category in categories.items():
            if keyword in feature_name: # This might lead to "防空" being "防災"
                return category
                
        return "其他"

    def log_user_feature_interaction(self, user_id: str, feature_name: str, interaction_type: str = "used"):
        """記錄用戶與特定功能的互動"""
        if not self.connected or not self.driver:
            logger.warning(f"Neo4j not connected, skipping log_user_feature_interaction for user {user_id}, feature {feature_name}")
            return

        try:
            with self.driver.session() as session:
                session.run("""
                    MERGE (u:User {id: $user_id})
                    MERGE (f:Feature {name: $feature_name})
                    ON CREATE SET
                        f.category = $category,
                        f.usage_count = 0,
                        f.created_at = datetime()
                    ON MATCH SET // Ensure category is set even if feature node already exists
                        f.category = $category

                    CREATE (u)-[r:INTERACTED_WITH_FEATURE {type: $interaction_type, timestamp: datetime()}]->(f)
                    SET f.usage_count = coalesce(f.usage_count, 0) + 1
                """, user_id=user_id, feature_name=feature_name,
                   interaction_type=interaction_type, category=self._get_feature_category(feature_name))
                logger.info(f"User {user_id} interaction '{interaction_type}' with feature '{feature_name}' logged.")
        except Exception as e:
            logger.error(f"Error logging user feature interaction to Neo4j: {e}")
            # Optionally re-raise
            # raise

    def log_user_vote(self, user_id: str, vote_id: str, vote_topic: str, option_chosen: str):
        """記錄用戶投票行為到 Neo4j"""
        if not self.connected or not self.driver:
            logger.warning(f"Neo4j not connected, skipping log_user_vote for user {user_id}, vote {vote_id}")
            return

        try:
            with self.driver.session() as session:
                session.run("""
                    MERGE (u:User {id: $user_id})
                    MERGE (v:Vote {id: $vote_id})
                    ON CREATE SET
                        v.topic = $vote_topic,
                        v.created_at = datetime(),
                        v.last_activity_at = datetime()
                    ON MATCH SET
                        v.last_activity_at = datetime()

                    MERGE (u)-[r:VOTED {option: $option_chosen}]->(v)
                    ON CREATE SET
                        r.timestamp = datetime()
                """, user_id=user_id, vote_id=vote_id, vote_topic=vote_topic, option_chosen=option_chosen)
                logger.info(f"User {user_id} vote for '{option_chosen}' on vote '{vote_id}' ({vote_topic}) logged.")
        except Exception as e:
            logger.error(f"Error logging user vote to Neo4j: {e}")
            # Optionally re-raise or handle more gracefully depending on desired app behavior
            raise

    def log_joke_submission(self, user_id: str, joke_id: str, joke_text_preview: str):
        """記錄用戶提交笑話的行為到 Neo4j"""
        if not self.connected or not self.driver:
            logger.warning(f"Neo4j not connected, skipping log_joke_submission for user {user_id}, joke {joke_id}")
            return
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MERGE (u:User {id: $user_id})
                    MERGE (j:Joke {id: $joke_id})
                    ON CREATE SET
                        j.text_preview = $joke_text_preview,
                        j.created_at = datetime(),
                        j.like_count = 0 // Initialize like_count
                    MERGE (u)-[r:SUBMITTED {timestamp: datetime()}]->(j)
                    RETURN j
                """, user_id=user_id, joke_id=joke_id, joke_text_preview=joke_text_preview)
                logger.info(f"User {user_id} submitted joke {joke_id} logged. Preview: {joke_text_preview}")
                return result.single()["j"]
        except Exception as e:
            logger.error(f"Error logging joke submission to Neo4j for user {user_id}, joke {joke_id}: {e}")
            raise

    def log_joke_like(self, user_id: str, joke_id: str):
        """記錄用戶按讚笑話的行為到 Neo4j"""
        if not self.connected or not self.driver:
            logger.warning(f"Neo4j not connected, skipping log_joke_like for user {user_id}, joke {joke_id}")
            return
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MERGE (u:User {id: $user_id})
                    MERGE (j:Joke {id: $joke_id})
                    ON CREATE SET // Should ideally not happen if joke is liked after being seen
                        j.created_at = datetime(),
                        j.like_count = 0
                    MERGE (u)-[r:LIKED {timestamp: datetime()}]->(j)
                    SET j.like_count = coalesce(j.like_count, 0) + 1
                    RETURN j
                """, user_id=user_id, joke_id=joke_id)
                logger.info(f"User {user_id} liked joke {joke_id} logged.")
                return result.single()["j"]
        except Exception as e:
            logger.error(f"Error logging joke like to Neo4j for user {user_id}, joke {joke_id}: {e}")
            raise

    def get_friends_who_liked_joke(self, user_id: str, joke_id: str, limit: int = 3) -> List[str]:
        """找出也喜歡同一個笑話的朋友們 (簡化版：其他也按讚的用戶)"""
        if not self.connected or not self.driver:
            logger.warning(f"Neo4j not connected, skipping get_friends_who_liked_joke for user {user_id}, joke {joke_id}")
            return []
        
        try:
            with self.driver.session() as session:
                # Query for other users who liked the same joke, excluding the current user.
                result = session.run("""
                    MATCH (currentUser:User {id: $user_id})-[:LIKED]->(j:Joke {id: $joke_id})
                    MATCH (otherUser:User)-[:LIKED]->(j)
                    WHERE currentUser <> otherUser
                    RETURN otherUser.id AS friend_id
                    LIMIT $limit
                """, user_id=user_id, joke_id=joke_id, limit=limit)

                friend_ids = [record["friend_id"] for record in result]
                if friend_ids:
                    logger.info(f"Found {len(friend_ids)} other users who liked joke {joke_id} for user {user_id}.")
                return friend_ids
        except Exception as e:
            logger.error(f"Error getting friends who liked joke {joke_id} for user {user_id}: {e}")
            return [] # Return empty list on error

    def export_graph_data(self, format: str = "json") -> str:
        """匯出圖資料供視覺化"""
        if not self.connected or not self.driver: # Check connection for export too
            logger.warning("Neo4j not connected, cannot export graph data.")
            return json.dumps({"nodes": [], "edges": []}) if format == "json" else {"nodes": [], "edges": []}

        with self.driver.session() as session:
            nodes_query = """
                MATCH (n)
                WHERE n:User OR n:Feature OR n:Topic OR n:Vote OR n:Joke // Added Joke
                RETURN id(n) as id, labels(n)[0] as type, 
                       properties(n) as properties
                LIMIT 1000
            """
            nodes_result = session.run(nodes_query)
            
            edges_query = """
                MATCH (n1)-[r]->(n2)
                WHERE ((n1:User OR n1:Message) AND
                       (n2:Message OR n2:Feature OR n2:Topic OR n2:Vote OR n2:Joke))
                   OR (n1:User AND r:VOTED AND n2:Vote)
                   OR (n1:User AND r:SUBMITTED AND n2:Joke)
                   OR (n1:User AND r:LIKED AND n2:Joke)
                   OR (n1:User AND r:INTERACTED_WITH_FEATURE AND n2:Feature) // Added INTERACTED_WITH_FEATURE
                RETURN id(n1) as source, id(n2) as target,
                       type(r) as type, properties(r) as properties
                LIMIT 1000
            """
            edges_result = session.run(edges_query)

            graph_data = {
                "nodes": [dict(n) for n in nodes_result],
                "edges": [dict(e) for e in edges]
            }
            
            if format == "json":
                return json.dumps(graph_data, indent=2, default=str)
            else:
                return graph_data