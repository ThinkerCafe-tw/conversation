# Neo4j 知識圖譜整合指南

## 概述

我們已成功整合 Neo4j 圖資料庫到 LINE Bot 系統中，實現了智慧的自然語言理解和用戶行為分析。

## 新增的模組

### 1. knowledge_graph.py
知識圖譜核心模組，管理所有圖資料庫操作：
- 用戶、訊息、功能、主題節點的 CRUD 操作
- 關係建立（SENT、TRIGGERS、MENTIONS、FOLLOWED_BY）
- 查詢功能（相似意圖、用戶偏好、社交推薦）
- 社群洞察和分析

### 2. intent_analyzer.py
意圖分析模組，使用 NLP 和知識圖譜理解用戶意圖：
- 語義嵌入（使用 sentence-transformers）
- 中文分詞（使用 jieba）
- 規則匹配 + 機器學習混合方法
- 基於歷史行為的個人化推薦

### 3. test_neo4j_connection.py
測試腳本，驗證 Neo4j 連接和基本功能

## 環境設定

在 `.env` 檔案中加入以下變數：

```bash
# Neo4j AuraDB 連接資訊
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-generated-password
```

## 新增的依賴

```txt
neo4j==5.15.0              # Neo4j Python 驅動
sentence-transformers==2.2.2  # 語義嵌入模型
jieba==0.42.1              # 中文分詞
numpy==1.24.3              # 數值計算
```

## 主要功能改進

### 1. 智慧意圖識別
系統現在可以理解自然語言並自動導向對應功能：
- "我想玩遊戲" → 自動開始接龍
- "看看統計" → 顯示即時統計
- "3" → 智慧識別為投票選項

### 2. 個人化推薦
基於用戶歷史行為和社交關係推薦功能：
- 分析用戶偏好的功能
- 基於朋友使用的功能推薦
- 時間相關的智慧建議

### 3. 知識累積
所有互動都會儲存到知識圖譜中：
- 建立用戶-訊息-功能的關聯
- 追蹤對話流程
- 挖掘熱門主題

### 4. 雙寫機制
保持 Redis（即時性）和 Neo4j（持久性）同步：
- Redis 用於快速讀寫和即時功能
- Neo4j 用於複雜查詢和關係分析

## 資料模型

```cypher
// 節點類型
(:User {id, name, joined_at, message_count})
(:Message {id, content, timestamp, embedding})
(:Feature {name, category, usage_count})
(:Topic {name, frequency})

// 關係類型
(:User)-[:SENT {time}]->(:Message)
(:Message)-[:TRIGGERS]->(:Feature)
(:Message)-[:MENTIONS]->(:Topic)
(:Message)-[:FOLLOWED_BY {time}]->(:Message)
```

## 部署注意事項

1. **Neo4j AuraDB Free 限制**
   - 最多 50,000 個節點和關係
   - 足夠支援約 2,000 個活躍用戶

2. **效能優化**
   - 已建立必要的索引和約束
   - 查詢已優化以減少遍歷深度
   - 實作快取機制減少重複查詢

3. **錯誤處理**
   - Neo4j 連接失敗時系統仍可運作
   - 雙寫失敗不影響主要功能
   - 所有錯誤都會記錄但不中斷服務

## 測試方法

1. 執行連接測試：
```bash
python test_neo4j_connection.py
```

2. 測試自然語言理解：
- 發送 "我想玩接龍" → 應自動開始接龍
- 發送 "查看統計" → 應顯示統計資訊
- 發送數字 → 應識別為投票

## 未來擴展

1. **進階分析**
   - 社群網絡分析
   - 話題趨勢預測
   - 異常行為檢測

2. **更多 AI 功能**
   - 對話摘要生成
   - 智慧問答系統
   - 內容推薦引擎

3. **視覺化**
   - 知識圖譜視覺化界面
   - 用戶互動網絡圖
   - 即時資料儀表板

## 監控指標

通過 `/health` 端點可查看系統狀態：
```json
{
  "status": "healthy",
  "firestore": "connected",
  "neo4j": "connected",
  "redis": "connected"
}
```

## 故障排除

1. **Neo4j 連接失敗**
   - 檢查環境變數是否正確設定
   - 確認 Neo4j AuraDB 實例正在運行
   - 檢查網路連接

2. **意圖分析不準確**
   - 可能需要更多訓練資料
   - 調整信心度閾值（目前為 0.8）
   - 檢查分詞結果是否正確

3. **效能問題**
   - 檢查 Neo4j 查詢執行計畫
   - 考慮增加快取
   - 減少嵌入向量維度