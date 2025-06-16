#!/usr/bin/env python3
"""
測試 Firestore 寫入功能
"""

import os
import sys
from dotenv import load_dotenv
import logging
import time
from google.cloud import firestore
from datetime import datetime

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 載入環境變數
if os.path.exists('.env'):
    load_dotenv()

def test_firestore_write():
    """測試 Firestore 寫入"""
    try:
        # 直接初始化 Firestore 客戶端
        db = firestore.Client()
        logger.info("Firestore 客戶端初始化成功")
        
        # 測試寫入訊息
        current_hour = int(time.time()) // 3600
        test_messages = [
            ("測試訊息1", "測試用戶1"),
            ("測試訊息2", "測試用戶2"),
            ("測試訊息3", "測試用戶1"),
        ]
        
        # 手動寫入測試訊息
        for msg, user in test_messages:
            # 使用簡單的寫入方式
            message_ref = db.collection('broadcasts').document(str(current_hour)).collection('messages').document()
            message_data = {
                'content': msg,
                'user_id': user,
                'timestamp': datetime.now()
            }
            message_ref.set(message_data)
            logger.info(f"訊息已寫入: {msg} by {user}")
            
        # 更新統計
        stats_ref = db.collection('broadcasts').document(str(current_hour))
        stats_ref.set({
            'message_count': len(test_messages),
            'updated_at': datetime.now(),
            'hour': current_hour
        }, merge=True)
        logger.info(f"統計已更新")
        
        # 檢查文件是否存在
        doc = stats_ref.get()
        if doc.exists:
            logger.info(f"Firestore 文件存在: {doc.to_dict()}")
        else:
            logger.info("Firestore 文件不存在")
            
        # 檢查訊息子集合
        messages = list(stats_ref.collection('messages').limit(10).stream())
        logger.info(f"訊息子集合中有 {len(messages)} 則訊息")
        
        for i, msg_doc in enumerate(messages[:3]):
            logger.info(f"訊息 {i+1}: {msg_doc.to_dict()}")
            
        # 列出所有 broadcasts 集合的文件
        logger.info("\n檢查所有 broadcasts 文件:")
        broadcasts = db.collection('broadcasts').limit(10).stream()
        for broadcast_doc in broadcasts:
            logger.info(f"文件 ID: {broadcast_doc.id}, 資料: {broadcast_doc.to_dict()}")
            
        # 列出所有 generated_broadcasts 集合的文件
        logger.info("\n檢查所有 generated_broadcasts 文件:")
        generated = db.collection('generated_broadcasts').limit(10).stream()
        for gen_doc in generated:
            logger.info(f"文件 ID: {gen_doc.id}, 資料: {gen_doc.to_dict()}")
            
    except Exception as e:
        logger.error(f"測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_firestore_write()