"""
測試意圖分析器
"""

import os
from dotenv import load_dotenv

# 載入環境變數
if os.path.exists('.env'):
    load_dotenv()

from intent_analyzer import IntentAnalyzer
from knowledge_graph import KnowledgeGraph

# 測試意圖分析
kg = KnowledgeGraph()
analyzer = IntentAnalyzer(kg)

# 測試案例
test_cases = [
    '我想玩接龍',
    '查看統計',
    '投票 晚餐吃什麼/火鍋/燒烤/日料',
    '3',
    '今天天氣真好',
    '有沒有避難所？',
    '防空洞在哪裡'
]

print('=== 意圖分析測試 ===\n')
for msg in test_cases:
    result = analyzer.analyze(msg, 'test_user')
    print(f'訊息: {msg}')
    print(f'意圖: {result.get("intent")}, 功能: {result.get("feature")}, 信心度: {result.get("confidence", 0):.2f}')
    if result.get("reason"):
        print(f'原因: {result.get("reason")}')
    print()

# 測試個人化推薦
print('\n=== 個人化推薦測試 ===\n')
suggestions = analyzer.get_feature_suggestions('test_user')
for s in suggestions:
    print(f'推薦功能: {s["feature"]} - {s["reason"]}')

kg.close()
print('\n測試完成！')