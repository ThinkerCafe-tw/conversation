"""
文字接龍格式化器
提供更好的接龍顯示效果
"""

def format_word_chain_display(chain_data: dict, is_start: bool = False) -> str:
    """格式化接龍顯示"""
    chain = chain_data.get('chain', [])
    current_word = chain_data.get('current_word', '')
    progress = len(chain)
    target = chain_data.get('target_length', 10)
    participants = len(chain_data.get('participants', []))
    
    if is_start:
        # 開始新接龍
        message = f"""🎯 文字接龍開始！

📝 起始詞：{current_word}
📍 下一個詞要以「{current_word[-1]}」開頭
🎯 目標：接龍 {target} 個詞

💡 提示：輸入「接龍 [詞語]」來繼續"""
    else:
        # 繼續接龍
        # 建立接龍路徑顯示
        if len(chain) <= 5:
            # 顯示完整路徑
            chain_display = ' → '.join(chain)
        else:
            # 顯示前3個和後2個
            chain_display = ' → '.join(chain[:3]) + ' → ... → ' + ' → '.join(chain[-2:])
        
        message = f"""✅ 接龍成功！

🔗 接龍路徑：
{chain_display}

📍 當前詞：{current_word}
📊 進度：{progress}/{target}
👥 參與者：{participants} 人
🔤 下一個詞要以「{current_word[-1]}」開頭"""
        
        # 如果接近完成，加上鼓勵
        if progress >= target - 2:
            message += f"\n\n🔥 還差 {target - progress} 個詞就完成了！加油！"
    
    return message


def format_chain_complete(chain_data: dict) -> str:
    """格式化接龍完成訊息"""
    chain = chain_data.get('chain', [])
    participants = chain_data.get('participants', [])
    
    # 完整的接龍路徑（每5個換行）
    chain_lines = []
    for i in range(0, len(chain), 5):
        line_words = chain[i:i+5]
        chain_lines.append(' → '.join(line_words))
    
    chain_display = '\n'.join(chain_lines)
    
    message = f"""🎊 恭喜！接龍完成！

🏆 完整接龍路徑：
{chain_display}

📊 統計資料：
• 總詞數：{len(chain)} 個
• 參與者：{len(participants)} 人
• 最長的詞：{max(chain, key=len)}（{len(max(chain, key=len))} 個字）

✨ 這是一次精彩的接龍！"""
    
    return message


def format_chain_error(error_type: str, details: dict) -> str:
    """格式化錯誤訊息"""
    if error_type == 'wrong_start':
        return f"""❌ 接龍失敗！

「{details['word']}」的第一個字必須是「{details['expected']}」

💡 提示：試試以「{details['expected']}」開頭的詞語
例如：{get_example_words(details['expected'])}"""
    
    elif error_type == 'duplicate':
        return f"""❌ 「{details['word']}」已經用過了！

🔍 已使用的詞：
{' → '.join(details['recent_words'][-5:])}

💡 請換一個詞試試"""
    
    elif error_type == 'no_chain':
        return """❓ 目前沒有進行中的接龍

💡 輸入「接龍 [詞語]」開始新接龍
例如：接龍 蘋果"""
    
    return "❌ 發生錯誤，請稍後再試"


def get_example_words(char: str) -> str:
    """取得範例詞語"""
    examples = {
        '果': '果汁、果然、果斷',
        '子': '子女、子夜、子彈',
        '花': '花園、花樣、花費',
        '水': '水果、水準、水晶',
        '天': '天空、天氣、天才',
        '地': '地方、地圖、地球',
        '人': '人生、人氣、人情',
        '心': '心情、心得、心願'
    }
    return examples.get(char, f'{char}...（請發揮創意！）')


def format_chain_status() -> str:
    """格式化接龍狀態查詢"""
    return """📊 接龍狀態

• 輸入「接龍 [詞語]」開始新接龍
• 輸入「接龍狀態」查看當前進度
• 輸入「接龍紀錄」查看歷史紀錄

💡 範例：接龍 蘋果"""