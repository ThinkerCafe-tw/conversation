"""
頻率共振廣播系統 - Firestore 版本
使用 Google Firestore 實現零成本方案
"""

import os
import time
import logging
from datetime import datetime, timedelta
from google.cloud import firestore
from google.cloud.firestore_v1 import Increment
from google.api_core import retry
import google.generativeai as genai
import sentry_sdk
from knowledge_graph import KnowledgeGraph
from collective_memory import CollectiveMemorySystem, MemoryAnalyzer

logger = logging.getLogger(__name__)


class FrequencyBotFirestore:
    def __init__(self, knowledge_graph=None):
        """初始化頻率廣播機器人 (Firestore 版本)"""
        # 初始化 Firestore
        self.db = firestore.Client()
        
        # Gemini API 設定
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 設定集合名稱
        self.broadcasts_collection = 'broadcasts'
        self.generated_collection = 'generated_broadcasts'
        
        # 初始化知識圖譜和集體記憶系統
        self.graph = knowledge_graph
        if self.graph:
            self.memory_system = CollectiveMemorySystem(self.graph)
            self.memory_analyzer = MemoryAnalyzer(self.graph)
        else:
            self.memory_system = None
            self.memory_analyzer = None
        
    def add_to_broadcast(self, message: str, user_id: str = None):
        """將訊息加入廣播池並同步到集體記憶"""
        current_hour = int(time.time()) // 3600
        
        # 使用批次寫入提高效能
        batch = self.db.batch()
        
        # 儲存訊息
        message_ref = self.db.collection(self.broadcasts_collection).document(str(current_hour)).collection('messages').document()
        message_data = {
            'content': message,
            'user_id': user_id,
            'timestamp': datetime.now()
        }
        batch.set(message_ref, message_data)
        
        # 同步到集體記憶系統
        if self.memory_system and user_id:
            try:
                memory_result = self.memory_system.process_message(user_id, message)
                logger.info(f"訊息已加入集體記憶: {memory_result.get('message_id')}")
            except Exception as e:
                logger.warning(f"無法加入集體記憶: {e}")
        
        # 更新統計（使用 merge 避免覆蓋）
        stats_ref = self.db.collection(self.broadcasts_collection).document(str(current_hour))
        batch.set(stats_ref, {
            'message_count': Increment(1),
            'updated_at': datetime.now(),
            'hour': current_hour
        }, merge=True)
        
        # 更新用戶貢獻
        if user_id:
            contrib_ref = stats_ref.collection('contributors').document(user_id)
            batch.set(contrib_ref, {
                'count': Increment(1),
                'last_message': datetime.now()
            }, merge=True)
        
        # 執行批次寫入
        batch.commit()
        
        # 獲取並返回當前訊息數
        doc = stats_ref.get()
        message_count = doc.to_dict().get('message_count', 1) if doc.exists else 1
        
        logger.info(f"訊息已加入廣播池 - 小時: {current_hour}, 總數: {message_count}")
        return message_count
        
    def get_frequency_stats(self):
        """獲取當前頻率統計"""
        current_hour = int(time.time()) // 3600
        doc_ref = self.db.collection(self.broadcasts_collection).document(str(current_hour))
        
        # 獲取統計資料
        doc = doc_ref.get()
        if not doc.exists:
            return self._empty_stats()
            
        stats = doc.to_dict()
        message_count = stats.get('message_count', 0)
        
        # 獲取貢獻者排行（使用快照減少讀取次數）
        contributors = []
        contrib_query = doc_ref.collection('contributors').order_by('count', direction=firestore.Query.DESCENDING).limit(5)
        
        for contrib_doc in contrib_query.stream():
            data = contrib_doc.to_dict()
            contributors.append((contrib_doc.id, data['count']))
        
        # 獲取總用戶數（使用聚合查詢）
        total_users = len(list(doc_ref.collection('contributors').list_documents()))
        
        # 計算進度和時間
        progress_percent = min(int((message_count / 1000) * 100), 100)
        messages_needed = max(0, 1000 - message_count)
        
        current_time = int(time.time())
        next_hour = ((current_hour + 1) * 3600)
        time_until_broadcast = next_hour - current_time
        
        # 簡單的詞頻分析（為了節省讀取次數，只在訊息少於100時執行）
        top_frequencies = []
        if message_count < 100:
            word_freq = {}
            messages_query = doc_ref.collection('messages').limit(100)
            for msg_doc in messages_query.stream():
                content = msg_doc.to_dict().get('content', '')
                words = content.split()
                for word in words:
                    if len(word) > 1:
                        word_freq[word] = word_freq.get(word, 0) + 1
            
            top_frequencies = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'message_count': message_count,
            'progress_percent': progress_percent,
            'messages_needed': messages_needed,
            'time_until_broadcast': {
                'minutes': time_until_broadcast // 60,
                'seconds': time_until_broadcast % 60
            },
            'top_frequencies': top_frequencies,
            'contributors': {
                'total_users': total_users,
                'top_contributors': contributors
            }
        }
    
    def generate_hourly_broadcast(self):
        """生成每小時的頻率廣播（支援10x優化）"""
        current_hour = int(time.time()) // 3600
        doc_ref = self.db.collection(self.broadcasts_collection).document(str(current_hour))
        
        # 檢查是否已生成過
        existing_broadcast = self.db.collection(self.generated_collection).document(str(current_hour)).get()
        if existing_broadcast.exists:
            logger.info(f"小時 {current_hour} 的廣播已存在")
            return existing_broadcast.to_dict()
        
        # 獲取所有訊息（限制1000則）
        messages = []
        message_dicts = []
        contributors = set()
        messages_query = doc_ref.collection('messages').limit(1000).order_by('timestamp')
        
        for msg_doc in messages_query.stream():
            data = msg_doc.to_dict()
            messages.append(data['content'])
            message_dicts.append({
                'content': data['content'],
                'user_id': data.get('user_id', '匿名'),
                'timestamp': data.get('timestamp')
            })
            contributors.add(data.get('user_id', '匿名'))
            
        if not messages:
            logger.info(f"小時 {current_hour} 沒有訊息")
            return None
            
        logger.info(f"準備生成廣播 - 訊息數: {len(messages)}")
        
        broadcast_content = ""
        compression_ratio = 1.0
        optimization_type = "standard"
        
        # 嘗試使用10x核心價值優化器（Elon Musk要求）
        if len(messages) >= 100:
            try:
                from optimizations.core_value_optimizer import CoreValueOptimizer
                core_optimizer = CoreValueOptimizer(self.graph)
                optimization_result = core_optimizer.generate_10x_broadcast(message_dicts)
                broadcast_content = optimization_result['broadcast']
                compression_ratio = optimization_result['compression_ratio']
                optimization_type = "10x_optimized"
                logger.info(f"使用10x優化器，達成 {compression_ratio:.1f}x 壓縮")
            except Exception as e:
                logger.warning(f"10x優化器未啟用或失敗: {e}")
        
        # 如果10x失敗，嘗試集體記憶系統
        if not broadcast_content and self.memory_system and len(messages) >= 10:
            try:
                prompt = self.memory_system.generate_broadcast_prompt(current_hour % 24)
                response = self.model.generate_content(prompt)
                if response and response.candidates:
                    broadcast_content = response.candidates[0].content.parts[0].text
                    optimization_type = "collective_memory"
                    logger.info("使用集體記憶系統生成廣播")
            except Exception as e:
                logger.warning(f"集體記憶系統失敗: {e}")
        
        # 降級到標準廣播
        if not broadcast_content:
            prompt = self._create_prompt(messages)
            try:
                response = self.model.generate_content(prompt)
                if response and response.candidates:
                    broadcast_content = response.candidates[0].content.parts[0].text
                    optimization_type = "standard"
            except Exception as e:
                logger.error(f"Gemini API 錯誤: {e}")
                broadcast_content = f"📻 本小時收集了 {len(messages)} 則訊息，來自 {len(contributors)} 位朋友的分享。"
                optimization_type = "fallback"
        
        # 儲存廣播結果
        broadcast_data = {
            'content': broadcast_content,
            'timestamp': current_hour * 3600,
            'message_count': len(messages),
            'contributor_count': len(contributors),
            'generated_at': datetime.now(),
            'hour': current_hour,
            'api_calls': 1,
            'optimization_type': optimization_type,
            'compression_ratio': compression_ratio
        }
        
        self.db.collection(self.generated_collection).document(str(current_hour)).set(broadcast_data)
        
        logger.info(f"廣播生成成功 - 小時: {current_hour}, 類型: {optimization_type}")
        
        # 觸發清理任務
        self._schedule_cleanup(current_hour)
        
        return broadcast_data
    
    def get_latest_broadcast(self):
        """獲取最新的廣播"""
        # 查詢最近24小時的廣播
        twenty_four_hours_ago = int(time.time()) - (24 * 3600)
        
        broadcasts = self.db.collection(self.generated_collection)\
            .where('timestamp', '>=', twenty_four_hours_ago)\
            .order_by('timestamp', direction=firestore.Query.DESCENDING)\
            .limit(1)\
            .stream()
        
        for broadcast in broadcasts:
            return broadcast.to_dict()
            
        return None
    
    def get_broadcast_by_time(self, hour: int):
        """獲取特定時間的廣播"""
        doc = self.db.collection(self.generated_collection).document(str(hour)).get()
        return doc.to_dict() if doc.exists else None
    
    def track_contributor(self, user_id: str):
        """追蹤貢獻者（已整合在 add_to_broadcast 中）"""
        pass  # 功能已整合
    
    def get_contributors_stats(self, hour: int):
        """獲取貢獻者統計（已整合在 get_frequency_stats 中）"""
        pass  # 功能已整合
    
    def _empty_stats(self):
        """返回空統計資料"""
        current_hour = int(time.time()) // 3600
        current_time = int(time.time())
        next_hour = ((current_hour + 1) * 3600)
        time_until_broadcast = next_hour - current_time
        
        return {
            'message_count': 0,
            'progress_percent': 0,
            'messages_needed': 1000,
            'time_until_broadcast': {
                'minutes': time_until_broadcast // 60,
                'seconds': time_until_broadcast % 60
            },
            'top_frequencies': [],
            'contributors': {
                'total_users': 0,
                'top_contributors': []
            }
        }
    
    def _create_prompt(self, messages):
        """創建 AI 提示詞"""
        # 如果有集體記憶系統，使用智慧提示詞
        if self.memory_system:
            current_hour = int(time.time()) // 3600
            return self.memory_system.generate_broadcast_prompt(current_hour)
        
        # 否則使用原本的簡單提示詞
        prompt_prefix = ""
        if len(messages) > 1000:
            messages = messages[:1000]
            prompt_prefix = "（以下為前1000則訊息）\n"
            
        return f"""你是一個頻率廣播電台的主持人，將收集到的訊息編織成優美的廣播。

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
    
    def _schedule_cleanup(self, current_hour):
        """排程清理任務（將由 Cloud Scheduler 處理）"""
        # 標記需要清理的舊資料
        cleanup_hour = current_hour - 24
        cleanup_ref = self.db.collection('cleanup_tasks').document()
        cleanup_ref.set({
            'hour_to_cleanup': cleanup_hour,
            'scheduled_at': datetime.now(),
            'status': 'pending'
        })
    
    def cleanup_old_data(self):
        """清理超過24小時的資料"""
        # 獲取待清理任務
        tasks = self.db.collection('cleanup_tasks')\
            .where('status', '==', 'pending')\
            .limit(10)\
            .stream()
        
        for task_doc in tasks:
            task_data = task_doc.to_dict()
            hour_to_cleanup = task_data['hour_to_cleanup']
            
            try:
                # 刪除舊的廣播資料
                self._delete_broadcast_data(hour_to_cleanup)
                
                # 更新任務狀態
                task_doc.reference.update({
                    'status': 'completed',
                    'completed_at': datetime.now()
                })
                
                logger.info(f"已清理小時 {hour_to_cleanup} 的資料")
                
            except Exception as e:
                logger.error(f"清理失敗: {e}")
                task_doc.reference.update({
                    'status': 'failed',
                    'error': str(e)
                })
    
    def _delete_broadcast_data(self, hour: int):
        """刪除特定小時的廣播資料"""
        batch = self.db.batch()
        batch_count = 0
        max_batch_size = 500  # Firestore 批次限制
        
        # 刪除訊息
        doc_ref = self.db.collection(self.broadcasts_collection).document(str(hour))
        messages = doc_ref.collection('messages').list_documents()
        
        for msg_ref in messages:
            batch.delete(msg_ref)
            batch_count += 1
            
            if batch_count >= max_batch_size:
                batch.commit()
                batch = self.db.batch()
                batch_count = 0
        
        # 刪除貢獻者
        contributors = doc_ref.collection('contributors').list_documents()
        for contrib_ref in contributors:
            batch.delete(contrib_ref)
            batch_count += 1
            
            if batch_count >= max_batch_size:
                batch.commit()
                batch = self.db.batch()
                batch_count = 0
        
        # 刪除主文件
        batch.delete(doc_ref)
        
        # 提交最後的批次
        if batch_count > 0:
            batch.commit()


# 保持與原版相容的輔助函數
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
        1: "🎉 第一則訊息！開啟這小時的共振\n\n💡 輸入「玩」探索更多功能",
        10: "🌱 種子發芽了！已有10則訊息\n\n💡 輸入「統計」查看即時進度",
        50: "🌿 頻率漸強！50則訊息達成",
        100: "🌳 百則達成！聲音開始共鳴\n\n💡 輸入「看」查看各種統計",
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