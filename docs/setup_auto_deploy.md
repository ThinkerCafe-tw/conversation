# 設定自動部署 (GitHub Actions)

## 步驟 1: 創建服務帳號

```bash
# 創建服務帳號
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions Deploy"

# 授予必要權限
gcloud projects add-iam-policy-binding probable-axon-451311-e1 \
  --member="serviceAccount:github-actions@probable-axon-451311-e1.iam.gserviceaccount.com" \
  --role="roles/run.developer"

gcloud projects add-iam-policy-binding probable-axon-451311-e1 \
  --member="serviceAccount:github-actions@probable-axon-451311-e1.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding probable-axon-451311-e1 \
  --member="serviceAccount:github-actions@probable-axon-451311-e1.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

# 創建金鑰
gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions@probable-axon-451311-e1.iam.gserviceaccount.com
```

## 步驟 2: 設定 GitHub Secret

1. 開啟瀏覽器，前往：https://github.com/ThinkerCafe-tw/conversation/settings/secrets/actions
2. 點擊 "New repository secret"
3. Name: `GCP_SA_KEY`
4. Value: 貼上 `key.json` 的內容
5. 點擊 "Add secret"

## 步驟 3: 測試自動部署

推送任何變更到 main 分支，GitHub Actions 會自動：
1. 檢查代碼
2. 部署到 Cloud Run
3. 驗證健康狀態

## 查看部署狀態

前往：https://github.com/ThinkerCafe-tw/conversation/actions

## 手動觸發部署

1. 前往 Actions 頁面
2. 選擇 "Auto Deploy to Cloud Run"
3. 點擊 "Run workflow"

## 部署日誌

所有部署記錄都會保存在 GitHub Actions 中，包括：
- 部署時間
- 部署結果
- 錯誤訊息（如果有）
- 健康檢查結果