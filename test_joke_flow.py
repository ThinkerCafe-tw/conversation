"""
Test the complete joke feature flow as it would run in production
"""

import os
import logging
from dotenv import load_dotenv
from google.cloud import firestore
from frequency_bot_firestore import FrequencyBotFirestore
from community_features import CommunityFeatures
from knowledge_graph import KnowledgeGraph

# Load environment variables
load_dotenv()

# Set up logging to see all debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_joke_flow():
    """Test the complete joke flow as in app.py"""
    
    print("=== Testing Complete Joke Flow ===\n")
    
    # 1. Initialize knowledge graph (optional, can be None)
    print("1. Initializing knowledge graph...")
    try:
        knowledge_graph = KnowledgeGraph()
        print("   ✓ Knowledge graph initialized")
    except Exception as e:
        print(f"   ℹ Knowledge graph not available: {e}")
        knowledge_graph = None
    
    # 2. Initialize FrequencyBotFirestore (this creates the db instance)
    print("\n2. Initializing FrequencyBotFirestore...")
    try:
        frequency_bot = FrequencyBotFirestore(knowledge_graph)
        print("   ✓ FrequencyBotFirestore initialized")
        print(f"   ✓ frequency_bot.db is: {type(frequency_bot.db)}")
    except Exception as e:
        print(f"   ✗ FrequencyBotFirestore initialization failed: {e}")
        return
    
    # 3. Initialize CommunityFeatures with the db from frequency_bot
    print("\n3. Initializing CommunityFeatures...")
    try:
        # Simulating app.py line 104
        community = CommunityFeatures(
            redis_client=None,  # We're testing without Redis
            knowledge_graph=knowledge_graph,
            db=frequency_bot.db  # This is the key part
        )
        print("   ✓ CommunityFeatures initialized")
        print(f"   ✓ community.db is: {type(community.db)}")
    except Exception as e:
        print(f"   ✗ CommunityFeatures initialization failed: {e}")
        return
    
    # 4. Test the joke feature
    print("\n4. Testing joke retrieval...")
    try:
        # This simulates what happens when a user says "說個笑話"
        result = community.get_random_joke(user_id_for_cache="test_user_1234")
        
        print(f"   Success: {result['success']}")
        print(f"   Message preview: {result['message'][:100]}...")
        
        if result['success']:
            joke = result.get('joke', {})
            print(f"   ✓ Joke ID: {joke.get('id')}")
            print(f"   ✓ Category: {joke.get('category')}")
            print(f"   ✓ User: {joke.get('user')}")
        else:
            print(f"   ✗ Failed with message: {result['message']}")
            
    except Exception as e:
        print(f"   ✗ Exception during joke retrieval: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Test adding a joke
    print("\n5. Testing joke submission...")
    try:
        test_joke = "測試笑話：為什麼資料庫喜歡說冷笑話？因為它們都存在冷儲存裡！"
        add_result = community.add_joke("test_user_1234", test_joke)
        
        print(f"   Success: {add_result['success']}")
        print(f"   Message: {add_result['message']}")
        
    except Exception as e:
        print(f"   ✗ Exception during joke submission: {type(e).__name__}: {e}")
    
    print("\n=== Test Complete ===")


if __name__ == "__main__":
    test_joke_flow()