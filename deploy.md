# 部署指南

## 系統需求
- Python 3.9+
- Redis 服務
- LINE Messaging API 帳號
- Google Gemini API 金鑰
- Sentry 帳號（選用）

## 環境變數設定
1. 複製 `.env.example` 為 `.env`
2. 填入所有必要的環境變數：
   - `LINE_CHANNEL_ACCESS_TOKEN` - LINE Bot 存取權杖
   - `LINE_CHANNEL_SECRET` - LINE Bot 頻道密鑰
   - `REDIS_HOST` - Redis 主機位址
   - `REDIS_PORT` - Redis 連接埠（預設 6379）
   - `GEMINI_API_KEY` - Google Gemini API 金鑰
   - `SENTRY_DSN` - Sentry DSN（選用）
   - `ENVIRONMENT` - 環境設定（production/development）
   - `PORT` - 應用程式連接埠（預設 5001）

## 部署方式

### 方式一：使用 Docker

```bash
# 建置映像檔
docker build -t frequency-bot .

# 執行容器
docker run -d \
  --name frequency-bot \
  -p 5001:5001 \
  --env-file .env \
  frequency-bot
```

### 方式二：使用 Heroku

1. 安裝 Heroku CLI
2. 登入 Heroku: `heroku login`
3. 建立新應用: `heroku create your-app-name`
4. 加入 Redis 附加元件: `heroku addons:create heroku-redis:hobby-dev`
5. 設定環境變數:
   ```bash
   heroku config:set LINE_CHANNEL_ACCESS_TOKEN=your_token
   heroku config:set LINE_CHANNEL_SECRET=your_secret
   heroku config:set GEMINI_API_KEY=your_key
   heroku config:set ENVIRONMENT=production
   ```
6. 部署: `git push heroku main`

### 方式三：使用 Railway

1. 登入 Railway
2. 建立新專案
3. 連接 GitHub repository
4. 加入 Redis 服務
5. 設定環境變數
6. 部署會自動進行

## LINE Bot 設定

1. 登入 [LINE Developers Console](https://developers.line.biz/)
2. 進入你的 Messaging API channel
3. 設定 Webhook URL：`https://your-domain.com/webhook`
4. 啟用 Webhook
5. 關閉自動回應訊息

## 安全建議

1. **HTTPS**: 確保使用 HTTPS（LINE 要求）
2. **環境變數**: 永遠不要將敏感資訊寫死在程式碼中
3. **錯誤處理**: 生產環境已關閉 debug 模式
4. **日誌**: 使用 Sentry 追蹤錯誤
5. **速率限制**: 考慮在反向代理層加入速率限制

## 監控與維護

1. **Sentry**: 監控錯誤和效能
2. **日誌**: 檢查應用程式日誌
3. **Redis**: 監控記憶體使用量
4. **定期更新**: 保持依賴套件更新

## 故障排除

### Redis 連線失敗
- 檢查 `REDIS_HOST` 和 `REDIS_PORT` 設定
- 確認 Redis 服務正在執行
- 檢查防火牆設定

### LINE Webhook 失敗
- 確認 Webhook URL 正確
- 檢查 SSL 憑證有效
- 查看 Sentry 錯誤日誌

### Gemini API 錯誤
- 確認 API 金鑰有效
- 檢查配額限制
- 查看錯誤訊息詳情