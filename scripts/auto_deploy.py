#!/usr/bin/env python3
"""
自動部署腳本
由 Claude 自動執行
"""

import subprocess
import sys
import json
import time
from datetime import datetime

class AutoDeployer:
    def __init__(self):
        self.service_name = "frequency-bot"
        self.region = "asia-east1"
        self.project_id = "probable-axon-451311-e1"
        self.service_url = "https://frequency-bot-808270083585.asia-east1.run.app"
        
    def log(self, message, level="INFO"):
        """輸出日誌"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def run_command(self, command, check=True):
        """執行命令並返回結果"""
        self.log(f"執行: {command}")
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True,
                check=check
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.CalledProcessError as e:
            return False, e.stdout, e.stderr
            
    def check_syntax(self):
        """檢查 Python 語法"""
        self.log("檢查 Python 語法...")
        files = ["app.py", "frequency_bot_firestore.py", "community_features.py"]
        
        for file in files:
            success, _, error = self.run_command(f"python -m py_compile {file}")
            if not success:
                self.log(f"❌ {file} 語法錯誤: {error}", "ERROR")
                return False
                
        self.log("✅ 語法檢查通過")
        return True
        
    def git_operations(self):
        """Git 操作：提交和推送"""
        self.log("執行 Git 操作...")
        
        # 檢查是否有變更
        success, stdout, _ = self.run_command("git status --porcelain")
        if not stdout.strip():
            self.log("沒有需要提交的變更")
            return True
            
        # 添加所有變更
        self.run_command("git add -A")
        
        # 提交
        commit_msg = f"auto: Deploy optimizations at {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        success, _, _ = self.run_command(f'git commit -m "{commit_msg}"')
        
        if success:
            # 推送到 GitHub
            success, _, _ = self.run_command("git push origin main")
            if success:
                self.log("✅ 代碼已推送到 GitHub")
            else:
                self.log("⚠️  無法推送到 GitHub（可能需要認證）", "WARNING")
                
        return True
        
    def deploy(self):
        """部署到 Cloud Run"""
        self.log("開始部署到 Cloud Run...")
        
        # 建構部署命令
        deploy_cmd = f"""
        gcloud run deploy {self.service_name} \
            --source . \
            --region={self.region} \
            --project={self.project_id} \
            --allow-unauthenticated \
            --quiet \
            --format=json
        """
        
        # 嘗試部署
        success, stdout, stderr = self.run_command(deploy_cmd, check=False)
        
        if "Reauthentication failed" in stderr:
            self.log("❌ 需要重新認證，請執行: gcloud auth login", "ERROR")
            self.log("部署腳本已準備好，等待手動認證後重試", "INFO")
            
            # 創建手動部署命令
            with open("manual_deploy.sh", "w") as f:
                f.write("#!/bin/bash\n")
                f.write("echo '請先執行: gcloud auth login'\n")
                f.write("echo '認證完成後，此腳本將自動部署'\n")
                f.write("read -p '按 Enter 繼續部署...'\n")
                f.write(deploy_cmd)
            
            subprocess.run("chmod +x manual_deploy.sh", shell=True)
            self.log("已創建 manual_deploy.sh，請執行此腳本完成部署")
            return False
            
        if success:
            self.log("✅ 部署成功！")
            return True
        else:
            self.log(f"❌ 部署失敗: {stderr}", "ERROR")
            return False
            
    def verify_deployment(self):
        """驗證部署是否成功"""
        self.log("驗證部署...")
        
        # 等待服務啟動
        time.sleep(10)
        
        # 檢查健康端點
        success, stdout, _ = self.run_command(
            f"curl -s {self.service_url}/health"
        )
        
        if success and stdout:
            try:
                health_data = json.loads(stdout)
                if health_data.get("status") == "healthy":
                    self.log("✅ 服務健康檢查通過")
                    self.log(f"服務狀態: {json.dumps(health_data, indent=2)}")
                    return True
            except:
                pass
                
        self.log("⚠️  無法驗證服務狀態", "WARNING")
        return False
        
    def run(self):
        """執行完整的部署流程"""
        self.log("=== 開始自動部署流程 ===")
        
        # 1. 語法檢查
        if not self.check_syntax():
            self.log("部署中止：語法錯誤", "ERROR")
            return False
            
        # 2. Git 操作
        self.git_operations()
        
        # 3. 部署
        if self.deploy():
            # 4. 驗證
            self.verify_deployment()
            self.log("=== 部署流程完成 ===")
            return True
        else:
            self.log("=== 部署失敗，請查看錯誤訊息 ===", "ERROR")
            return False

if __name__ == "__main__":
    deployer = AutoDeployer()
    success = deployer.run()
    sys.exit(0 if success else 1)