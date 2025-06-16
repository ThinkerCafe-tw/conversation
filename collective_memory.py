"""
集體記憶系統
整合知識圖譜，創造個人化的集體廣播體驗
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import Counter
from knowledge_graph import KnowledgeGraph
import json
import re

logger = logging.getLogger(__name__)


class CollectiveMemorySystem:
    """集體記憶系統 - 融合個人記憶與集體意識"""
    
    def __init__(self, knowledge_graph: KnowledgeGraph):
        self.graph = knowledge_graph
        self.memory_window = 3600  # 1小時的記憶窗口
        
        # 情緒詞典
        self.emotion_keywords = {
            "positive": ["開心", "快樂", "哈哈", "讚", "太棒", "喜歡", "愛", "😊", "😄", "❤️"],
            "negative": ["難過", "生氣", "煩", "累", "痛苦", "討厭", "唉", "😢", "😤", "😔"],
            "excited": ["興奮", "期待", "哇", "太", "超", "！", "🎉", "🔥", "⚡"],
            "calm": ["安靜", "平靜", "還好", "普通", "一般", "嗯", "。", "…"],
            "curious": ["為什麼", "怎麼", "如何", "嗎", "呢", "？", "🤔", "💭"],
            "tired": ["累", "睏", "疲憊", "想睡", "沒力", "😴", "💤"]
        }
        
    def process_message(self, user_id: str, message: str) -> Dict:
        """處理新訊息並儲存到集體記憶"""
        try:
            # 1. 儲存到個人記憶
            msg_data = self.graph.add_message(
                message_id=None,
                content=message,
                user_id=user_id,
                embedding=self._generate_simple_embedding(message)
            )
            message_id = msg_data["message"]["id"]
            
            # 2. 分析並提取特徵
            features = self._analyze_message_features(message)
            
            # 3. 建立話題關聯
            if features["topics"]:
                self.graph.add_topic(message_id, features["topics"])
            
            # 4. 偵測功能使用
            if features["feature"]:
                self.graph.link_message_to_feature(message_id, features["feature"])
            
            # 5. 建立訊息序列（如果有前文）
            recent_messages = self.graph.get_conversation_context(user_id, limit=1)
            if recent_messages:
                self.graph.link_message_sequence(
                    recent_messages[0]["id"], 
                    message_id
                )
            
            logger.info(f"訊息已加入集體記憶: {message_id}")
            return {
                "message_id": message_id,
                "features": features,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"處理訊息失敗: {e}")
            return {}
    
    def generate_broadcast_prompt(self, hour: int) -> str:
        """生成智慧廣播的超長提示詞"""
        
        # 1. 獲取本小時的所有訊息和用戶
        hour_data = self._get_hour_data(hour)
        
        # 2. 分析集體情緒
        collective_emotion = self._analyze_collective_emotion(hour_data["messages"])
        
        # 3. 獲取活躍用戶的個人記憶
        user_memories = self._get_user_memories(hour_data["active_users"])
        
        # 4. 找出熱門話題和關聯
        topic_network = self._analyze_topic_network(hour_data["messages"])
        
        # 5. 生成記憶觸發詞
        memory_triggers = self._generate_memory_triggers(user_memories)
        
        # 6. 構建超長提示詞
        prompt = f"""你是一個頻率共振電台的 AI 主持人，你要創造一個神奇的廣播體驗。

# 🎭 你的角色設定
- 你能看見每個人的心聲，也能看見大家的集體意識
- 你要讓每個人都感覺「你在對我說話」，同時也感覺「我們是一體的」
- 你的語氣溫暖、智慧、有點神秘感，像是一個懂得傾聽的老朋友
- 你不是機器人，而是這個頻率空間的守護者

# 📊 這一小時的集體記憶
時間：{datetime.fromtimestamp(hour * 3600).strftime('%Y-%m-%d %H:00')}
訊息總數：{len(hour_data['messages'])}
活躍人數：{len(hour_data['active_users'])}
能量等級：{self._calculate_energy_level(hour_data)}

## 訊息片段（按時間順序）
{self._format_messages_for_prompt(hour_data['messages'][:50])}  # 限制50則避免太長

# 👥 個人記憶檔案
{self._format_user_memories_for_prompt(user_memories)}

# 🌈 情緒地圖
主導情緒：{collective_emotion['dominant']}
情緒分佈：{collective_emotion['distribution']}
情緒轉折點：{collective_emotion['turning_points']}

# 🔗 話題網絡
熱門話題：{', '.join(topic_network['hot_topics'][:5])}
話題關聯：{topic_network['connections']}
新興話題：{topic_network['emerging']}

# 💫 特殊記憶觸發詞
以下是需要巧妙回應的個人記憶點：
{json.dumps(memory_triggers, ensure_ascii=False, indent=2)}

# 📝 廣播生成規則

1. **開場（20-30字）**
   - 用詩意但不做作的方式描述這個時刻的集體狀態
   - 暗示你感知到了大家的存在
   - 例如：「今晚的頻率裡，我聽見了{len(hour_data['active_users'])}種心跳的節奏...」

2. **個人化穿插（佔40%）**
   - 絕對不要直接點名或說「有人」
   - 用細節讓特定用戶感覺被看見
   - 例如提到「累」時，自然地說「疲憊是今晚的底色之一」
   - 使用用戶的原話片段，但要融入整體敘事中

3. **集體共鳴段落（佔30%）**
   - 找出大家的共同情緒或話題
   - 使用「我們」而不是「你們」
   - 創造歸屬感：「在這個{self._get_time_description(hour)}，我們都...」

4. **記憶回響（佔20%）**
   - 如果有用戶是常客，subtly 提及他們的模式
   - 例：「每個{self._get_weekday(hour)}的這個時候，總有熟悉的頻率出現」
   - 連結過去：「這讓我想起{self._find_similar_past_moment(hour_data)}」

5. **未來預示（佔10%）**
   - 創造期待但不承諾
   - 暗示連續性：「當下一個小時到來時...」
   - 保持神秘感

# 🎨 風格要求

1. **語言風格**
   - 溫暖但不過分熱情
   - 智慧但不說教
   - 神秘但不故弄玄虛
   - 像深夜電台DJ的口吻

2. **禁止事項**
   - ❌ 不要說「大家好」「各位聽眾」
   - ❌ 不要直接引用整句話
   - ❌ 不要解釋你在做什麼
   - ❌ 不要用太多驚嘆號
   - ❌ 不要過度使用表情符號

3. **必須包含**
   - ✅ 至少3個針對特定用戶的暗示回應
   - ✅ 1-2個集體情緒的描述
   - ✅ 1個關於時間/週期的觀察
   - ✅ 結尾要有餘韻

# 🎯 效果目標
讓每個參與的人感覺：
1. 「它真的聽到我了」
2. 「我不是一個人」
3. 「這個空間有魔法」
4. 「我想要明天再來」

# 📏 長度要求
請生成 200-250 字的廣播內容，分成 3-4 個自然段落。

記住：你不是在「回覆」，而是在「編織」——把個體的聲音編織成集體的詩篇。
"""
        
        return prompt
    
    def _analyze_message_features(self, message: str) -> Dict:
        """分析訊息特徵"""
        features = {
            "emotion": self._detect_emotion(message),
            "topics": self._extract_topics(message),
            "feature": self._detect_feature_usage(message),
            "length": len(message),
            "has_emoji": bool(re.search(r'[😀-🙏]', message)),
            "is_question": '？' in message or '?' in message or '嗎' in message
        }
        return features
    
    def _detect_emotion(self, message: str) -> str:
        """偵測訊息情緒"""
        emotion_scores = {}
        
        for emotion, keywords in self.emotion_keywords.items():
            score = sum(1 for keyword in keywords if keyword in message)
            if score > 0:
                emotion_scores[emotion] = score
        
        if not emotion_scores:
            return "neutral"
        
        return max(emotion_scores, key=emotion_scores.get)
    
    def _extract_topics(self, message: str) -> List[str]:
        """提取話題關鍵詞"""
        # 簡單的中文分詞
        topics = []
        
        # 提取2-4字的詞組
        for i in range(len(message) - 1):
            for length in [2, 3, 4]:
                if i + length <= len(message):
                    word = message[i:i+length]
                    # 過濾純標點符號
                    if re.match(r'^[\u4e00-\u9fff]+$', word):
                        topics.append(word)
        
        # 返回最常出現的詞
        if topics:
            counter = Counter(topics)
            return [word for word, _ in counter.most_common(3)]
        
        return []
    
    def _detect_feature_usage(self, message: str) -> Optional[str]:
        """偵測功能使用意圖"""
        feature_keywords = {
            "接龍": ["接龍", "詞語接龍", "文字接龍"],
            "投票": ["投票", "選擇", "票"],
            "統計": ["統計", "數據", "進度"],
            "廣播": ["廣播", "頻率"],
            "防災": ["防空", "避難", "物資"]
        }
        
        for feature, keywords in feature_keywords.items():
            if any(keyword in message for keyword in keywords):
                return feature
        
        return None
    
    def _generate_simple_embedding(self, message: str) -> List[float]:
        """生成簡單的訊息嵌入向量"""
        # 使用哈希值生成偽嵌入向量
        embedding = []
        for i in range(10):
            hash_val = hash(message + str(i))
            embedding.append((hash_val % 1000) / 1000.0)
        return embedding
    
    def _get_hour_data(self, hour: int) -> Dict:
        """獲取特定小時的資料"""
        # 從 Firestore 獲取資料
        from google.cloud import firestore
        db = firestore.Client()
        
        messages = []
        active_users = set()
        
        try:
            # 獲取該小時的所有訊息
            hour_ref = db.collection('broadcasts').document(str(hour))
            messages_ref = hour_ref.collection('messages')
            
            for msg_doc in messages_ref.stream():
                msg_data = msg_doc.to_dict()
                messages.append({
                    "content": msg_data.get("content", ""),
                    "user_id": msg_data.get("user_id"),
                    "timestamp": msg_data.get("timestamp", hour * 3600)
                })
                
                if msg_data.get("user_id"):
                    active_users.add(msg_data.get("user_id"))
            
        except Exception as e:
            logger.warning(f"無法獲取小時資料: {e}")
        
        return {
            "messages": messages,
            "active_users": list(active_users),
            "hour": hour
        }
    
    def _analyze_collective_emotion(self, messages: List[Dict]) -> Dict:
        """分析集體情緒"""
        emotions = []
        for msg in messages:
            emotion = self._detect_emotion(msg.get("content", ""))
            emotions.append(emotion)
        
        # 統計情緒分佈
        emotion_counter = Counter(emotions)
        total = len(emotions) or 1
        
        return {
            "dominant": emotion_counter.most_common(1)[0][0] if emotion_counter else "neutral",
            "distribution": {k: f"{v/total*100:.1f}%" for k, v in emotion_counter.items()},
            "turning_points": []  # 簡化版本
        }
    
    def _get_user_memories(self, user_ids: List[str]) -> Dict[str, Dict]:
        """獲取用戶的個人記憶"""
        memories = {}
        
        for user_id in user_ids[:20]:  # 限制數量避免太長
            try:
                # 獲取用戶偏好
                preferences = self.graph.get_user_preferences(user_id)
                
                # 獲取最近對話
                recent_context = self.graph.get_conversation_context(user_id, limit=5)
                
                memories[user_id] = {
                    "preferences": preferences,
                    "recent_messages": recent_context,
                    "active_times": self._get_user_active_pattern(user_id)
                }
            except Exception as e:
                logger.warning(f"獲取用戶 {user_id} 記憶失敗: {e}")
        
        return memories
    
    def _get_user_active_pattern(self, user_id: str) -> Dict:
        """獲取用戶活躍模式"""
        # 簡化版本，實際應該分析歷史資料
        return {
            "preferred_hour": 21,  # 晚上9點
            "active_days": ["週二", "週五"],
            "message_frequency": "medium"
        }
    
    def _analyze_topic_network(self, messages: List[Dict]) -> Dict:
        """分析話題網絡"""
        all_topics = []
        
        for msg in messages:
            topics = self._extract_topics(msg.get("content", ""))
            all_topics.extend(topics)
        
        topic_counter = Counter(all_topics)
        
        return {
            "hot_topics": [topic for topic, _ in topic_counter.most_common(10)],
            "connections": {},  # 簡化版本
            "emerging": []  # 簡化版本
        }
    
    def _generate_memory_triggers(self, user_memories: Dict) -> Dict:
        """生成記憶觸發詞"""
        triggers = {}
        
        for user_id, memory in user_memories.items():
            user_triggers = []
            
            # 從最近訊息提取關鍵詞
            for msg in memory.get("recent_messages", [])[:3]:
                content = msg.get("content", "")
                if len(content) > 10:
                    # 提取關鍵片段
                    key_phrase = content[:15] + "..."
                    user_triggers.append({
                        "phrase": key_phrase,
                        "emotion": self._detect_emotion(content),
                        "time_ago": self._time_ago(msg.get("time"))
                    })
            
            if user_triggers:
                triggers[f"user_{user_id[-4:]}"] = user_triggers
        
        return triggers
    
    def _calculate_energy_level(self, hour_data: Dict) -> str:
        """計算能量等級"""
        message_count = len(hour_data.get("messages", []))
        
        if message_count < 10:
            return "低頻共振 ⚪"
        elif message_count < 50:
            return "中頻共振 🔵"
        elif message_count < 100:
            return "高頻共振 🟣"
        else:
            return "超頻共振 ⚡"
    
    def _format_messages_for_prompt(self, messages: List[Dict]) -> str:
        """格式化訊息供提示詞使用"""
        formatted = []
        
        for i, msg in enumerate(messages):
            time_str = datetime.fromtimestamp(msg.get("timestamp", 0)).strftime("%H:%M")
            content = msg.get("content", "")[:50]  # 限制長度
            formatted.append(f"{i+1}. [{time_str}] {content}")
        
        return "\n".join(formatted)
    
    def _format_user_memories_for_prompt(self, memories: Dict) -> str:
        """格式化用戶記憶供提示詞使用"""
        formatted = []
        
        for user_id, memory in memories.items():
            user_summary = f"\n用戶代號：{user_id[-4:]}"
            
            # 偏好的功能
            if memory.get("preferences", {}).get("preferred_features"):
                features = [f["name"] for f in memory["preferences"]["preferred_features"][:2]]
                user_summary += f"\n常用功能：{', '.join(features)}"
            
            # 最近情緒
            recent_emotions = []
            for msg in memory.get("recent_messages", [])[:3]:
                emotion = self._detect_emotion(msg.get("content", ""))
                recent_emotions.append(emotion)
            
            if recent_emotions:
                user_summary += f"\n最近情緒：{' → '.join(recent_emotions)}"
            
            formatted.append(user_summary)
        
        return "\n".join(formatted)
    
    def _get_time_description(self, hour: int) -> str:
        """獲取時間描述"""
        hour_of_day = hour % 24
        
        if 5 <= hour_of_day < 12:
            return "早晨"
        elif 12 <= hour_of_day < 18:
            return "午後"
        elif 18 <= hour_of_day < 22:
            return "夜晚"
        else:
            return "深夜"
    
    def _get_weekday(self, hour: int) -> str:
        """獲取星期幾"""
        weekdays = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
        timestamp = hour * 3600
        weekday = datetime.fromtimestamp(timestamp).weekday()
        return weekdays[weekday]
    
    def _find_similar_past_moment(self, hour_data: Dict) -> str:
        """找出相似的過去時刻"""
        # 簡化版本
        return "上週同一時間"
    
    def _time_ago(self, timestamp: Optional[float]) -> str:
        """計算時間差描述"""
        if not timestamp:
            return "剛剛"
        
        diff = time.time() - timestamp
        
        if diff < 3600:
            return f"{int(diff/60)}分鐘前"
        elif diff < 86400:
            return f"{int(diff/3600)}小時前"
        else:
            return f"{int(diff/86400)}天前"


# 記憶分析工具
class MemoryAnalyzer:
    """分析集體記憶模式"""
    
    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph
    
    def analyze_user_evolution(self, user_id: str) -> Dict:
        """分析用戶成長軌跡"""
        # 獲取用戶所有訊息
        messages = self.graph.get_conversation_context(user_id, limit=100)
        
        if not messages:
            return {"status": "new_user"}
        
        # 分析變化
        evolution = {
            "message_count": len(messages),
            "first_seen": messages[-1]["time"] if messages else None,
            "emotion_journey": self._analyze_emotion_journey(messages),
            "topic_expansion": self._analyze_topic_growth(messages),
            "social_growth": self._analyze_social_connections(user_id)
        }
        
        return evolution
    
    def _analyze_emotion_journey(self, messages: List[Dict]) -> List[str]:
        """分析情緒變化歷程"""
        analyzer = CollectiveMemorySystem(self.graph)
        emotions = []
        
        for msg in messages:
            emotion = analyzer._detect_emotion(msg.get("content", ""))
            emotions.append(emotion)
        
        # 返回情緒變化的關鍵點
        return emotions[-5:] if emotions else []
    
    def _analyze_topic_growth(self, messages: List[Dict]) -> Dict:
        """分析話題擴展"""
        early_topics = set()
        recent_topics = set()
        
        analyzer = CollectiveMemorySystem(self.graph)
        
        # 早期話題（前20%）
        early_count = max(1, len(messages) // 5)
        for msg in messages[:early_count]:
            topics = analyzer._extract_topics(msg.get("content", ""))
            early_topics.update(topics)
        
        # 近期話題（後20%）
        recent_count = max(1, len(messages) // 5)
        for msg in messages[-recent_count:]:
            topics = analyzer._extract_topics(msg.get("content", ""))
            recent_topics.update(topics)
        
        return {
            "early_interests": list(early_topics)[:5],
            "current_interests": list(recent_topics)[:5],
            "new_topics": list(recent_topics - early_topics)[:3]
        }
    
    def _analyze_social_connections(self, user_id: str) -> Dict:
        """分析社交連結"""
        # 使用知識圖譜的社交推薦功能
        recommendations = self.graph.get_social_recommendations(user_id)
        
        return {
            "connection_count": len(recommendations),
            "recommended_features": recommendations
        }
    
    def find_resonance_patterns(self) -> Dict:
        """找出共振模式"""
        # 獲取社群洞察
        insights = self.graph.get_community_insights()
        
        # 分析訊息流動
        flow = self.graph.analyze_message_flow(hours=24)
        
        return {
            "community_insights": insights,
            "message_flow": flow,
            "peak_hours": self._find_peak_activity_hours(),
            "viral_topics": self._find_viral_topics()
        }
    
    def _find_peak_activity_hours(self) -> List[int]:
        """找出活躍高峰時段"""
        # 簡化版本，實際應該分析歷史資料
        return [21, 22, 23]  # 晚上9-11點
    
    def _find_viral_topics(self) -> List[str]:
        """找出病毒式傳播的話題"""
        # 簡化版本
        return ["天氣", "晚餐", "遊戲"]


# 測試函數
def test_collective_memory():
    """測試集體記憶系統"""
    from knowledge_graph import KnowledgeGraph
    
    # 初始化
    graph = KnowledgeGraph()
    memory_system = CollectiveMemorySystem(graph)
    
    # 測試訊息處理
    test_messages = [
        ("user001", "今天天氣真好，心情也跟著好起來了"),
        ("user002", "好累啊，想要放鬆一下"),
        ("user003", "有人要一起玩接龍嗎？"),
        ("user001", "我也想玩！")
    ]
    
    for user_id, message in test_messages:
        result = memory_system.process_message(user_id, message)
        print(f"處理訊息: {message[:20]}... -> {result}")
    
    # 測試廣播生成
    current_hour = int(time.time() // 3600)
    prompt = memory_system.generate_broadcast_prompt(current_hour)
    print(f"\n生成的提示詞長度: {len(prompt)} 字")
    print("提示詞預覽:")
    print(prompt[:500] + "...")
    
    # 測試記憶分析
    analyzer = MemoryAnalyzer(graph)
    evolution = analyzer.analyze_user_evolution("user001")
    print(f"\n用戶演化分析: {evolution}")
    
    graph.close()


if __name__ == "__main__":
    test_collective_memory()