#!/bin/bash

echo "設定自動監控和測試..."

SERVICE_URL="https://frequency-bot-808270083585.asia-east1.run.app"
REGION="asia-east1"

# 1. 建立健康檢查 Cloud Scheduler 任務
echo "建立健康檢查任務..."
gcloud scheduler jobs create http health-monitor \
    --location=$REGION \
    --schedule="*/5 * * * *" \
    --uri="$SERVICE_URL/health" \
    --http-method=GET \
    --attempt-deadline="30s" \
    --description="每5分鐘健康檢查"

# 2. 建立測試訊息任務（每小時發送測試）
echo "建立測試訊息任務..."
gcloud scheduler jobs create http test-message \
    --location=$REGION \
    --schedule="30 * * * *" \
    --uri="$SERVICE_URL/scheduler/test" \
    --http-method=POST \
    --headers="X-Cloudscheduler=true" \
    --attempt-deadline="60s" \
    --description="每小時30分發送測試訊息"

# 3. 設定錯誤警報
echo "設定錯誤警報..."
gcloud alpha monitoring policies create \
    --notification-channels=YOUR_NOTIFICATION_CHANNEL_ID \
    --display-name="Frequency Bot 錯誤警報" \
    --condition-display-name="錯誤率過高" \
    --condition-expression='
    resource.type="cloud_run_revision"
    AND resource.label.service_name="frequency-bot"
    AND metric.type="logging.googleapis.com/user/error_count"
    AND metric.value > 10'

echo "監控設定完成！"