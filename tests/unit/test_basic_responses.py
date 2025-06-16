"""
單元測試：基本回應功能
確保核心功能不會壞掉
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# 加入專案路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class TestBasicResponses:
    """測試基本回應功能"""
    
    def test_new_user_greeting(self):
        """測試新用戶說你好必須有回應"""
        from app import handle_text_message
        
        # 模擬事件
        event = Mock()
        event.message.text = "你好"
        event.source.user_id = "new_test_user"
        event.reply_token = "test_token"
        
        # 模擬依賴
        with patch('app.frequency_bot') as mock_bot:
            with patch('app.line_bot_api') as mock_api:
                # 設定模擬回傳值
                mock_bot.get_frequency_stats.return_value = {
                    'contributors': {'top_contributors': []},
                    'message_count': 0
                }
                mock_bot.add_to_broadcast.return_value = 1
                
                # 執行測試
                handle_text_message(event)
                
                # 驗證有回覆訊息
                mock_api.reply_message.assert_called_once()
                
                # 檢查回覆內容
                call_args = mock_api.reply_message.call_args[0][0]
                reply_text = call_args.messages[0].text
                
                # 必須包含歡迎詞
                assert "歡迎" in reply_text
                assert "頻率共振" in reply_text
                assert "輸入「玩」" in reply_text
    
    def test_natural_language_understanding(self):
        """測試自然語言理解：我想玩遊戲"""
        from app import handle_text_message
        
        event = Mock()
        event.message.text = "我想玩遊戲"
        event.source.user_id = "test_user"
        event.reply_token = "test_token"
        
        with patch('app.line_bot_api') as mock_api:
            handle_text_message(event)
            
            # 應該回覆遊戲選單
            mock_api.reply_message.assert_called_once()
            call_args = mock_api.reply_message.call_args[0][0]
            reply_text = call_args.messages[0].text
            
            assert "選擇遊戲" in reply_text
            assert "文字接龍" in reply_text
            assert "發起投票" in reply_text
    
    def test_statistics_command(self):
        """測試統計指令"""
        from app import handle_text_message
        
        event = Mock()
        event.message.text = "統計"
        event.source.user_id = "test_user"
        event.reply_token = "test_token"
        
        with patch('app.frequency_bot') as mock_bot:
            with patch('app.line_bot_api') as mock_api:
                # 模擬統計資料
                mock_bot.get_frequency_stats.return_value = {
                    'message_count': 42,
                    'progress_percent': 4.2,
                    'messages_needed': 958,
                    'time_until_broadcast': {'minutes': 45, 'seconds': 30},
                    'top_frequencies': [('測試', 5), ('你好', 3)],
                    'contributors': {
                        'total_users': 10,
                        'top_contributors': [('user1', 10), ('user2', 8)]
                    }
                }
                
                handle_text_message(event)
                
                # 檢查回覆
                mock_api.reply_message.assert_called_once()
                call_args = mock_api.reply_message.call_args[0][0]
                reply_text = call_args.messages[0].text
                
                assert "即時頻率統計" in reply_text
                assert "42/1000" in reply_text
                assert "4.2%" in reply_text
    
    def test_error_format_suggestion(self):
        """測試錯誤格式提示"""
        from app import handle_text_message
        
        event = Mock()
        event.message.text = "接龍"  # 缺少參數
        event.source.user_id = "test_user"
        event.reply_token = "test_token"
        
        with patch('app.smart_error_handler') as mock_handler:
            with patch('app.line_bot_api') as mock_api:
                # 模擬錯誤處理器
                mock_handler.suggest_correction.return_value = "💡 接龍格式：接龍 [詞語]\n例如：接龍 蘋果"
                
                handle_text_message(event)
                
                # 應該顯示格式提示
                mock_api.reply_message.assert_called()
                call_args = mock_api.reply_message.call_args[0][0]
                reply_text = call_args.messages[0].text
                
                assert "接龍格式" in reply_text
                assert "例如：接龍 蘋果" in reply_text
    
    def test_general_message_recording(self):
        """測試一般訊息會被記錄"""
        from app import handle_text_message
        
        event = Mock()
        event.message.text = "今天天氣真好"
        event.source.user_id = "test_user"
        event.reply_token = "test_token"
        
        with patch('app.frequency_bot') as mock_bot:
            with patch('app.line_bot_api') as mock_api:
                # 模擬已有10則訊息
                mock_bot.get_frequency_stats.return_value = {
                    'contributors': {'top_contributors': [('test_user', 10)]}
                }
                mock_bot.add_to_broadcast.return_value = 11
                
                handle_text_message(event)
                
                # 確認訊息被加入廣播池
                mock_bot.add_to_broadcast.assert_called_with("今天天氣真好", "test_user")
                
                # 應該有回饋
                mock_api.reply_message.assert_called_once()
                call_args = mock_api.reply_message.call_args[0][0]
                reply_text = call_args.messages[0].text
                
                # 應該顯示訊息計數
                assert "11" in reply_text or "第11則" in reply_text


class TestCriticalPaths:
    """測試關鍵路徑"""
    
    @pytest.mark.parametrize("greeting", ["你好", "嗨", "哈囉", "安安", "hello", "hi"])
    def test_all_greeting_variations(self, greeting):
        """測試所有問候語變化"""
        from app import handle_text_message
        
        event = Mock()
        event.message.text = greeting
        event.source.user_id = f"test_user_{greeting}"
        event.reply_token = "test_token"
        
        with patch('app.frequency_bot') as mock_bot:
            with patch('app.line_bot_api') as mock_api:
                mock_bot.get_frequency_stats.return_value = {
                    'contributors': {'top_contributors': []}
                }
                mock_bot.add_to_broadcast.return_value = 1
                
                handle_text_message(event)
                
                # 新用戶應該看到歡迎訊息
                mock_api.reply_message.assert_called_once()
                call_args = mock_api.reply_message.call_args[0][0]
                reply_text = call_args.messages[0].text
                
                assert "歡迎" in reply_text
                assert "頻率共振" in reply_text
    
    def test_help_command(self):
        """測試幫助指令"""
        from app import handle_text_message
        
        event = Mock()
        event.message.text = "幫助"
        event.source.user_id = "test_user"
        event.reply_token = "test_token"
        
        with patch('app.line_bot_api') as mock_api:
            handle_text_message(event)
            
            # 應該顯示完整說明
            mock_api.reply_message.assert_called_once()
            call_args = mock_api.reply_message.call_args[0][0]
            reply_text = call_args.messages[0].text
            
            assert "使用說明" in reply_text
            assert "資訊查詢" in reply_text
            assert "互動功能" in reply_text
            assert "防災互助" in reply_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])