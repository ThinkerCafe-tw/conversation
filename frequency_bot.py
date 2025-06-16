"""
頻率共振廣播系統
將所有聲音編織成集體意識的廣播
"""

import os
import json
import time
import redis
from datetime import datetime
import google.generativeai as genai
import logging
import sentry_sdk

logger = logging.getLogger(__name__)


class FrequencyBot:
    def __init__(self):
        """初始化頻率廣播機器人"""
        # Redis 連線
        self.redis_client = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True
        )
        
        # Gemini API 設定
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        self.broadcast_ttl = 24 * 60 * 60  # 廣播保留24小時
        
    def add_to_broadcast(self, message: str, user_id: str = None):
        """將訊息加入廣播池"""
        current_hour = int(time.time()) // 3600
        hour_key = f"broadcast:messages:{current_hour}"
        
        # 加入訊息
        self.redis_client.rpush(hour_key, message)
        self.redis_client.expire(hour_key, 7200)  # 保留2小時
        
        # 追蹤貢獻者
        if user_id:
            self.track_contributor(user_id)
        
        logger.info(f"訊息已加入廣播池 - 小時: {current_hour}")
        
        # 返回當前訊息數以供即時回饋
        message_count = self.redis_client.llen(hour_key)
        return message_count
        
    def generate_hourly_broadcast(self):
        """生成每小時的頻率廣播"""
        current_hour = int(time.time()) // 3600
        hour_key = f"broadcast:messages:{current_hour}"
        
        # 獲取這個小時的所有訊息
        messages = self.redis_client.lrange(hour_key, 0, -1)
        
        if not messages:
            logger.info(f"小時 {current_hour} 沒有訊息")
            return None
            
        logger.info(f"準備生成廣播 - 訊息數: {len(messages)}")
        
        # 如果訊息超過1000則，只取前1000則
        if len(messages) > 1000:
            messages = messages[:1000]
            prompt_prefix = "（以下為前1000則訊息）\n"
        else:
            prompt_prefix = ""
        
        # 準備提示詞
        prompt = f"""你是一個頻率廣播電台的主持人，將收集到的訊息編織成優美的廣播。

{prompt_prefix}收到的訊息片段：
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
            response = self.model.generate_content(prompt)
            if response and response.candidates:
                broadcast_content = response.candidates[0].content.parts[0].text
                
                # 儲存廣播
                broadcast_data = {
                    'content': broadcast_content,
                    'timestamp': current_hour * 3600,
                    'message_count': len(messages),
                    'generated_at': int(time.time())
                }
                
                broadcast_key = f"broadcast:generated:{current_hour}"
                self.redis_client.set(
                    broadcast_key,
                    json.dumps(broadcast_data, ensure_ascii=False),
                    ex=self.broadcast_ttl
                )
                
                logger.info(f"廣播生成成功 - 小時: {current_hour}")
                return broadcast_data
                
        except Exception as e:
            logger.error(f"生成廣播失敗: {e}")
            sentry_sdk.capture_exception(e)
            return None
            
    def get_latest_broadcast(self):
        """獲取最新的廣播"""
        current_hour = int(time.time()) // 3600
        
        # 先檢查當前小時
        for hour_offset in range(0, 24):
            check_hour = current_hour - hour_offset
            broadcast_key = f"broadcast:generated:{check_hour}"
            
            broadcast_data = self.redis_client.get(broadcast_key)
            if broadcast_data:
                return json.loads(broadcast_data)
                
        return None
        
    def get_broadcast_by_time(self, hour: int):
        """獲取特定時間的廣播"""
        broadcast_key = f"broadcast:generated:{hour}"
        broadcast_data = self.redis_client.get(broadcast_key)
        
        if broadcast_data:
            return json.loads(broadcast_data)
        return None
        
    def get_frequency_stats(self):
        """獲取當前頻率統計"""
        current_hour = int(time.time()) // 3600
        hour_key = f"broadcast:messages:{current_hour}"
        
        messages = self.redis_client.lrange(hour_key, 0, -1)
        message_count = len(messages)
        
        # 簡單的詞頻統計
        word_freq = {}
        for msg in messages:
            words = msg.split()
            for word in words:
                if len(word) > 1:  # 忽略單字
                    word_freq[word] = word_freq.get(word, 0) + 1
                    
        # 返回前10個高頻詞
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # 計算進度和時間
        progress_percent = min(int((message_count / 1000) * 100), 100)
        messages_needed = max(0, 1000 - message_count)
        
        # 計算下次廣播時間
        current_time = int(time.time())
        next_hour = ((current_hour + 1) * 3600)
        time_until_broadcast = next_hour - current_time
        minutes_left = time_until_broadcast // 60
        seconds_left = time_until_broadcast % 60
        
        # 獲取活躍用戶統計
        contributors = self.get_contributors_stats(current_hour)
        
        return {
            'message_count': message_count,
            'progress_percent': progress_percent,
            'messages_needed': messages_needed,
            'time_until_broadcast': {
                'minutes': minutes_left,
                'seconds': seconds_left
            },
            'top_frequencies': top_words,
            'contributors': contributors
        }
    
    def get_contributors_stats(self, hour: int):
        """獲取貢獻者統計"""
        stats_key = f"broadcast:contributors:{hour}"
        contributors = self.redis_client.hgetall(stats_key)
        
        # 轉換為整數並排序
        contributor_list = [(user, int(count)) for user, count in contributors.items()]
        contributor_list.sort(key=lambda x: x[1], reverse=True)
        
        return {
            'total_users': len(contributor_list),
            'top_contributors': contributor_list[:5]
        }
    
    def track_contributor(self, user_id: str):
        """追蹤貢獻者"""
        current_hour = int(time.time()) // 3600
        stats_key = f"broadcast:contributors:{current_hour}"
        
        # 增加用戶貢獻計數
        self.redis_client.hincrby(stats_key, user_id, 1)
        self.redis_client.expire(stats_key, 7200)  # 保留2小時


def format_broadcast_message(broadcast_data):
    """格式化廣播訊息"""
    if not broadcast_data:
        return "📡 目前還沒有廣播"
        
    timestamp = datetime.fromtimestamp(broadcast_data['timestamp'])
    time_str = timestamp.strftime("%Y-%m-%d %H:00")
    
    message = f"""🌊 頻率廣播
📅 {time_str}
━━━━━━━━━━━━━━

{broadcast_data['content']}

━━━━━━━━━━━━━━
💭 共 {broadcast_data['message_count']} 個聲音參與共振
✨ 輸入「廣播」查詢最新內容"""
    
    return message


def format_stats_message(stats):
    """格式化統計訊息 - 即時互動顯示"""
    progress_bar = create_progress_bar(stats['progress_percent'])
    
    # 建立熱詞清單
    hot_words = []
    for word, count in stats['top_frequencies'][:5]:
        hot_words.append(f"「{word}」×{count}")
    hot_words_str = " ".join(hot_words) if hot_words else "等待更多訊息..."
    
    # 建立貢獻者排行
    contributors_str = ""
    if stats['contributors']['top_contributors']:
        contributors_list = []
        for i, (user, count) in enumerate(stats['contributors']['top_contributors'], 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "🏅"
            contributors_list.append(f"{medal} {user} ({count}則)")
        contributors_str = "\n".join(contributors_list)
    else:
        contributors_str = "期待第一位參與者！"
    
    message = f"""📊 即時頻率統計
━━━━━━━━━━━━━━

⏰ 下次廣播倒數：{stats['time_until_broadcast']['minutes']}分{stats['time_until_broadcast']['seconds']}秒

📈 本小時進度
{progress_bar}
💬 {stats['message_count']}/1000 則 ({stats['progress_percent']}%)

🔥 熱門頻率
{hot_words_str}

🏆 參與排行榜 (共{stats['contributors']['total_users']}人)
{contributors_str}

━━━━━━━━━━━━━━
💡 當訊息達1000則將提前生成廣播！
🎯 快邀請朋友一起參與全民共編"""
    
    return message


def format_instant_feedback(message_count, user_rank=None):
    """格式化即時回饋訊息"""
    milestone_messages = {
        1: "🎉 第一則訊息！開啟這小時的共振",
        10: "🌱 種子發芽了！已有10則訊息",
        50: "🌿 頻率漸強！50則訊息達成",
        100: "🌳 百則達成！聲音開始共鳴",
        250: "🔥 四分之一進度！熱度上升中",
        500: "⚡ 半程達標！500則訊息",
        750: "🚀 衝刺階段！剩最後250則",
        900: "💫 即將完成！還差100則",
        950: "🎊 最後衝刺！還差50則",
        1000: "🎆 達標！1000則訊息，準備生成廣播！"
    }
    
    # 尋找最接近的里程碑
    feedback = ""
    for milestone, msg in milestone_messages.items():
        if message_count == milestone:
            feedback = msg
            break
    
    # 如果不是里程碑，給予一般回饋
    if not feedback:
        if message_count < 100:
            feedback = f"✨ 第{message_count}則！繼續加油"
        elif message_count < 500:
            feedback = f"🌊 第{message_count}則！頻率漸強"
        elif message_count < 900:
            feedback = f"🔥 第{message_count}則！共振升溫"
        else:
            feedback = f"⚡ 第{message_count}則！即將達標"
    
    # 加入用戶排名資訊
    if user_rank and user_rank <= 10:
        rank_emoji = "🥇" if user_rank == 1 else "🥈" if user_rank == 2 else "🥉" if user_rank == 3 else "🏅"
        feedback += f"\n{rank_emoji} 你是第{user_rank}名貢獻者！"
    
    return feedback


def create_progress_bar(percent):
    """建立視覺化進度條"""
    filled = int(percent / 10)
    empty = 10 - filled
    bar = "█" * filled + "░" * empty
    return f"[{bar}]"