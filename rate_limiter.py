"""
API 速率限制中間件
使用滑動視窗算法實現速率限制
"""

import time
import logging
from functools import wraps
from typing import Dict, Optional, Tuple
from flask import request, jsonify, g
import redis
from datetime import timedelta
from connection_manager import connection_manager

logger = logging.getLogger(__name__)


class RateLimiter:
    """速率限制器實作"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """初始化速率限制器"""
        self.redis = redis_client
        self.redis_pool = None
        
        if not self.redis:
            import os
            redis_host = os.getenv('REDIS_HOST')
            redis_port = int(os.getenv('REDIS_PORT', 6379))
            redis_password = os.getenv('REDIS_PASSWORD')
            redis_username = os.getenv('REDIS_USERNAME', 'default')
            
            if redis_host:
                try:
                    self.redis_pool = connection_manager.setup_redis(
                        host=redis_host,
                        port=redis_port,
                        password=redis_password,
                        username=redis_username
                    )
                    self.redis = self.redis_pool.get_connection()
                    logger.info("Rate limiter Redis 連接成功")
                except Exception as e:
                    logger.error(f"Rate limiter Redis 連接失敗: {e}")
                    self.redis = None
    
    def is_allowed(self, identifier: str, limit: int, window: int) -> Tuple[bool, Dict]:
        """
        檢查請求是否允許
        
        Args:
            identifier: 識別符（如 IP 或用戶 ID）
            limit: 時間窗口內的請求限制
            window: 時間窗口（秒）
            
        Returns:
            (是否允許, 詳細資訊)
        """
        if not self.redis:
            # Redis 不可用時，允許所有請求但記錄警告
            logger.warning("Rate limiter Redis not available, allowing request")
            return True, {"allowed": True, "limit": limit, "remaining": limit, "reset": 0}
        
        try:
            now = time.time()
            window_start = now - window
            key = f"rate_limit:{identifier}"
            
            # 使用 Redis 管道提高效能
            pipe = self.redis.pipeline()
            
            # 移除過期的請求記錄
            pipe.zremrangebyscore(key, 0, window_start)
            
            # 獲取當前請求數
            pipe.zcard(key)
            
            # 添加當前請求
            pipe.zadd(key, {str(now): now})
            
            # 設置過期時間
            pipe.expire(key, window)
            
            results = pipe.execute()
            current_requests = results[1]
            
            # 計算剩餘請求數
            remaining = max(0, limit - current_requests - 1)
            
            # 獲取最早的請求時間以計算重置時間
            earliest = self.redis.zrange(key, 0, 0, withscores=True)
            if earliest:
                reset_time = int(earliest[0][1] + window)
            else:
                reset_time = int(now + window)
            
            allowed = current_requests < limit
            
            return allowed, {
                "allowed": allowed,
                "limit": limit,
                "remaining": remaining if allowed else 0,
                "reset": reset_time,
                "retry_after": reset_time - int(now) if not allowed else None
            }
            
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # 發生錯誤時允許請求通過
            return True, {"allowed": True, "limit": limit, "remaining": limit, "reset": 0}
    
    def get_identifier(self) -> str:
        """獲取請求識別符"""
        # 優先使用 LINE 用戶 ID
        if hasattr(g, 'user_id') and g.user_id:
            return f"user:{g.user_id}"
        
        # 使用 IP 地址作為備選
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            ip = forwarded_for.split(',')[0].strip()
        else:
            ip = request.headers.get('X-Real-IP', request.remote_addr)
        
        return f"ip:{ip}"


# 全域速率限制器實例
rate_limiter = RateLimiter()


def rate_limit(requests: int = 60, window: int = 60, identifier_func: Optional[callable] = None):
    """
    速率限制裝飾器
    
    Args:
        requests: 時間窗口內允許的請求數
        window: 時間窗口（秒）
        identifier_func: 自定義識別符函數
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 獲取識別符
            if identifier_func:
                identifier = identifier_func()
            else:
                identifier = rate_limiter.get_identifier()
            
            # 檢查速率限制
            allowed, info = rate_limiter.is_allowed(identifier, requests, window)
            
            # 設置響應頭
            g.rate_limit_headers = {
                'X-RateLimit-Limit': str(info['limit']),
                'X-RateLimit-Remaining': str(info['remaining']),
                'X-RateLimit-Reset': str(info['reset'])
            }
            
            if not allowed:
                # 超過速率限制
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': f'請稍後再試。您已超過速率限制 ({requests} 請求/{window} 秒)',
                    'retry_after': info['retry_after']
                })
                response.status_code = 429
                
                # 添加速率限制頭
                for header, value in g.rate_limit_headers.items():
                    response.headers[header] = value
                
                if info.get('retry_after'):
                    response.headers['Retry-After'] = str(info['retry_after'])
                
                return response
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator


def add_rate_limit_headers(response):
    """添加速率限制頭到響應"""
    if hasattr(g, 'rate_limit_headers'):
        for header, value in g.rate_limit_headers.items():
            response.headers[header] = value
    return response


# 不同端點的預設速率限制
class RateLimits:
    """預定義的速率限制設定"""
    
    # Webhook 端點：每分鐘 120 次（LINE 平台限制）
    WEBHOOK = {"requests": 120, "window": 60}
    
    # 廣播端點：每小時 5 次
    BROADCAST = {"requests": 5, "window": 3600}
    
    # API 查詢端點：每分鐘 30 次
    API_QUERY = {"requests": 30, "window": 60}
    
    # 管理端點：每分鐘 10 次
    ADMIN = {"requests": 10, "window": 60}
    
    # 健康檢查：每分鐘 60 次
    HEALTH = {"requests": 60, "window": 60}


# 使用範例
if __name__ == "__main__":
    # 測試速率限制器
    limiter = RateLimiter()
    
    test_id = "test_user_123"
    limit = 5
    window = 10
    
    print(f"測試速率限制：{limit} 請求/{window} 秒")
    
    for i in range(10):
        allowed, info = limiter.is_allowed(test_id, limit, window)
        print(f"請求 {i+1}: {'允許' if allowed else '拒絕'} - 剩餘: {info['remaining']}")
        time.sleep(1)