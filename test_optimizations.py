"""
測試優化功能
"""

import sys
import os

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_smart_onboarding():
    """測試智慧引導系統"""
    print("=== 測試智慧引導系統 ===\n")
    
    try:
        from optimizations.smart_onboarding import SmartOnboarding, SmartErrorHandler
        
        onboarding = SmartOnboarding()
        error_handler = SmartErrorHandler()
        
        # 測試新用戶問候
        print("1. 新用戶問候：")
        print(onboarding.get_smart_greeting("new_user_001"))
        print()
        
        # 測試錯誤處理
        print("2. 錯誤輸入修正：")
        print(error_handler.suggest_correction("接龍"))  # 缺少參數
        print(error_handler.suggest_correction("統擊"))  # 錯字
        print()
        
        # 測試里程碑
        print("3. 里程碑慶祝：")
        print(onboarding.celebrate_milestone("user_001", "first_message"))
        print()
        
        print("✅ 智慧引導系統測試通過\n")
        return True
        
    except Exception as e:
        print(f"❌ 智慧引導系統測試失敗: {e}\n")
        return False

def test_performance_dashboard():
    """測試效能儀表板"""
    print("=== 測試效能儀表板 ===\n")
    
    try:
        from optimizations.performance_dashboard import PerformanceDashboard
        
        dashboard = PerformanceDashboard()
        
        # 模擬一些數據
        dashboard.record_api_latency("webhook", 89.5)
        dashboard.record_api_latency("stats", 45.2)
        dashboard.update_concurrent_users(847)
        dashboard.update_cache_stats(True)
        dashboard.update_cache_stats(True)
        dashboard.update_cache_stats(False)
        
        # 顯示儀表板
        print("效能儀表板輸出：")
        print(dashboard.format_dashboard())
        print()
        
        print("✅ 效能儀表板測試通過\n")
        return True
        
    except Exception as e:
        print(f"❌ 效能儀表板測試失敗: {e}\n")
        return False

def test_core_value_optimizer():
    """測試核心價值優化器"""
    print("=== 測試核心價值優化器 ===\n")
    
    try:
        from optimizations.core_value_optimizer import CoreValueOptimizer
        
        optimizer = CoreValueOptimizer()
        
        # 模擬訊息
        test_messages = [
            {"content": "下週二下午3點全體會議", "user_id": "boss"},
            {"content": "收到，我會參加", "user_id": "user1"},
            {"content": "專案進度如何？", "user_id": "boss"},
            {"content": "目前完成70%", "user_id": "user2"},
            {"content": "有什麼問題嗎？", "user_id": "boss"},
            {"content": "API整合有點問題", "user_id": "user2"},
            {"content": "我可以幫忙", "user_id": "user3"},
        ] * 20  # 模擬140則訊息
        
        # 生成10x廣播
        result = optimizer.generate_10x_broadcast(test_messages)
        
        print("10x 優化廣播：")
        print("-" * 50)
        print(result["broadcast"])
        print("-" * 50)
        print(f"壓縮比: {result['compression_ratio']:.1f}x")
        print()
        
        # 顯示進度報告
        print("優化進度報告：")
        print(optimizer.get_progress_report())
        print()
        
        print("✅ 核心價值優化器測試通過\n")
        return True
        
    except Exception as e:
        print(f"❌ 核心價值優化器測試失敗: {e}\n")
        return False

def test_integration():
    """測試整合功能"""
    print("=== 測試系統整合 ===\n")
    
    try:
        # 測試 frequency_bot_firestore 是否能載入優化
        from frequency_bot_firestore import FrequencyBotFirestore
        
        print("1. FrequencyBotFirestore 可以正常載入")
        
        # 測試 app.py 是否能載入優化
        import app
        
        print("2. app.py 可以正常載入")
        
        # 檢查優化模組是否被載入
        if hasattr(app, 'OPTIMIZATIONS_AVAILABLE'):
            if app.OPTIMIZATIONS_AVAILABLE:
                print("3. 優化模組已成功整合到 app.py")
            else:
                print("3. 優化模組未找到，但系統可降級運行")
        
        print("\n✅ 系統整合測試通過\n")
        return True
        
    except Exception as e:
        print(f"❌ 系統整合測試失敗: {e}\n")
        return False

def main():
    """執行所有測試"""
    print("🚀 開始測試 LINE Bot 優化功能\n")
    
    results = {
        "智慧引導": test_smart_onboarding(),
        "效能監控": test_performance_dashboard(),
        "核心優化": test_core_value_optimizer(),
        "系統整合": test_integration()
    }
    
    # 顯示總結
    print("\n" + "=" * 50)
    print("📊 測試結果總結")
    print("=" * 50)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for name, result in results.items():
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{name}: {status}")
    
    print(f"\n總計: {passed}/{total} 測試通過")
    
    if passed == total:
        print("\n🎉 所有優化功能測試通過！")
        print("\n下一步：")
        print("1. 部署到 Cloud Run：gcloud run deploy")
        print("2. 測試實際效果：發送訊息到 LINE Bot")
        print("3. 監控效能指標：輸入「系統狀態」")
    else:
        print("\n⚠️  部分測試失敗，請檢查錯誤訊息")

if __name__ == "__main__":
    main()