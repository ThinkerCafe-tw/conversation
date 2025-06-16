#!/bin/bash

# 部署包含 Neo4j 的更新版本

echo "開始部署 Neo4j 整合版本..."

# 設定專案 ID
PROJECT_ID="probable-axon-451311-e1"
gcloud config set project $PROJECT_ID

# 更新 Secret Manager 中的 Neo4j 認證
echo "更新 Neo4j 認證到 Secret Manager..."

# 創建或更新 Neo4j 密鑰
echo -n "neo4j+s://9e6ab431.databases.neo4j.io" | gcloud secrets create NEO4J_URI --data-file=- 2>/dev/null || \
echo -n "neo4j+s://9e6ab431.databases.neo4j.io" | gcloud secrets versions add NEO4J_URI --data-file=-

echo -n "neo4j" | gcloud secrets create NEO4J_USER --data-file=- 2>/dev/null || \
echo -n "neo4j" | gcloud secrets versions add NEO4J_USER --data-file=-

echo -n "kAL3-VS_Mn-vVNO7491TF6sv7dU9UeIuAWD94_gKNIg" | gcloud secrets create NEO4J_PASSWORD --data-file=- 2>/dev/null || \
echo -n "kAL3-VS_Mn-vVNO7491TF6sv7dU9UeIuAWD94_gKNIg" | gcloud secrets versions add NEO4J_PASSWORD --data-file=-

# 部署到 Cloud Run
echo "部署應用程式到 Cloud Run..."
gcloud run deploy frequency-bot \
    --source . \
    --platform managed \
    --region asia-east1 \
    --allow-unauthenticated \
    --memory 512Mi \
    --timeout 300 \
    --set-secrets=LINE_CHANNEL_ACCESS_TOKEN=LINE_CHANNEL_ACCESS_TOKEN:latest,LINE_CHANNEL_SECRET=LINE_CHANNEL_SECRET:latest,GEMINI_API_KEY=GEMINI_API_KEY:latest,REDIS_HOST=REDIS_HOST:latest,REDIS_PORT=REDIS_PORT:latest,REDIS_PASSWORD=REDIS_PASSWORD:latest,REDIS_USERNAME=REDIS_USERNAME:latest,NEO4J_URI=NEO4J_URI:latest,NEO4J_USER=NEO4J_USER:latest,NEO4J_PASSWORD=NEO4J_PASSWORD:latest

echo "部署完成！"
echo ""
echo "注意事項："
echo "1. Neo4j 免費版限制 50,000 個節點"
echo "2. 首次連接可能需要等待 1-2 分鐘"
echo "3. 檢查 /health 端點確認 Neo4j 連接狀態"