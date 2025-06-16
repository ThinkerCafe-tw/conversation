from flask import Flask, request, abort, jsonify
from linebot.v3.webhook import WebhookHandler
from linebot.v3.messaging import MessagingApi, ReplyMessageRequest, TextMessage, ApiClient, Configuration
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import os
import time
from datetime import datetime
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
import logging
from frequency_bot_firestore import (
    FrequencyBotFirestore, 
    format_broadcast_message,
    format_stats_message,
    format_instant_feedback
)
from google.cloud import firestore
import redis
from community_features import (
    CommunityFeatures,
    format_api_stats_message,
    format_emergency_info_message
)
from knowledge_graph import KnowledgeGraph
from intent_analyzer import IntentAnalyzer
from security_filter import SecurityFilter

# 導入優化模組
try:
    from optimizations.smart_onboarding import SmartOnboarding, SmartErrorHandler
    from optimizations.performance_dashboard import PerformanceDashboard
    from optimizations.core_value_optimizer import CoreValueOptimizer
    OPTIMIZATIONS_AVAILABLE = True
except ImportError:
    logging.warning("優化模組未找到，使用基礎功能")
    OPTIMIZATIONS_AVAILABLE = False

# 載入環境變量（開發環境用）
if os.path.exists('.env'):
    load_dotenv()

# 初始化 Sentry
sentry_dsn = os.getenv('SENTRY_DSN')
if sentry_dsn and not sentry_dsn.startswith('https://your_'):
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            FlaskIntegration(
                transaction_style='endpoint',
            ),
        ],
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        environment=os.getenv('ENVIRONMENT', 'development'),
        release=os.getenv('RELEASE_VERSION', 'frequency-bot@1.0.0')
    )
    print("Sentry 已啟用")
else:
    print("警告: Sentry DSN 未設定或使用範例值，Sentry 未啟用")

app = Flask(__name__)

# 設定日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 從環境變量讀取 LINE 憑證
configuration = Configuration(access_token=os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
line_bot_api = MessagingApi(ApiClient(configuration))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 初始化知識圖譜和意圖分析器
try:
    knowledge_graph = KnowledgeGraph()
    intent_analyzer = IntentAnalyzer(knowledge_graph)
    logger.info("知識圖譜連接成功")
except Exception as e:
    logger.warning(f"知識圖譜連接失敗: {e}，智慧功能將受限")
    knowledge_graph = None
    intent_analyzer = None

# 初始化頻率廣播機器人 (傳入知識圖譜以支援集體記憶)
frequency_bot = FrequencyBotFirestore(knowledge_graph)

# 初始化 Redis 和社群功能
try:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        password=os.getenv('REDIS_PASSWORD'),
        username=os.getenv('REDIS_USERNAME', 'default'),
        decode_responses=True,
        socket_keepalive=True,
        socket_connect_timeout=5
    )
    redis_client.ping()
    # 傳入知識圖譜實例以支援雙寫及 Firestore db
    community = CommunityFeatures(redis_client, knowledge_graph, frequency_bot.db)
    logger.info("Redis 連接成功, CommunityFeatures 初始化完畢 (含 Firestore DB)")
except Exception as e:
    logger.warning(f"Redis 連接失敗或 CommunityFeatures 初始化失敗: {e}，社群功能將受限")
    redis_client = None
    community = None

# 初始化安全過濾器
security_filter = SecurityFilter()
logger.info("安全過濾器初始化成功")

# 定義快捷選單資料結構
QUICK_MENUS = {
    "玩": {
        "title": "🎮 選擇遊戲",
        "options": [
            ("🔗 文字接龍", "接龍範例"),
            ("📊 發起投票", "投票範例"),
            ("💭 查看廣播", "廣播"),
            ("💝 更多功能", "幫助")
        ],
        "footer": "💡 輸入「指令」即可開始！"
    },
    "看": {
        "title": "📊 查看資訊",
        "options": [
            ("📈 即時統計", "統計"),
            ("🤖 API用量", "API統計"),
            ("🌊 最新廣播", "廣播"),
            ("🏆 排行榜", "排行")
        ],
        "footer": "💡 輸入「指令」即可開始！"
    },
    "救": {
        "title": "🚨 防災互助",
        "options": [
            ("🏠 避難所", "防災資訊"),
            ("📝 提供避難所", "防空範例"),
            ("🥫 物資分享", "物資範例"),
            ("🗺 查看地圖", "防災地圖")
        ],
        "footer": "💡 輸入「指令」即可開始！"
    }
}

# 初始化優化系統
if OPTIMIZATIONS_AVAILABLE:
    smart_onboarding = SmartOnboarding(knowledge_graph)
    smart_error_handler = SmartErrorHandler()
    performance_dashboard = PerformanceDashboard(redis_client)
    core_optimizer = CoreValueOptimizer(knowledge_graph)
    logger.info("優化系統初始化成功")
else:
    smart_onboarding = None
    smart_error_handler = None
    performance_dashboard = None
    core_optimizer = None

# 只在開發環境啟用測試端點
if os.getenv('ENVIRONMENT', 'production') == 'development':
    @app.route("/test-sentry")
    def test_sentry():
        raise Exception("測試 Sentry 錯誤追蹤 - 手動觸發")

@app.route("/")
def index():
    """首頁"""
    return jsonify({
        "service": "frequency-bot",
        "version": "1.0.0",
        "status": "running"
    })

@app.route("/health")
def health_check():
    """健康檢查端點"""
    try:
        # 檢查 Firestore 連線
        test_doc = frequency_bot.db.collection('test').document('health_check')
        test_doc.set({'timestamp': firestore.SERVER_TIMESTAMP})
        
        # 檢查 Neo4j 連線
        neo4j_status = "disconnected"
        if knowledge_graph:
            try:
                # 簡單的連線測試
                with knowledge_graph.driver.session() as session:
                    session.run("RETURN 1")
                neo4j_status = "connected"
            except:
                neo4j_status = "error"
        
        # 檢查環境變數
        env_status = {
            "LINE_TOKEN": bool(os.getenv('LINE_CHANNEL_ACCESS_TOKEN')),
            "LINE_SECRET": bool(os.getenv('LINE_CHANNEL_SECRET')),
            "GEMINI_KEY": bool(os.getenv('GEMINI_API_KEY'))
        }
        
        return jsonify({
            "status": "healthy", 
            "service": "frequency-bot",
            "firestore": "connected",
            "neo4j": neo4j_status,
            "env_vars": env_status
        }), 200
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/neo4j/status")
def neo4j_status():
    """檢查 Neo4j 連接狀態和資料統計"""
    if not knowledge_graph:
        return jsonify({
            "status": "not_initialized",
            "message": "Knowledge graph not initialized"
        })
    
    if not knowledge_graph.connected:
        return jsonify({
            "status": "disconnected", 
            "message": "Neo4j connection failed",
            "uri": knowledge_graph.uri if knowledge_graph else None
        })
    
    try:
        # 獲取統計資料
        stats = knowledge_graph.get_community_insights()
        return jsonify({
            "status": "connected",
            "statistics": stats['statistics'],
            "message": "Neo4j is working properly"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}, 503

@app.route("/webhook", methods=['POST'])
def webhook():
    logger.info("收到 webhook 請求")
    # 獲取 X-Line-Signature header
    signature = request.headers.get('X-Line-Signature')
    
    if not signature:
        sentry_sdk.capture_message("Missing X-Line-Signature header", level="warning")
        abort(400)

    # 獲取請求體
    body = request.get_data(as_text=True)
    logger.info(f"Webhook body 長度: {len(body)}")
    
    # 設定 Sentry context
    sentry_sdk.set_tag("webhook.type", "line")
    sentry_sdk.set_context("webhook_data", {
        "has_signature": bool(signature),
        "body_length": len(body) if body else 0
    })
    
    try:
        # 處理 webhook 事件
        logger.info("開始處理 webhook 事件")
        handler.handle(body, signature)
        logger.info("webhook 事件處理完成")
    except InvalidSignatureError as e:
        sentry_sdk.capture_exception(e)
        abort(400)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        abort(500)
    
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_text_message(event):
    logger.info(f"收到訊息: {event.message.text}")
    
    # 記錄效能指標
    start_time = time.time()
    if performance_dashboard:
        performance_dashboard.record_message(event.source.user_id if hasattr(event.source, 'user_id') else 'unknown')
    
    # 使用意圖分析器分析訊息
    intent_result = None
    if intent_analyzer:
        try:
            # 獲取用戶對話上下文
            context = []
            if knowledge_graph and hasattr(event.source, 'user_id'):
                user_id_hash = f"用戶{hash(event.source.user_id) % 10000:04d}"
                context = knowledge_graph.get_conversation_context(user_id_hash, limit=3)
            
            # 分析意圖
            intent_result = intent_analyzer.analyze(
                message=event.message.text,
                user_id=user_id_hash if hasattr(event.source, 'user_id') else "anonymous",
                context=context
            )
            logger.info(f"意圖分析結果: {intent_result}")
        except Exception as e:
            logger.error(f"意圖分析失敗: {e}")
    
    # 檢查環境變數
    logger.info(f"LINE_CHANNEL_ACCESS_TOKEN exists: {bool(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))}")
    logger.info(f"GEMINI_API_KEY exists: {bool(os.getenv('GEMINI_API_KEY'))}")
    
    # 獲取用戶ID（匿名化）
    user_id = None
    if hasattr(event.source, 'user_id'):
        # 使用匿名化的用戶識別
        user_id = f"用戶{hash(event.source.user_id) % 10000:04d}"
    
    # 基於意圖的智慧導航
    if intent_result and intent_result.get('confidence', 0) > 0.8:
        intent = intent_result.get('intent')
        feature = intent_result.get('feature')
        
        # 根據意圖自動導向對應功能
        if intent == "use_feature" and feature == "接龍":
            # 檢查是否已經包含詞語
            if event.message.text.startswith('接龍 ') and len(event.message.text) > 3:
                # 讓它繼續往下處理，不要在這裡攔截
                pass
            else:
                # 只有單獨輸入「接龍」時才顯示提示
                if not community:
                    reply_message = "❌ 社群功能暫時無法使用"
                else:
                    result = community.get_word_chain_status()
                    reply_message = result['message']
                
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        replyToken=event.reply_token,
                        messages=[TextMessage(text=reply_message)]
                    )
                )
                return
        elif intent == "vote" and feature == "投票":
            # 處理投票數字
            option_num = intent_result.get('option', 0)
            result = community.cast_vote(option_num, user_id)
            
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    replyToken=event.reply_token,
                    messages=[TextMessage(text=result['message'])]
                )
            )
            return
        elif intent == "query" and feature:
            # 智慧查詢對應功能
            if feature == "統計":
                stats = frequency_bot.get_frequency_stats()
                reply_message = format_stats_message(stats)
            elif feature == "廣播":
                latest_broadcast = frequency_bot.get_latest_broadcast()
                reply_message = format_broadcast_message(latest_broadcast) if latest_broadcast else "📡 目前還沒有廣播"
            else:
                reply_message = f"🤖 為您查詢「{feature}」相關資訊..."
            
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    replyToken=event.reply_token,
                    messages=[TextMessage(text=reply_message)]
                )
            )
            return
    
    # 擴展自然語言理解
    text_lower = event.message.text.lower()

    # 快捷選單系統
    if text_lower in QUICK_MENUS:
        menu_data = QUICK_MENUS[text_lower]
        menu_items = []
        for option_text, option_command in menu_data["options"]:
            menu_items.append(f"{option_text}\n→ 輸入「{option_command}」")
        
        reply_message = f"{menu_data['title']}\n━━━━━━━━━━━━━━\n\n"
        reply_message += "\n\n".join(menu_items)
        reply_message += f"\n\n{menu_data['footer']}"
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=reply_message)]
            )
        )
        return

    # 幫助功能
    # Note: The 'help' keyword might be part of QUICK_MENUS "玩" (更多功能 -> 幫助)
    # If user types "幫助" directly, this handler will catch it.
    # If "幫助" is also a quick menu key, it would be handled by the QUICK_MENUS logic first.
    # Current QUICK_MENUS keys are "玩", "看", "救", so "幫助" is fine here.
    if event.message.text.lower() in ['幫助', 'help', '說明', '?']:
        help_message = """🌊 頻率共振 Bot 使用說明
━━━━━━━━━━━━━━
👋 你好！我是大家的AI夥伴。試試輸入以下關鍵字探索功能：

🎮 **玩** - 探索互動遊戲
    → 文字接龍、發起投票等

📊 **看** - 查看即時資訊
    → 廣播、統計、API用量等

🚨 **救** - 獲取防災互助資訊
    → 避難所查詢、物資分享等

😂 **笑話**
    → 輸入「說個笑話」聽笑話
    → 輸入「笑話 [內容]」分享你的笑話

💬 **參與共振**
    → 直接發送任何訊息，就能成為每小時廣播的一部分！
    → 輸入「廣播」查看最新共振內容
    → 輸入「統計」查看本小時參與進度

💡 小提示：許多功能都有範例指令，例如「投票範例」、「接龍範例」。
❓ 如需更詳細指令，請參考專案說明文件。"""
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=help_message)]
            )
        )
        return
    
    # 檢查是否為查詢廣播
    if event.message.text.lower() in ['廣播', 'broadcast', 'b', '頻率', 'freq']:
        # 回傳最新廣播
        latest_broadcast = frequency_bot.get_latest_broadcast()
        if latest_broadcast:
            reply_message = format_broadcast_message(latest_broadcast)
        else:
            reply_message = "📡 目前還沒有廣播，請稍後再試"
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=reply_message)]
            )
        )
        return
    
    # 檢查是否為查詢統計
    if event.message.text.lower() in ['統計', 'stats', '進度', 'progress', '排行']:
        stats = frequency_bot.get_frequency_stats()
        reply_message = format_stats_message(stats)
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=reply_message)]
            )
        )
        return
    
    # 效能儀表板（Jensen Huang 要求的功能）
    if event.message.text.lower() in ['系統狀態', 'system', 'performance', '效能']:
        if performance_dashboard:
            reply_message = performance_dashboard.format_dashboard()
        else:
            reply_message = "❌ 效能監控功能未啟用"
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=reply_message)]
            )
        )
        return
    
    # API 統計
    if event.message.text.lower() in ['api統計', 'api stats', 'api']:
        if not community:
            reply_message = "❌ 社群功能暫時無法使用"
        else:
            api_stats = community.get_api_stats()
            reply_message = format_api_stats_message(api_stats)
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=reply_message)]
            )
        )
        return
    
    # 文字接龍
    if event.message.text.startswith('接龍 '):
        word = event.message.text[3:].strip()
        if not community:
            reply_message = "❌ 社群功能暫時無法使用"
        else:
            result = community.start_word_chain(word, user_id)
            reply_message = result['message']
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=reply_message)]
            )
        )
        return
    
    # 接龍狀態查詢
    if event.message.text in ['接龍狀態', '接龍進度', '接龍']:
        if not community:
            reply_message = "❌ 社群功能暫時無法使用"
        else:
            result = community.get_word_chain_status()
            reply_message = result['message']
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=reply_message)]
            )
        )
        return
    
    # 投票功能
    if event.message.text.startswith('投票 '):
        parts = event.message.text[3:].split('/')
        if len(parts) >= 3:
            topic = parts[0].strip()
            options = [opt.strip() for opt in parts[1:]]
            result = community.create_vote(topic, options, user_id)
        else:
            result = {'message': '❌ 格式錯誤！請使用：投票 主題/選項1/選項2/選項3'}
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=result['message'])]
            )
        )
        return
    
    # 投票結果
    if event.message.text == '投票結果':
        result = community.get_vote_results()
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=result['message'])]
            )
        )
        return
    
    # 防空資訊
    if event.message.text.startswith('防空 '):
        parts = event.message.text[3:].split(' ')
        if len(parts) >= 3:
            location = parts[0]
            shelter_type = parts[1]
            try:
                capacity = int(parts[2])
                result = community.add_shelter_info(location, shelter_type, capacity, user_id)
            except:
                result = {'message': '❌ 容量必須是數字'}
        else:
            result = {'message': '❌ 格式錯誤！請使用：防空 地點 類型 容量'}
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=result['message'])]
            )
        )
        return
    
    # 範例展示
    if event.message.text == '投票範例':
        example_message = """📊 投票範例集：

🍽 餐廳選擇
投票 晚餐吃什麼/火鍋/燒烤/日料/熱炒

🎮 活動決定  
投票 週末活動/爬山/看電影/桌遊/在家耍廢

📅 時間協調
投票 聚會時間/週六下午/週六晚上/週日下午

💡 格式：投票 主題/選項1/選項2/選項3"""
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=example_message)]
            )
        )
        return
    
    if event.message.text == '防空範例':
        example_message = """🏠 避難所資訊範例：

防空 信義區市政府站 捷運站地下層 500
防空 大安區某大樓 地下停車場 200
防空 中山區某公園 防空洞 100

格式：防空 [地點] [類型] [容量]
💡 地點會自動模糊化保護隱私"""
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=example_message)]
            )
        )
        return
    
    # 防災資訊總覽
    if event.message.text in ['防災資訊', '緊急']:
        summary = community.get_emergency_summary()
        reply_message = format_emergency_info_message(summary)
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=reply_message)]
            )
        )
        return
    
    # 檢查是否為數字（投票）
    if event.message.text.isdigit():
        option_num = int(event.message.text)
        result = community.cast_vote(option_num, user_id)
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=result['message'])]
            )
        )
        return
    
    # 檢查是否為接龍（如果有進行中的接龍）
    if community and community.connected and len(event.message.text) >= 2: # Ensure community object exists
        chain_data = community.redis.get("word_chain:current")
        if chain_data:
            result = community.continue_word_chain(event.message.text, user_id)
            if result['success']:
                line_bot_api.reply_message(
                    ReplyMessageRequest(
                        replyToken=event.reply_token,
                        messages=[TextMessage(text=result['message'])]
                    )
                )
                return
    
    # 笑話功能
    if event.message.text.startswith('笑話 '):
        if community: # Check if community features are available
            joke_text = event.message.text[3:].strip()
            if not joke_text:
                reply_message = "🤔 笑話內容不能為空喔！請輸入「笑話 [你的笑話內容]」"
            else:
                result = community.add_joke(user_id, joke_text) # user_id is already hashed
                reply_message = result['message']
        else:
            reply_message = "❌ 社群功能（包含笑話）暫時無法使用"

        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=reply_message)]
            )
        )
        return

    if event.message.text.lower() in ['說個笑話', '聽笑話']:
        if community: # Check if community features are available
            result = community.get_random_joke()
            reply_message = result['message']
        else:
            reply_message = "❌ 社群功能（包含笑話）暫時無法使用"

        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=reply_message)]
            )
        )
        return

    # 檢查是否為新用戶的第一次互動
    if event.message.text.lower() in ['hi', 'hello', '你好', '嗨', '哈囉', '安安']:
        is_new_user = False # Default to false
        if smart_onboarding and user_id:
            is_new_user = smart_onboarding.is_new_user(user_id)

        if is_new_user:
            welcome_message = "👋 歡迎來到頻率共振！\n\n我是大家共創的 AI 助手\n直接輸入文字就能參與廣播喔！\n\n想玩點什麼嗎？\n━━━━━━━━━━━━\n🎮 輸入「玩」看互動遊戲\n📊 輸入「看」查看統計\n🚨 輸入「救」查看防災資訊\n━━━━━━━━━━━━\n或直接打字聊天也可以！"
        else:
            hour = datetime.now().hour
            if 6 <= hour < 12:
                greeting = "早安"
            elif 12 <= hour < 18:
                greeting = "午安"
            else:
                greeting = "晚安"
            welcome_message = f"{greeting}！今天想做什麼呢？\n輸入「玩」「看」「救」快速開始"

        # 如果有智慧推薦功能，加入個人化建議
        if intent_analyzer and user_id:
            suggestions = intent_analyzer.get_feature_suggestions(user_id)
            if suggestions:
                welcome_message += "\n\n💡 為您推薦："
                for s in suggestions[:2]:
                    welcome_message += f"\n• {s['feature']} - {s['reason']}"
        
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=welcome_message)]
            )
        )
        return
    
    # 智慧錯誤處理（處理可能的輸入錯誤）
    if smart_error_handler:
        # 檢查是否可能是錯誤輸入
        suggestion = smart_error_handler.suggest_correction(event.message.text)
        if "您是想輸入" in suggestion or "格式：" in suggestion:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    replyToken=event.reply_token,
                    messages=[TextMessage(text=suggestion)]
                )
            )
            return
    
    # 安全過濾檢查
    is_valid, cleaned_message = security_filter.validate_for_broadcast(event.message.text)
    if not is_valid:
        # 如果是技術內容，直接回覆錯誤訊息
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=cleaned_message)]  # cleaned_message 此時是錯誤提示
            )
        )
        return
    
    # 檢查是否為新用戶第一則訊息
    is_new_user = False
    if user_id:
        stats = frequency_bot.get_frequency_stats()
        user_messages = 0
        for contributor, count in stats['contributors']['top_contributors']:
            if contributor == user_id:
                user_messages = count
                break
        is_new_user = (user_messages == 0)
    
    # 儲存訊息到廣播池（使用清理後的訊息）
    message_count = frequency_bot.add_to_broadcast(cleaned_message, user_id)
    
    # 檢查用戶排名
    user_rank = None
    if user_id:
        stats = frequency_bot.get_frequency_stats()
        for rank, (contributor, _) in enumerate(stats['contributors']['top_contributors'], 1):
            if contributor == user_id:
                user_rank = rank
                break
    
    # 生成即時回饋
    if is_new_user:
        # 新用戶特別歡迎訊息
        feedback = f"""👋 歡迎來到頻率共振！

我會收集大家的訊息，每小時編成一個美麗的廣播
你剛才說的「{cleaned_message[:20]}...」已經被收錄了！

🔥 快速體驗：
• 輸入「玩」- 開始互動遊戲
• 輸入「看」- 查看即時統計  
• 輸入「廣播」- 聽聽大家在說什麼

或繼續聊天，你的每句話都會成為廣播的一部分！"""
    else:
        feedback = format_instant_feedback(message_count, user_rank, user_id, frequency_bot.db)
    
    # 如果達到1000則，立即生成廣播
    if message_count >= 1000:
        frequency_bot.generate_hourly_broadcast()
        feedback += "\n🎆 廣播已生成！輸入「廣播」查看"
    
    # 回覆即時回饋
    try:
        line_bot_api.reply_message(
            ReplyMessageRequest(
                replyToken=event.reply_token,
                messages=[TextMessage(text=feedback)]
            )
        )
        logger.info("回覆訊息成功")
        
        # 記錄 API 延遲
        if performance_dashboard:
            elapsed_time = (time.time() - start_time) * 1000  # 轉換為毫秒
            performance_dashboard.record_api_latency("webhook", elapsed_time)
            
        # 檢查是否為里程碑
        if smart_onboarding and user_id and message_count in [1, 10, 50, 100, 500, 1000]:
            milestone_type = {
                1: "first_message",
                10: "tenth_message",
                50: "active_user",
                100: "super_active",
                500: "veteran",
                1000: "legend"
            }.get(message_count)
            
            if milestone_type:
                celebration = smart_onboarding.celebrate_milestone(user_id, milestone_type)
                # 可以考慮推送慶祝訊息（這裡暫時不實作避免過多訊息）
                logger.info(f"用戶 {user_id} 達成里程碑: {milestone_type}")
                
    except Exception as e:
        logger.error(f"回覆訊息失敗: {e}")
        sentry_sdk.capture_exception(e)
    
    # 設定 Sentry context 並匯名化用戶 ID
    sentry_sdk.set_tag("message.type", "text")
    sentry_sdk.set_tag("source.type", event.source.type)
    sentry_sdk.set_context("line_event", {
        "event_type": event.type,
        "message_id": event.message.id,
        "source_type": event.source.type,
        "user_id_hash": hash(event.source.user_id) if hasattr(event.source, 'user_id') else None,
        "group_id_hash": hash(event.source.group_id) if hasattr(event.source, 'group_id') else None,
        "timestamp": event.timestamp
    })
    
    # 測試錯誤追蹤
    if event.message.text.lower() == "error":
        logger.warning("觸發測試錯誤給 Sentry")
        raise Exception("測試 Sentry 錯誤追蹤功能 - LINE 訊息觸發")

# 自動測試端點
@app.route("/scheduler/test", methods=['POST'])
def scheduled_test():
    """由 Cloud Scheduler 觸發的自動測試"""
    # 驗證請求來源
    if not request.headers.get('X-Cloudscheduler'):
        abort(403)
    
    try:
        # 模擬測試訊息
        test_messages = ["系統測試", "統計", "廣播"]
        test_user = "system_test_user"
        
        results = []
        for msg in test_messages:
            count = frequency_bot.add_to_broadcast(msg, test_user)
            results.append({"message": msg, "count": count})
        
        # 獲取統計資訊
        stats = frequency_bot.get_frequency_stats()
        
        return jsonify({
            "status": "success",
            "tests": results,
            "current_stats": {
                "message_count": stats['message_count'],
                "progress": stats['progress_percent']
            }
        })
    except Exception as e:
        logger.error(f"自動測試失敗: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Cloud Scheduler 端點
@app.route("/scheduler/broadcast", methods=['POST'])
def scheduled_broadcast():
    """由 Cloud Scheduler 觸發的廣播生成"""
    # 驗證請求來源（Cloud Scheduler 會帶特定 header）
    if not request.headers.get('X-Cloudscheduler'):
        abort(403)
    
    result = frequency_bot.generate_hourly_broadcast()
    if result:
        return jsonify({
            "status": "success",
            "message_count": result['message_count']
        })
    return jsonify({"status": "no_messages"})

@app.route("/scheduler/cleanup", methods=['POST'])
def scheduled_cleanup():
    """由 Cloud Scheduler 觸發的資料清理"""
    # 驗證請求來源
    if not request.headers.get('X-Cloudscheduler'):
        abort(403)
    
    try:
        frequency_bot.cleanup_old_data()
        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"清理失敗: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# 只在開發環境啟用手動觸發
if os.getenv('ENVIRONMENT', 'production') == 'development':
    @app.route("/trigger-broadcast")
    def trigger_broadcast():
        """手動觸發廣播生成（測試用）"""
        result = frequency_bot.generate_hourly_broadcast()
        if result:
            return f"廣播已生成：{result['message_count']} 則訊息"
        return "沒有訊息可生成廣播"

# 啟動時檢查必要環境變數
def check_required_env_vars():
    required_vars = [
        'LINE_CHANNEL_ACCESS_TOKEN',
        'LINE_CHANNEL_SECRET',
        'GEMINI_API_KEY'
    ]
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"缺少必要的環境變數: {', '.join(missing_vars)}")
        logger.error("請參考 .env.example 設定環境變數")
        exit(1)

if __name__ == '__main__':
    # 檢查環境變數
    check_required_env_vars()
    
    # Cloud Run 會設定 PORT 環境變數
    port = int(os.getenv('PORT', 8080))
    debug = os.getenv('ENVIRONMENT', 'production') == 'development'
    
    logger.info(f"啟動應用程式 - Port: {port}, Debug: {debug}")
    app.run(host='0.0.0.0', port=port, debug=debug)