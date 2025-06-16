#!/bin/bash

echo "快速部署 Frequency Bot..."

gcloud run deploy frequency-bot \
  --source . \
  --region asia-east1 \
  --allow-unauthenticated \
  --set-secrets="LINE_CHANNEL_ACCESS_TOKEN=LINE_CHANNEL_ACCESS_TOKEN:latest,LINE_CHANNEL_SECRET=LINE_CHANNEL_SECRET:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest,REDIS_HOST=REDIS_HOST:latest,REDIS_PORT=REDIS_PORT:latest,REDIS_PASSWORD=REDIS_PASSWORD:latest" \
  --max-instances 10 \
  --memory 512Mi

echo "部署完成！"