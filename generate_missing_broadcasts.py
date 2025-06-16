#!/usr/bin/env python3
"""
生成所有遺漏的廣播
"""

import os
from dotenv import load_dotenv
from google.cloud import firestore
from frequency_bot_firestore import FrequencyBotFirestore
import logging
import time
from datetime import datetime

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 載入環境變數
if os.path.exists('.env'):
    load_dotenv()

def generate_missing_broadcasts():
    """生成所有遺漏的廣播"""
    try:
        # 初始化
        db = firestore.Client()
        bot = FrequencyBotFirestore()
        
        # 查找有訊息但沒有廣播的時段
        logger.info("查找需要生成廣播的時段...")
        
        # 獲取所有有訊息的時段
        broadcasts = db.collection('broadcasts').stream()
        hours_with_messages = []
        
        for doc in broadcasts:
            data = doc.to_dict()
            if data.get('message_count', 0) > 0:
                hours_with_messages.append(int(doc.id))
                
        logger.info(f"發現 {len(hours_with_messages)} 個有訊息的時段")
        
        # 檢查哪些時段沒有廣播
        missing_hours = []
        for hour in hours_with_messages:
            generated = db.collection('generated_broadcasts').document(str(hour)).get()
            if not generated.exists:
                missing_hours.append(hour)
                
        logger.info(f"有 {len(missing_hours)} 個時段需要生成廣播: {missing_hours}")
        
        # 為每個遺漏的時段生成廣播
        for hour in missing_hours:
            logger.info(f"\n生成 Hour {hour} 的廣播...")
            
            # 獲取該時段的訊息
            doc_ref = db.collection('broadcasts').document(str(hour))
            messages = []
            message_dicts = []
            contributors = set()
            
            messages_query = doc_ref.collection('messages').limit(1000).stream()
            for msg_doc in messages_query:
                data = msg_doc.to_dict()
                messages.append(data['content'])
                message_dicts.append({
                    'content': data['content'],
                    'user_id': data.get('user_id', '匿名'),
                    'timestamp': data.get('timestamp')
                })
                contributors.add(data.get('user_id', '匿名'))
                
            if not messages:
                logger.info(f"Hour {hour} 沒有訊息，跳過")
                continue
                
            logger.info(f"收集到 {len(messages)} 則訊息")
            
            # 生成廣播內容
            import google.generativeai as genai
            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompt = f"""你是一個頻率廣播電台的主持人，將收集到的訊息編織成優美的廣播。

收到的訊息片段：
{chr(10).join(messages)}

請根據以下要求生成廣播：
1. 找出訊息間共振的頻率和情緒，不要單純摘要
2. 用溫暖易懂的語言，捕捉這個時刻的集體脈動
3. 反映人們的共同情緒和關注點
4. 如果某些情緒特別強烈，要點出來
5. 長度控制在150-200字
6. 不要加音樂描述或旁白指示

請生成這個小時的頻率廣播："""
            
            try:
                response = model.generate_content(prompt)
                broadcast_content = response.candidates[0].content.parts[0].text
            except Exception as e:
                logger.error(f"Gemini API 錯誤: {e}")
                broadcast_content = f"📻 本小時收集了 {len(messages)} 則訊息，來自 {len(contributors)} 位朋友的分享。"
            
            # 儲存廣播
            broadcast_data = {
                'content': broadcast_content,
                'timestamp': hour * 3600,
                'message_count': len(messages),
                'contributor_count': len(contributors),
                'generated_at': datetime.now(),
                'hour': hour,
                'api_calls': 1,
                'optimization_type': 'retroactive',
                'compression_ratio': 1.0
            }
            
            db.collection('generated_broadcasts').document(str(hour)).set(broadcast_data)
            logger.info(f"Hour {hour} 廣播生成成功！")
            logger.info(f"內容預覽: {broadcast_content[:100]}...")
            
            # 避免 API 限制
            time.sleep(2)
            
        logger.info(f"\n完成！共生成 {len(missing_hours)} 個廣播")
        
    except Exception as e:
        logger.error(f"生成失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_missing_broadcasts()