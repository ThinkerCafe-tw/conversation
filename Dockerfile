FROM python:3.9-slim

# 設定時區為台北時間
ENV TZ=Asia/Taipei
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app

# 複製所有檔案
COPY . .

# 安裝Python依賴
RUN pip install --no-cache-dir -r requirements.txt

# app.py 已經是主程式檔案，不需要重命名

# Cloud Run 會自動設定 PORT 環境變數
EXPOSE 8080

# 使用 gunicorn 作為生產伺服器
CMD exec gunicorn --bind :${PORT:-8080} --workers 1 --threads 8 --timeout 0 app:app