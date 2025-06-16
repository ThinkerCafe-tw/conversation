"""
社群互動功能模組
包含文字接龍、投票、防災資訊等功能
"""

import time
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from word_chain_formatter import (
    format_word_chain_display, 
    format_chain_complete,
    format_chain_error,
    format_chain_status
)
from google.cloud import firestore # Added for joke feature
import random # For new get_random_joke strategy

logger = logging.getLogger(__name__)


class CommunityFeatures:
    def __init__(self, redis_client, knowledge_graph=None, db=None): # Added db
        self.redis = redis_client
        self.graph = knowledge_graph
        self.db = db # Store db instance
        self.api_usage_key = "api:usage:gemini"
        self.not_connected_message = "❌ 社群功能暫時無法使用"
        
    @property
    def connected(self):
        """檢查 Redis 是否連接"""
        if not self.redis:
            return False
        try:
            self.redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis 連接檢查失敗: {e}")
            return False
        
    # ========== API 統計功能 ==========
    def track_api_usage(self, tokens_used: int = 1):
        """追蹤 API 使用量"""
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")
        
        # 記錄每日和每月使用量
        self.redis.hincrby(f"{self.api_usage_key}:daily:{today}", "count", 1)
        self.redis.hincrby(f"{self.api_usage_key}:daily:{today}", "tokens", tokens_used)
        self.redis.hincrby(f"{self.api_usage_key}:monthly:{month}", "count", 1)
        self.redis.hincrby(f"{self.api_usage_key}:monthly:{month}", "tokens", tokens_used)
        
        # 設定過期時間
        self.redis.expire(f"{self.api_usage_key}:daily:{today}", 86400 * 7)  # 保留7天
        self.redis.expire(f"{self.api_usage_key}:monthly:{month}", 86400 * 35)  # 保留35天
        
    def get_api_stats(self) -> Dict:
        """獲取 API 使用統計"""
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")
        
        daily_stats = self.redis.hgetall(f"{self.api_usage_key}:daily:{today}")
        monthly_stats = self.redis.hgetall(f"{self.api_usage_key}:monthly:{month}")
        
        # 免費額度
        daily_limit = 1500
        monthly_limit = 45000
        
        daily_count = int(daily_stats.get('count', 0))
        monthly_count = int(monthly_stats.get('count', 0))
        
        # 預估月底使用量
        day_of_month = datetime.now().day
        days_in_month = 30
        estimated_monthly = int(monthly_count * days_in_month / day_of_month) if day_of_month > 0 else 0
        
        return {
            'daily': {
                'used': daily_count,
                'limit': daily_limit,
                'percentage': round(daily_count / daily_limit * 100, 1)
            },
            'monthly': {
                'used': monthly_count,
                'limit': monthly_limit,
                'percentage': round(monthly_count / monthly_limit * 100, 1),
                'estimated': estimated_monthly
            },
            'status': '✅ 正常' if monthly_count < monthly_limit * 0.8 else '⚠️ 接近上限'
        }
    
    # ========== 文字接龍功能 ==========
    def start_word_chain(self, word: str, user_id: str) -> Dict:
        """開始文字接龍"""
        if not self.connected:
            return {'success': False, 'message': self.not_connected_message}
            
        chain_key = "word_chain:current"
        
        # 檢查是否已有進行中的接龍
        existing = self.redis.get(chain_key)
        if existing:
            # 如果已有接龍，當作繼續接龍
            return self.continue_word_chain(word, user_id)
            
        chain_data = {
            'chain_id': f"chain_{int(time.time())}",
            'current_word': word,
            'chain': [word],
            'participants': [user_id],
            'created_at': int(time.time()),
            'target_length': 10
        }
        
        self.redis.setex(chain_key, 3600, json.dumps(chain_data))  # 1小時過期
        
        return {
            'success': True,
            'message': format_word_chain_display(chain_data, is_start=True)
        }
    
    def continue_word_chain(self, word: str, user_id: str) -> Dict:
        """繼續文字接龍"""
        if not self.connected:
            return {'success': False, 'message': self.not_connected_message}
            
        chain_key = "word_chain:current"
        chain_data = self.redis.get(chain_key)
        
        if not chain_data:
            return {'success': False, 'message': format_chain_error('no_chain', {})}
            
        chain = json.loads(chain_data)
        current_word = chain['current_word']
        
        # 檢查接龍是否有效（最後一個字要相同）
        if word[0] != current_word[-1]:
            return {
                'success': False, 
                'message': format_chain_error('wrong_start', {
                    'word': word,
                    'expected': current_word[-1]
                })
            }
            
        # 檢查是否重複
        if word in chain['chain']:
            return {
                'success': False,
                'message': format_chain_error('duplicate', {
                    'word': word,
                    'recent_words': chain['chain']
                })
            }
            
        # 更新接龍
        chain['chain'].append(word)
        chain['current_word'] = word
        if user_id not in chain['participants']:
            chain['participants'].append(user_id)
            
        progress = len(chain['chain'])
        
        # 檢查是否完成
        if progress >= chain['target_length']:
            self.redis.delete(chain_key)
            # 保存完成的接龍
            complete_key = f"word_chain:complete:{chain['chain_id']}"
            self.redis.setex(complete_key, 86400, json.dumps(chain))
            
            return {
                'success': True,
                'completed': True,
                'message': format_chain_complete(chain)
            }
        
        self.redis.setex(chain_key, 3600, json.dumps(chain))
        
        return {
            'success': True,
            'message': format_word_chain_display(chain)
        }
    
    def get_word_chain_status(self) -> Dict:
        """取得當前接龍狀態"""
        if not self.connected:
            return {'success': False, 'message': self.not_connected_message}
            
        chain_key = "word_chain:current"
        chain_data = self.redis.get(chain_key)
        
        if not chain_data:
            return {
                'success': True,
                'message': format_chain_status()
            }
        
        chain = json.loads(chain_data)
        return {
            'success': True,
            'message': format_word_chain_display(chain)
        }
    
    # ========== 投票功能 ==========
    def create_vote(self, topic: str, options: List[str], user_id: str) -> Dict:
        """創建投票"""
        vote_id = f"vote_{int(time.time())}"
        vote_key = f"votes:{vote_id}"
        
        vote_data = {
            'vote_id': vote_id,
            'topic': topic,
            'options': options,
            'votes': {opt: [] for opt in options},
            'created_by': user_id,
            'created_at': int(time.time()),
            'expires_at': int(time.time()) + 3600  # 1小時後過期
        }
        
        self.redis.setex(vote_key, 3600, json.dumps(vote_data))
        self.redis.set("votes:current", vote_id)  # 記錄當前投票
        
        options_text = '\n'.join([f"{i+1}️⃣ {opt} (0票)" for i, opt in enumerate(options)])
        
        return {
            'success': True,
            'message': f"📊 投票開始！主題：{topic}\n{options_text}\n回覆數字投票，輸入「投票結果」查看"
        }
    
    def cast_vote(self, option_num: int, user_id: str) -> Dict:
        """投票"""
        current_vote_id = self.redis.get("votes:current")
        if not current_vote_id:
            return {'success': False, 'message': '目前沒有進行中的投票'}
            
        vote_key = f"votes:{current_vote_id}"
        vote_data = self.redis.get(vote_key)
        
        if not vote_data:
            return {'success': False, 'message': '投票已結束'}
            
        vote = json.loads(vote_data)
        
        if option_num < 1 or option_num > len(vote['options']):
            return {'success': False, 'message': '無效的選項'}
            
        option = vote['options'][option_num - 1]
        
        # 檢查是否已投票
        for opt, voters in vote['votes'].items():
            if user_id in voters:
                return {'success': False, 'message': '您已經投過票了'}
                
        # 記錄投票
        vote['votes'][option].append(user_id)
        self.redis.setex(vote_key, 3600, json.dumps(vote))

        # Log vote to Neo4j
        if self.graph and self.graph.connected:
            try:
                self.graph.log_user_vote(
                    user_id=user_id,
                    vote_id=current_vote_id,
                    vote_topic=vote['topic'],
                    option_chosen=option
                )
                logger.info(f"Vote by {user_id} for vote {current_vote_id} ('{vote['topic']}') option '{option}' logged in Neo4j.")
            except Exception as e:
                # Log the error but don't let it break the primary functionality (voting in Redis)
                logger.error(f"Failed to log vote in Neo4j for user {user_id}, vote {current_vote_id}: {e}")
        
        return {
            'success': True,
            'message': f"✅ 投票成功！您投給了「{option}」"
        }
    
    def get_vote_results(self) -> Dict:
        """獲取投票結果"""
        current_vote_id = self.redis.get("votes:current")
        if not current_vote_id:
            return {'success': False, 'message': '目前沒有進行中的投票'}
            
        vote_key = f"votes:{current_vote_id}"
        vote_data = self.redis.get(vote_key)
        
        if not vote_data:
            return {'success': False, 'message': '投票已結束'}
            
        vote = json.loads(vote_data)
        
        results = []
        total_votes = sum(len(voters) for voters in vote['votes'].values())
        
        for i, option in enumerate(vote['options']):
            count = len(vote['votes'][option])
            percentage = round(count / total_votes * 100, 1) if total_votes > 0 else 0
            results.append(f"{i+1}️⃣ {option}: {count}票 ({percentage}%)")
            
        results_text = '\n'.join(results)
        
        return {
            'success': True,
            'message': f"📊 投票結果 - {vote['topic']}\n參與人數：{total_votes}\n\n{results_text}"
        }
    
    # ========== 防災資訊功能 ==========
    def add_shelter_info(self, location: str, shelter_type: str, capacity: int, user_id: str) -> Dict:
        """新增避難所資訊"""
        # 位置模糊化
        location_hash = hashlib.md5(location.encode()).hexdigest()[:8]
        district = self._extract_district(location)
        
        shelter_id = f"shelter_{location_hash}"
        shelter_key = f"shelters:{shelter_id}"
        
        shelter_data = {
            'shelter_id': shelter_id,
            'district': district,
            'type': shelter_type,
            'capacity': capacity,
            'verified_by': [user_id],
            'created_by': user_id,
            'created_at': int(time.time()),
            'status': 'pending'  # pending, verified
        }
        
        self.redis.set(shelter_key, json.dumps(shelter_data))
        self.redis.sadd("shelters:all", shelter_id)
        
        return {
            'success': True,
            'message': f"🏠 避難資訊已記錄\n地區：{district}\n類型：{shelter_type}\n容量：{capacity}人\n狀態：待驗證（需3人確認）"
        }
    
    def verify_shelter(self, shelter_id: str, user_id: str) -> Dict:
        """驗證避難所資訊"""
        shelter_key = f"shelters:{shelter_id}"
        shelter_data = self.redis.get(shelter_key)
        
        if not shelter_data:
            return {'success': False, 'message': '找不到此避難所資訊'}
            
        shelter = json.loads(shelter_data)
        
        if user_id in shelter['verified_by']:
            return {'success': False, 'message': '您已經驗證過了'}
            
        shelter['verified_by'].append(user_id)
        
        if len(shelter['verified_by']) >= 3:
            shelter['status'] = 'verified'
            
        self.redis.set(shelter_key, json.dumps(shelter))
        
        return {
            'success': True,
            'message': f"✅ 驗證成功！目前 {len(shelter['verified_by'])}/3 人確認",
            'verified': shelter['status'] == 'verified'
        }
    
    def add_supply_info(self, supply_type: str, quantity: str, location: str, contact: str, user_id: str) -> Dict:
        """新增物資資訊"""
        # 隱私保護
        location_district = self._extract_district(location)
        contact_hash = hashlib.md5(contact.encode()).hexdigest()[:6]
        
        supply_id = f"supply_{int(time.time())}_{user_id[:4]}"
        supply_key = f"supplies:{supply_id}"
        
        supply_data = {
            'supply_id': supply_id,
            'type': supply_type,
            'quantity': quantity,
            'location': location_district,
            'contact_hash': contact_hash,
            'provider': f"用戶#{user_id[-4:]}",
            'created_at': int(time.time()),
            'status': 'available',  # available, reserved, taken
            'expires_at': int(time.time()) + 86400 * 3  # 3天後過期
        }
        
        self.redis.setex(supply_key, 86400 * 3, json.dumps(supply_data))
        self.redis.sadd("supplies:available", supply_id)
        
        return {
            'success': True,
            'message': f"🥫 物資資訊已登記\n提供者：{supply_data['provider']}\n物資：{supply_type} {quantity}\n地區：{location_district}\n聯絡代碼：#{contact_hash}"
        }
    
    def _extract_district(self, location: str) -> str:
        """從地址提取區域（隱私保護）"""
        # 簡單的區域提取邏輯
        districts = ['中正區', '大同區', '中山區', '松山區', '大安區', '萬華區', 
                    '信義區', '士林區', '北投區', '內湖區', '南港區', '文山區']
        
        for district in districts:
            if district in location:
                return district
                
        # 如果找不到，返回模糊地區
        if '台北' in location or '臺北' in location:
            return '台北市'
        elif '新北' in location:
            return '新北市'
        else:
            return '其他地區'
    
    def get_emergency_summary(self) -> Dict:
        """獲取防災資訊摘要"""
        if not self.connected: # Ensure redis is connected for existing features
            logger.warning("Emergency summary attempted but Redis not connected.")
            # Return a structure that format_emergency_info_message can handle
            return {
                'shelters': {'total': 0, 'verified': 0, 'capacity': 0},
                'supplies': {'available': 0}
            }
        # 統計避難所
        shelter_ids = list(self.redis.smembers("shelters:all"))
        verified_shelters = 0
        total_capacity = 0
        
        for shelter_id in shelter_ids:
            shelter_data = self.redis.get(f"shelters:{shelter_id}")
            if shelter_data:
                shelter = json.loads(shelter_data)
                if shelter['status'] == 'verified':
                    verified_shelters += 1
                    total_capacity += shelter.get('capacity', 0)
        
        # 統計物資
        supply_ids = list(self.redis.smembers("supplies:available"))
        available_supplies = len(supply_ids)
        
        return {
            'shelters': {
                'total': len(shelter_ids),
                'verified': verified_shelters,
                'capacity': total_capacity
            },
            'supplies': {
                'available': available_supplies
            }
        }

    # ========== Joke Features ==========
    def add_joke(self, user_id: str, joke_text: str) -> Dict:
        """新增笑話到 Firestore"""
        if not self.db:
            return {'success': False, 'message': '❌ 笑話功能資料庫未連接'}

        try:
            joke_data = {
                'text': joke_text,
                'user_id': user_id, # Already anonymized hash from app.py
                'timestamp': datetime.now(),
                'status': 'approved', # Default status
                'category': '用戶分享',
                'likes': 0,
                'views': 0
            }
            doc_ref = self.db.collection('jokes').add(joke_data)
            new_joke_firestore_id = doc_ref[1].id # add() returns a tuple (timestamp, DocumentReference)
            logger.info(f"笑話已新增 by {user_id} to Firestore with ID: {new_joke_firestore_id}")

            # Log submission to Neo4j
            if self.graph and self.graph.connected:
                try:
                    # Use Firestore document ID as joke_id in Neo4j
                    self.graph.log_joke_submission(
                        user_id=user_id,
                        joke_id=new_joke_firestore_id,
                        joke_text_preview=joke_text[:50] # First 50 chars as preview
                    )
                    logger.info(f"Joke submission {new_joke_firestore_id} by {user_id} logged to Neo4j.")
                except Exception as e_neo:
                    logger.error(f"Failed to log joke submission {new_joke_firestore_id} to Neo4j: {e_neo}")
                    # Non-critical error, so we don't change the user-facing success message

            return {'success': True, 'message': '😄 你的笑話已成功收錄！感謝分享！'}
        except Exception as e:
            logger.error(f"新增笑話失敗: {e}")
            return {'success': False, 'message': '😥 新增笑話失敗，請稍後再試'}

    def get_random_joke(self, user_id_for_cache: Optional[str] = None) -> Dict: # Added user_id for caching
        """從 Firestore 獲取隨機笑話，並快取其 ID 給用戶"""
        if not self.db:
            return {'success': False, 'message': '❌ 笑話功能資料庫未連接'}
        try:
            # 使用不同的隨機策略來獲取笑話
            random_strategy = random.randint(1, 3)
            
            if random_strategy == 1:
                # 策略1: 使用隨機偏移
                total_jokes = 200  # 假設上限
                random_offset = random.randint(0, min(100, total_jokes))
                jokes_query = self.db.collection('jokes').limit(50).offset(random_offset)
            elif random_strategy == 2:
                # 策略2: 獲取前100則
                jokes_query = self.db.collection('jokes').limit(100)
            else:
                # 策略3: 獲取更大批次
                jokes_query = self.db.collection('jokes').limit(200)

            # 執行查詢
            joke_docs = list(jokes_query.stream())
            
            # 過濾出已批准的笑話（或所有笑話如果沒有狀態欄位）
            approved_jokes = []
            for doc in joke_docs:
                joke_data = doc.to_dict()
                # 如果沒有 status 欄位或 status 是 approved，都納入
                if joke_data.get('status', 'approved') == 'approved':
                    approved_jokes.append(doc)
            
            if not approved_jokes:
                logger.warning(f"策略 {random_strategy} 未找到可用笑話")
                # 嘗試直接獲取任何笑話
                any_jokes = list(self.db.collection('jokes').limit(50).stream())
                if any_jokes:
                    approved_jokes = any_jokes
                    logger.info("使用所有笑話（忽略狀態）")
                else:
                    return {'success': False, 'message': '目前還沒有笑話，快來輸入「笑話 [內容]」分享一個吧！'}
            
            # 從結果中隨機選擇一則
            selected_joke_doc = random.choice(approved_jokes)
            joke_firestore_id = selected_joke_doc.id
            joke_data = selected_joke_doc.to_dict()
            
            # 記錄 debug 資訊
            logger.info(f"使用策略 {random_strategy}，從 {len(approved_jokes)} 則笑話中選擇")
            
            # 處理可能的欄位名稱變化
            joke_user = joke_data.get('user_id', '匿名用戶')
            joke_text_content = joke_data.get('text') or joke_data.get('content') or '這個笑話不見了...'
            joke_category = joke_data.get('category', '綜合')
            
            # 更新瀏覽次數
            try:
                current_views = joke_data.get('views', 0)
                selected_joke_doc.reference.update({
                    'views': current_views + 1
                })
            except Exception as e:
                logger.warning(f"無法更新瀏覽次數: {e}")

            # 快取笑話 ID
            if user_id_for_cache and self.connected:
                try:
                    redis_key = f"user:{user_id_for_cache}:last_joke_id"
                    self.redis.setex(redis_key, 300, joke_firestore_id)
                    logger.info(f"Cached last joke ID {joke_firestore_id} for user {user_id_for_cache}")
                except Exception as e_redis:
                    logger.error(f"Failed to cache last joke ID for user {user_id_for_cache}: {e_redis}")

            response_data = {
                'success': True,
                'joke': {
                    'id': joke_firestore_id,
                    'text': joke_text_content,
                    'user': joke_user,
                    'category': joke_category
                },
                'message': f"🗣️ {joke_user} 分享的{joke_category}笑話：\n\n{joke_text_content}"
            }

            # 添加社交情境
            social_context_str = ""
            if self.graph and self.graph.connected and user_id_for_cache:
                try:
                    friend_ids = self.graph.get_friends_who_liked_joke(user_id_for_cache, joke_firestore_id)
                    if friend_ids:
                        display_friends = friend_ids[:2]
                        friends_list_str = ", ".join(display_friends)
                        if len(friend_ids) == 1:
                            social_context_str = f"\n\n💡 你的朋友 {friends_list_str} 也喜歡這個笑話！"
                        elif len(friend_ids) > 1:
                            additional_likes = len(friend_ids) - len(display_friends)
                            if additional_likes > 0:
                                social_context_str = f"\n\n💡 你的朋友們 {friends_list_str} 及其他 {additional_likes} 位也喜歡這個笑話！"
                            else:
                                social_context_str = f"\n\n💡 你的朋友們 {friends_list_str} 也都喜歡這個笑話！"
                except Exception as e_social:
                    logger.error(f"Error getting joke social context for joke {joke_firestore_id}: {e_social}")

            response_data['message'] += social_context_str
            return response_data
            
        except Exception as e:
            logger.error(f"獲取笑話失敗: Type: {type(e).__name__}, Details: {e}")
            import traceback
            logger.error(f"完整錯誤追蹤:\n{traceback.format_exc()}")
            
            # 更詳細的錯誤訊息
            if "IndexError" in str(type(e)):
                return {'success': False, 'message': '😅 笑話庫正在裝填中，請稍後再試！'}
            elif "Permission" in str(e):
                return {'success': False, 'message': '❌ 無法存取笑話資料庫，請聯絡管理員'}
            elif "credentials" in str(e).lower() or "auth" in str(e).lower():
                return {'success': False, 'message': '❌ 資料庫認證失敗，請聯絡管理員'}
            elif "not found" in str(e).lower():
                return {'success': False, 'message': '😅 笑話庫正在初始化，請稍後再試！'}
            else:
                # 生產環境不要顯示詳細錯誤
                return {'success': False, 'message': '😥 獲取笑話時發生錯誤，請稍後再試'}

    def like_last_joke(self, user_id: str) -> Dict:
        """對用戶上一個看到的笑話按讚"""
        if not self.connected: # Check Redis
            return {'success': False, 'message': self.not_connected_message}
        if not self.graph or not self.graph.connected: # Check Neo4j
             return {'success': False, 'message': '❌ 評價功能暫時無法連接知識圖譜'}

        try:
            redis_key = f"user:{user_id}:last_joke_id"
            last_joke_id = self.redis.get(redis_key)

            if not last_joke_id:
                return {'success': False, 'message': '您最近沒有看過笑話，或者時間太久了，無法評價。'}

            # Log the like to Neo4j
            self.graph.log_joke_like(user_id, last_joke_id)
            # Optionally, remove the key from Redis after liking to prevent multiple likes on same "last" joke?
            # self.redis.delete(redis_key)
            logger.info(f"User {user_id} liked joke {last_joke_id}. Logged to Neo4j.")
            return {'success': True, 'message': '👍 已讚！感謝您的評價。'}
        except Exception as e:
            logger.error(f"按讚笑話失敗 for user {user_id}: {e}")
            # Check if it's a Neo4j specific error from log_joke_like if it re-raises
            return {'success': False, 'message': '😥 按讚失敗，請稍後再試'}


def format_api_stats_message(stats: Dict) -> str:
    """格式化 API 統計訊息"""
    daily = stats['daily']
    monthly = stats['monthly']
    
    return f"""📊 Gemini API 使用狀況
━━━━━━━━━━━━━━
📅 今日使用
{daily['used']}/{daily['limit']} 次 ({daily['percentage']}%)

📈 本月使用  
{monthly['used']}/{monthly['limit']} 次 ({monthly['percentage']}%)
預估月底：{monthly['estimated']} 次

狀態：{stats['status']}
━━━━━━━━━━━━━━
💡 每次廣播生成約消耗 1 次配額"""


def format_emergency_info_message(summary: Dict) -> str:
    """格式化防災資訊訊息"""
    return f"""🚨 防災資訊總覽
━━━━━━━━━━━━━━
🏠 避難所資訊
總數：{summary['shelters']['total']} 處
已驗證：{summary['shelters']['verified']} 處
總容量：{summary['shelters']['capacity']} 人

🥫 物資共享
可用物資點：{summary['supplies']['available']} 處

━━━━━━━━━━━━━━
📝 提供資訊請輸入：
「防空 [地點] [類型] [容量]」
「物資 [類型] [數量] [地區] [聯絡]」"""