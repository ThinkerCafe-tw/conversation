#!/bin/bash

# 設定 Cloud Scheduler 來自動生成每小時廣播

echo "=== 設定 Cloud Scheduler ==="

# 創建一個每小時執行的排程任務
gcloud scheduler jobs create http generate-hourly-broadcast \
    --location=asia-east1 \
    --schedule="0 * * * *" \
    --uri="https://frequency-bot-808270083585.asia-east1.run.app/generate-broadcast" \
    --http-method=POST \
    --time-zone="Asia/Taipei" \
    --attempt-deadline="60s" \
    --description="每小時生成頻率廣播"

echo ""
echo "=== 創建立即執行的排程（用於測試）==="
gcloud scheduler jobs create http generate-broadcast-now \
    --location=asia-east1 \
    --schedule="*/5 * * * *" \
    --uri="https://frequency-bot-808270083585.asia-east1.run.app/generate-broadcast" \
    --http-method=POST \
    --time-zone="Asia/Taipei" \
    --attempt-deadline="60s" \
    --description="每5分鐘檢查並生成廣播（測試用）"

echo ""
echo "✅ Cloud Scheduler 設定完成！"
echo ""
echo "執行以下命令來手動觸發廣播生成："
echo "gcloud scheduler jobs run generate-hourly-broadcast --location=asia-east1"
echo ""
echo "查看排程狀態："
echo "gcloud scheduler jobs list --location=asia-east1"