#!/bin/bash

# Cloud Scheduler 設定腳本
# 使用前請確保已經登入 gcloud 並選擇正確的專案

PROJECT_ID=$(gcloud config get-value project)
REGION="asia-east1"
SERVICE_URL="https://frequency-bot-808270083585.asia-east1.run.app"

echo "設定 Cloud Scheduler 任務..."
echo "專案 ID: $PROJECT_ID"
echo "區域: $REGION"

# 1. 建立每小時廣播生成任務
echo "建立廣播生成任務..."
gcloud scheduler jobs create http broadcast-generator \
    --location=$REGION \
    --schedule="0 * * * *" \
    --uri="$SERVICE_URL/scheduler/broadcast" \
    --http-method=POST \
    --headers="X-Cloudscheduler=true" \
    --attempt-deadline="30m" \
    --time-zone="Asia/Taipei" \
    --description="每小時生成頻率廣播"

# 2. 建立每日資料清理任務
echo "建立資料清理任務..."
gcloud scheduler jobs create http data-cleanup \
    --location=$REGION \
    --schedule="0 3 * * *" \
    --uri="$SERVICE_URL/scheduler/cleanup" \
    --http-method=POST \
    --headers="X-Cloudscheduler=true" \
    --attempt-deadline="30m" \
    --description="每日清理過期資料"

# 3. 建立健康檢查任務（保持 Cloud Run 實例溫暖）
echo "建立健康檢查任務..."
gcloud scheduler jobs create http health-check \
    --location=$REGION \
    --schedule="*/5 * * * *" \
    --uri="$SERVICE_URL/health" \
    --http-method=GET \
    --attempt-deadline="15s" \
    --description="每5分鐘健康檢查，減少冷啟動"

echo "Cloud Scheduler 設定完成！"
echo ""
echo "查看任務列表："
echo "gcloud scheduler jobs list --location=$REGION"
echo ""
echo "手動執行任務："
echo "gcloud scheduler jobs run broadcast-generator --location=$REGION"