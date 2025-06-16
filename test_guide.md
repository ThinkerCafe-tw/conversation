# 系統測試指南

## 1. 基本健康檢查

### API 端點測試
```bash
# 健康檢查
curl https://frequency-bot-fqtwx7n5ma-de.a.run.app/health

# 首頁
curl https://frequency-bot-fqtwx7n5ma-de.a.run.app/
```

## 2. LINE Bot 功能測試

### 測試步驟：

1. **在 LINE 中加入您的 Bot**
2. **發送以下測試訊息**：

### A. 智慧意圖識別測試
測試 Neo4j 的自然語言理解功能：

```
發送: 我想玩遊戲
預期: 系統應該理解並自動開始文字接龍

發送: 看看統計
預期: 系統應該顯示即時統計資訊

發送: 查看廣播
預期: 系統應該顯示最新廣播
```

### B. 快捷選單測試
```
發送: 玩
預期: 顯示遊戲選單

發送: 看
預期: 顯示資訊查看選單

發送: 救
預期: 顯示防災互助選單
```

### C. 核心功能測試

#### 1. 廣播系統
```
發送: 今天天氣真好
預期: 加入廣播池，顯示進度

發送: 統計
預期: 查看當前小時的訊息統計

發送: 廣播
預期: 查看最新生成的廣播
```

#### 2. 文字接龍
```
發送: 接龍 蘋果
預期: 開始新的接龍遊戲

發送: 果汁
預期: 接龍成功，顯示進度
```

#### 3. 投票功能
```
發送: 投票 晚餐吃什麼/火鍋/燒烤/日料
預期: 創建新投票

發送: 1
預期: 投票給第一個選項

發送: 投票結果
預期: 顯示當前投票結果
```

#### 4. 防災資訊
```
發送: 防空 台北車站地下層 捷運站 500
預期: 新增避難所資訊

發送: 防災資訊
預期: 查看所有防災資訊
```

#### 5. API 統計
```
發送: API統計
預期: 顯示 Gemini API 使用量
```

### D. 新用戶體驗測試
```
發送: 你好
預期: 顯示歡迎訊息和快速開始指南
```

## 3. 知識圖譜驗證

### 使用測試腳本驗證 Neo4j 資料
```bash
# 在本地執行
python test_neo4j_connection.py

# 測試意圖分析
python test_intent_analyzer.py
```

### 查看 Neo4j 資料
1. 登入 Neo4j Aura Console: https://console.neo4j.io
2. 使用 Neo4j Browser 執行查詢：

```cypher
// 查看所有用戶
MATCH (u:User) RETURN u LIMIT 10

// 查看訊息和功能關聯
MATCH (u:User)-[:SENT]->(m:Message)-[:TRIGGERS]->(f:Feature)
RETURN u.id, m.content, f.name LIMIT 20

// 查看功能使用統計
MATCH (f:Feature)
RETURN f.name, f.usage_count
ORDER BY f.usage_count DESC
```

## 4. 監控和日誌

### 查看服務日誌
```bash
# 實時日誌
gcloud run services logs tail frequency-bot --region=asia-east1

# 最近的錯誤
gcloud run services logs read frequency-bot --region=asia-east1 --limit=50 | grep ERROR
```

### 查看指標
```bash
# CPU 和記憶體使用
gcloud monitoring metrics list --filter="resource.type=cloud_run_revision AND metric.type:request_count"
```

## 5. 預期行為

### 成功的智慧功能表現：
1. **自然語言理解**
   - "我想玩" → 自動推薦遊戲
   - "好無聊" → 可能推薦接龍或其他互動
   - 數字 → 自動識別為投票

2. **個人化體驗**
   - 系統會學習用戶偏好
   - 根據使用歷史推薦功能
   - 記住用戶的互動模式

3. **知識累積**
   - 每次互動都會儲存到圖資料庫
   - 建立用戶之間的關聯
   - 發現熱門話題和使用模式

## 6. 故障排除

### 如果功能不正常：

1. **檢查服務狀態**
```bash
curl https://frequency-bot-fqtwx7n5ma-de.a.run.app/health
```

2. **查看錯誤日誌**
```bash
gcloud run services logs read frequency-bot --region=asia-east1 --limit=20
```

3. **驗證環境變數**
確保所有必要的 Secret 都已設定：
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_CHANNEL_SECRET  
- GEMINI_API_KEY
- NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
- REDIS 相關設定

4. **檢查 Neo4j 連接**
- 確認 Neo4j Aura 實例正在運行
- 檢查網路連接

## 7. 性能測試

### 並發測試
```bash
# 使用 ab (Apache Bench) 測試
ab -n 100 -c 10 https://frequency-bot-fqtwx7n5ma-de.a.run.app/health
```

### 響應時間測試
```bash
# 測量 API 響應時間
time curl https://frequency-bot-fqtwx7n5ma-de.a.run.app/health
```

## 8. 測試檢查清單

- [ ] 健康檢查端點正常
- [ ] LINE Webhook 接收訊息
- [ ] 廣播功能正常累積訊息
- [ ] 統計功能顯示正確數據
- [ ] 文字接龍可以開始和進行
- [ ] 投票創建和參與正常
- [ ] 防災資訊可以新增和查詢
- [ ] Neo4j 正確記錄用戶互動
- [ ] 智慧意圖識別準確
- [ ] 錯誤處理優雅（不會崩潰）

## 測試建議順序

1. 先測試基本功能（廣播、統計）
2. 測試互動功能（接龍、投票）
3. 測試智慧功能（自然語言理解）
4. 檢查知識圖譜資料
5. 進行壓力測試