# 頻率共振 LINE Bot

一個結合集體記憶與 AI 廣播的 LINE Bot，透過收集群體訊息創造每小時的智慧廣播。

## 🌟 特色功能

### 核心功能
- **頻率廣播**：每小時自動生成 AI 廣播，將大家的訊息編織成詩意的內容
- **集體記憶**：結合個人記憶與群體意識，創造獨特的廣播體驗
- **知識圖譜**：使用 Neo4j 建立訊息關聯，理解話題演變

### 社群互動
- **文字接龍**：多人參與的接龍遊戲，支援完整路徑顯示
- **即時投票**：快速發起投票，收集群體意見
- **防災互助**：分享避難所資訊與物資

### 智慧功能
- **自然語言理解**：理解「我想玩遊戲」、「好無聊」等口語表達
- **智慧引導**：為新用戶提供個人化使用建議
- **10x 優化廣播**：濃縮資訊精華，提供行動建議

## 🚀 快速開始

### 環境需求
- Python 3.9+
- Google Cloud Platform 帳號
- LINE Messaging API 帳號
- Neo4j Aura (免費版)
- Redis Cloud (免費版)

### 本地開發
```bash
# 1. 複製專案
git clone git@github.com:ThinkerCafe-tw/conversation.git
cd conversation

# 2. 建立虛擬環境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 設定環境變數
cp .env.example .env
# 編輯 .env 填入你的 API keys

# 5. 執行
python app.py
```

### 部署到 Google Cloud Run
```bash
# 1. 設定 gcloud
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. 啟用必要的 APIs
gcloud services enable run.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable secretmanager.googleapis.com

# 3. 部署
gcloud run deploy frequency-bot \
  --source . \
  --region asia-east1 \
  --allow-unauthenticated
```

## 📖 使用指南

### 基本指令
- `統計` - 查看即時統計資訊
- `廣播` - 查看最新的頻率廣播
- `幫助` - 顯示所有功能

### 遊戲功能
- `接龍 [詞語]` - 開始文字接龍
- `接龍狀態` - 查看當前接龍進度
- `投票 主題/選項1/選項2` - 發起投票

### 快捷選單
- `玩` - 顯示遊戲選單
- `看` - 顯示資訊查詢選單
- `救` - 顯示防災功能選單

## 🏗️ 系統架構

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   LINE App  │────▶│  Cloud Run   │────▶│  Firestore  │
└─────────────┘     └──────────────┘     └─────────────┘
                            │                     
                            ├────────────▶ ┌─────────────┐
                            │              │    Neo4j    │
                            │              └─────────────┘
                            │                     
                            └────────────▶ ┌─────────────┐
                                          │    Redis    │
                                          └─────────────┘
```

### 技術棧
- **後端**：Python Flask
- **AI**：Google Gemini API
- **資料庫**：Firestore (NoSQL), Neo4j (Graph), Redis (Cache)
- **部署**：Google Cloud Run
- **排程**：Cloud Scheduler

## 🔧 環境變數

```env
# LINE Bot
LINE_CHANNEL_ACCESS_TOKEN=your_token
LINE_CHANNEL_SECRET=your_secret

# Google Cloud
GOOGLE_CLOUD_PROJECT=your_project_id
GEMINI_API_KEY=your_gemini_key

# Neo4j
NEO4J_URI=neo4j+s://xxxxx.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Redis
REDIS_HOST=redis-xxxxx.c302.asia-northeast1-1.gce.redns.redis-cloud.com
REDIS_PORT=13623
REDIS_PASSWORD=your_password
```

## 📝 開發指南

### 專案結構
```
conversation/
├── app.py                    # 主程式進入點
├── frequency_bot_firestore.py # 核心廣播功能
├── collective_memory.py      # 集體記憶系統
├── knowledge_graph.py        # Neo4j 知識圖譜
├── community_features.py     # 社群互動功能
├── security_filter.py        # 安全過濾器
├── optimizations/           # 優化模組
│   ├── smart_onboarding.py  # 智慧引導
│   ├── performance_dashboard.py # 效能監控
│   └── core_value_optimizer.py  # 10x 優化
└── tests/                   # 測試檔案
```

### 測試
```bash
# 執行單元測試
pytest tests/unit/

# 執行關鍵流程測試
python tests/critical_flows.py

# 執行生產環境測試
python tests/production_tests.py --url YOUR_SERVICE_URL
```

## 🤝 貢獻指南

1. Fork 專案
2. 建立功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交變更 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

## 📄 授權

本專案採用 MIT 授權 - 詳見 [LICENSE](LICENSE) 檔案

## 🙏 致謝

- Google Cloud Platform 提供的免費額度
- LINE Messaging API
- Neo4j Aura 免費版
- Redis Cloud 免費版

---

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>