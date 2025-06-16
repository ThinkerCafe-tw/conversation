"""
智慧引導系統 - 降低新用戶上手門檻
"""

import time
from typing import Dict, Optional
from datetime import datetime

class SmartOnboarding:
    """智慧引導系統，根據用戶階段提供個人化指引"""
    
    def __init__(self, knowledge_graph=None):
        self.graph = knowledge_graph
        
        # 用戶階段定義
        self.stages = {
            "new": {
                "message_count": 0,
                "next_action": "say_hello",
                "features_unlocked": ["廣播", "統計"]
            },
            "beginner": {
                "message_count": 1,
                "next_action": "explore_features",
                "features_unlocked": ["廣播", "統計", "玩", "看"]
            },
            "active": {
                "message_count": 5,
                "next_action": "try_games",
                "features_unlocked": ["接龍", "投票"]
            },
            "regular": {
                "message_count": 20,
                "next_action": "advanced_features",
                "features_unlocked": ["防災", "API統計"]
            },
            "expert": {
                "message_count": 50,
                "next_action": "community_leader",
                "features_unlocked": ["所有功能"]
            }
        }
        
        # 智慧提示模板
        self.smart_prompts = {
            "new_user_first": "👋 歡迎來到頻率共振！\n\n我會把大家的訊息編成美妙的廣播～\n直接打字就能參與，試試看說「你好」吧！",
            
            "after_first_message": "✨ 太棒了！你的聲音已經加入今晚的頻率\n\n💡 小提示：輸入「{suggestion}」可以{action}",
            
            "encourage_exploration": "🎯 你已經發了 {count} 則訊息！\n\n🎁 解鎖新功能：{features}\n要試試看嗎？",
            
            "game_invitation": "🎮 發現你很活躍！要不要玩個遊戲？\n\n• 文字接龍 - 輸入「接龍 {word}」\n• 發起投票 - 輸入「投票範例」",
            
            "milestone_celebration": "🎉 恭喜達成 {count} 則訊息！\n{achievement}\n\n繼續保持，下個里程碑：{next_milestone}",
            
            "return_greeting": "💫 歡迎回來！距離上次見面已經 {days} 天了\n\n最近大家在{hot_topic}，要加入討論嗎？"
        }
        
        # 個人化建議
        self.suggestions = {
            "morning": {
                "time_range": (6, 12),
                "suggestion": "統計",
                "action": "看看昨晚的精彩回顧"
            },
            "afternoon": {
                "time_range": (12, 18),
                "suggestion": "投票 午餐吃什麼/便當/麵/自己煮",
                "action": "發起午餐投票"
            },
            "evening": {
                "time_range": (18, 22),
                "suggestion": "玩",
                "action": "探索互動遊戲"
            },
            "night": {
                "time_range": (22, 6),
                "suggestion": "廣播",
                "action": "聽聽今天的頻率廣播"
            }
        }
    
    def get_user_stage(self, user_id: str) -> str:
        """判斷用戶所在階段"""
        if not self.graph:
            return "new"
        
        try:
            # 從知識圖譜獲取用戶資料
            user_data = self.graph.get_user_preferences(user_id)
            message_count = self._get_user_message_count(user_id)
            
            # 根據訊息數量判斷階段
            for stage_name, stage_data in reversed(list(self.stages.items())):
                if message_count >= stage_data["message_count"]:
                    return stage_name
            
            return "new"
        except:
            return "new"
    
    def get_smart_greeting(self, user_id: str, context: Dict = None) -> str:
        """生成智慧問候語"""
        stage = self.get_user_stage(user_id)
        
        # 新用戶
        if stage == "new":
            return self.smart_prompts["new_user_first"]
        
        # 回訪用戶
        last_seen = self._get_last_seen(user_id)
        if last_seen and (time.time() - last_seen) > 86400:  # 超過一天
            days = int((time.time() - last_seen) / 86400)
            hot_topic = self._get_hot_topic()
            return self.smart_prompts["return_greeting"].format(
                days=days,
                hot_topic=hot_topic
            )
        
        # 根據時間提供建議
        hour = datetime.now().hour
        for time_period, data in self.suggestions.items():
            start, end = data["time_range"]
            if start <= hour < end or (start > end and (hour >= start or hour < end)):
                return self.smart_prompts["after_first_message"].format(
                    suggestion=data["suggestion"],
                    action=data["action"]
                )
        
        # 預設問候
        return self._get_stage_appropriate_greeting(stage, user_id)
    
    def get_feature_suggestion(self, user_id: str, user_input: str) -> Optional[str]:
        """根據用戶輸入提供功能建議"""
        stage = self.get_user_stage(user_id)
        
        # 偵測可能的功能意圖
        intent_mappings = {
            ("玩", "遊戲", "無聊"): {
                "feature": "接龍",
                "prompt": "想玩遊戲嗎？試試「接龍 開始」吧！"
            },
            ("統計", "數據", "多少"): {
                "feature": "統計",
                "prompt": "想看統計資料嗎？輸入「統計」即可！"
            },
            ("投票", "選擇", "決定"): {
                "feature": "投票",
                "prompt": "要發起投票嗎？看看「投票範例」！"
            },
            ("幫助", "怎麼", "不會"): {
                "feature": "幫助",
                "prompt": "需要幫助嗎？輸入「幫助」查看所有功能！"
            }
        }
        
        for keywords, suggestion in intent_mappings.items():
            if any(keyword in user_input for keyword in keywords):
                # 檢查用戶是否已解鎖該功能
                if self._is_feature_unlocked(stage, suggestion["feature"]):
                    return f"💡 {suggestion['prompt']}"
        
        return None
    
    def celebrate_milestone(self, user_id: str, milestone_type: str) -> str:
        """慶祝用戶達成里程碑"""
        celebrations = {
            "first_message": "🎤 第一次發聲！你已經成為頻率的一部分",
            "tenth_message": "💬 10則訊息達成！你是活躍的參與者",
            "first_game": "🎮 遊戲新手！期待看到你的表現",
            "vote_creator": "🗳️ 民主先鋒！你發起了第一個投票",
            "helping_hand": "🤝 樂於助人！感謝你的分享"
        }
        
        achievement = celebrations.get(milestone_type, "🎉 太棒了！")
        count = self._get_user_message_count(user_id)
        
        # 計算下個里程碑
        milestones = [1, 10, 50, 100, 500, 1000]
        next_milestone = next((m for m in milestones if m > count), None)
        
        if next_milestone:
            return self.smart_prompts["milestone_celebration"].format(
                count=count,
                achievement=achievement,
                next_milestone=f"{next_milestone}則訊息"
            )
        else:
            return f"{achievement}\n\n你已經是頻率大師了！🌟"
    
    def _get_user_message_count(self, user_id: str) -> int:
        """獲取用戶訊息數量"""
        if not self.graph:
            return 0
        
        try:
            # 實際實作應該從知識圖譜查詢
            # 這裡簡化處理
            return 10  # 示例值
        except:
            return 0
    
    def _get_last_seen(self, user_id: str) -> Optional[float]:
        """獲取用戶最後活躍時間"""
        # 實際實作應該從資料庫查詢
        return None
    
    def _get_hot_topic(self) -> str:
        """獲取當前熱門話題"""
        topics = ["聊天氣", "玩接龍", "討論晚餐", "分享心情"]
        import random
        return random.choice(topics)
    
    def _is_feature_unlocked(self, stage: str, feature: str) -> bool:
        """檢查功能是否已解鎖"""
        stage_data = self.stages.get(stage, {})
        unlocked_features = stage_data.get("features_unlocked", [])
        return feature in unlocked_features or "所有功能" in unlocked_features
    
    def _get_stage_appropriate_greeting(self, stage: str, user_id: str) -> str:
        """根據階段生成適當的問候"""
        count = self._get_user_message_count(user_id)
        
        if stage == "beginner":
            return self.smart_prompts["encourage_exploration"].format(
                count=count,
                features="快捷選單（玩/看/救）"
            )
        elif stage == "active":
            return self.smart_prompts["game_invitation"].format(
                word="開始"
            )
        else:
            return "歡迎回來！今天想做什麼呢？"


class SmartErrorHandler:
    """智慧錯誤處理與建議系統"""
    
    def __init__(self):
        self.error_patterns = {
            "format_error": {
                "接龍": "💡 接龍格式：接龍 [詞語]\n例如：接龍 蘋果",
                "投票": "💡 投票格式：投票 主題/選項1/選項2\n例如：投票 晚餐/火鍋/日料",
                "防空": "💡 防空格式：防空 地點 類型 容量\n例如：防空 信義區某大樓 地下室 200"
            },
            "typo_suggestions": {
                "統計": ["統計", "狀態", "數據"],
                "接龍": ["接龍", "結龍", "節龍"],
                "投票": ["投票", "頭票", "透票"],
                "廣播": ["廣播", "光波", "廣撥"]
            }
        }
    
    def suggest_correction(self, user_input: str, error_type: str = None) -> str:
        """提供智慧錯誤修正建議"""
        # 檢查是否為格式錯誤
        for feature, keywords in [("接龍", ["接龍"]), ("投票", ["投票"]), ("防空", ["防空"])]:
            if any(k in user_input for k in keywords):
                # 檢查格式是否正確
                if feature == "接龍" and len(user_input.split()) < 2:
                    return self.error_patterns["format_error"]["接龍"]
                elif feature == "投票" and "/" not in user_input:
                    return self.error_patterns["format_error"]["投票"]
                elif feature == "防空" and len(user_input.split()) < 4:
                    return self.error_patterns["format_error"]["防空"]
        
        # 模糊匹配可能的錯字
        from difflib import get_close_matches
        for correct, variations in self.error_patterns["typo_suggestions"].items():
            matches = get_close_matches(user_input, variations, n=1, cutoff=0.6)
            if matches:
                return f"💡 您是想輸入「{correct}」嗎？"
        
        # 預設建議
        return "💡 不確定如何使用？輸入「幫助」查看所有功能！"


# 測試用例
if __name__ == "__main__":
    onboarding = SmartOnboarding()
    error_handler = SmartErrorHandler()
    
    # 測試不同階段的用戶
    print("=== 智慧引導測試 ===\n")
    
    # 新用戶
    print("新用戶問候：")
    print(onboarding.get_smart_greeting("new_user_001"))
    print()
    
    # 錯誤格式測試
    print("錯誤修正建議：")
    print(error_handler.suggest_correction("接龍"))
    print(error_handler.suggest_correction("投票 要吃什麼"))
    print(error_handler.suggest_correction("統擊"))  # 錯字
    print()
    
    # 里程碑慶祝
    print("里程碑慶祝：")
    print(onboarding.celebrate_milestone("user_001", "first_message"))
    print(onboarding.celebrate_milestone("user_002", "tenth_message"))