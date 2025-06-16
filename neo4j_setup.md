# Neo4j AuraDB 設定指南

## 1. 註冊 Neo4j AuraDB Free

1. 訪問 https://neo4j.com/cloud/aura-free/
2. 註冊帳號並選擇 "AuraDB Free"
3. 選擇最近的區域（推薦 Singapore）
4. 記下以下資訊：
   - Connection URI: `neo4j+s://xxxxx.databases.neo4j.io`
   - Username: `neo4j`
   - Password: `your-generated-password`

## 2. 設定環境變數

```bash
# 在 Google Cloud Secret Manager 中設定
echo -n "neo4j+s://xxxxx.databases.neo4j.io" | gcloud secrets create NEO4J_URI --data-file=-
echo -n "neo4j" | gcloud secrets create NEO4J_USER --data-file=-
echo -n "your-password" | gcloud secrets create NEO4J_PASSWORD --data-file=-
```

## 3. 測試連接

使用下方的測試腳本確認連接正常。

## 4. 資料庫初始化

連接成功後，執行初始化腳本建立索引和約束。