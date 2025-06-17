"""
Response Caching Module - 減少重複計算和 API 呼叫
實現 LRU 快取機制以提升效能
"""

import time
import json
import hashlib
from typing import Any, Optional, Dict, Callable
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class ResponseCache:
    """回應快取實作 - 使用 Redis 作為後端"""
    
    def __init__(self, redis_client=None, default_ttl: int = 300):
        """
        初始化快取
        
        Args:
            redis_client: Redis 客戶端
            default_ttl: 預設快取時間（秒）
        """
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.cache_prefix = "cache:response:"
        self.stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0
        }
    
    def _generate_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """生成快取鍵值"""
        # 建立唯一識別符
        cache_data = {
            "func": func_name,
            "args": args,
            "kwargs": kwargs
        }
        # 使用 JSON 序列化並計算 hash
        cache_str = json.dumps(cache_data, sort_keys=True, default=str)
        cache_hash = hashlib.md5(cache_str.encode()).hexdigest()
        return f"{self.cache_prefix}{func_name}:{cache_hash}"
    
    def get(self, key: str) -> Optional[Any]:
        """從快取獲取資料"""
        if not self.redis:
            return None
            
        try:
            cached_data = self.redis.get(key)
            if cached_data:
                self.stats["hits"] += 1
                return json.loads(cached_data)
            self.stats["misses"] += 1
            return None
        except Exception as e:
            logger.error(f"快取讀取錯誤: {e}")
            self.stats["errors"] += 1
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """設定快取資料"""
        if not self.redis:
            return False
            
        try:
            ttl = ttl or self.default_ttl
            serialized = json.dumps(value, default=str, ensure_ascii=False)
            self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"快取寫入錯誤: {e}")
            self.stats["errors"] += 1
            return False
    
    def delete(self, pattern: str) -> int:
        """刪除符合模式的快取"""
        if not self.redis:
            return 0
            
        try:
            keys = self.redis.keys(f"{self.cache_prefix}{pattern}*")
            if keys:
                return self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"快取刪除錯誤: {e}")
            return 0
    
    def get_stats(self) -> Dict[str, int]:
        """獲取快取統計"""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            **self.stats,
            "total": total,
            "hit_rate": round(hit_rate, 2)
        }
    
    def cache(self, ttl: Optional[int] = None, key_prefix: Optional[str] = None):
        """快取裝飾器"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 生成快取鍵
                cache_key = self._generate_key(
                    f"{key_prefix or ''}{func.__name__}", 
                    args, 
                    kwargs
                )
                
                # 嘗試從快取獲取
                cached_result = self.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"快取命中: {func.__name__}")
                    return cached_result
                
                # 執行函數
                result = func(*args, **kwargs)
                
                # 存入快取
                self.set(cache_key, result, ttl)
                
                return result
            
            # 添加清除快取的方法
            wrapper.clear_cache = lambda: self.delete(f"{key_prefix or ''}{func.__name__}")
            
            return wrapper
        return decorator


class LocalMemoryCache:
    """本地記憶體快取 - 用於極高頻率的查詢"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 60):
        """
        初始化本地快取
        
        Args:
            max_size: 最大快取項目數
            default_ttl: 預設快取時間（秒）
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.access_times: Dict[str, float] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """獲取快取項目"""
        if key in self.cache:
            item = self.cache[key]
            if time.time() < item["expires_at"]:
                self.access_times[key] = time.time()
                return item["value"]
            else:
                # 過期，刪除
                del self.cache[key]
                if key in self.access_times:
                    del self.access_times[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """設定快取項目"""
        # 如果超過大小限制，移除最少使用的項目
        if len(self.cache) >= self.max_size:
            # LRU 淘汰策略
            lru_key = min(self.access_times, key=self.access_times.get)
            del self.cache[lru_key]
            del self.access_times[lru_key]
        
        ttl = ttl or self.default_ttl
        self.cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl
        }
        self.access_times[key] = time.time()
    
    def clear(self) -> None:
        """清空快取"""
        self.cache.clear()
        self.access_times.clear()


# 全域快取實例（需要在 app.py 中初始化）
response_cache: Optional[ResponseCache] = None
local_cache = LocalMemoryCache()


# 預定義的快取策略
class CacheStrategies:
    """常用的快取策略"""
    
    # 統計資料：5分鐘快取
    STATS = {"ttl": 300, "key_prefix": "stats:"}
    
    # 廣播內容：10分鐘快取
    BROADCAST = {"ttl": 600, "key_prefix": "broadcast:"}
    
    # API 結果：1分鐘快取
    API_RESULT = {"ttl": 60, "key_prefix": "api:"}
    
    # 用戶資料：30分鐘快取
    USER_DATA = {"ttl": 1800, "key_prefix": "user:"}
    
    # 搜尋結果：15分鐘快取
    SEARCH = {"ttl": 900, "key_prefix": "search:"}


# 使用範例
if __name__ == "__main__":
    # 測試本地快取
    cache = LocalMemoryCache(max_size=3)
    
    # 設定快取
    cache.set("key1", "value1", ttl=5)
    cache.set("key2", {"data": "value2"}, ttl=10)
    cache.set("key3", [1, 2, 3], ttl=15)
    
    # 獲取快取
    print(f"key1: {cache.get('key1')}")
    print(f"key2: {cache.get('key2')}")
    print(f"key3: {cache.get('key3')}")
    
    # 測試 LRU 淘汰
    cache.set("key4", "value4")  # 應該淘汰 key1
    print(f"\n加入 key4 後:")
    print(f"key1: {cache.get('key1')}")  # None
    print(f"key4: {cache.get('key4')}")  # value4
    
    # 測試過期
    print(f"\n等待 6 秒...")
    time.sleep(6)
    print(f"key1 (已過期): {cache.get('key1')}")
    
    # 清空快取
    cache.clear()
    print(f"\n清空後 key2: {cache.get('key2')}")