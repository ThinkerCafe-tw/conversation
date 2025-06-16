#!/usr/bin/env python3
"""
測試廣播功能
"""

from frequency_bot import FrequencyBot
import time
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

def test_broadcast():
    bot = FrequencyBot()
    
    # 測試訊息
    test_messages = [
        "今天好累，終於下班了",
        "期待週末的到來！",
        "剛剛喝了一杯超好喝的咖啡",
        "有人也覺得最近天氣很奇怪嗎",
        "感謝今天幫助我的同事",
        "壓力好大，需要放鬆一下",
        "晚餐吃什麼好呢",
        "追的劇終於更新了！",
        "明天還要早起，先睡了",
        "今天運動了，感覺很棒"
    ]
    
    print("📡 加入測試訊息到廣播池...")
    for msg in test_messages:
        bot.add_to_broadcast(msg)
        print(f"  ✓ {msg}")
    
    print("\n⏳ 生成廣播中...")
    result = bot.generate_hourly_broadcast()
    
    if result:
        print(f"\n✅ 廣播生成成功！")
        print(f"訊息數量: {result['message_count']}")
        print(f"\n廣播內容:\n{result['content']}")
    else:
        print("\n❌ 廣播生成失敗")
    
    # 測試獲取最新廣播
    print("\n📻 測試獲取最新廣播...")
    latest = bot.get_latest_broadcast()
    if latest:
        from frequency_bot import format_broadcast_message
        print(format_broadcast_message(latest))

if __name__ == "__main__":
    test_broadcast()