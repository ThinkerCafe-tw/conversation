"""
測試集體記憶廣播效果
"""

import os
import time
from dotenv import load_dotenv
from knowledge_graph import KnowledgeGraph
from collective_memory import CollectiveMemorySystem, MemoryAnalyzer
from frequency_bot_firestore import FrequencyBotFirestore
import google.generativeai as genai

# 載入環境變數
if os.path.exists('.env'):
    load_dotenv()

def test_collective_broadcast():
    """測試集體記憶廣播生成"""
    print("=== 集體記憶廣播測試 ===\n")
    
    # 初始化系統
    print("1. 初始化系統...")
    try:
        graph = KnowledgeGraph()
        memory_system = CollectiveMemorySystem(graph)
        frequency_bot = FrequencyBotFirestore(graph)
        print("   ✅ 系統初始化成功")
    except Exception as e:
        print(f"   ❌ 初始化失敗: {e}")
        return
    
    # 模擬用戶訊息
    print("\n2. 模擬用戶訊息...")
    test_messages = [
        ("用戶0001", "今天天氣真好，心情也跟著好起來了"),
        ("用戶0002", "好累啊，想要放鬆一下"),
        ("用戶0003", "有人要一起玩接龍嗎？"),
        ("用戶0001", "我也想玩！開始吧"),
        ("用戶0004", "晚安大家，準備睡覺了"),
        ("用戶0002", "真的好累，明天還要早起"),
        ("用戶0005", "今晚的月亮很美呢"),
        ("用戶0003", "接龍：月亮"),
        ("用戶0001", "亮晶晶"),
        ("用戶0006", "大家都在聊什麼呀"),
        ("用戶0007", "剛下班，錯過什麼了嗎"),
        ("用戶0008", "想吃宵夜，有推薦嗎"),
        ("用戶0002", "我也餓了，一起點外送？"),
        ("用戶0009", "今天過得真快"),
        ("用戶0010", "時間總是不夠用")
    ]
    
    # 將訊息加入廣播池和集體記憶
    for user_id, message in test_messages:
        frequency_bot.add_to_broadcast(message, user_id)
        print(f"   已加入: [{user_id}] {message[:20]}...")
    
    print(f"\n   ✅ 已加入 {len(test_messages)} 則訊息")
    
    # 生成集體記憶廣播提示詞
    print("\n3. 生成集體記憶廣播提示詞...")
    current_hour = int(time.time() // 3600)
    prompt = memory_system.generate_broadcast_prompt(current_hour)
    
    print(f"   提示詞長度: {len(prompt)} 字")
    print(f"   提示詞預覽:")
    print("   " + "-" * 50)
    print(prompt[:500] + "...")
    print("   " + "-" * 50)
    
    # 使用 AI 生成廣播
    print("\n4. 使用 Gemini AI 生成廣播...")
    try:
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        response = model.generate_content(prompt)
        if response and response.candidates:
            broadcast = response.candidates[0].content.parts[0].text
            
            print("\n🌙 生成的集體記憶廣播：")
            print("=" * 60)
            print(broadcast)
            print("=" * 60)
            
            # 分析廣播效果
            print("\n5. 廣播效果分析：")
            analyze_broadcast_effect(broadcast, test_messages)
            
        else:
            print("   ❌ AI 生成失敗")
            
    except Exception as e:
        print(f"   ❌ 生成廣播時發生錯誤: {e}")
    
    # 用戶演化分析
    print("\n6. 用戶演化分析...")
    analyzer = MemoryAnalyzer(graph)
    
    for user_id in ["用戶0001", "用戶0002", "用戶0003"]:
        evolution = analyzer.analyze_user_evolution(user_id)
        print(f"\n   {user_id}:")
        print(f"   - 訊息數量: {evolution.get('message_count', 0)}")
        print(f"   - 情緒歷程: {' → '.join(evolution.get('emotion_journey', []))}")
        if evolution.get('topic_expansion', {}).get('current_interests'):
            print(f"   - 關注話題: {', '.join(evolution['topic_expansion']['current_interests'])}")
    
    # 找出共振模式
    print("\n7. 社群共振模式...")
    patterns = analyzer.find_resonance_patterns()
    print(f"   活躍高峰: {patterns.get('peak_hours', [])}")
    print(f"   熱門話題: {patterns.get('viral_topics', [])}")
    
    graph.close()
    print("\n=== 測試完成 ===")

def analyze_broadcast_effect(broadcast: str, original_messages):
    """分析廣播是否成功回應了用戶"""
    responded_users = []
    
    # 檢查關鍵詞匹配
    keywords_map = {
        "累": ["用戶0002", "用戶0006"],
        "接龍": ["用戶0003", "用戶0001"],
        "月亮": ["用戶0005", "用戶0003"],
        "餓": ["用戶0008", "用戶0002"],
        "時間": ["用戶0009", "用戶0010"]
    }
    
    for keyword, users in keywords_map.items():
        if keyword in broadcast:
            responded_users.extend(users)
    
    unique_responded = set(responded_users)
    total_users = len(set([msg[0] for msg in original_messages]))
    
    print(f"   - 回應覆蓋率: {len(unique_responded)}/{total_users} 用戶 ({len(unique_responded)/total_users*100:.1f}%)")
    print(f"   - 被回應的用戶: {', '.join(unique_responded)}")
    
    # 檢查集體化用語
    collective_words = ["我們", "大家", "一起", "共同", "彼此"]
    collective_count = sum(1 for word in collective_words if word in broadcast)
    print(f"   - 集體化用語: {collective_count} 個")
    
    # 檢查時間感知
    time_words = ["今晚", "夜晚", "此刻", "這個時候"]
    has_time_awareness = any(word in broadcast for word in time_words)
    print(f"   - 時間感知: {'✅ 有' if has_time_awareness else '❌ 無'}")

if __name__ == "__main__":
    test_collective_broadcast()