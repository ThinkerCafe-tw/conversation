# Claude 專案配置文件

## 自動部署設定

### 部署指令
當完成功能開發或修復後，自動執行以下部署流程：

1. **提交代碼到 GitHub**
   ```bash
   git add -A
   git commit -m "提交訊息"
   git push origin main
   ```

2. **部署到 Cloud Run**
   ```bash
   gcloud run deploy frequency-bot \
     --source . \
     --region=asia-east1 \
     --allow-unauthenticated \
     --quiet
   ```

### 部署參數
- **服務名稱**: frequency-bot
- **區域**: asia-east1
- **專案**: probable-axon-451311-e1
- **記憶體**: 512Mi
- **CPU**: 1
- **並發**: 100
- **超時**: 60m

### 部署時機
- 完成新功能開發
- 修復錯誤
- 性能優化
- 安全更新

### 部署前檢查
1. 語法檢查: `python -m py_compile app.py`
2. 本地測試通過
3. 沒有敏感資訊外洩

### 部署後驗證
1. 健康檢查: `/health` 端點
2. 主要功能測試
3. 錯誤日誌檢查

## 環境變數
需要設定的環境變數（已在 Cloud Run 中配置）：
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_CHANNEL_SECRET
- GEMINI_API_KEY
- CUSTOM_SEARCH_API_KEY
- REDIS_HOST
- REDIS_PORT
- REDIS_PASSWORD
- NEO4J_URI
- NEO4J_USER
- NEO4J_PASSWORD

## 注意事項
- 部署需要 Google Cloud 認證
- 如果認證過期，需要手動執行 `gcloud auth login`
- 部署通常需要 2-3 分鐘完成
- 使用 `--quiet` 參數避免交互式確認

## 常用命令

### 查看服務狀態
```bash
gcloud run services describe frequency-bot --region=asia-east1
```

### 查看日誌
```bash
gcloud run services logs read frequency-bot --region=asia-east1 --limit=50
```

### 更新環境變數
```bash
gcloud run services update frequency-bot \
  --set-env-vars="KEY=VALUE" \
  --region=asia-east1
```

---
此文件由 Claude 自動維護，用於記錄部署流程和配置。