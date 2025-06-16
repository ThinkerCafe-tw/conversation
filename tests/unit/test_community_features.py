import unittest
from unittest.mock import MagicMock, patch
from community_features import CommunityFeatures # Assuming this is the correct import path
from google.cloud import firestore # For firestore.SERVER_TIMESTAMP and FieldPath

class TestCommunityFeatures(unittest.TestCase):

    def setUp(self):
        # Mock Firestore client and other dependencies if needed
        self.mock_db = MagicMock()
        self.mock_redis = MagicMock() # CommunityFeatures takes redis_client
        self.mock_kg = MagicMock()    # CommunityFeatures takes knowledge_graph

        # Initialize CommunityFeatures with mocked dependencies
        self.community_features = CommunityFeatures(
            redis_client=self.mock_redis,
            knowledge_graph=self.mock_kg,
            db=self.mock_db
        )
        self.community_features_no_db = CommunityFeatures(
            redis_client=self.mock_redis,
            knowledge_graph=self.mock_kg,
            db=None # Test case for db not available
        )


    # --- add_joke tests ---
    def test_add_joke_success(self):
        user_id = "user123"
        joke_text = "This is a test joke."

        # Configure the mock db's behavior for collection().add()
        mock_collection_ref = self.mock_db.collection.return_value
        mock_add_method = mock_collection_ref.add

        result = self.community_features.add_joke(user_id, joke_text)

        self.assertTrue(result['success'])
        self.assertEqual(result['message'], '😄 你的笑話已成功收錄！感謝分享！')

        # Verify that collection('jokes').add() was called correctly
        self.mock_db.collection.assert_called_once_with('jokes')
        # Firestore add() returns a tuple (timestamp, DocumentReference)
        # We need to mock this DocumentReference and its id attribute.
        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "firestore_doc_id_123"
        mock_add_method.return_value = (MagicMock(), mock_doc_ref) # Mock the return of add()

        # Reset mock_kg for this specific call verification if it's used in setUp for other tests
        self.mock_kg.reset_mock()
        self.mock_kg.connected = True # Ensure KG is connected for this path

        result = self.community_features.add_joke(user_id, joke_text)

        self.assertTrue(result['success'])
        self.assertEqual(result['message'], '😄 你的笑話已成功收錄！感謝分享！')

        mock_add_method.assert_called_once_with({
            'text': joke_text,
            'user_id': user_id,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'status': 'approved'
        })
        self.mock_kg.log_joke_submission.assert_called_once_with(
            user_id=user_id,
            joke_id="firestore_doc_id_123",
            joke_text_preview=joke_text[:50]
        )

    def test_add_joke_kg_disconnected(self):
        user_id = "user_kg_dc"
        joke_text = "Joke for KG disconnected test."
        self.mock_kg.connected = False # Simulate KG disconnected

        mock_doc_ref = MagicMock()
        mock_doc_ref.id = "firestore_doc_id_456"
        self.mock_db.collection.return_value.add.return_value = (MagicMock(), mock_doc_ref)

        result = self.community_features.add_joke(user_id, joke_text)

        self.assertTrue(result['success']) # Firestore part should still succeed
        self.mock_kg.log_joke_submission.assert_not_called()


    def test_add_joke_db_unavailable(self):
        result = self.community_features_no_db.add_joke("user1", "a joke")
        self.assertFalse(result['success'])
        self.assertEqual(result['message'], '❌ 笑話功能資料庫未連接')

    @patch('community_features.logger.error') # To check logging
    def test_add_joke_firestore_exception(self, mock_logger_error):
        self.mock_db.collection.return_value.add.side_effect = Exception("Firestore error")

        result = self.community_features.add_joke("user1", "another joke")

        self.assertFalse(result['success'])
        self.assertEqual(result['message'], '😥 新增笑話失敗，請稍後再試')
        mock_logger_error.assert_called_once_with("新增笑話失敗: Firestore error")

    # --- get_random_joke tests ---
    def test_get_random_joke_found_first_try(self):
        mock_doc_id = "random_doc_id_123"
        joke_content = "Why did the scarecrow win an award? Because he was outstanding in his field!"
        joke_user_id = "user_joker"

        # Mock document ID generation
        self.mock_db.collection.return_value.document.return_value.id = mock_doc_id

        # Mock Firestore query stream
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.to_dict.return_value = {
            'text': joke_content,
            'user_id': joke_user_id,
            'status': 'approved' # Ensure status is approved
        }
        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_doc_snapshot] # Simulate one document found

        # Configure the chain of query calls
        self.mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_query

        # Mock KG interactions
        self.mock_kg.reset_mock()
        self.mock_kg.connected = True
        self.mock_kg.get_friends_who_liked_joke.return_value = ["friend1", "friend2"]

        user_id_for_cache = "test_current_user"
        result = self.community_features.get_random_joke(user_id_for_cache=user_id_for_cache)

        self.assertTrue(result['success'])
        self.assertEqual(result['joke']['text'], joke_content)
        self.assertEqual(result['joke']['user'], joke_user_id)
        self.assertEqual(result['joke']['id'], mock_doc_snapshot.id) # Check joke ID is passed

        expected_message_base = f"🗣️ {joke_user_id} 分享的笑話：\n\n{joke_content}"
        expected_social_context = "\n\n💡 你的朋友們 friend1, friend2 也都喜歡這個笑話！"
        self.assertEqual(result['message'], expected_message_base + expected_social_context)

        self.mock_redis.setex.assert_called_once_with(f"user:{user_id_for_cache}:last_joke_id", 300, mock_doc_snapshot.id)
        self.mock_kg.get_friends_who_liked_joke.assert_called_once_with(user_id_for_cache, mock_doc_snapshot.id)

        # Check the query conditions for the first attempt
        calls = self.mock_db.collection.return_value.where.call_args_list
        self.assertEqual(calls[0][0][0], firestore.FieldPath.document_id())
        self.assertEqual(calls[0][0][1], '>=')
        self.assertEqual(calls[0][0][2], mock_doc_id)
        self.assertEqual(calls[1][0][0], 'status') # Second where call
        self.assertEqual(calls[1][0][1], '==')
        self.assertEqual(calls[1][0][2], 'approved')


    def test_get_random_joke_found_second_try(self):
        mock_doc_id = "random_doc_id_456"
        joke_content = "What do you call cheese that isn't yours? Nacho cheese!"
        joke_user_id = "user_cheesy"

        self.mock_db.collection.return_value.document.return_value.id = mock_doc_id

        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.to_dict.return_value = {'text': joke_content, 'user_id': joke_user_id, 'status': 'approved'}

        # Simulate first query returns empty, second query returns a doc
        query_ge = self.mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value
        query_ge.stream.return_value = [] # First attempt fails

        query_lt = MagicMock() # This will be returned by the second limit call
        query_lt.stream.return_value = [mock_doc_snapshot]

        # Make the first limit call return query_ge, and second return query_lt
        # This requires careful mocking of chained calls.
        # If collection().where().where().limit() is called twice, this needs to reflect that.
        # Let's assume a fresh chain for the second call for simplicity in mocking.
        # A more robust way would be to have `limit` return different objects based on call count or args.

        # This is tricky. Let's simplify:
        # The first where chain (>=) will return an empty stream.
        # The second where chain (<) will return the doc.

        # Mock the first query chain (>= random_key)
        mock_query_ge_limit = MagicMock()
        mock_query_ge_limit.stream.return_value = []

        # Mock the second query chain (< random_key)
        mock_query_lt_limit = MagicMock()
        mock_query_lt_limit.stream.return_value = [mock_doc_snapshot]

        # Use a side_effect to return different query objects based on the FieldPath.document_id() comparison
        def where_side_effect_for_get_joke(*args, **kwargs):
            # args[0] is the field_path, args[1] is opstring, args[2] is value
            if args[1] == '>=': # First call for document_id
                # This where is for document_id >= random_key
                # It needs to return an object that, when 'status' where and limit are called, returns mock_query_ge_limit
                status_where_mock_ge = MagicMock()
                status_where_mock_ge.limit.return_value = mock_query_ge_limit
                # The first where (doc_id) returns an object that has another 'where' method for status
                doc_id_where_mock_ge = MagicMock()
                doc_id_where_mock_ge.where.return_value = status_where_mock_ge
                return doc_id_where_mock_ge
            elif args[1] == '<': # Second call for document_id
                status_where_mock_lt = MagicMock()
                status_where_mock_lt.limit.return_value = mock_query_lt_limit
                doc_id_where_mock_lt = MagicMock()
                doc_id_where_mock_lt.where.return_value = status_where_mock_lt
                return doc_id_where_mock_lt
            return MagicMock() # Default for other where calls if any

        self.mock_db.collection.return_value.where.side_effect = where_side_effect_for_get_joke
        self.mock_kg.reset_mock()
        self.mock_kg.connected = True
        self.mock_kg.get_friends_who_liked_joke.return_value = ["friend_single"]


        user_id_for_cache = "test_current_user_single_friend"
        result = self.community_features.get_random_joke(user_id_for_cache=user_id_for_cache)

        self.assertTrue(result['success'])
        self.assertEqual(result['joke']['text'], joke_content)
        self.assertIn(f"🗣️ {joke_user_id} 分享的笑話：\n\n{joke_content}", result['message'])
        self.assertIn("\n\n💡 你的朋友 friend_single 也喜歡這個笑話！", result['message'])
        self.mock_kg.get_friends_who_liked_joke.assert_called_once_with(user_id_for_cache, mock_doc_snapshot.id)

        # Verify the >= query was made, then the < query
        # The side_effect handles which stream is returned.
        # We can check call_args on self.mock_db.collection.return_value.where
        first_call_args = self.mock_db.collection.return_value.where.call_args_list[0][0]
        self.assertEqual(first_call_args[0], firestore.FieldPath.document_id())
        self.assertEqual(first_call_args[1], '>=')

        second_call_args = self.mock_db.collection.return_value.where.call_args_list[1][0]
        self.assertEqual(second_call_args[0], firestore.FieldPath.document_id())
        self.assertEqual(second_call_args[1], '<')


    def test_get_random_joke_not_found_at_all(self):
        self.mock_db.collection.return_value.document.return_value.id = "some_id"
        # Both queries should return empty lists
        self.mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value.stream.return_value = []
        self.mock_kg.reset_mock() # Ensure no KG calls if no joke found

        result = self.community_features.get_random_joke()

        self.assertFalse(result['success'])
        self.mock_kg.get_friends_who_liked_joke.assert_not_called()
        self.assertEqual(result['message'], '目前還沒有笑話，快來輸入「笑話 [內容]」分享一個吧！')

    def test_get_random_joke_db_unavailable(self):
        result = self.community_features_no_db.get_random_joke()
        self.assertFalse(result['success'])
        self.assertEqual(result['message'], '❌ 笑話功能資料庫未連接')

    @patch('community_features.logger.error')
    def test_get_random_joke_firestore_exception(self, mock_logger_error):
        self.mock_db.collection.return_value.document.side_effect = Exception("Firestore error")

        result = self.community_features.get_random_joke()

        self.assertFalse(result['success'])
        self.assertEqual(result['message'], '😥 獲取笑話時發生錯誤，請稍後再試')
        mock_logger_error.assert_called_once_with("獲取笑話失敗: Firestore error")

    def test_get_random_joke_kg_disconnected(self):
        mock_doc_id = "random_doc_id_kg_dc"
        joke_content = "Joke for KG disconnected test"
        joke_user_id = "user_kg_dc_joker"

        self.mock_db.collection.return_value.document.return_value.id = mock_doc_id
        mock_doc_snapshot = MagicMock()
        mock_doc_snapshot.id = "firestore_joke_id_kg_dc" # Ensure the snapshot has an ID
        mock_doc_snapshot.to_dict.return_value = {'text': joke_content, 'user_id': joke_user_id, 'status': 'approved'}

        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_doc_snapshot]
        self.mock_db.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_query

        self.mock_kg.connected = False # Simulate KG disconnected
        user_id_for_cache = "test_current_user_kg_dc"
        result = self.community_features.get_random_joke(user_id_for_cache=user_id_for_cache)

        self.assertTrue(result['success'])
        expected_message_base = f"🗣️ {joke_user_id} 分享的笑話：\n\n{joke_content}"
        self.assertEqual(result['message'], expected_message_base) # No social context
        self.mock_kg.get_friends_who_liked_joke.assert_not_called()


    # --- like_last_joke tests ---
    def test_like_last_joke_success(self):
        user_id = "user_liker"
        last_joke_id = "joke_to_like_123"
        self.mock_redis.get.return_value = last_joke_id
        self.mock_kg.connected = True # Ensure KG is connected

        result = self.community_features.like_last_joke(user_id)

        self.assertTrue(result['success'])
        self.assertEqual(result['message'], '👍 已讚！感謝您的評價。')
        self.mock_redis.get.assert_called_once_with(f"user:{user_id}:last_joke_id")
        self.mock_kg.log_joke_like.assert_called_once_with(user_id, last_joke_id)

    def test_like_last_joke_no_last_joke(self):
        user_id = "user_no_joke_to_like"
        self.mock_redis.get.return_value = None # No last joke in Redis

        result = self.community_features.like_last_joke(user_id)

        self.assertFalse(result['success'])
        self.assertEqual(result['message'], '您最近沒有看過笑話，或者時間太久了，無法評價。')
        self.mock_kg.log_joke_like.assert_not_called()

    def test_like_last_joke_kg_disconnected(self):
        user_id = "user_kg_dc_liker"
        last_joke_id = "joke_kg_dc_like_456"
        self.mock_redis.get.return_value = last_joke_id
        self.mock_kg.connected = False # KG disconnected

        result = self.community_features.like_last_joke(user_id)

        self.assertFalse(result['success'])
        self.assertEqual(result['message'], '❌ 評價功能暫時無法連接知識圖譜')
        self.mock_kg.log_joke_like.assert_not_called()

    @patch('community_features.logger.error')
    def test_like_last_joke_kg_exception(self, mock_logger_error):
        user_id = "user_kg_ex_liker"
        last_joke_id = "joke_kg_ex_like_789"
        self.mock_redis.get.return_value = last_joke_id
        self.mock_kg.connected = True
        self.mock_kg.log_joke_like.side_effect = Exception("Neo4j write error")

        result = self.community_features.like_last_joke(user_id)

        self.assertFalse(result['success'])
        self.assertEqual(result['message'], '😥 按讚失敗，請稍後再試')
        self.mock_kg.log_joke_like.assert_called_once_with(user_id, last_joke_id)
        mock_logger_error.assert_called_with(f"按讚笑話失敗 for user {user_id}: Neo4j write error")

    def test_like_last_joke_redis_disconnected(self):
        user_id = "user_redis_dc_liker"
        # Simulate redis not connected for the main feature object
        self.community_features.redis = None # Or make self.community_features.connected return False

        # Need to re-initialize or modify the specific instance for this test
        cf_no_redis = CommunityFeatures(redis_client=None, knowledge_graph=self.mock_kg, db=self.mock_db)

        result = cf_no_redis.like_last_joke(user_id)
        self.assertFalse(result['success'])
        self.assertEqual(result['message'], cf_no_redis.not_connected_message) # Check specific message
        self.mock_kg.log_joke_like.assert_not_called()


if __name__ == '__main__':
    unittest.main()
