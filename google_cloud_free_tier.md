# Google Cloud 免費層方案（接近0成本）

## 🎯 目標：利用 Google Cloud 永久免費層

### ✅ 可用的免費服務

## 1. Cloud Run（應用程式託管）
**永久免費額度：**
- 200萬次請求/月
- 360,000 GB-秒記憶體
- 180,000 vCPU-秒
- 1GB 網路傳出流量

**適用性分析：**
- 1000用戶 × 10訊息/天 × 30天 = 300,000請求/月 ✅
- CPU使用量：每請求約0.1秒 = 30,000 vCPU-秒 ✅
- 記憶體：512MB × 30,000秒 = 15,000 GB-秒 ✅
- **完全免費** 💯

## 2. Firestore（NoSQL 資料庫）
**永久免費額度：**
- 1GB 儲存空間
- 50,000次讀取/天
- 20,000次寫入/天
- 20,000次刪除/天

**適用性分析：**
- 寫入：10,000訊息/天 ✅
- 讀取：24次廣播 × 1000次讀取 = 24,000/天 ✅
- 儲存：每則訊息100bytes × 300,000 = 30MB ✅
- **完全免費** 💯

## 3. Cloud Scheduler（定時任務）
**永久免費額度：**
- 3個工作

**用途：**
- 每小時觸發廣播生成 ✅
- 每日清理過期資料 ✅
- 每週備份 ✅
- **完全免費** 💯

## 4. Cloud Functions（無伺服器函數）
**永久免費額度：**
- 200萬次調用/月
- 400,000 GB-秒
- 200,000 GHz-秒

**可選用途：**
- Webhook 處理
- 資料處理
- **完全免費** 💯

## 5. Secret Manager（環境變數管理）
**永久免費額度：**
- 6個有效密鑰
- 10,000次存取/月

**用途：**
- LINE API 金鑰
- Gemini API 金鑰
- **完全免費** 💯

## 6. Cloud Logging & Monitoring
**永久免費額度：**
- 50GB 日誌/月
- 基本監控指標

**完全免費** 💯

---

## 🔄 架構調整（從 Redis 改為 Firestore）

### 修改 frequency_bot.py 使用 Firestore：

```python
from google.cloud import firestore
import os
from datetime import datetime, timedelta

class FrequencyBot:
    def __init__(self):
        # 初始化 Firestore
        self.db = firestore.Client()
        
        # Gemini API 設定
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
    def add_to_broadcast(self, message: str, user_id: str = None):
        """將訊息加入廣播池"""
        current_hour = int(time.time()) // 3600
        
        # 儲存訊息到 Firestore
        doc_ref = self.db.collection('broadcasts').document(str(current_hour))
        doc_ref.collection('messages').add({
            'content': message,
            'user_id': user_id,
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        
        # 更新統計
        doc_ref.set({
            'message_count': firestore.Increment(1),
            'updated_at': firestore.SERVER_TIMESTAMP
        }, merge=True)
        
        # 更新用戶貢獻
        if user_id:
            doc_ref.collection('contributors').document(user_id).set({
                'count': firestore.Increment(1)
            }, merge=True)
            
        # 返回當前訊息數
        doc = doc_ref.get()
        return doc.to_dict().get('message_count', 0) if doc.exists else 0
        
    def get_frequency_stats(self):
        """獲取當前頻率統計"""
        current_hour = int(time.time()) // 3600
        doc_ref = self.db.collection('broadcasts').document(str(current_hour))
        
        # 獲取統計資料
        doc = doc_ref.get()
        if not doc.exists:
            return self._empty_stats()
            
        stats = doc.to_dict()
        message_count = stats.get('message_count', 0)
        
        # 獲取貢獻者排行
        contributors = []
        contrib_docs = doc_ref.collection('contributors').order_by('count', direction=firestore.Query.DESCENDING).limit(5).stream()
        for contrib_doc in contrib_docs:
            contributors.append((contrib_doc.id, contrib_doc.to_dict()['count']))
        
        # 計算進度和時間
        progress_percent = min(int((message_count / 1000) * 100), 100)
        messages_needed = max(0, 1000 - message_count)
        
        current_time = int(time.time())
        next_hour = ((current_hour + 1) * 3600)
        time_until_broadcast = next_hour - current_time
        
        return {
            'message_count': message_count,
            'progress_percent': progress_percent,
            'messages_needed': messages_needed,
            'time_until_broadcast': {
                'minutes': time_until_broadcast // 60,
                'seconds': time_until_broadcast % 60
            },
            'top_frequencies': [],  # 簡化版本不做詞頻分析
            'contributors': {
                'total_users': len(contributors),
                'top_contributors': contributors
            }
        }
    
    def generate_hourly_broadcast(self):
        """生成每小時的頻率廣播"""
        current_hour = int(time.time()) // 3600
        doc_ref = self.db.collection('broadcasts').document(str(current_hour))
        
        # 獲取所有訊息
        messages = []
        message_docs = doc_ref.collection('messages').limit(1000).stream()
        for msg_doc in message_docs:
            messages.append(msg_doc.to_dict()['content'])
            
        if not messages:
            return None
            
        # 使用 Gemini 生成廣播
        prompt = self._create_prompt(messages)
        
        try:
            response = self.model.generate_content(prompt)
            if response and response.candidates:
                broadcast_content = response.candidates[0].content.parts[0].text
                
                # 儲存廣播結果
                broadcast_ref = self.db.collection('generated_broadcasts').document(str(current_hour))
                broadcast_data = {
                    'content': broadcast_content,
                    'timestamp': current_hour * 3600,
                    'message_count': len(messages),
                    'generated_at': firestore.SERVER_TIMESTAMP
                }
                broadcast_ref.set(broadcast_data)
                
                # 清理舊資料（選擇性）
                self._cleanup_old_data(current_hour)
                
                return broadcast_data
                
        except Exception as e:
            logger.error(f"生成廣播失敗: {e}")
            return None
    
    def _cleanup_old_data(self, current_hour):
        """清理超過24小時的資料"""
        old_hour = current_hour - 24
        old_doc = self.db.collection('broadcasts').document(str(old_hour))
        
        # 批次刪除子集合
        batch = self.db.batch()
        for doc in old_doc.collection('messages').stream():
            batch.delete(doc.reference)
        for doc in old_doc.collection('contributors').stream():
            batch.delete(doc.reference)
        batch.delete(old_doc)
        batch.commit()
```

---

## 📱 部署到 Cloud Run

### 1. 建立 Dockerfile（Cloud Run 優化版）
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製應用
COPY . .

# Cloud Run 使用 PORT 環境變數
ENV PORT 8080
EXPOSE 8080

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app
```

### 2. 更新 requirements.txt
```txt
flask==3.0.0
line-bot-sdk==3.5.0
python-dotenv==1.0.0
sentry-sdk[flask]==1.38.0
google-cloud-firestore==2.13.1
google-cloud-secret-manager==2.17.0
google-generativeai==0.3.1
apscheduler==3.10.4
gunicorn==21.2.0
```

### 3. 部署指令
```bash
# 建置並部署到 Cloud Run
gcloud run deploy frequency-bot \
  --source . \
  --platform managed \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-env-vars ENVIRONMENT=production
```

---

## 💰 最終成本分析

### 完全免費項目 ✅
1. **Cloud Run**: 應用程式託管
2. **Firestore**: 資料庫
3. **Cloud Scheduler**: 定時任務
4. **Secret Manager**: 密鑰管理
5. **Gemini API**: AI 生成（免費額度）
6. **Cloud Logging**: 日誌監控

### 仍需付費項目 ❌
1. **網域名稱**: ~$10/年（$0.83/月）
2. **SSL 憑證**: Cloudflare 免費 ✅

## 🎉 總成本：$0.83/月（僅網域費用）

### 限制與注意事項
1. **Firestore 限制**:
   - 每秒寫入限制：500次
   - 需要實作批次寫入
   
2. **Cloud Run 冷啟動**:
   - 首次請求可能較慢
   - 可用 Cloud Scheduler 定期喚醒

3. **資料清理**:
   - 必須定期清理舊資料
   - 避免超過 1GB 免費額度

4. **監控**:
   - 設定配額警報
   - 追蹤使用量

## 🚀 實作步驟
1. 建立 Google Cloud 專案
2. 啟用必要的 API
3. 修改程式碼使用 Firestore
4. 部署到 Cloud Run
5. 設定 Cloud Scheduler
6. 配置 LINE Webhook URL

這樣就能實現**接近零成本**的完整解決方案！