# 部署前檢查清單

## 🚨 必須通過的測試（阻擋部署）

### 1. 關鍵用戶流程測試 ⚡
這些測試失敗將**立即中止部署**：

- [ ] **新用戶說「你好」必須有歡迎訊息**
  - 測試輸入：你好、嗨、哈囉、安安、hello、hi
  - 必須包含：歡迎詞、功能介紹、使用提示
  
- [ ] **自然語言理解**
  - 「我想玩遊戲」→ 顯示遊戲選單
  - 「好無聊」→ 顯示遊戲選單
  - 「怎麼用」→ 顯示幫助
  
- [ ] **基本指令回應**
  - 統計 → 顯示即時統計
  - 幫助 → 顯示完整功能列表
  - 廣播 → 查詢最新廣播
  
- [ ] **錯誤格式提示**
  - 「接龍」（無參數）→ 提示正確格式
  - 「投票」（無選項）→ 提示正確格式

### 2. 系統健康檢查 🏥
- [ ] `/health` 端點返回 200
- [ ] Neo4j 連接狀態正常
- [ ] Redis 連接狀態正常（如有使用）
- [ ] Firestore 連接正常

### 3. 效能基準 ⚡
- [ ] Webhook 回應時間 < 3 秒
- [ ] 健康檢查回應時間 < 1 秒
- [ ] 無記憶體洩漏警告

## 📋 部署流程

### 1. 本地測試（開發者）
```bash
# 執行關鍵流程測試
python tests/critical_flows.py

# 執行單元測試
pytest tests/unit/ -v

# 檢查程式碼品質
flake8 app.py
```

### 2. CI/CD 自動化測試
```yaml
# GitHub Actions 流程
1. 程式碼推送 → 觸發 CI
2. 執行單元測試
3. 執行整合測試（含 Neo4j、Redis）
4. 執行關鍵流程測試
5. 構建 Docker 映像
6. 部署到測試環境
7. 執行 Smoke Tests
8. 手動批准後部署到生產環境
9. 執行生產環境測試
10. 失敗自動回滾
```

### 3. 測試環境驗證
- 部署到 `frequency-bot-staging`
- 執行 Smoke Tests
- 手動測試關鍵功能

### 4. 生產環境部署
- 需要手動批准
- 部署後立即執行生產測試
- 監控錯誤率 15 分鐘

## 🔍 監控指標

### 部署後立即監控（15分鐘）
1. **錯誤率**
   - Webhook 500 錯誤 < 1%
   - 無重複的錯誤模式
   
2. **回應時間**
   - P95 < 3秒
   - P99 < 5秒
   
3. **用戶回饋**
   - 無「沒反應」投訴
   - 新用戶成功互動率 > 80%

## 🚨 回滾條件

立即回滾如果：
1. 關鍵流程測試失敗
2. 錯誤率 > 5%
3. 多個用戶回報「沒反應」
4. Neo4j 或 Firestore 連接失敗

## 📝 測試案例範本

### 手動測試腳本
```
1. 開啟 LINE
2. 找到 Bot
3. 輸入「你好」
   ✓ 應該看到歡迎訊息
   ✓ 應該有功能介紹
4. 輸入「我想玩遊戲」
   ✓ 應該看到遊戲選單
5. 輸入「統計」
   ✓ 應該看到即時統計
6. 輸入「接龍」
   ✓ 應該看到格式提示
7. 輸入隨意文字
   ✓ 應該看到訊息計數回饋
```

## 🛡️ 安全網

### 1. 灰度發布
```bash
# 10% 流量到新版本
gcloud run services update-traffic frequency-bot \
  --to-revisions=frequency-bot-00016=10,frequency-bot-00015=90

# 觀察 15 分鐘後增加到 50%
gcloud run services update-traffic frequency-bot \
  --to-revisions=frequency-bot-00016=50,frequency-bot-00015=50

# 確認無誤後 100%
gcloud run services update-traffic frequency-bot \
  --to-revisions=frequency-bot-00016=100
```

### 2. 快速回滾
```bash
# 一鍵回滾到前一版本
gcloud run services update-traffic frequency-bot \
  --to-revisions=PRIOR=100 --region=asia-east1
```

## ✅ 最終確認清單

部署前，請確認：
- [ ] 所有關鍵流程測試通過
- [ ] 程式碼已通過 Code Review
- [ ] 環境變數已正確設定
- [ ] 監控告警已設定
- [ ] 回滾計劃已準備
- [ ] 團隊成員已通知

只有當所有項目都勾選後，才能進行生產環境部署！