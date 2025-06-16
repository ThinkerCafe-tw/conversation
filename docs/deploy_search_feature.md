# 部署網路搜尋功能指南

## 更新 Cloud Run 環境變數

執行以下命令來新增 Google Custom Search API Key：

```bash
gcloud run services update conversation-bot \
  --set-env-vars="CUSTOM_SEARCH_API_KEY=AIzaSyDpKSsBHHym3w7QwT_ci0_rmptvt1-gKT4" \
  --region=asia-east1
```

## 驗證設定

1. 檢查服務是否正常運行：
```bash
gcloud run services describe conversation-bot --region=asia-east1
```

2. 測試搜尋功能：
- 在 LINE 聊天中輸入：「搜尋 今天天氣」
- 應該會收到前 3 筆搜尋結果

## 功能說明

### 支援的搜尋指令
- 搜尋 [關鍵字]
- search [關鍵字]
- 找一下 [關鍵字]
- 查一下 [關鍵字]
- 搜 [關鍵字]
- 查 [關鍵字]

### API 限制
- 每日限制：100 次搜尋
- 搜尋引擎 ID：f4bbd246ef2324d78（已內建於程式碼中）

### 錯誤排除

如果搜尋功能無法使用：

1. 確認環境變數已設定：
```bash
gcloud run services describe conversation-bot --region=asia-east1 --format="value(spec.template.spec.containers[0].env[?name=='CUSTOM_SEARCH_API_KEY'].value)"
```

2. 檢查日誌：
```bash
gcloud run services logs read conversation-bot --region=asia-east1 --limit=50
```

3. 確認 API 配額：
- 訪問 [Google Cloud Console](https://console.cloud.google.com/apis/api/customsearch.googleapis.com)
- 檢查 Custom Search API 的使用情況

## 注意事項

- API Key 已包含在程式碼中，請妥善保管
- 搜尋引擎 ID `f4bbd246ef2324d78` 已硬編碼在 `search_service.py` 中
- 建議定期檢查 API 使用量，避免超出配額