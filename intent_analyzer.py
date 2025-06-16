"""
意圖分析模組
使用知識圖譜和語義分析理解用戶意圖
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from knowledge_graph import KnowledgeGraph
import jieba
import re

# 嘗試導入 sentence_transformers，如果失敗則使用簡化版本
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    SENTENCE_TRANSFORMER_AVAILABLE = True
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("SentenceTransformer not available, using simplified intent analysis")
    SENTENCE_TRANSFORMER_AVAILABLE = False

logger = logging.getLogger(__name__)


class IntentAnalyzer:
    def __init__(self, graph: KnowledgeGraph = None):
        """初始化意圖分析器"""
        self.graph = graph or KnowledgeGraph()
        
        # 初始化句子嵌入模型（如果可用）
        if SENTENCE_TRANSFORMER_AVAILABLE:
            model_name = os.getenv('SENTENCE_TRANSFORMER_MODEL', 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
            logger.info(f"載入語義模型: {model_name}")
            self.embedder = SentenceTransformer(model_name)
        else:
            logger.info("使用簡化的意圖分析（無語義嵌入）")
            self.embedder = None
        
        # 初始化中文分詞
        jieba.setLogLevel(logging.WARNING)
        
        # 功能關鍵詞映射
        self.feature_keywords = {
            "接龍": ["接龍", "文字接龍", "詞語接龍", "玩接龍"],
            "投票": ["投票", "表決", "選擇", "票選", "選舉"],
            "統計": ["統計", "查看統計", "進度", "排行", "數據"],
            "廣播": ["廣播", "頻率", "查看廣播", "最新廣播"],
            "防空": ["防空", "避難", "避難所", "防災", "躲避"],
            "物資": ["物資", "補給", "用品", "援助", "分享"],
            "API統計": ["API", "用量", "使用量", "API統計"],
            "幫助": ["幫助", "help", "說明", "怎麼用", "教學"]
        }
        
        # 意圖模式
        self.intent_patterns = {
            "查詢": ["查看", "查詢", "看看", "顯示", "告訴我"],
            "開始": ["開始", "啟動", "發起", "玩", "來"],
            "參與": ["參加", "加入", "我要", "一起"],
            "分享": ["分享", "提供", "給", "有"],
            "結束": ["結束", "停止", "不玩了"]
        }
        
    def analyze(self, message: str, user_id: str, context: List[Dict] = None) -> Dict:
        """分析用戶意圖"""
        try:
            # 1. 基礎文本處理
            cleaned_message = self._preprocess_text(message)
            
            # 2. 生成語義嵌入（如果可用）
            if self.embedder:
                embedding = self.embedder.encode(message).tolist()
            else:
                # 使用簡單的哈希值作為替代
                embedding = [float(hash(message + str(i)) % 1000) / 1000 for i in range(10)]
            
            # 3. 提取關鍵詞和實體
            keywords = self._extract_keywords(cleaned_message)
            entities = self._extract_entities(cleaned_message)
            
            # 4. 規則基礎匹配（快速路徑）
            direct_match = self._match_feature_keywords(cleaned_message)
            if direct_match:
                logger.info(f"直接匹配到功能: {direct_match}")
                return {
                    "intent": "use_feature",
                    "feature": direct_match,
                    "confidence": 0.95,
                    "entities": entities,
                    "embedding": embedding
                }
            
            # 5. 圖資料庫查詢相似意圖
            similar_intents = self.graph.find_similar_intents(user_id, embedding)
            
            # 6. 獲取用戶偏好
            user_preferences = self.graph.get_user_preferences(user_id)
            
            # 7. 分析上下文
            context_features = self._analyze_context(context) if context else []
            
            # 8. 綜合判斷意圖
            intent_result = self._determine_intent(
                message=cleaned_message,
                keywords=keywords,
                entities=entities,
                similar_intents=similar_intents,
                user_preferences=user_preferences,
                context_features=context_features,
                embedding=embedding
            )
            
            # 9. 儲存到知識圖譜
            if intent_result["confidence"] > 0.7:
                message_id = self._save_to_graph(
                    message=message,
                    user_id=user_id,
                    intent_result=intent_result,
                    embedding=embedding
                )
                intent_result["message_id"] = message_id
            
            return intent_result
            
        except Exception as e:
            logger.error(f"意圖分析失敗: {e}")
            return {
                "intent": "unknown",
                "confidence": 0,
                "error": str(e)
            }
    
    def _preprocess_text(self, text: str) -> str:
        """預處理文本"""
        # 移除多餘空白
        text = " ".join(text.split())
        # 轉小寫（保留中文）
        text = text.lower()
        # 移除特殊符號但保留中文標點
        text = re.sub(r'[^\w\s\u4e00-\u9fff，。！？、]', ' ', text)
        return text.strip()
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取關鍵詞"""
        # 使用 jieba 分詞
        words = jieba.lcut(text)
        # 過濾停用詞（簡單版本）
        stopwords = {"的", "了", "是", "在", "我", "你", "他", "她", "它", "們", "這", "那", "有", "和", "與"}
        keywords = [w for w in words if len(w) > 1 and w not in stopwords]
        return keywords
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """提取實體（簡化版）"""
        entities = {
            "numbers": [],
            "locations": [],
            "time": []
        }
        
        # 提取數字
        numbers = re.findall(r'\d+', text)
        entities["numbers"] = numbers
        
        # 簡單的地點識別（包含「區」「路」「站」的詞）
        location_patterns = [r'\w+區', r'\w+路', r'\w+站', r'\w+里']
        for pattern in location_patterns:
            locations = re.findall(pattern, text)
            entities["locations"].extend(locations)
        
        # 時間識別
        time_patterns = [r'\d+[點時分秒]', r'早上|下午|晚上|凌晨', r'今天|明天|昨天']
        for pattern in time_patterns:
            times = re.findall(pattern, text)
            entities["time"].extend(times)
        
        return entities
    
    def _match_feature_keywords(self, text: str) -> Optional[str]:
        """匹配功能關鍵詞"""
        for feature, keywords in self.feature_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return feature
        return None
    
    def _analyze_context(self, context: List[Dict]) -> List[str]:
        """分析上下文獲取相關功能"""
        features = []
        for msg in context[-5:]:  # 只看最近5條
            content = msg.get("content", "")
            matched_feature = self._match_feature_keywords(content)
            if matched_feature:
                features.append(matched_feature)
        return features
    
    def _determine_intent(self, **kwargs) -> Dict:
        """綜合判斷用戶意圖"""
        message = kwargs.get("message", "")
        keywords = kwargs.get("keywords", [])
        entities = kwargs.get("entities", {})
        similar_intents = kwargs.get("similar_intents", [])
        user_preferences = kwargs.get("user_preferences", {})
        context_features = kwargs.get("context_features", [])
        embedding = kwargs.get("embedding", [])
        
        # 1. 檢查是否為數字（投票）
        if message.isdigit():
            return {
                "intent": "vote",
                "feature": "投票",
                "option": int(message),
                "confidence": 0.99,
                "entities": entities,
                "embedding": embedding
            }
        
        # 2. 檢查意圖模式
        detected_intent = None
        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if pattern in message:
                    detected_intent = intent_type
                    break
        
        # 3. 基於用戶歷史偏好
        if user_preferences.get("preferred_features"):
            top_feature = user_preferences["preferred_features"][0]["name"]
            if detected_intent in ["查詢", "開始"]:
                return {
                    "intent": "use_feature",
                    "feature": top_feature,
                    "confidence": 0.8,
                    "reason": "based_on_user_history",
                    "entities": entities,
                    "embedding": embedding
                }
        
        # 4. 基於上下文
        if context_features:
            most_recent_feature = context_features[-1]
            if detected_intent == "參與":
                return {
                    "intent": "continue_feature",
                    "feature": most_recent_feature,
                    "confidence": 0.85,
                    "reason": "based_on_context",
                    "entities": entities,
                    "embedding": embedding
                }
        
        # 5. 基於相似意圖（知識圖譜）
        if similar_intents:
            top_similar = similar_intents[0]
            return {
                "intent": "use_feature",
                "feature": top_similar["feature"],
                "confidence": 0.75,
                "reason": "based_on_similarity",
                "entities": entities,
                "embedding": embedding
            }
        
        # 6. 自然對話（加入廣播池）
        if len(message) > 5 and not any(k in ["?", "？", "嗎", "呢"] for k in message):
            return {
                "intent": "contribute",
                "feature": "廣播",
                "confidence": 0.7,
                "reason": "natural_conversation",
                "entities": entities,
                "embedding": embedding
            }
        
        # 7. 問句處理
        if any(k in message for k in ["?", "？", "嗎", "呢", "什麼", "怎麼", "如何"]):
            return {
                "intent": "query",
                "confidence": 0.6,
                "entities": entities,
                "embedding": embedding
            }
        
        # 8. 預設：不確定
        return {
            "intent": "unknown",
            "confidence": 0.3,
            "entities": entities,
            "embedding": embedding
        }
    
    def _save_to_graph(self, message: str, user_id: str, intent_result: Dict, embedding: List[float]) -> str:
        """將分析結果儲存到知識圖譜"""
        # 新增用戶節點
        self.graph.add_user(user_id)
        
        # 新增訊息節點
        message_data = self.graph.add_message(
            message_id=None,  # 自動生成
            content=message,
            user_id=user_id,
            embedding=embedding
        )
        message_id = message_data["message"]["id"]
        
        # 建立功能關聯
        if intent_result.get("feature"):
            self.graph.link_message_to_feature(message_id, intent_result["feature"])
        
        # 提取並建立主題關聯
        topics = self._extract_topics(message)
        if topics:
            self.graph.add_topic(message_id, topics)
        
        return message_id
    
    def _extract_topics(self, message: str) -> List[str]:
        """從訊息中提取主題"""
        # 使用 jieba 提取名詞
        words = jieba.lcut(message)
        topics = []
        
        # 簡單的主題提取規則
        for word in words:
            if len(word) >= 2 and word not in self.feature_keywords:
                # 這裡可以加入更複雜的主題識別邏輯
                topics.append(word)
        
        return topics[:3]  # 最多3個主題
    
    def get_feature_suggestions(self, user_id: str) -> List[Dict]:
        """基於用戶行為推薦功能"""
        # 獲取社交推薦
        social_recommendations = self.graph.get_social_recommendations(user_id)
        
        # 獲取用戶偏好
        user_preferences = self.graph.get_user_preferences(user_id)
        
        suggestions = []
        
        # 加入社交推薦
        for feature in social_recommendations:
            suggestions.append({
                "feature": feature,
                "reason": "朋友們都在玩",
                "type": "social"
            })
        
        # 基於時間推薦
        import datetime
        hour = datetime.datetime.now().hour
        if 6 <= hour < 12:
            suggestions.append({
                "feature": "統計",
                "reason": "早安！看看昨晚的統計",
                "type": "time_based"
            })
        elif 18 <= hour < 24:
            suggestions.append({
                "feature": "接龍",
                "reason": "晚上來玩文字接龍吧",
                "type": "time_based"
            })
        
        return suggestions[:3]  # 最多返回3個建議
    
    def explain_intent(self, intent_result: Dict) -> str:
        """解釋意圖分析結果（用於調試）"""
        explanations = {
            "based_on_user_history": "根據您的使用習慣",
            "based_on_context": "延續剛才的對話",
            "based_on_similarity": "類似其他用戶的用法",
            "natural_conversation": "加入大家的對話",
            "direct_match": "直接匹配到功能"
        }
        
        reason = intent_result.get("reason", "unknown")
        explanation = explanations.get(reason, "智慧分析結果")
        
        if intent_result.get("feature"):
            return f"{explanation}，為您啟動「{intent_result['feature']}」"
        else:
            return explanation


# 輔助函數
def test_intent_analyzer():
    """測試意圖分析器"""
    analyzer = IntentAnalyzer()
    
    test_cases = [
        ("我想玩遊戲", "test_user"),
        ("接龍 蘋果", "test_user"),
        ("看看統計", "test_user"),
        ("3", "test_user"),
        ("今天天氣真好", "test_user"),
        ("有沒有避難所？", "test_user")
    ]
    
    for message, user_id in test_cases:
        result = analyzer.analyze(message, user_id)
        print(f"\n訊息: {message}")
        print(f"意圖: {result.get('intent')}")
        print(f"功能: {result.get('feature')}")
        print(f"信心度: {result.get('confidence')}")
        print(f"原因: {result.get('reason', 'N/A')}")


if __name__ == "__main__":
    # 測試模組
    test_intent_analyzer()