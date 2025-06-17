"""
Neo4j 交友功能查詢
"""

class DatingQueries:
    """交友相關的 Neo4j 查詢"""
    
    @staticmethod
    def create_dating_profile(tx, profile):
        """創建交友檔案"""
        query = """
        MERGE (u:User {user_id: $user_id})
        SET u.display_name = $display_name,
            u.age = $age,
            u.gender = $gender,
            u.location = $location,
            u.bio = $bio,
            u.created_at = datetime(),
            u.last_active = datetime(),
            u.dating_active = true
        
        // 添加興趣標籤
        WITH u
        UNWIND $interests as interest
        MERGE (i:Interest {name: interest})
        MERGE (u)-[:INTERESTED_IN]->(i)
        
        // 添加個性特質
        WITH u
        UNWIND keys($personality_traits) as trait_name
        MERGE (t:PersonalityTrait {name: trait_name})
        MERGE (u)-[r:HAS_TRAIT]->(t)
        SET r.score = $personality_traits[trait_name]
        
        RETURN u.user_id as user_id
        """
        
        result = tx.run(query, {
            'user_id': profile.user_id,
            'display_name': profile.display_name,
            'age': profile.age,
            'gender': profile.gender,
            'location': profile.location,
            'bio': profile.bio,
            'interests': profile.interests,
            'personality_traits': profile.personality_traits
        })
        return result.single()['user_id']
    
    @staticmethod
    def get_dating_recommendations(tx, user_id, limit=10):
        """獲取交友推薦"""
        query = """
        MATCH (me:User {user_id: $user_id, dating_active: true})
        MATCH (other:User {dating_active: true})
        WHERE other.user_id <> $user_id
        
        // 排除已經滑過的用戶
        AND NOT EXISTS {
            MATCH (me)-[:SWIPED]->(other)
        }
        
        // 排除已配對的用戶
        AND NOT EXISTS {
            MATCH (me)-[:MATCHED]-(other)
        }
        
        // 基本過濾條件
        AND abs(me.age - other.age) <= 10  // 年齡差距不超過10歲
        
        // 計算共同興趣分數
        OPTIONAL MATCH (me)-[:INTERESTED_IN]->(common_interest)<-[:INTERESTED_IN]-(other)
        WITH me, other, count(common_interest) as common_interests
        
        // 計算個性相容性
        OPTIONAL MATCH (me)-[mt:HAS_TRAIT]->(trait)<-[ot:HAS_TRAIT]-(other)
        WITH me, other, common_interests, 
             avg(abs(mt.score - ot.score)) as personality_diff
        
        // 計算地理位置分數 (簡化版)
        WITH me, other, common_interests, personality_diff,
             CASE 
                WHEN me.location = other.location THEN 1.0
                ELSE 0.5
             END as location_score
        
        // 計算總體相容性分數
        WITH other, 
             (common_interests * 0.4 + 
              (1 - coalesce(personality_diff, 0.5)) * 0.4 + 
              location_score * 0.2) as compatibility_score
        
        RETURN other.user_id as user_id,
               other.display_name as display_name,
               other.age as age,
               other.location as location,
               other.bio as bio,
               round(compatibility_score * 100) as compatibility_score
        
        ORDER BY compatibility_score DESC, other.last_active DESC
        LIMIT $limit
        """
        
        result = tx.run(query, {'user_id': user_id, 'limit': limit})
        return [record.data() for record in result]
    
    @staticmethod
    def record_swipe_action(tx, user_id, target_user_id, action):
        """記錄滑動動作"""
        query = """
        MATCH (user:User {user_id: $user_id})
        MATCH (target:User {user_id: $target_user_id})
        
        MERGE (user)-[s:SWIPED]->(target)
        SET s.action = $action,
            s.timestamp = datetime(),
            s.is_super_like = false
        
        RETURN s.action as recorded_action
        """
        
        result = tx.run(query, {
            'user_id': user_id,
            'target_user_id': target_user_id,
            'action': action
        })
        return result.single()['recorded_action']
    
    @staticmethod
    def record_super_like(tx, user_id, target_user_id):
        """記錄超級喜歡"""
        query = """
        MATCH (user:User {user_id: $user_id})
        MATCH (target:User {user_id: $target_user_id})
        
        MERGE (user)-[s:SWIPED]->(target)
        SET s.action = 'like',
            s.timestamp = datetime(),
            s.is_super_like = true
        
        RETURN s.is_super_like as is_super_like
        """
        
        result = tx.run(query, {
            'user_id': user_id,
            'target_user_id': target_user_id
        })
        return result.single()['is_super_like']
    
    @staticmethod
    def check_mutual_like(tx, user_id, target_user_id):
        """檢查互相喜歡"""
        query = """
        MATCH (user:User {user_id: $user_id})
        MATCH (target:User {user_id: $target_user_id})
        
        MATCH (user)-[s1:SWIPED]->(target)
        MATCH (target)-[s2:SWIPED]->(user)
        
        WHERE s1.action = 'like' AND s2.action = 'like'
        
        RETURN true as is_mutual_like
        """
        
        result = tx.run(query, {
            'user_id': user_id,
            'target_user_id': target_user_id
        })
        record = result.single()
        return record['is_mutual_like'] if record else False
    
    @staticmethod
    def create_match(tx, match):
        """創建配對"""
        query = """
        MATCH (user1:User {user_id: $user1_id})
        MATCH (user2:User {user_id: $user2_id})
        
        MERGE (user1)-[m1:MATCHED]->(user2)
        MERGE (user2)-[m2:MATCHED]->(user1)
        
        SET m1.match_id = $match_id,
            m1.compatibility_score = $compatibility_score,
            m1.matched_at = datetime(),
            m1.conversation_started = false
        
        SET m2.match_id = $match_id,
            m2.compatibility_score = $compatibility_score,
            m2.matched_at = datetime(),
            m2.conversation_started = false
        
        RETURN m1.match_id as match_id
        """
        
        result = tx.run(query, {
            'match_id': match.match_id,
            'user1_id': match.user1_id,
            'user2_id': match.user2_id,
            'compatibility_score': match.compatibility_score
        })
        return result.single()['match_id']
    
    @staticmethod
    def get_user_matches(tx, user_id):
        """獲取用戶配對"""
        query = """
        MATCH (me:User {user_id: $user_id})-[m:MATCHED]->(partner:User)
        
        RETURN partner.user_id as partner_id,
               partner.display_name as partner_name,
               partner.age as partner_age,
               m.match_id as match_id,
               m.compatibility_score as compatibility_score,
               m.matched_at as matched_at,
               m.conversation_started as conversation_started
        
        ORDER BY m.matched_at DESC
        """
        
        result = tx.run(query, {'user_id': user_id})
        return [record.data() for record in result]
    
    @staticmethod
    def get_dating_insights(tx, user_id):
        """獲取約會洞察"""
        query = """
        MATCH (me:User {user_id: $user_id})
        
        // 統計滑動數據
        OPTIONAL MATCH (me)-[s:SWIPED]->()
        WITH me, count(s) as total_swipes,
             size([s IN collect(s) WHERE s.action = 'like']) as likes_sent,
             size([s IN collect(s) WHERE s.is_super_like = true]) as super_likes_sent
        
        // 統計收到的喜歡
        OPTIONAL MATCH ()-[sr:SWIPED]->(me)
        WITH me, total_swipes, likes_sent, super_likes_sent,
             size([sr IN collect(sr) WHERE sr.action = 'like']) as likes_received
        
        // 統計配對
        OPTIONAL MATCH (me)-[m:MATCHED]->()
        WITH me, total_swipes, likes_sent, super_likes_sent, likes_received,
             count(m) as total_matches
        
        RETURN total_swipes,
               likes_sent,
               super_likes_sent,
               likes_received,
               total_matches,
               CASE 
                   WHEN likes_sent > 0 THEN round(toFloat(total_matches) / likes_sent * 100, 1)
                   ELSE 0
               END as match_rate_percentage
        """
        
        result = tx.run(query, {'user_id': user_id})
        record = result.single()
        return record.data() if record else {}
    
    @staticmethod
    def get_popular_interests(tx, limit=10):
        """獲取熱門興趣"""
        query = """
        MATCH (u:User {dating_active: true})-[:INTERESTED_IN]->(i:Interest)
        
        RETURN i.name as interest,
               count(u) as user_count
        
        ORDER BY user_count DESC
        LIMIT $limit
        """
        
        result = tx.run(query, {'limit': limit})
        return [record.data() for record in result]
    
    @staticmethod
    def update_last_active(tx, user_id):
        """更新最後活躍時間"""
        query = """
        MATCH (u:User {user_id: $user_id})
        SET u.last_active = datetime()
        RETURN u.last_active as last_active
        """
        
        result = tx.run(query, {'user_id': user_id})
        return result.single()['last_active']

# 將查詢方法添加到 KnowledgeGraph 類別中
def extend_knowledge_graph_with_dating(knowledge_graph_class):
    """擴展 KnowledgeGraph 類別添加交友功能"""
    
    def create_dating_profile(self, profile):
        """創建交友檔案"""
        if not self.connected:
            return None
        
        with self.driver.session() as session:
            return session.execute_write(DatingQueries.create_dating_profile, profile)
    
    def get_dating_recommendations(self, user_id, limit=10, include_compatibility=True):
        """獲取交友推薦"""
        if not self.connected:
            return []
        
        with self.driver.session() as session:
            return session.execute_read(DatingQueries.get_dating_recommendations, user_id, limit)
    
    def record_swipe_action(self, user_id, target_user_id, action):
        """記錄滑動動作"""
        if not self.connected:
            return None
        
        with self.driver.session() as session:
            return session.execute_write(DatingQueries.record_swipe_action, user_id, target_user_id, action)
    
    def check_mutual_like(self, user_id, target_user_id):
        """檢查互相喜歡"""
        if not self.connected:
            return False
        
        with self.driver.session() as session:
            return session.execute_read(DatingQueries.check_mutual_like, user_id, target_user_id)
    
    def create_match(self, match):
        """創建配對"""
        if not self.connected:
            return None
        
        with self.driver.session() as session:
            return session.execute_write(DatingQueries.create_match, match)
    
    def get_user_matches(self, user_id):
        """獲取用戶配對"""
        if not self.connected:
            return []
        
        with self.driver.session() as session:
            return session.execute_read(DatingQueries.get_user_matches, user_id)
    
    def get_dating_insights(self, user_id):
        """獲取約會洞察"""
        if not self.connected:
            return {}
        
        with self.driver.session() as session:
            return session.execute_read(DatingQueries.get_dating_insights, user_id)
    
    # 動態添加方法到類別
    knowledge_graph_class.create_dating_profile = create_dating_profile
    knowledge_graph_class.get_dating_recommendations = get_dating_recommendations
    knowledge_graph_class.record_swipe_action = record_swipe_action
    knowledge_graph_class.check_mutual_like = check_mutual_like
    knowledge_graph_class.create_match = create_match
    knowledge_graph_class.get_user_matches = get_user_matches
    knowledge_graph_class.get_dating_insights = get_dating_insights
    
    return knowledge_graph_class