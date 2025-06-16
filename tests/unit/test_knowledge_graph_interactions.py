import unittest
from unittest.mock import patch, MagicMock
from knowledge_graph import KnowledgeGraph # Assuming your file is knowledge_graph.py
# If datetime is used directly in Cypher queries via parameters, it's fine.
# If KG methods construct datetime objects, ensure they are comparable or mock datetime if needed.

class TestKnowledgeGraphInteractions(unittest.TestCase):

    def setUp(self):
        # This setup will be used for each test method.
        # We patch 'neo4j.GraphDatabase.driver' for each test that needs a fresh KG instance.
        # Alternatively, patch it at the class level if all tests use it.
        pass

    @patch('knowledge_graph.GraphDatabase.driver')
    def test_log_user_vote(self, mock_driver_constructor):
        mock_session_run = MagicMock()
        mock_session = MagicMock()
        mock_session.run = mock_session_run
        mock_driver_instance = MagicMock()
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session
        mock_driver_constructor.return_value = mock_driver_instance

        kg = KnowledgeGraph(uri="bolt://localhost:7687", user="neo4j", password="password")
        kg.connected = True # Force connected state for the test

        user_id="test_user_vote"
        vote_id="v123"
        vote_topic="Colors"
        option_chosen="Red"
        kg.log_user_vote(user_id, vote_id, vote_topic, option_chosen)

        mock_session_run.assert_called_once()
        args, _ = mock_session_run.call_args
        query = args[0]
        params = args[1]

        self.assertIn("MERGE (u:User {id: $user_id})", query)
        self.assertIn("MERGE (v:Vote {id: $vote_id})", query)
        self.assertIn("ON CREATE SET", query)
        self.assertIn("v.topic = $vote_topic", query)
        self.assertIn("MERGE (u)-[r:VOTED {option: $option_chosen}]->(v)", query)
        self.assertEqual(params['user_id'], user_id)
        self.assertEqual(params['vote_id'], vote_id)
        self.assertEqual(params['vote_topic'], vote_topic)
        self.assertEqual(params['option_chosen'], option_chosen)

    @patch('knowledge_graph.GraphDatabase.driver')
    def test_log_joke_submission(self, mock_driver_constructor):
        mock_session_run = MagicMock()
        mock_session = MagicMock()
        mock_session.run = mock_session_run
        # To mock the return value of result.single()["j"] if needed for the method
        mock_single_result = MagicMock()
        mock_single_result.single.return_value = {"j": MagicMock()} # Mock the node object
        mock_session_run.return_value = mock_single_result

        mock_driver_instance = MagicMock()
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session
        mock_driver_constructor.return_value = mock_driver_instance

        kg = KnowledgeGraph(uri="bolt://localhost:7687", user="neo4j", password="password")
        kg.connected = True

        user_id="test_user_joke_sub"
        joke_id="j456"
        joke_text_preview="Why did the chicken..."
        kg.log_joke_submission(user_id, joke_id, joke_text_preview)

        mock_session_run.assert_called_once()
        args, _ = mock_session_run.call_args
        query = args[0]
        params = args[1]

        self.assertIn("MERGE (j:Joke {id: $joke_id})", query)
        self.assertIn("j.text_preview = $joke_text_preview", query)
        self.assertIn("j.like_count = 0", query)
        self.assertIn("MERGE (u)-[r:SUBMITTED {timestamp: datetime()}]->(j)", query)
        self.assertEqual(params['user_id'], user_id)
        self.assertEqual(params['joke_id'], joke_id)
        self.assertEqual(params['joke_text_preview'], joke_text_preview)

    @patch('knowledge_graph.GraphDatabase.driver')
    def test_log_joke_like(self, mock_driver_constructor):
        mock_session_run = MagicMock()
        mock_session = MagicMock()
        mock_session.run = mock_session_run
        mock_single_result = MagicMock()
        mock_single_result.single.return_value = {"j": MagicMock()}
        mock_session_run.return_value = mock_single_result
        mock_driver_instance = MagicMock()
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session
        mock_driver_constructor.return_value = mock_driver_instance

        kg = KnowledgeGraph(uri="bolt://localhost:7687", user="neo4j", password="password")
        kg.connected = True

        user_id="test_user_joke_like"
        joke_id="j789"
        kg.log_joke_like(user_id, joke_id)

        mock_session_run.assert_called_once()
        args, _ = mock_session_run.call_args
        query = args[0]
        params = args[1]

        self.assertIn("MERGE (j:Joke {id: $joke_id})", query)
        self.assertIn("MERGE (u)-[r:LIKED {timestamp: datetime()}]->(j)", query)
        self.assertIn("SET j.like_count = coalesce(j.like_count, 0) + 1", query)
        self.assertEqual(params['user_id'], user_id)
        self.assertEqual(params['joke_id'], joke_id)

    @patch('knowledge_graph.GraphDatabase.driver')
    def test_get_friends_who_liked_joke_found(self, mock_driver_constructor):
        mock_session_run = MagicMock()
        mock_session = MagicMock()
        mock_session.run = mock_session_run
        # Simulate Neo4j returning some records
        mock_records = [{"friend_id": "friend1"}, {"friend_id": "friend2"}]
        mock_session_run.return_value = mock_records # session.run directly returns an iterable of records

        mock_driver_instance = MagicMock()
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session
        mock_driver_constructor.return_value = mock_driver_instance

        kg = KnowledgeGraph(uri="bolt://localhost:7687", user="neo4j", password="password")
        kg.connected = True

        user_id="test_user_social"
        joke_id="j101"
        limit=3
        friends = kg.get_friends_who_liked_joke(user_id, joke_id, limit)

        mock_session_run.assert_called_once()
        args, _ = mock_session_run.call_args
        query = args[0]
        params = args[1]

        self.assertIn("MATCH (currentUser:User {id: $user_id})-[:LIKED]->(j:Joke {id: $joke_id})", query)
        self.assertIn("MATCH (otherUser:User)-[:LIKED]->(j)", query)
        self.assertIn("WHERE currentUser <> otherUser", query)
        self.assertIn("RETURN otherUser.id AS friend_id", query)
        self.assertIn("LIMIT $limit", query)
        self.assertEqual(params['user_id'], user_id)
        self.assertEqual(params['joke_id'], joke_id)
        self.assertEqual(params['limit'], limit)
        self.assertEqual(friends, ["friend1", "friend2"])

    @patch('knowledge_graph.GraphDatabase.driver')
    def test_get_friends_who_liked_joke_not_found(self, mock_driver_constructor):
        mock_session_run = MagicMock()
        mock_session_run.return_value = [] # Simulate Neo4j returning no records
        mock_session = MagicMock()
        mock_session.run = mock_session_run
        mock_driver_instance = MagicMock()
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session
        mock_driver_constructor.return_value = mock_driver_instance

        kg = KnowledgeGraph(uri="bolt://localhost:7687", user="neo4j", password="password")
        kg.connected = True
        friends = kg.get_friends_who_liked_joke("user_social_none", "j102")
        self.assertEqual(friends, [])

    @patch('knowledge_graph.GraphDatabase.driver')
    def test_log_user_feature_interaction(self, mock_driver_constructor):
        mock_session_run = MagicMock()
        mock_session = MagicMock()
        mock_session.run = mock_session_run
        mock_driver_instance = MagicMock()
        mock_driver_instance.session.return_value.__enter__.return_value = mock_session
        mock_driver_constructor.return_value = mock_driver_instance

        kg = KnowledgeGraph(uri="bolt://localhost:7687", user="neo4j", password="password")
        kg.connected = True

        user_id="test_user_feat"
        feature_name="TestFeature"
        interaction_type="tested"
        # Mock _get_feature_category to avoid complex setup for it
        kg._get_feature_category = MagicMock(return_value="TestCategory")

        kg.log_user_feature_interaction(user_id, feature_name, interaction_type)

        mock_session_run.assert_called_once()
        args, _ = mock_session_run.call_args
        query = args[0]
        params = args[1]

        self.assertIn("MERGE (f:Feature {name: $feature_name})", query)
        self.assertIn("ON CREATE SET", query)
        self.assertIn("f.category = $category", query)
        self.assertIn("CREATE (u)-[r:INTERACTED_WITH_FEATURE {type: $interaction_type, timestamp: datetime()}]->(f)", query)
        self.assertIn("SET f.usage_count = coalesce(f.usage_count, 0) + 1", query)
        self.assertEqual(params['user_id'], user_id)
        self.assertEqual(params['feature_name'], feature_name)
        self.assertEqual(params['interaction_type'], interaction_type)
        self.assertEqual(params['category'], "TestCategory")

    def test_log_methods_when_not_connected(self,): # No driver patch, so KG will be not connected by default if no env vars
        kg = KnowledgeGraph() # Will be disconnected if no env vars
        self.assertFalse(kg.connected) # Sanity check

        with patch.object(kg, 'logger') as mock_logger: # Use patch.object for instance's logger
            kg.log_user_vote("u1", "v1", "t1", "o1")
            mock_logger.warning.assert_called_with("Neo4j not connected, skipping log_user_vote for user u1, vote v1")

            kg.log_joke_submission("u2", "j1", "preview")
            mock_logger.warning.assert_called_with("Neo4j not connected, skipping log_joke_submission for user u2, joke j1")

            kg.log_joke_like("u3", "j2")
            mock_logger.warning.assert_called_with("Neo4j not connected, skipping log_joke_like for user u3, joke j2")

            kg.log_user_feature_interaction("u4", "f1", "i1")
            mock_logger.warning.assert_called_with("Neo4j not connected, skipping log_user_feature_interaction for user u4, feature f1")

            result = kg.get_friends_who_liked_joke("u5", "j3")
            self.assertEqual(result, [])
            mock_logger.warning.assert_called_with("Neo4j not connected, skipping get_friends_who_liked_joke for user u5, joke j3")


if __name__ == '__main__':
    unittest.main()
