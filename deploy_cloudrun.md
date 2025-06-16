# Google Cloud Run 零成本部署指南

## 前置準備

### 1. 建立 Google Cloud 專案
1. 前往 [Google Cloud Console](https://console.cloud.google.com)
2. 建立新專案或選擇現有專案
3. 記下專案 ID

### 2. 啟用必要的 API
```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

### 3. 設定 Firestore
```bash
# 建立 Firestore 資料庫（選擇 Native mode）
gcloud firestore databases create --region=asia-east1
```

### 4. 設定環境變數
1. 複製環境變數範例：
   ```bash
   cp .env.cloudrun.example .env
   ```
2. 填入所有必要的值

## 部署步驟

### 方法一：使用 gcloud CLI（推薦）

1. **安裝 gcloud CLI**
   - [下載並安裝 gcloud](https://cloud.google.com/sdk/docs/install)

2. **登入並設定專案**
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```

3. **使用 Secret Manager 儲存敏感資料**
   ```bash
   # 建立密鑰
   echo -n "your_line_channel_access_token" | gcloud secrets create LINE_CHANNEL_ACCESS_TOKEN --data-file=-
   echo -n "your_line_channel_secret" | gcloud secrets create LINE_CHANNEL_SECRET --data-file=-
   echo -n "your_gemini_api_key" | gcloud secrets create GEMINI_API_KEY --data-file=-
   ```

4. **部署到 Cloud Run**
   ```bash
   # 直接從原始碼部署
   gcloud run deploy frequency-bot \
     --source . \
     --platform managed \
     --region asia-east1 \
     --allow-unauthenticated \
     --set-secrets="LINE_CHANNEL_ACCESS_TOKEN=LINE_CHANNEL_ACCESS_TOKEN:latest,LINE_CHANNEL_SECRET=LINE_CHANNEL_SECRET:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest" \
     --max-instances 10 \
     --min-instances 0 \
     --memory 512Mi \
     --timeout 300
   ```

5. **記下服務 URL**
   部署完成後會顯示服務 URL，格式如：
   ```
   https://frequency-bot-xxxxxxxxxx-de.a.run.app
   ```

### 方法二：使用 Cloud Build

1. **設定 Cloud Build**
   ```bash
   gcloud builds submit --config cloudbuild.yaml
   ```

## 設定 Cloud Scheduler

1. **更新 setup_cloud_scheduler.sh**
   編輯檔案，將 `SERVICE_URL` 改為實際的 Cloud Run URL

2. **執行設定腳本**
   ```bash
   ./setup_cloud_scheduler.sh
   ```

## 設定 LINE Webhook

1. 登入 [LINE Developers Console](https://developers.line.biz/)
2. 選擇你的 Messaging API channel
3. 在 Webhook settings 中：
   - Webhook URL: `https://your-service-url.run.app/webhook`
   - 啟用 Use webhook
   - 關閉 Auto-reply messages

## 監控與維護

### 查看日誌
```bash
gcloud run services logs read frequency-bot --limit 50
```

### 查看 Firestore 使用量
1. 前往 [Firestore Console](https://console.cloud.google.com/firestore)
2. 查看使用量標籤

### 監控免費額度
1. 前往 [Cloud Console 計費](https://console.cloud.google.com/billing)
2. 設定預算警報（建議設為 $1）

## 成本控制建議

1. **Firestore 優化**
   - 定期執行清理任務
   - 避免大量讀取操作
   - 使用批次寫入

2. **Cloud Run 優化**
   - 設定合理的最大實例數
   - 使用最小記憶體配置（512Mi）
   - 啟用 CPU allocation = "CPU is only allocated during request processing"

3. **監控使用量**
   ```bash
   # 查看 Cloud Run 使用統計
   gcloud run services describe frequency-bot --region asia-east1
   
   # 查看 Firestore 操作數
   # 前往 Console 查看
   ```

## 故障排除

### Cloud Run 部署失敗
- 檢查 Docker 映像是否正確建置
- 確認所有環境變數都已設定
- 查看 Cloud Build 日誌

### Firestore 連線錯誤
- 確認已啟用 Firestore API
- 檢查服務帳號權限
- 確認資料庫已建立

### LINE Webhook 失敗
- 確認 URL 正確且可訪問
- 檢查 Channel Secret 是否正確
- 查看 Cloud Run 日誌

## 免費額度監控指標

| 服務 | 免費額度 | 預估使用量 | 餘量 |
|------|----------|------------|------|
| Cloud Run | 200萬 請求/月 | 30萬 | 充足 |
| Firestore 讀取 | 5萬/天 | 3.4萬 | 32% |
| Firestore 寫入 | 2萬/天 | 1萬 | 50% |
| Firestore 儲存 | 1GB | 30MB | 3% |
| Cloud Scheduler | 3個任務 | 3個 | 100% |

## 下一步

1. **設定自訂網域**（選用）
   - 使用 Cloud Run domain mapping
   - 設定 SSL 憑證

2. **增加監控**
   - 設定 Cloud Monitoring 警報
   - 整合 Sentry 錯誤追蹤

3. **效能優化**
   - 實作快取機制
   - 優化 Firestore 查詢