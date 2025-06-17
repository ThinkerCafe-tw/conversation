"""
交友功能整合到 LINE Bot
"""

from dating_features import AIMatchingEngine, DatingAIService, format_dating_profile_card, format_matches_list

# 在 app.py 中添加以下處理器

def initialize_dating_system(gemini_client, redis_client, graph_db):
    """初始化交友系統"""
    dating_ai = DatingAIService(gemini_client)
    dating_engine = AIMatchingEngine(redis_client, graph_db, dating_ai)
    return dating_engine

# 主要交友指令處理器
def handle_dating_commands(event, user_id, dating_engine):
    """處理交友相關指令"""
    message_text = event.message.text.lower()
    
    # 開始交友
    if message_text in ['交友', '開始交友', '尋找對象']:
        return handle_start_dating(user_id, dating_engine)
    
    # 創建檔案
    elif message_text.startswith('建立檔案'):
        return handle_create_profile_prompt(user_id)
    
    # 檔案設定格式: "檔案 小明,25,男,台北,音樂/旅行/美食,喜歡探索新事物"
    elif message_text.startswith('檔案 '):
        return handle_create_profile(user_id, message_text[3:], dating_engine)
    
    # 發現新朋友
    elif message_text in ['發現', '探索', '滑卡']:
        return handle_discover_users(user_id, dating_engine)
    
    # 滑動動作: "喜歡 user123" 或 "略過 user123"
    elif message_text.startswith(('喜歡 ', '略過 ')):
        action = "like" if message_text.startswith('喜歡') else "pass"
        target_id = message_text.split(' ')[1]
        return handle_swipe_action(user_id, target_id, action, dating_engine)
    
    # 超級喜歡
    elif message_text.startswith('超級喜歡 '):
        target_id = message_text.split(' ')[1]
        return handle_super_like(user_id, target_id, dating_engine)
    
    # 查看配對
    elif message_text in ['配對', '我的配對', 'matches']:
        return handle_view_matches(user_id, dating_engine)
    
    # 檔案加速
    elif message_text in ['加速', 'boost', '提升曝光']:
        return handle_boost_profile(user_id, dating_engine)
    
    # AI 戀愛教練
    elif message_text.startswith('戀愛教練 '):
        question = message_text[5:]
        return handle_dating_coach(user_id, question, dating_engine)
    
    return None

def handle_start_dating(user_id: str, dating_engine: AIMatchingEngine) -> str:
    """開始交友流程"""
    # 檢查是否已有檔案
    if dating_engine.redis:
        existing_profile = dating_engine.redis.get(f"dating_profile:{user_id}")
        if existing_profile:
            return """💕 歡迎回到 AI 交友！

🎯 快速指令：
• 「發現」- 探索新朋友
• 「配對」- 查看配對列表  
• 「戀愛教練 [問題]」- AI 約會建議

✨ Premium 功能：
• 「超級喜歡」- 優先配對
• 「加速」- 5倍曝光度
• 「戀愛教練」- 專業建議"""
    
    return """💕 歡迎來到 AI 智慧交友！

🤖 我們的特色：
✨ AI 個性分析配對
🎯 智慧對話建議
💬 即時相容性分析
🌟 個人化推薦

📝 首先建立您的檔案：
輸入「建立檔案」開始設定

或查看範例：
「檔案 小明,25,男,台北,音樂/旅行/美食,喜歡探索新事物的人」"""

def handle_create_profile_prompt(user_id: str) -> str:
    """檔案建立提示"""
    return """📝 建立交友檔案

請依照以下格式輸入：
「檔案 暱稱,年齡,性別,地區,興趣1/興趣2/興趣3,自我介紹」

📋 範例：
「檔案 Alex,28,女,台北,攝影/咖啡/登山,喜歡用鏡頭記錄生活美好時刻」

💡 小提示：
• 暱稱請使用真實感的名字
• 興趣用「/」分隔
• 自我介紹展現您的個性
• 真誠的檔案更容易配對成功！"""

def handle_create_profile(user_id: str, profile_data: str, dating_engine: AIMatchingEngine) -> str:
    """處理檔案創建"""
    try:
        parts = profile_data.split(',')
        if len(parts) < 6:
            return "❌ 格式錯誤！請參考範例格式輸入完整資訊"
        
        profile_info = {
            'display_name': parts[0].strip(),
            'age': int(parts[1].strip()),
            'gender': parts[2].strip(),
            'location': parts[3].strip(),
            'interests': parts[4].strip().split('/'),
            'bio': parts[5].strip()
        }
        
        result = dating_engine.create_dating_profile(user_id, profile_info)
        
        if result['success']:
            return f"""{result['message']}

🤖 AI 個性分析：
{result['ai_insights']}

🎯 下一步：
• 「發現」- 開始探索
• 「配對」- 查看推薦"""
        else:
            return f"❌ {result['message']}"
            
    except ValueError:
        return "❌ 年齡請輸入數字"
    except Exception as e:
        return "❌ 建立檔案時發生錯誤，請稍後再試"

def handle_discover_users(user_id: str, dating_engine: AIMatchingEngine) -> str:
    """發現新用戶"""
    recommendations = dating_engine.get_recommendations(user_id, limit=1)
    
    if not recommendations:
        return """😔 目前沒有新的推薦

💡 建議：
• 完善您的檔案資訊
• 擴大地區範圍
• 升級 Plus 獲得更多推薦

或稍後再來探索！"""
    
    user = recommendations[0]
    profile_card = format_dating_profile_card(user)
    
    return f"""{profile_card}

💫 操作選項：
• 「喜歡 {user['user_id']}」- 送出喜歡
• 「超級喜歡 {user['user_id']}」- 優先配對 ⭐
• 「略過 {user['user_id']}」- 查看下一位
• 「發現」- 繼續探索

相容性分數：{user.get('compatibility_score', 85)}%"""

def handle_swipe_action(user_id: str, target_id: str, action: str, dating_engine: AIMatchingEngine) -> str:
    """處理滑動動作"""
    result = dating_engine.swipe_action(user_id, target_id, action)
    
    if not result['success']:
        return f"❌ {result['message']}"
    
    if result.get('matched'):
        return f"""{result['message']}

💬 AI 推薦開場白：
「{result['ai_starter']}」

🎯 快速指令：
• 「配對」- 查看所有配對
• 「發現」- 繼續探索"""
    
    return f"{result['message']}\n\n• 「發現」- 繼續探索新朋友"

def handle_super_like(user_id: str, target_id: str, dating_engine: AIMatchingEngine) -> str:
    """處理超級喜歡"""
    result = dating_engine.super_like(user_id, target_id)
    
    if not result['success']:
        return f"{result['message']}\n\n💎 立即升級享受 Premium 功能！"
    
    if result.get('matched'):
        return f"""{result['message']}

✨ 這是命中注定的配對！
立即開始對話，分享這份特別的緣分 💕"""
    
    return f"{result['message']}\n\n• 「發現」- 繼續探索"

def handle_view_matches(user_id: str, dating_engine: AIMatchingEngine) -> str:
    """查看配對列表"""
    matches = dating_engine.get_matches(user_id)
    return format_matches_list(matches)

def handle_boost_profile(user_id: str, dating_engine: AIMatchingEngine) -> str:
    """檔案加速"""
    result = dating_engine.boost_profile(user_id)
    
    if not result['success']:
        return f"{result['message']}\n\n🚀 升級 Gold 立即享受極速配對！"
    
    return f"""{result['message']}

📈 加速效果：
• 5倍推薦優先度
• 更多優質用戶看到您
• 30分鐘黃金時段

💡 加速期間多發「超級喜歡」效果更佳！"""

def handle_dating_coach(user_id: str, question: str, dating_engine: AIMatchingEngine) -> str:
    """AI 戀愛教練"""
    result = dating_engine.get_ai_dating_coach(user_id, question)
    
    if not result['success']:
        return f"{result['message']}\n\n💎 升級 Gold 獲得專業戀愛指導！"
    
    response = f"""💎 AI 戀愛教練建議：

{result['advice']}

📋 行動建議："""
    
    for i, action in enumerate(result['action_items'], 1):
        response += f"\n{i}. {action}"
    
    response += "\n\n💡 有其他問題嗎？繼續問「戀愛教練 [問題]」"
    return response

# 快捷選單更新
DATING_QUICK_MENU = {
    "💕": {
        "title": "💕 AI 智慧交友",
        "options": [
            ("👀 發現新朋友", "發現"),
            ("💕 查看配對", "配對"), 
            ("⭐ 檔案加速", "加速"),
            ("💎 戀愛教練", "戀愛教練 如何開始對話")
        ],
        "footer": "💡 找到真愛從這裡開始！"
    }
}