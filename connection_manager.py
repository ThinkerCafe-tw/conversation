"""
連線管理器 - 提供穩定的連線重試機制
處理 Neo4j 和 Redis 的連線穩定性問題
"""

import time
import logging
from typing import Optional, Callable, Any, Dict
from functools import wraps
import redis
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, SessionExpired

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """斷路器模式實作 - 防止連續失敗"""
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """執行函數並處理斷路器邏輯"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info(f"斷路器進入半開狀態: {func.__name__}")
            else:
                raise Exception(f"斷路器開啟中，服務暫時無法使用: {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info(f"斷路器恢復正常: {func.__name__}")
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(f"斷路器開啟: {func.__name__} - 連續失敗 {self.failure_count} 次")
            
            raise e


class ConnectionPool:
    """連線池基礎類別"""
    def __init__(self, max_connections: int = 10, connection_timeout: int = 30):
        self.max_connections = max_connections
        self.connection_timeout = connection_timeout
        self.connections = []
        self.available_connections = []
        
    def get_connection(self):
        """獲取可用連線"""
        raise NotImplementedError
        
    def return_connection(self, conn):
        """歸還連線"""
        if conn and conn not in self.available_connections:
            self.available_connections.append(conn)
            
    def close_all(self):
        """關閉所有連線"""
        raise NotImplementedError


class Neo4jConnectionPool(ConnectionPool):
    """Neo4j 連線池實作"""
    def __init__(self, uri: str, auth: tuple, **kwargs):
        super().__init__(**kwargs)
        self.uri = uri
        self.auth = auth
        self.driver = None
        self.circuit_breaker = CircuitBreaker()
        
    def _create_driver(self):
        """建立 Neo4j 驅動程式"""
        if not self.driver:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=self.auth,
                max_connection_pool_size=self.max_connections,
                connection_timeout=self.connection_timeout,
                max_transaction_retry_time=30.0
            )
            logger.info("Neo4j 驅動程式已建立")
            
    def get_connection(self):
        """獲取 Neo4j 工作階段"""
        def _get_session():
            self._create_driver()
            return self.driver.session()
            
        return self.circuit_breaker.call(_get_session)
        
    def verify_connectivity(self) -> bool:
        """驗證連線狀態"""
        try:
            self._create_driver()
            self.driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f"Neo4j 連線驗證失敗: {e}")
            return False
            
    def close_all(self):
        """關閉驅動程式"""
        if self.driver:
            self.driver.close()
            self.driver = None


class RedisConnectionPool(ConnectionPool):
    """Redis 連線池實作"""
    def __init__(self, host: str, port: int, password: str, username: str = None, **kwargs):
        super().__init__(**kwargs)
        self.host = host
        self.port = port
        self.password = password
        self.username = username
        self.pool = None
        self.circuit_breaker = CircuitBreaker()
        
    def _create_pool(self):
        """建立 Redis 連線池"""
        if not self.pool:
            self.pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                password=self.password,
                username=self.username,
                decode_responses=True,
                max_connections=self.max_connections,
                socket_connect_timeout=self.connection_timeout,
                socket_timeout=self.connection_timeout,
                retry_on_timeout=True,
                health_check_interval=30
            )
            logger.info("Redis 連線池已建立")
            
    def get_connection(self) -> redis.Redis:
        """獲取 Redis 連線"""
        def _get_redis():
            self._create_pool()
            return redis.Redis(connection_pool=self.pool)
            
        return self.circuit_breaker.call(_get_redis)
        
    def verify_connectivity(self) -> bool:
        """驗證連線狀態"""
        try:
            conn = self.get_connection()
            conn.ping()
            return True
        except Exception as e:
            logger.error(f"Redis 連線驗證失敗: {e}")
            return False
            
    def close_all(self):
        """關閉連線池"""
        if self.pool:
            self.pool.disconnect()
            self.pool = None


def retry_on_connection_error(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """連線錯誤重試裝飾器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except (ServiceUnavailable, SessionExpired, redis.ConnectionError) as e:
                    retries += 1
                    if retries >= max_retries:
                        logger.error(f"連線重試已達上限 ({max_retries} 次): {func.__name__}")
                        raise
                    
                    logger.warning(f"連線錯誤，{current_delay} 秒後重試 (第 {retries} 次): {e}")
                    time.sleep(current_delay)
                    current_delay *= backoff
                    
            return None
        return wrapper
    return decorator


class ConnectionManager:
    """統一的連線管理器"""
    def __init__(self):
        self.neo4j_pool: Optional[Neo4jConnectionPool] = None
        self.redis_pool: Optional[RedisConnectionPool] = None
        self._health_check_interval = 60  # 秒
        self._last_health_check = 0
        
    def setup_neo4j(self, uri: str, user: str, password: str) -> Neo4jConnectionPool:
        """設定 Neo4j 連線池"""
        self.neo4j_pool = Neo4jConnectionPool(
            uri=uri,
            auth=(user, password)
        )
        return self.neo4j_pool
        
    def setup_redis(self, host: str, port: int, password: str, username: str = None) -> RedisConnectionPool:
        """設定 Redis 連線池"""
        self.redis_pool = RedisConnectionPool(
            host=host,
            port=port,
            password=password,
            username=username
        )
        return self.redis_pool
        
    def health_check(self) -> Dict[str, bool]:
        """執行健康檢查"""
        current_time = time.time()
        if current_time - self._last_health_check < self._health_check_interval:
            return {}
            
        self._last_health_check = current_time
        status = {}
        
        if self.neo4j_pool:
            status['neo4j'] = self.neo4j_pool.verify_connectivity()
            
        if self.redis_pool:
            status['redis'] = self.redis_pool.verify_connectivity()
            
        if any(not healthy for healthy in status.values()):
            logger.warning(f"健康檢查結果: {status}")
        
        return status
        
    def close_all(self):
        """關閉所有連線"""
        if self.neo4j_pool:
            self.neo4j_pool.close_all()
            
        if self.redis_pool:
            self.redis_pool.close_all()


# 全域連線管理器實例
connection_manager = ConnectionManager()


# 使用範例
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # 設定連線
    manager = ConnectionManager()
    
    # Neo4j
    if os.getenv('NEO4J_URI'):
        neo4j_pool = manager.setup_neo4j(
            uri=os.getenv('NEO4J_URI'),
            user=os.getenv('NEO4J_USER'),
            password=os.getenv('NEO4J_PASSWORD')
        )
        
        # 使用連線
        @retry_on_connection_error()
        def test_neo4j():
            with neo4j_pool.get_connection() as session:
                result = session.run("RETURN 1 as num")
                return result.single()['num']
                
        print(f"Neo4j 測試結果: {test_neo4j()}")
    
    # Redis
    if os.getenv('REDIS_HOST'):
        redis_pool = manager.setup_redis(
            host=os.getenv('REDIS_HOST'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            password=os.getenv('REDIS_PASSWORD'),
            username=os.getenv('REDIS_USERNAME')
        )
        
        # 使用連線
        @retry_on_connection_error()
        def test_redis():
            conn = redis_pool.get_connection()
            conn.set('test_key', 'test_value', ex=60)
            return conn.get('test_key')
            
        print(f"Redis 測試結果: {test_redis()}")
    
    # 健康檢查
    print(f"健康檢查: {manager.health_check()}")
    
    # 關閉連線
    manager.close_all()