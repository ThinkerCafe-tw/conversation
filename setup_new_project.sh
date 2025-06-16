#!/bin/bash

PROJECT_ID="probable-axon-451311-e1"

echo "設定專案 ID: $PROJECT_ID"
gcloud config set project $PROJECT_ID

echo "啟用必要的 API..."
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable cloudscheduler.googleapis.com
gcloud services enable secretmanager.googleapis.com

echo "檢查 Firestore 狀態..."
gcloud firestore databases list

echo "建立 Firestore（如果不存在）..."
gcloud firestore databases create --location=asia-east1 2>/dev/null || echo "Firestore 可能已存在"

echo "設定完成！"
echo "現在可以執行部署："
echo "gcloud run deploy frequency-bot --source . --dockerfile Dockerfile.cloudrun --region asia-east1 --allow-unauthenticated"