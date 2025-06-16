# Redis 設定指南

## 方案一：使用 Redis Cloud（推薦）

1. **註冊 Redis Cloud 免費帳號**
   - 訪問 https://redis.com/try-free/
   - 註冊並創建免費數據庫（30MB）

2. **獲取連接資訊**
   - Endpoint: `redis-xxxxx.c1.asia-northeast1-1.gce.cloud.redislabs.com:12345`
   - Password: `your-password`

3. **設定環境變數**
   ```bash
   # 在 Secret Manager 中設定
   echo -n "redis-xxxxx.c1.asia-northeast1-1.gce.cloud.redislabs.com" | gcloud secrets create REDIS_HOST --data-file=-
   echo -n "12345" | gcloud secrets create REDIS_PORT --data-file=-
   echo -n "your-password" | gcloud secrets create REDIS_PASSWORD --data-file=-
   ```

4. **更新部署腳本**
   ```bash
   gcloud run deploy frequency-bot \
     --source . \
     --region asia-east1 \
     --allow-unauthenticated \
     --set-secrets="LINE_CHANNEL_ACCESS_TOKEN=LINE_CHANNEL_ACCESS_TOKEN:latest,LINE_CHANNEL_SECRET=LINE_CHANNEL_SECRET:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest,REDIS_HOST=REDIS_HOST:latest,REDIS_PORT=REDIS_PORT:latest,REDIS_PASSWORD=REDIS_PASSWORD:latest" \
     --max-instances 10 \
     --memory 512Mi
   ```

## 方案二：使用 Memorystore（Google Cloud）

1. **創建 Memorystore 實例**
   ```bash
   gcloud redis instances create frequency-bot-redis \
     --size=1 \
     --region=asia-east1 \
     --redis-version=redis_6_x
   ```

2. **設定 VPC 連接**
   - Cloud Run 需要通過 VPC connector 連接 Memorystore

## 方案三：暫時使用 Firestore 替代

如果暫時不想設定 Redis，可以修改程式碼使用 Firestore 來儲存這些互動功能的資料。