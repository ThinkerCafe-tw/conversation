"""測試 Redis 連接"""
import redis

# 直接使用您提供的連接資訊
r = redis.Redis(
    host='redis-13623.c302.asia-northeast1-1.gce.redns.redis-cloud.com',
    port=13623,
    decode_responses=True,
    username="default",
    password="n4QoRbGmakLGMmGpxH3Pwa7hyVXR5YEL",
)

try:
    # 測試連接
    r.ping()
    print("✅ Redis 連接成功!")
    
    # 測試寫入
    success = r.set('test_key', 'Hello from Frequency Bot!')
    print(f"寫入測試: {'成功' if success else '失敗'}")
    
    # 測試讀取
    result = r.get('test_key')
    print(f"讀取測試: {result}")
    
    # 測試社群功能的鍵
    r.set('word_chain:test', 'test_value', ex=60)
    print("文字接龍測試鍵設定成功")
    
    # 清理測試資料
    r.delete('test_key', 'word_chain:test')
    print("測試資料已清理")
    
except Exception as e:
    print(f"❌ Redis 連接失敗: {e}")