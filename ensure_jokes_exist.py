"""
確保資料庫中有笑話的輔助腳本
"""

import os
import logging
from google.cloud import firestore
from datetime import datetime
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ensure_jokes_exist():
    """確保資料庫中至少有一些笑話"""
    try:
        db = firestore.Client()
        
        # 檢查現有笑話數量
        existing_jokes = list(db.collection('jokes').limit(10).stream())
        logger.info(f"現有笑話數量: {len(existing_jokes)}")
        
        if len(existing_jokes) < 5:
            logger.info("笑話數量不足，添加一些基本笑話...")
            
            basic_jokes = [
                {
                    'text': '為什麼程式設計師不喜歡大自然？因為大自然有太多 bugs！',
                    'category': '程式設計',
                    'user_id': '系統_初始化',
                    'status': 'approved',
                    'timestamp': datetime.now(),
                    'likes': 0,
                    'views': 0
                },
                {
                    'text': '醫生：你要減肥了。病人：我有在運動啊！醫生：什麼運動？病人：我每天都在跑...跑去買珍奶。',
                    'category': '日常生活', 
                    'user_id': '系統_初始化',
                    'status': 'approved',
                    'timestamp': datetime.now(),
                    'likes': 0,
                    'views': 0
                },
                {
                    'text': '老闆說：我們是一個大家庭。我心想：難怪，在家裡我也不想工作。',
                    'category': '辦公室',
                    'user_id': '系統_初始化',
                    'status': 'approved',
                    'timestamp': datetime.now(),
                    'likes': 0,
                    'views': 0
                }
            ]
            
            for joke in basic_jokes:
                db.collection('jokes').add(joke)
                logger.info(f"添加笑話: {joke['text'][:30]}...")
                
            logger.info("基本笑話添加完成")
        else:
            logger.info("笑話數量充足")
            
        # 確保至少有一些笑話有 approved 狀態
        approved_count = 0
        for doc in existing_jokes:
            if doc.to_dict().get('status') == 'approved':
                approved_count += 1
                
        if approved_count == 0:
            logger.info("沒有已批准的笑話，批准前3則...")
            for doc in existing_jokes[:3]:
                doc.reference.update({'status': 'approved'})
            logger.info("笑話批准完成")
            
    except Exception as e:
        logger.error(f"錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    ensure_jokes_exist()
    print("\n✅ 笑話檢查完成")