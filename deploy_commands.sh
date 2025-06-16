#!/bin/bash

# 部署指令集合
echo "開始部署 Frequency Bot 到 Google Cloud Run..."

# 1. 使用 Secret Manager 儲存敏感資料
echo "設定 Secret Manager..."
echo -n "請輸入 LINE_CHANNEL_ACCESS_TOKEN: "
read -s LINE_TOKEN
echo
echo -n "$LINE_TOKEN" | gcloud secrets create LINE_CHANNEL_ACCESS_TOKEN --data-file=- 2>/dev/null || echo "Secret 已存在"

echo -n "請輸入 LINE_CHANNEL_SECRET: "
read -s LINE_SECRET
echo
echo -n "$LINE_SECRET" | gcloud secrets create LINE_CHANNEL_SECRET --data-file=- 2>/dev/null || echo "Secret 已存在"

echo -n "請輸入 GEMINI_API_KEY: "
read -s GEMINI_KEY
echo
echo -n "$GEMINI_KEY" | gcloud secrets create GEMINI_API_KEY --data-file=- 2>/dev/null || echo "Secret 已存在"

# 2. 部署到 Cloud Run
echo "部署應用程式到 Cloud Run..."
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

echo "部署完成！"