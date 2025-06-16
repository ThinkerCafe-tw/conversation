"""
意圖分析器修復版本 - 增強遊戲識別
"""

# 在 feature_keywords 中增加：
self.feature_keywords = {
    "接龍": ["接龍", "文字接龍", "詞語接龍", "玩接龍", "遊戲", "玩遊戲", "玩"],
    # ... 其他保持不變
}

# 在 _determine_intent 方法中增加特殊處理：
def _determine_intent(self, **kwargs):
    message = kwargs.get("message", "")
    
    # 特殊處理「玩」相關的訊息
    if any(word in message for word in ["玩", "遊戲", "game", "play"]):
        # 如果沒有其他特定功能，預設導向接龍
        if not self._match_feature_keywords(message):
            return {
                "intent": "use_feature",
                "feature": "接龍",
                "confidence": 0.85,
                "reason": "game_intent",
                "entities": kwargs.get("entities", {}),
                "embedding": kwargs.get("embedding", [])
            }
    
    # ... 其他邏輯保持不變