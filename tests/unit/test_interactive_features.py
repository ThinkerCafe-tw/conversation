import unittest
from unittest.mock import patch, MagicMock

# Assuming app.py is in the root directory and QUICK_MENUS is defined there
# Adjust the import path as necessary if app.py is located elsewhere
from app import app, QUICK_MENUS, handle_text_message
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import ReplyMessageRequest, TextMessage

class TestInteractiveFeatures(unittest.TestCase):

    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()
        # It's good practice to have a test client, though for handle_text_message directly,
        # we might not use it if we call the function directly.
        self.client = app.test_client()

    def tearDown(self):
        self.app_context.pop()

    def _create_mock_event(self, message_text, user_id="test_user"):
        mock_event = MagicMock(spec=MessageEvent)
        mock_event.reply_token = "test_reply_token"
        mock_event.source.user_id = user_id
        mock_event.message = MagicMock(spec=TextMessageContent)
        mock_event.message.text = message_text
        return mock_event

    @patch('app.line_bot_api.reply_message')
    def test_quick_menu_play(self, mock_reply_message):
        mock_event = self._create_mock_event("玩")

        # Directly call the handler function from app.py
        # This requires app.py to be structured to allow this,
        # or refactoring handle_text_message if it's too coupled.
        # For this example, assume handle_text_message can be called.
        # If CommunityFeatures or other dependencies are an issue, they may need mocking too.
        with patch('app.community', MagicMock()): # Mock community if it's accessed early
            handle_text_message(mock_event)

        self.assertTrue(mock_reply_message.called)
        args, kwargs = mock_reply_message.call_args
        reply_request = args[0]
        self.assertIsInstance(reply_request, ReplyMessageRequest)

        sent_message = reply_request.messages[0]
        self.assertIsInstance(sent_message, TextMessage)

        menu_data = QUICK_MENUS["玩"]
        expected_items = []
        for option_text, option_command in menu_data["options"]:
            expected_items.append(f"{option_text}\n→ 輸入「{option_command}」")
        expected_reply = f"{menu_data['title']}\n━━━━━━━━━━━━━━\n\n"
        expected_reply += "\n\n".join(expected_items)
        expected_reply += f"\n\n{menu_data['footer']}"

        self.assertEqual(sent_message.text, expected_reply)

    @patch('app.line_bot_api.reply_message')
    def test_quick_menu_see(self, mock_reply_message):
        mock_event = self._create_mock_event("看")
        with patch('app.community', MagicMock()):
            handle_text_message(mock_event)

        self.assertTrue(mock_reply_message.called)
        args, kwargs = mock_reply_message.call_args
        reply_request = args[0]
        sent_message = reply_request.messages[0]

        menu_data = QUICK_MENUS["看"]
        expected_items = []
        for option_text, option_command in menu_data["options"]:
            expected_items.append(f"{option_text}\n→ 輸入「{option_command}」")
        expected_reply = f"{menu_data['title']}\n━━━━━━━━━━━━━━\n\n"
        expected_reply += "\n\n".join(expected_items)
        expected_reply += f"\n\n{menu_data['footer']}"

        self.assertEqual(sent_message.text, expected_reply)

    @patch('app.line_bot_api.reply_message')
    def test_quick_menu_help(self, mock_reply_message): # "救"
        mock_event = self._create_mock_event("救")
        with patch('app.community', MagicMock()):
            handle_text_message(mock_event)

        self.assertTrue(mock_reply_message.called)
        args, kwargs = mock_reply_message.call_args
        reply_request = args[0]
        sent_message = reply_request.messages[0]

        menu_data = QUICK_MENUS["救"]
        expected_items = []
        for option_text, option_command in menu_data["options"]:
            expected_items.append(f"{option_text}\n→ 輸入「{option_command}」")
        expected_reply = f"{menu_data['title']}\n━━━━━━━━━━━━━━\n\n"
        expected_reply += "\n\n".join(expected_items)
        expected_reply += f"\n\n{menu_data['footer']}"

        self.assertEqual(sent_message.text, expected_reply)

    # --- Joke Feature Tests (app.py handlers) ---
    @patch('app.knowledge_graph') # Mock knowledge_graph for interaction logging
    @patch('app.community')
    @patch('app.line_bot_api.reply_message')
    def test_submit_joke_success(self, mock_reply_message, mock_community_features, mock_kg):
        user_id = "test_user_submit_joke"
        mock_event = self._create_mock_event("笑話 這是一個超好笑的笑話", user_id=user_id)

        mock_kg.connected = True # Assume KG is connected
        # Configure the mock for community.add_joke
        mock_community_features.add_joke.return_value = {
            'success': True,
            'message': '😄 你的笑話已成功收錄！感謝分享！'
        }

        handle_text_message(mock_event)

        mock_community_features.add_joke.assert_called_once_with(
            user_id,
            "這是一個超好笑的笑話"
        )
        self.assertTrue(mock_reply_message.called)
        args, _ = mock_reply_message.call_args
        reply_request = args[0]
        self.assertEqual(reply_request.messages[0].text, '😄 你的笑話已成功收錄！感謝分享！')
        mock_kg.log_user_feature_interaction.assert_called_once_with(user_id, "笑話", "submitted_joke")

    @patch('app.knowledge_graph')
    @patch('app.community')
    @patch('app.line_bot_api.reply_message')
    def test_submit_joke_empty(self, mock_reply_message, mock_community_features, mock_kg):
        mock_event = self._create_mock_event("笑話 ") # Empty joke

        handle_text_message(mock_event)

        mock_community_features.add_joke.assert_not_called()
        mock_kg.log_user_feature_interaction.assert_not_called() # KG log should not be called
        self.assertTrue(mock_reply_message.called)
        args, _ = mock_reply_message.call_args
        reply_request = args[0]
        self.assertEqual(reply_request.messages[0].text, "🤔 笑話內容不能為空喔！請輸入「笑話 [你的笑話內容]」")

    @patch('app.knowledge_graph')
    @patch('app.community')
    @patch('app.line_bot_api.reply_message')
    def test_get_joke_found(self, mock_reply_message, mock_community_features, mock_kg):
        user_id = "test_user_get_joke"
        mock_event = self._create_mock_event("說個笑話", user_id=user_id)

        mock_kg.connected = True
        mock_community_features.get_random_joke.return_value = {
            'success': True,
            'joke': {'id': 'j1', 'text': '有個程式設計師...', 'user': '用戶1234'}, # Ensure 'joke' key is present
            'message': "🗣️ 用戶1234 分享的笑話：\n\n有個程式設計師..."
        }

        handle_text_message(mock_event)

        mock_community_features.get_random_joke.assert_called_once_with(user_id_for_cache=user_id)
        mock_kg.log_user_feature_interaction.assert_called_once_with(user_id, "笑話", "viewed_joke")
        self.assertTrue(mock_reply_message.called)
        args, _ = mock_reply_message.call_args
        reply_request = args[0]
        self.assertEqual(reply_request.messages[0].text, "🗣️ 用戶1234 分享的笑話：\n\n有個程式設計師...")

    @patch('app.knowledge_graph')
    @patch('app.community')
    @patch('app.line_bot_api.reply_message')
    def test_get_joke_not_found(self, mock_reply_message, mock_community_features, mock_kg):
        user_id = "test_user_get_joke_nf"
        mock_event = self._create_mock_event("聽笑話", user_id=user_id)

        mock_community_features.get_random_joke.return_value = {
            'success': False, # Important: success is false
            'message': '目前還沒有笑話，快來輸入「笑話 [內容]」分享一個吧！'
        }

        handle_text_message(mock_event)

        mock_community_features.get_random_joke.assert_called_once_with(user_id_for_cache=user_id)
        mock_kg.log_user_feature_interaction.assert_not_called() # Not called if no joke found
        self.assertTrue(mock_reply_message.called)
        args, _ = mock_reply_message.call_args
        reply_request = args[0]
        self.assertEqual(reply_request.messages[0].text, '目前還沒有笑話，快來輸入「笑話 [內容]」分享一個吧！')

    @patch('app.community', None) # Simulate community features not available
    @patch('app.line_bot_api.reply_message')
    def test_submit_joke_community_unavailable(self, mock_reply_message):
        mock_event = self._create_mock_event("笑話 測試")
        handle_text_message(mock_event)
        self.assertTrue(mock_reply_message.called)
        args, _ = mock_reply_message.call_args
        self.assertEqual(args[0].messages[0].text, "❌ 社群功能（包含笑話）暫時無法使用")

    @patch('app.knowledge_graph')
    @patch('app.community', None)
    @patch('app.line_bot_api.reply_message')
    def test_get_joke_community_unavailable(self, mock_reply_message, mock_kg):
        mock_event = self._create_mock_event("說個笑話")
        handle_text_message(mock_event)
        self.assertTrue(mock_reply_message.called)
        args, _ = mock_reply_message.call_args
        self.assertEqual(args[0].messages[0].text, "❌ 社群功能（包含笑話）暫時無法使用")
        mock_kg.log_user_feature_interaction.assert_not_called()

    @patch('app.knowledge_graph')
    @patch('app.community')
    @patch('app.line_bot_api.reply_message')
    def test_like_joke_success(self, mock_reply_message, mock_community_features, mock_kg):
        user_id = "test_user_like_joke"
        mock_event = self._create_mock_event("讚", user_id=user_id)

        mock_kg.connected = True
        mock_community_features.like_last_joke.return_value = {
            'success': True,
            'message': '👍 已讚！感謝您的評價。'
        }
        handle_text_message(mock_event)

        mock_community_features.like_last_joke.assert_called_once_with(user_id)
        self.assertTrue(mock_reply_message.called)
        args, _ = mock_reply_message.call_args
        self.assertEqual(args[0].messages[0].text, '👍 已讚！感謝您的評價。')
        mock_kg.log_user_feature_interaction.assert_called_once_with(user_id, "笑話", "liked_joke")

    # --- Tests for other feature logging ---
    @patch('app.knowledge_graph')
    @patch('app.community')
    @patch('app.line_bot_api.reply_message')
    def test_start_word_chain_logs_interaction(self, mock_reply_message, mock_community_features, mock_kg):
        user_id = "user_word_chain"
        mock_event = self._create_mock_event("接龍 開始詞", user_id=user_id)

        mock_kg.connected = True
        mock_community_features.start_word_chain.return_value = {
            'success': True,
            'message': '🔗 接龍遊戲已開始！請接「詞」' # Example success message
        }
        handle_text_message(mock_event)
        mock_community_features.start_word_chain.assert_called_once_with("開始詞", user_id)
        mock_kg.log_user_feature_interaction.assert_called_once_with(user_id, "接龍", "started")

    @patch('app.knowledge_graph')
    @patch('app.community')
    @patch('app.line_bot_api.reply_message')
    def test_create_vote_logs_interaction(self, mock_reply_message, mock_community_features, mock_kg):
        user_id = "user_create_vote"
        mock_event = self._create_mock_event("投票 主題/選項A/選項B", user_id=user_id)

        mock_kg.connected = True
        mock_community_features.create_vote.return_value = {
            'success': True,
            'message': '📊 投票開始！'
        }
        handle_text_message(mock_event)
        mock_community_features.create_vote.assert_called_once_with("主題", ["選項A", "選項B"], user_id)
        mock_kg.log_user_feature_interaction.assert_called_once_with(user_id, "投票", "created_poll")

    @patch('app.knowledge_graph')
    @patch('app.community')
    @patch('app.line_bot_api.reply_message')
    def test_cast_vote_logs_interaction(self, mock_reply_message, mock_community_features, mock_kg):
        user_id = "user_cast_vote"
        mock_event = self._create_mock_event("1", user_id=user_id) # User votes for option 1

        mock_kg.connected = True
        mock_community_features.cast_vote.return_value = {
            'success': True,
            'message': '✅ 投票成功！'
        }
        handle_text_message(mock_event)
        mock_community_features.cast_vote.assert_called_once_with(1, user_id)
        mock_kg.log_user_feature_interaction.assert_called_once_with(user_id, "投票", "cast_vote")

    @patch('app.knowledge_graph')
    @patch('app.community')
    @patch('app.line_bot_api.reply_message')
    def test_add_shelter_logs_interaction(self, mock_reply_message, mock_community_features, mock_kg):
        user_id = "user_add_shelter"
        mock_event = self._create_mock_event("防空 地點A 型態B 100人", user_id=user_id)

        mock_kg.connected = True
        mock_community_features.add_shelter_info.return_value = {
            'success': True,
            'message': '🏠 避難資訊已記錄'
        }
        handle_text_message(mock_event)
        mock_community_features.add_shelter_info.assert_called_once_with("地點A", "型態B", 100, user_id)
        mock_kg.log_user_feature_interaction.assert_called_once_with(user_id, "防災資訊", "added_shelter")

    # --- Web Search Feature Tests (app.py handlers) ---
    @patch('app.knowledge_graph')
    @patch('app.search_service') # Mock the search_service instance in app.py
    @patch('app.line_bot_api.reply_message')
    def test_web_search_success_with_results(self, mock_reply_message, mock_search_service_instance, mock_kg):
        user_id = "user_search_success"
        query = "python programming"
        mock_event = self._create_mock_event(f"搜尋 {query}", user_id=user_id)

        mock_kg.connected = True
        mock_search_service_instance.perform_search.return_value = {
            "success": True,
            "query": query,
            "results": [
                {"title": "Python for Beginners", "link": "example.com/python", "snippet": "Learn Python programming from scratch..."},
                {"title": "Advanced Python", "link": "example.com/advanced", "snippet": "Deep dive into Python features..."},
            ],
            "total_results_available": "12300"
        }

        handle_text_message(mock_event)

        mock_search_service_instance.perform_search.assert_called_once_with(query, num_results=3)
        mock_kg.log_user_feature_interaction.assert_called_once_with(user_id, "網路搜尋", "performed_search")

        self.assertTrue(mock_reply_message.called)
        args, _ = mock_reply_message.call_args
        reply_text = args[0].messages[0].text

        self.assertIn(f"🔍 「{query}」的網路搜尋結果 (前2筆)：", reply_text)
        self.assertIn("1. Python for Beginners", reply_text)
        self.assertIn("📝 Learn Python programming from scratch...", reply_text)
        self.assertIn("🔗 example.com/python", reply_text)
        self.assertIn("2. Advanced Python", reply_text)

    @patch('app.knowledge_graph')
    @patch('app.search_service')
    @patch('app.line_bot_api.reply_message')
    def test_web_search_success_no_results(self, mock_reply_message, mock_search_service_instance, mock_kg):
        user_id = "user_search_no_results"
        query = "unfindable query string"
        mock_event = self._create_mock_event(f"查一下 {query}", user_id=user_id)

        mock_kg.connected = True
        mock_search_service_instance.perform_search.return_value = {
            "success": True, "query": query, "results": [], "total_results_available": "0"
        }
        handle_text_message(mock_event)
        mock_search_service_instance.perform_search.assert_called_once_with(query, num_results=3)
        mock_kg.log_user_feature_interaction.assert_called_once_with(user_id, "網路搜尋", "performed_search")
        mock_reply_message.assert_called_once()
        self.assertEqual(mock_reply_message.call_args[0][0].messages[0].text, f"抱歉，找不到與「{query}」相關的結果。")

    @patch('app.knowledge_graph')
    @patch('app.search_service')
    @patch('app.line_bot_api.reply_message')
    def test_web_search_service_error(self, mock_reply_message, mock_search_service_instance, mock_kg):
        user_id = "user_search_error"
        query = "trigger error"
        mock_event = self._create_mock_event(f"search {query}", user_id=user_id)

        mock_kg.connected = True # KG logging should still be attempted
        error_message_from_service = "Test API Error from Service"
        mock_search_service_instance.perform_search.return_value = {
            "success": False, "error": "API Error", "message": error_message_from_service
        }
        handle_text_message(mock_event)
        mock_search_service_instance.perform_search.assert_called_once_with(query, num_results=3)
        mock_kg.log_user_feature_interaction.assert_called_once_with(user_id, "網路搜尋", "performed_search")
        mock_reply_message.assert_called_once()
        self.assertEqual(mock_reply_message.call_args[0][0].messages[0].text, error_message_from_service)

    @patch('app.search_service')
    @patch('app.line_bot_api.reply_message')
    def test_web_search_empty_query(self, mock_reply_message, mock_search_service_instance):
        mock_event = self._create_mock_event("搜尋 ") # Empty query
        handle_text_message(mock_event)
        mock_search_service_instance.perform_search.assert_not_called()
        mock_reply_message.assert_called_once()
        self.assertEqual(mock_reply_message.call_args[0][0].messages[0].text, "請輸入您想搜尋的關鍵字。\n例如：「搜尋 今天天氣如何」")

    @patch('app.line_bot_api.reply_message')
    def test_web_search_service_unavailable(self, mock_reply_message):
        with patch('app.search_service', None): # Simulate search_service is None
            mock_event = self._create_mock_event("搜尋 unavailable test")
            handle_text_message(mock_event)
            mock_reply_message.assert_called_once()
            self.assertEqual(mock_reply_message.call_args[0][0].messages[0].text, "抱歉，網路搜尋功能目前暫時無法使用，請稍後再試。")


if __name__ == '__main__':
    unittest.main()
