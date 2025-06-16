#!/bin/bash

# 部署搜尋功能到 Cloud Run

echo "=== 更新 Cloud Run 環境變數 ==="
echo "正在更新 frequency-bot 服務..."

# 更新環境變數
gcloud run services update frequency-bot \
  --set-env-vars="CUSTOM_SEARCH_API_KEY=AIzaSyDpKSsBHHym3w7QwT_ci0_rmptvt1-gKT4" \
  --region=asia-east1

echo ""
echo "=== 檢查服務狀態 ==="
gcloud run services describe frequency-bot --region=asia-east1 --format="value(status.url)"

echo ""
echo "=== 查看最新日誌 ==="
gcloud run services logs read frequency-bot --region=asia-east1 --limit=20

echo ""
echo "✅ 部署完成！"
echo ""
echo "測試搜尋功能："
echo "1. 在 LINE 中輸入: 搜尋 今天天氣"
echo "2. 檢查 /health 端點: $(gcloud run services describe frequency-bot --region=asia-east1 --format='value(status.url)')/health"