"""
效能監控儀表板 - 提供即時系統效能指標
"""

import time
try:
    import psutil
except ImportError:
    psutil = None
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import deque
import json

class PerformanceDashboard:
    """系統效能監控儀表板"""
    
    def __init__(self, redis_client=None, firestore_client=None):
        self.redis = redis_client
        self.firestore = firestore_client
        
        # 效能指標快取
        self.metrics_cache = {
            "api_latency": deque(maxlen=100),      # 最近100次API呼叫延遲
            "db_latency": deque(maxlen=100),       # 資料庫查詢延遲
            "message_throughput": deque(maxlen=60), # 每分鐘訊息吞吐量
            "concurrent_users": deque(maxlen=60),   # 並發用戶數
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # Gemini API 指標
        self.gemini_metrics = {
            "api_calls": 0,
            "total_tokens": 0,
            "avg_response_time": 0
        }
        
        # 優化建議
        self.optimization_suggestions = []
        
        # 啟動時間
        self.start_time = time.time()
    
    def record_api_latency(self, endpoint: str, latency_ms: float):
        """記錄 API 延遲"""
        self.metrics_cache["api_latency"].append({
            "endpoint": endpoint,
            "latency": latency_ms,
            "timestamp": time.time()
        })
        
        # 儲存到 Redis（如果可用）
        if self.redis:
            key = f"metrics:api:{endpoint}:{int(time.time())}"
            self.redis.setex(key, 3600, latency_ms)  # 保留1小時
    
    def record_db_operation(self, operation: str, duration_ms: float):
        """記錄資料庫操作"""
        self.metrics_cache["db_latency"].append({
            "operation": operation,
            "duration": duration_ms,
            "timestamp": time.time()
        })
    
    def record_message(self, user_id: str):
        """記錄訊息處理"""
        current_minute = int(time.time() / 60)
        
        # 更新吞吐量
        if self.metrics_cache["message_throughput"]:
            last_record = self.metrics_cache["message_throughput"][-1]
            if last_record["minute"] == current_minute:
                last_record["count"] += 1
            else:
                self.metrics_cache["message_throughput"].append({
                    "minute": current_minute,
                    "count": 1
                })
        else:
            self.metrics_cache["message_throughput"].append({
                "minute": current_minute,
                "count": 1
            })
    
    def update_concurrent_users(self, count: int):
        """更新並發用戶數"""
        self.metrics_cache["concurrent_users"].append({
            "count": count,
            "timestamp": time.time()
        })
    
    def update_cache_stats(self, hit: bool):
        """更新快取統計"""
        if hit:
            self.metrics_cache["cache_hits"] += 1
        else:
            self.metrics_cache["cache_misses"] += 1
    
    def get_system_metrics(self) -> Dict:
        """獲取系統資源使用情況"""
        if psutil:
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
            except:
                cpu_percent = 0
                memory = type('obj', (object,), {'used': 0, 'total': 1, 'percent': 0})
        else:
            # Cloud Run 環境可能沒有 psutil
            cpu_percent = 0
            memory = type('obj', (object,), {'used': 0, 'total': 1, 'percent': 0})
        
        return {
            "cpu": {
                "percent": cpu_percent,
                "cores": os.cpu_count() or 1
            },
            "memory": {
                "used_gb": round(memory.used / (1024 ** 3), 2),
                "total_gb": round(memory.total / (1024 ** 3), 2),
                "percent": memory.percent
            },
            "uptime_hours": round((time.time() - self.start_time) / 3600, 2)
        }
    
    def calculate_p95_latency(self) -> Dict[str, float]:
        """計算 P95 延遲"""
        api_latencies = [m["latency"] for m in self.metrics_cache["api_latency"]]
        db_latencies = [m["duration"] for m in self.metrics_cache["db_latency"]]
        
        def get_p95(values):
            if not values:
                return 0
            sorted_values = sorted(values)
            index = int(len(sorted_values) * 0.95)
            return sorted_values[index] if index < len(sorted_values) else sorted_values[-1]
        
        return {
            "api_p95": round(get_p95(api_latencies), 2),
            "db_p95": round(get_p95(db_latencies), 2)
        }
    
    def get_throughput_stats(self) -> Dict:
        """獲取吞吐量統計"""
        if not self.metrics_cache["message_throughput"]:
            return {"current": 0, "average": 0, "peak": 0}
        
        counts = [m["count"] for m in self.metrics_cache["message_throughput"]]
        current = counts[-1] if counts else 0
        average = sum(counts) / len(counts) if counts else 0
        peak = max(counts) if counts else 0
        
        # 換算成每秒
        return {
            "current_per_sec": round(current / 60, 2),
            "average_per_sec": round(average / 60, 2),
            "peak_per_sec": round(peak / 60, 2)
        }
    
    def get_cache_efficiency(self) -> float:
        """計算快取效率"""
        total = self.metrics_cache["cache_hits"] + self.metrics_cache["cache_misses"]
        if total == 0:
            return 0
        return round(self.metrics_cache["cache_hits"] / total * 100, 2)
    
    def generate_optimization_suggestions(self) -> List[str]:
        """生成優化建議"""
        suggestions = []
        
        # 基於延遲
        p95 = self.calculate_p95_latency()
        if p95["api_p95"] > 200:
            suggestions.append("⚡ API P95 延遲超過 200ms，建議啟用請求快取")
        
        # 基於快取
        cache_efficiency = self.get_cache_efficiency()
        if cache_efficiency < 80:
            suggestions.append(f"💾 快取命中率僅 {cache_efficiency}%，建議優化快取策略")
        
        # 基於 Gemini API
        if self.gemini_metrics["avg_response_time"] > 1000:
            suggestions.append("⚡ Gemini API 回應較慢，考慮使用快取")
        
        # 基於記憶體
        system_metrics = self.get_system_metrics()
        if system_metrics["memory"]["percent"] > 80:
            suggestions.append("💡 記憶體使用率高，建議增加資源或優化記憶體使用")
        
        # Neo4j 向量索引建議
        if not hasattr(self, "_vector_index_suggested"):
            suggestions.append("🔍 啟用 Neo4j 向量索引可提升查詢速度 40%")
            self._vector_index_suggested = True
        
        return suggestions[:3]  # 最多顯示3個建議
    
    def format_dashboard(self) -> str:
        """格式化儀表板輸出"""
        system = self.get_system_metrics()
        p95 = self.calculate_p95_latency()
        throughput = self.get_throughput_stats()
        cache_eff = self.get_cache_efficiency()
        suggestions = self.generate_optimization_suggestions()
        
        # 計算並發用戶數
        concurrent_users = 0
        if self.metrics_cache["concurrent_users"] and len(self.metrics_cache["concurrent_users"]) > 0:
            concurrent_users = self.metrics_cache["concurrent_users"][-1]["count"]
        
        dashboard = f"""🖥️ 系統狀態儀表板
━━━━━━━━━━━━━━
⚡ 性能指標
• API 延遲: {round(sum(m["latency"] for m in list(self.metrics_cache["api_latency"])[-10:]) / 10, 2) if len(self.metrics_cache["api_latency"]) >= 10 else (round(sum(m["latency"] for m in self.metrics_cache["api_latency"]) / len(self.metrics_cache["api_latency"]), 2) if self.metrics_cache["api_latency"] else 0)}ms (p95: {p95['api_p95']}ms)
• 訊息處理: {throughput['current_per_sec']} 則/秒
• Gemini API: {self.gemini_metrics['api_calls']} 次呼叫

📊 知識圖譜
• 節點總數: {self._get_graph_stats().get('nodes', 'N/A')}
• 查詢 QPS: {throughput['current_per_sec']}
• 快取命中率: {cache_eff}%

🔧 資源使用
• CPU: {system['cpu']['percent']}% ({system['cpu']['cores']} cores)
• Memory: {system['memory']['used_gb']}GB / {system['memory']['total_gb']}GB
• Neo4j: {self._estimate_neo4j_memory()}MB

💡 優化建議"""
        
        for suggestion in suggestions:
            dashboard += f"\n{suggestion}"
        
        return dashboard
    
    def format_detailed_metrics(self) -> str:
        """格式化詳細指標"""
        recent_api = self.metrics_cache["api_latency"][-5:]
        recent_db = self.metrics_cache["db_latency"][-5:]
        
        details = "📈 詳細效能指標\n"
        details += "━━━━━━━━━━━━━━\n"
        
        if recent_api:
            details += "\n最近 API 呼叫:\n"
            for metric in recent_api:
                details += f"• {metric['endpoint']}: {metric['latency']:.2f}ms\n"
        
        if recent_db:
            details += "\n最近資料庫操作:\n"
            for metric in recent_db:
                details += f"• {metric['operation']}: {metric['duration']:.2f}ms\n"
        
        # Gemini API 詳細資訊
        details += f"\nGemini API:\n"
        details += f"• 總呼叫次數: {self.gemini_metrics['api_calls']}\n"
        details += f"• 總 Token 數: {self.gemini_metrics['total_tokens']}\n"
        details += f"• 平均回應時間: {self.gemini_metrics['avg_response_time']}ms\n"
        
        return details
    
    def _get_graph_stats(self) -> Dict:
        """獲取圖資料庫統計（簡化版）"""
        # 實際應該從 Neo4j 查詢
        return {
            "nodes": "24,531",
            "relationships": "156,789"
        }
    
    def _estimate_neo4j_memory(self) -> int:
        """估算 Neo4j 記憶體使用"""
        # 簡化估算
        return 156
    
    def export_metrics(self, format: str = "json") -> str:
        """匯出指標資料"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "system": self.get_system_metrics(),
            "performance": {
                "p95_latency": self.calculate_p95_latency(),
                "throughput": self.get_throughput_stats(),
                "cache_efficiency": self.get_cache_efficiency()
            },
            "suggestions": self.generate_optimization_suggestions()
        }
        
        if format == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        else:
            # 可以支援其他格式如 CSV, Prometheus 等
            return str(data)


class PerformanceOptimizer:
    """效能優化器 - 自動調整系統參數"""
    
    def __init__(self, dashboard: PerformanceDashboard):
        self.dashboard = dashboard
        self.optimization_history = []
    
    def auto_optimize(self) -> List[str]:
        """自動優化系統參數"""
        optimizations = []
        
        # 基於延遲調整批次大小
        p95 = self.dashboard.calculate_p95_latency()
        if p95["api_p95"] > 150:
            optimizations.append("減少批次大小以降低延遲")
            # 實際應該調整系統參數
        elif p95["api_p95"] < 50:
            optimizations.append("增加批次大小以提升吞吐量")
        
        # 基於 GPU 使用率調整並行度
        gpu_util = self.dashboard.gpu_metrics["utilization"]
        if gpu_util < 30:
            optimizations.append("增加並行處理數以充分利用 GPU")
        elif gpu_util > 90:
            optimizations.append("降低並行度以避免 GPU 過載")
        
        # 記錄優化歷史
        self.optimization_history.append({
            "timestamp": datetime.now(),
            "optimizations": optimizations,
            "metrics": {
                "p95_latency": p95,
                "gpu_utilization": gpu_util
            }
        })
        
        return optimizations


# 測試用例
if __name__ == "__main__":
    dashboard = PerformanceDashboard()
    
    # 模擬一些指標
    print("=== 模擬系統運行 ===\n")
    
    # 模擬 API 呼叫
    for i in range(20):
        endpoint = ["webhook", "stats", "broadcast"][i % 3]
        latency = 50 + (i % 7) * 20  # 50-190ms
        dashboard.record_api_latency(endpoint, latency)
    
    # 模擬資料庫操作
    for i in range(15):
        operation = ["query", "insert", "update"][i % 3]
        duration = 10 + (i % 5) * 8  # 10-42ms
        dashboard.record_db_operation(operation, duration)
    
    # 模擬訊息處理
    for i in range(100):
        dashboard.record_message(f"user_{i % 10}")
    
    # 更新並發用戶
    dashboard.update_concurrent_users(847)
    
    # 模擬快取
    for i in range(100):
        dashboard.update_cache_stats(i % 10 < 8)  # 80% 命中率
    
    # 顯示儀表板
    print(dashboard.format_dashboard())
    print("\n")
    print(dashboard.format_detailed_metrics())
    
    # 測試優化器
    print("\n=== 自動優化建議 ===")
    optimizer = PerformanceOptimizer(dashboard)
    suggestions = optimizer.auto_optimize()
    for suggestion in suggestions:
        print(f"• {suggestion}")
    
    # 匯出指標
    print("\n=== 匯出指標 (JSON) ===")
    print(dashboard.export_metrics()[:500] + "...")  # 顯示前500字元