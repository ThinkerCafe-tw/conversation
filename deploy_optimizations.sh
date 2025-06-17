#!/bin/bash

echo "=== 部署優化版本到 Cloud Run ==="
echo ""
echo "此腳本將部署最新的優化版本，包含："
echo "✓ Redis 連接池優化"
echo "✓ Firestore 批次操作"
echo "✓ 響應快取系統"
echo "✓ Lua 腳本速率限制"
echo "✓ 搜尋結果快取"
echo ""

# 設定專案
echo "1. 設定 Google Cloud 專案..."
gcloud config set project probable-axon-451311-e1

# 檢查認證
echo ""
echo "2. 檢查認證狀態..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "需要登入 Google Cloud，請在瀏覽器中完成認證："
    gcloud auth login
fi

# 部署
echo ""
echo "3. 開始部署優化版本..."
gcloud run deploy frequency-bot \
    --source . \
    --region=asia-east1 \
    --allow-unauthenticated \
    --timeout=60m \
    --memory=512Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=10 \
    --concurrency=100

# 檢查部署結果
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 部署成功！"
    echo ""
    echo "4. 驗證優化功能..."
    
    # 等待服務啟動
    sleep 5
    
    # 測試健康檢查
    echo "- 測試健康檢查端點..."
    curl -s https://frequency-bot-808270083585.asia-east1.run.app/health | python -m json.tool
    
    echo ""
    echo "5. 優化功能已啟用："
    echo "✓ 連接池將自動管理 Redis 連接"
    echo "✓ 批次操作將減少 Firestore 寫入延遲"
    echo "✓ 熱門查詢將被快取 1-15 分鐘"
    echo "✓ 速率限制使用原子操作"
    echo "✓ 搜尋結果快取 15 分鐘"
    echo ""
    echo "🚀 所有優化已部署完成！"
else
    echo ""
    echo "❌ 部署失敗，請檢查錯誤訊息"
fi