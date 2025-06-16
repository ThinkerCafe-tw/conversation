"""
哨兵 (Sentry) - LINE 智慧摘要助理
每小時自動生成群組對話摘要
"""

import os
import json
import time
import redis
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import google.generativeai as genai
from linebot.v3.messaging import MessagingApi, PushMessageRequest, TextMessage, ApiClient, Configuration
import logging
import sentry_sdk

logger = logging.getLogger(__name__)


class SentryBot:
    def __init__(self):
        """初始化哨兵機器人"""
        # Redis 連線設定
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        
        # Gemini API 設定
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # LINE API 設定
        configuration = Configuration(access_token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
        self.line_bot_api = MessagingApi(ApiClient(configuration))
        
        # 設定
        self.anonymize_ttl = 70 * 60  # 70 分鐘
        self.message_ttl = 65 * 60    # 65 分鐘
        
    def anonymize_user_id(self, user_id: str, group_id: str) -> str:
        """將用戶 ID 匿名化"""
        # 為每個群組創建獨立的匿名化映射
        hash_key = f"anon_map:{group_id}"
        
        # 檢查是否已有映射
        anon_id = self.redis_client.hget(hash_key, user_id)
        if anon_id:
            return anon_id
            
        # 創建新的匿名 ID
        user_count = self.redis_client.hlen(hash_key)
        anon_id = f"使用者{chr(65 + user_count)}"  # 使用者A, 使用者B, ...
        
        # 儲存映射並設定 TTL
        self.redis_client.hset(hash_key, user_id, anon_id)
        self.redis_client.expire(hash_key, self.anonymize_ttl)
        
        return anon_id
    
    def store_message(self, group_id: str, user_id: str, message: str, timestamp: int):
        """儲存匿名化的訊息"""
        # 匿名化用戶 ID
        anon_id = self.anonymize_user_id(user_id, group_id)
        
        # LINE 的 timestamp 是毫秒，需要轉換成秒
        timestamp_seconds = timestamp / 1000
        
        # 準備訊息資料
        message_data = {
            "user": anon_id,
            "text": message,
            "timestamp": timestamp_seconds
        }
        
        # 儲存到 Redis Sorted Set（以時間戳排序）
        message_key = f"messages:{group_id}"
        self.redis_client.zadd(
            message_key,
            {json.dumps(message_data, ensure_ascii=False): timestamp_seconds}
        )
        self.redis_client.expire(message_key, self.message_ttl)
        
        logger.info(f"儲存訊息 - 群組: {group_id[:8]}..., 用戶: {anon_id}, 訊息長度: {len(message)}")
    
    def get_recent_messages(self, group_id: str, hours: int = 1) -> List[Dict]:
        """取得最近的訊息"""
        message_key = f"messages:{group_id}"
        
        # 計算時間範圍
        now = time.time()
        start_time = now - (hours * 3600)
        
        # 從 Redis 取得訊息
        messages = self.redis_client.zrangebyscore(
            message_key,
            start_time,
            now
        )
        
        # 解析訊息
        parsed_messages = []
        for msg in messages:
            try:
                parsed_messages.append(json.loads(msg))
            except json.JSONDecodeError:
                logger.error(f"無法解析訊息: {msg}")
                
        return parsed_messages
    
    def generate_summary(self, messages: List[Dict]) -> Optional[str]:
        """使用 Gemini 生成摘要"""
        if not messages:
            return None
            
        # 準備對話內容
        conversation = "\n".join([
            f"{msg['user']}: {msg['text']}"
            for msg in messages
        ])
        
        logger.info(f"準備生成摘要，對話長度: {len(conversation)}")
        logger.info(f"對話內容預覽: {conversation[:100]}...")
        
        # 準備提示詞
        prompt = f"""請為以下 LINE 群組對話生成一個簡潔的摘要。

要求：
1. 摘要必須是繁體中文
2. 使用條列式格式，每個要點一行
3. 長度控制在 50-100 字內
4. 只摘要重要的討論內容和決定
5. 保持中立客觀，不要加入個人意見
6. 絕對不要猜測或還原真實的用戶身份

對話內容：
{conversation}

摘要："""
        
        try:
            # 直接使用字串
            response = self.model.generate_content(prompt)
            # 直接從 candidates 獲取文本
            if response and response.candidates:
                candidate = response.candidates[0]
                if candidate.content and candidate.content.parts:
                    # 獲取第一個 part 的文本
                    part = candidate.content.parts[0]
                    if hasattr(part, 'text'):
                        return part.text
                    else:
                        logger.error(f"Part 沒有 text 屬性: {part}")
                        return None
            logger.error(f"Gemini API 回應結構無效")
            return None
        except Exception as e:
            logger.error(f"Gemini API 錯誤: {e}")
            logger.error(f"錯誤類型: {type(e)}")
            import traceback
            logger.error(f"完整錯誤追蹤:\n{traceback.format_exc()}")
            sentry_sdk.capture_exception(e)
            return None
    
    def send_summary_to_group(self, group_id: str, summary: str):
        """發送摘要到群組"""
        try:
            # 加上時間標記
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            message = f"📊 過去一小時對話摘要 ({now})\n\n{summary}"
            
            self.line_bot_api.push_message(
                PushMessageRequest(
                    to=group_id,
                    messages=[TextMessage(text=message)]
                )
            )
            logger.info(f"摘要已發送到群組: {group_id[:8]}...")
        except Exception as e:
            logger.error(f"發送摘要失敗: {e}")
            sentry_sdk.capture_exception(e)
    
    def process_group_summary(self, group_id: str):
        """處理單一群組的摘要"""
        logger.info(f"開始處理群組摘要: {group_id[:8]}...")
        
        # 1. 取得最近一小時的訊息
        messages = self.get_recent_messages(group_id)
        
        if not messages:
            logger.info(f"群組 {group_id[:8]}... 沒有訊息需要摘要")
            return
            
        logger.info(f"找到 {len(messages)} 則訊息")
        
        # 2. 生成摘要
        summary = self.generate_summary(messages)
        
        if not summary:
            logger.error(f"無法生成摘要 - 群組: {group_id[:8]}...")
            return
            
        # 3. 發送摘要
        self.send_summary_to_group(group_id, summary)
        
        # 4. 清理過期的匿名化映射
        self.cleanup_old_data(group_id)
    
    def cleanup_old_data(self, group_id: str):
        """清理過期資料"""
        # Redis 會自動處理 TTL，這裡可以做額外的清理工作
        pass
    
    def get_active_groups(self) -> List[str]:
        """取得所有有訊息的群組"""
        # 從 Redis 中找出所有訊息鍵
        pattern = "messages:*"
        groups = []
        
        for key in self.redis_client.scan_iter(match=pattern):
            group_id = key.replace("messages:", "")
            groups.append(group_id)
            
        return groups
    
    def run_hourly_summary(self):
        """執行每小時摘要任務"""
        logger.info("開始執行每小時摘要任務")
        
        # 取得所有活躍的群組
        groups = self.get_active_groups()
        logger.info(f"找到 {len(groups)} 個活躍群組")
        
        # 處理每個群組
        for group_id in groups:
            try:
                self.process_group_summary(group_id)
            except Exception as e:
                logger.error(f"處理群組 {group_id[:8]}... 時發生錯誤: {e}")
                sentry_sdk.capture_exception(e)
        
        logger.info("每小時摘要任務完成")