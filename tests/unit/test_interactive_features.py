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
    @patch('app.community') # Mock the entire community module/object used in app.py
    @patch('app.line_bot_api.reply_message')
    def test_submit_joke_success(self, mock_reply_message, mock_community_features):
        mock_event = self._create_mock_event("笑話 這是一個超好笑的笑話")

        # Configure the mock for community.add_joke
        mock_community_features.add_joke.return_value = {
            'success': True,
            'message': '😄 你的笑話已成功收錄！感謝分享！'
        }

        handle_text_message(mock_event) # user_id is part of mock_event

        mock_community_features.add_joke.assert_called_once_with(
            "test_user", # This should match the user_id in _create_mock_event
            "這是一個超好笑的笑話"
        )
        self.assertTrue(mock_reply_message.called)
        args, _ = mock_reply_message.call_args
        reply_request = args[0]
        self.assertEqual(reply_request.messages[0].text, '😄 你的笑話已成功收錄！感謝分享！')

    @patch('app.community')
    @patch('app.line_bot_api.reply_message')
    def test_submit_joke_empty(self, mock_reply_message, mock_community_features):
        mock_event = self._create_mock_event("笑話 ") # Empty joke

        handle_text_message(mock_event)

        mock_community_features.add_joke.assert_not_called() # Should not be called
        self.assertTrue(mock_reply_message.called)
        args, _ = mock_reply_message.call_args
        reply_request = args[0]
        self.assertEqual(reply_request.messages[0].text, "🤔 笑話內容不能為空喔！請輸入「笑話 [你的笑話內容]」")

    @patch('app.community')
    @patch('app.line_bot_api.reply_message')
    def test_get_joke_found(self, mock_reply_message, mock_community_features):
        mock_event = self._create_mock_event("說個笑話")

        mock_community_features.get_random_joke.return_value = {
            'success': True,
            'joke': {'text': '有個程式設計師...', 'user': '用戶1234'},
            'message': "🗣️ 用戶1234 分享的笑話：\n\n有個程式設計師..."
        }

        handle_text_message(mock_event)

        mock_community_features.get_random_joke.assert_called_once()
        self.assertTrue(mock_reply_message.called)
        args, _ = mock_reply_message.call_args
        reply_request = args[0]
        self.assertEqual(reply_request.messages[0].text, "🗣️ 用戶1234 分享的笑話：\n\n有個程式設計師...")

    @patch('app.community')
    @patch('app.line_bot_api.reply_message')
    def test_get_joke_not_found(self, mock_reply_message, mock_community_features):
        mock_event = self._create_mock_event("聽笑話")

        mock_community_features.get_random_joke.return_value = {
            'success': False,
            'message': '目前還沒有笑話，快來輸入「笑話 [內容]」分享一個吧！'
        }

        handle_text_message(mock_event)

        mock_community_features.get_random_joke.assert_called_once()
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

    @patch('app.community', None) # Simulate community features not available
    @patch('app.line_bot_api.reply_message')
    def test_get_joke_community_unavailable(self, mock_reply_message):
        mock_event = self._create_mock_event("說個笑話")
        handle_text_message(mock_event)
        self.assertTrue(mock_reply_message.called)
        args, _ = mock_reply_message.call_args
        self.assertEqual(args[0].messages[0].text, "❌ 社群功能（包含笑話）暫時無法使用")


if __name__ == '__main__':
    unittest.main()
