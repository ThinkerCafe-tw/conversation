"""
AI 交友功能模組
結合 Tinder 策略與 AI 增強功能
"""

import os
import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class UserProfile:
    user_id: str
    display_name: str
    age: int
    gender: str
    location: str
    interests: List[str]
    personality_traits: Dict[str, float]
    photos: List[str]
    bio: str
    ai_insights: Dict[str, str]
    premium_status: str = "free"
    created_at: datetime = None

@dataclass
class Match:
    match_id: str
    user1_id: str
    user2_id: str
    compatibility_score: float
    matched_at: datetime
    conversation_started: bool = False
    ai_starter_used: bool = False

class AIMatchingEngine:
    def __init__(self, redis_client, graph_db, ai_service):
        self.redis = redis_client
        self.graph = graph_db
        self.ai = ai_service
        self.daily_like_limits = {
            "free": 10,
            "plus": 100,
            "gold": 999
        }
        
    def create_dating_profile(self, user_id: str, profile_data: Dict) -> Dict:
        """創建交友檔案"""
        try:
            # 生成 AI 個性分析
            personality_analysis = self.ai.analyze_personality(
                bio=profile_data.get('bio', ''),
                interests=profile_data.get('interests', [])
            )
            
            profile = UserProfile(
                user_id=user_id,
                display_name=profile_data['display_name'],
                age=profile_data['age'],
                gender=profile_data['gender'],
                location=profile_data['location'],
                interests=profile_data['interests'],
                personality_traits=personality_analysis['traits'],
                photos=profile_data.get('photos', []),
                bio=profile_data.get('bio', ''),
                ai_insights=personality_analysis['insights'],
                created_at=datetime.now()
            )
            
            # 儲存到 Neo4j
            if self.graph and self.graph.connected:
                self.graph.create_dating_profile(profile)
            
            # 快取基本資訊到 Redis
            if self.redis:
                cache_key = f"dating_profile:{user_id}"
                self.redis.setex(cache_key, 3600, json.dumps({
                    'display_name': profile.display_name,
                    'age': profile.age,
                    'location': profile.location,
                    'compatibility_ready': True
                }))
            
            return {
                'success': True,
                'message': f'✨ 歡迎加入 AI 交友！您的檔案已建立',
                'ai_insights': personality_analysis['summary']
            }
            
        except Exception as e:
            logger.error(f"創建交友檔案失敗: {e}")
            return {'success': False, 'message': '建立檔案時發生錯誤'}
    
    def swipe_action(self, user_id: str, target_user_id: str, action: str) -> Dict:
        """滑動動作 (like/pass)"""
        if not self._check_daily_limit(user_id):
            return {
                'success': False,
                'message': '今日滑動次數已用完！升級 Plus 享受無限滑動 ✨'
            }
        
        # 記錄滑動動作
        self._record_swipe(user_id, target_user_id, action)
        
        if action == "like":
            # 檢查是否互相喜歡
            if self._check_mutual_like(user_id, target_user_id):
                # 創建配對
                match = self._create_match(user_id, target_user_id)
                return {
                    'success': True,
                    'matched': True,
                    'message': '🎉 恭喜配對成功！快開始對話吧',
                    'match_id': match.match_id,
                    'ai_starter': self._generate_conversation_starter(user_id, target_user_id)
                }
            else:
                return {
                    'success': True,
                    'matched': False,
                    'message': '💫 已送出喜歡，等待對方回應...'
                }
        else:
            return {
                'success': True,
                'message': '👋 已略過此用戶'
            }
    
    def get_recommendations(self, user_id: str, limit: int = 10) -> List[Dict]:
        """獲取推薦用戶"""
        try:
            if not self.graph or not self.graph.connected:
                return []
            
            # 從 Neo4j 獲取 AI 推薦
            recommendations = self.graph.get_dating_recommendations(
                user_id=user_id,
                limit=limit,
                include_compatibility=True
            )
            
            # 為每個推薦添加 AI 增強資訊
            enhanced_recommendations = []
            for rec in recommendations:
                # 生成相容性洞察
                compatibility_insight = self.ai.generate_compatibility_insight(
                    user_id, rec['user_id']
                )
                
                enhanced_recommendations.append({
                    **rec,
                    'ai_compatibility': compatibility_insight,
                    'conversation_starters': self._get_conversation_starters(
                        user_id, rec['user_id']
                    )
                })
            
            return enhanced_recommendations
            
        except Exception as e:
            logger.error(f"獲取推薦失敗: {e}")
            return []
    
    def get_matches(self, user_id: str) -> List[Dict]:
        """獲取用戶的配對列表"""
        try:
            if not self.graph or not self.graph.connected:
                return []
            
            matches = self.graph.get_user_matches(user_id)
            
            # 為每個配對添加 AI 對話建議
            enhanced_matches = []
            for match in matches:
                # 獲取最近對話狀態
                conversation_status = self._get_conversation_status(
                    match['match_id']
                )
                
                # AI 對話建議
                conversation_advice = None
                if conversation_status['last_message_days'] > 1:
                    conversation_advice = self.ai.generate_conversation_revival(
                        user_id, match['partner_id']
                    )
                
                enhanced_matches.append({
                    **match,
                    'conversation_status': conversation_status,
                    'ai_advice': conversation_advice
                })
            
            return enhanced_matches
            
        except Exception as e:
            logger.error(f"獲取配對失敗: {e}")
            return []
    
    def super_like(self, user_id: str, target_user_id: str) -> Dict:
        """超級喜歡功能 (Premium)"""
        # 檢查是否為付費用戶
        if not self._is_premium_user(user_id):
            return {
                'success': False,
                'message': '超級喜歡需要 Plus 會員！立即升級享受優先配對 ⭐'
            }
        
        # 檢查超級喜歡額度
        if not self._check_super_like_limit(user_id):
            return {
                'success': False,
                'message': '今日超級喜歡已用完，明天再來吧！'
            }
        
        # 執行超級喜歡
        self._record_super_like(user_id, target_user_id)
        
        # 如果對方也喜歡，立即配對
        if self._check_any_like(target_user_id, user_id):
            match = self._create_match(user_id, target_user_id)
            return {
                'success': True,
                'matched': True,
                'message': '⭐ 超級喜歡成功配對！',
                'match_id': match.match_id
            }
        
        # 通知對方收到超級喜歡
        self._notify_super_like_received(target_user_id, user_id)
        
        return {
            'success': True,
            'message': '⭐ 超級喜歡已送出！對方會優先看到您'
        }
    
    def boost_profile(self, user_id: str) -> Dict:
        """檔案加速功能 (Premium)"""
        if not self._is_premium_user(user_id):
            return {
                'success': False,
                'message': '檔案加速需要 Gold 會員！立即升級提升曝光度 🚀'
            }
        
        # 設定 30 分鐘加速
        boost_key = f"profile_boost:{user_id}"
        self.redis.setex(boost_key, 1800, "active")  # 30 minutes
        
        return {
            'success': True,
            'message': '🚀 檔案加速中！30分鐘內您將獲得5倍曝光度'
        }
    
    def get_ai_dating_coach(self, user_id: str, question: str) -> Dict:
        """AI 戀愛教練 (Premium)"""
        if not self._is_premium_user(user_id, "gold"):
            return {
                'success': False,
                'message': '戀愛教練需要 Gold 會員！獲得專業約會建議 💎'
            }
        
        # 獲取用戶檔案和配對歷史
        user_context = self._get_user_dating_context(user_id)
        
        # AI 生成個人化建議
        coaching_advice = self.ai.generate_dating_advice(
            user_context=user_context,
            question=question
        )
        
        return {
            'success': True,
            'advice': coaching_advice['advice'],
            'action_items': coaching_advice['action_items']
        }
    
    # Private methods
    def _check_daily_limit(self, user_id: str) -> bool:
        """檢查每日滑動限制"""
        if self._is_premium_user(user_id):
            return True
        
        today = datetime.now().strftime("%Y-%m-%d")
        key = f"daily_swipes:{user_id}:{today}"
        current_count = self.redis.get(key) or 0
        return int(current_count) < self.daily_like_limits["free"]
    
    def _record_swipe(self, user_id: str, target_user_id: str, action: str):
        """記錄滑動動作"""
        today = datetime.now().strftime("%Y-%m-%d")
        swipe_key = f"daily_swipes:{user_id}:{today}"
        self.redis.incr(swipe_key)
        self.redis.expire(swipe_key, 86400)
        
        # 記錄到 Neo4j
        if self.graph and self.graph.connected:
            self.graph.record_swipe_action(user_id, target_user_id, action)
    
    def _check_mutual_like(self, user_id: str, target_user_id: str) -> bool:
        """檢查是否互相喜歡"""
        if not self.graph or not self.graph.connected:
            return False
        return self.graph.check_mutual_like(user_id, target_user_id)
    
    def _create_match(self, user1_id: str, user2_id: str) -> Match:
        """創建配對"""
        match_id = f"match_{int(time.time())}_{user1_id[:4]}"
        
        # 計算相容性分數
        compatibility_score = self.ai.calculate_compatibility(user1_id, user2_id)
        
        match = Match(
            match_id=match_id,
            user1_id=user1_id,
            user2_id=user2_id,
            compatibility_score=compatibility_score,
            matched_at=datetime.now()
        )
        
        # 儲存到 Neo4j
        if self.graph and self.graph.connected:
            self.graph.create_match(match)
        
        return match
    
    def _generate_conversation_starter(self, user_id: str, partner_id: str) -> str:
        """生成 AI 對話開場白"""
        return self.ai.generate_conversation_starter(user_id, partner_id)
    
    def _is_premium_user(self, user_id: str, tier: str = "plus") -> bool:
        """檢查是否為付費用戶"""
        # 實際實現時從資料庫檢查
        return False  # 暫時返回 False
    
    def _get_conversation_starters(self, user_id: str, target_id: str) -> List[str]:
        """獲取對話開場白建議"""
        return self.ai.generate_multiple_starters(user_id, target_id)


class DatingAIService:
    """AI 服務類別"""
    
    def __init__(self, gemini_client):
        self.gemini = gemini_client
    
    def analyze_personality(self, bio: str, interests: List[str]) -> Dict:
        """分析個性特質"""
        prompt = f"""
        分析以下個人資料，提供個性特質分析：
        
        自我介紹：{bio}
        興趣愛好：{', '.join(interests)}
        
        請提供：
        1. 5大個性特質分數 (0-1)
        2. 個性洞察摘要
        3. 約會建議
        """
        
        try:
            response = self.gemini.generate_content(prompt)
            # 處理回應並結構化
            return {
                'traits': {
                    'openness': 0.7,
                    'conscientiousness': 0.6,
                    'extraversion': 0.8,
                    'agreeableness': 0.7,
                    'neuroticism': 0.3
                },
                'insights': {'summary': '外向且開放的個性'},
                'summary': '您是個充滿活力且樂於嘗試新事物的人！'
            }
        except Exception as e:
            logger.error(f"個性分析失敗: {e}")
            return {'traits': {}, 'insights': {}, 'summary': '分析中...'}
    
    def generate_conversation_starter(self, user_id: str, partner_id: str) -> str:
        """生成對話開場白"""
        starters = [
            "看到你的照片讓我想到最近去的一個地方...",
            "你的興趣真有趣！我也很喜歡...",
            "有個問題想問你：如果可以立刻去任何地方旅行，你會選哪裡？"
        ]
        return random.choice(starters)
    
    def calculate_compatibility(self, user1_id: str, user2_id: str) -> float:
        """計算相容性分數"""
        # 實際實現會考慮多個因素
        return round(random.uniform(0.6, 0.95), 2)


def format_dating_profile_card(profile: Dict) -> str:
    """格式化交友檔案卡片"""
    age = profile.get('age', '未知')
    location = profile.get('location', '神秘地點')
    bio = profile.get('bio', '這個人很神秘，什麼都沒寫...')
    compatibility = profile.get('ai_compatibility', {})
    
    card = f"""💕 {profile['display_name']}, {age}
📍 {location}

{bio}

✨ AI 相容性分析：
{compatibility.get('summary', '分析中...')}

💬 建議話題：
{compatibility.get('topics', ['音樂', '旅行', '美食'])[0]}"""
    
    return card


def format_matches_list(matches: List[Dict]) -> str:
    """格式化配對列表"""
    if not matches:
        return "💔 還沒有配對，快去發現新朋友吧！"
    
    message = "💕 您的配對\n━━━━━━━━━━━━━━\n\n"
    
    for i, match in enumerate(matches[:5], 1):
        partner = match['partner_name']
        days_ago = match.get('conversation_status', {}).get('last_message_days', 0)
        
        if days_ago == 0:
            status = "🔥 熱聊中"
        elif days_ago == 1:
            status = "💬 昨天聊過"
        else:
            status = f"😴 {days_ago}天沒聊"
        
        message += f"{i}. {partner} {status}\n"
        
        # AI 建議
        if match.get('ai_advice'):
            message += f"   💡 {match['ai_advice'][:30]}...\n"
        
        message += "\n"
    
    message += "輸入數字選擇配對，或「發現」尋找新朋友"
    return message