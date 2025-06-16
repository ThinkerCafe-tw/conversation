"""
Debug script to identify the exact joke feature error
"""

import os
import logging
from dotenv import load_dotenv
from google.cloud import firestore
from community_features import CommunityFeatures
import traceback

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def debug_joke_feature():
    """Debug the joke feature to find the exact error"""
    
    print("=== Debugging Joke Feature ===\n")
    
    # Step 1: Check environment variables
    print("1. Checking environment variables...")
    env_vars = {
        'GOOGLE_APPLICATION_CREDENTIALS': os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
        'GCLOUD_PROJECT': os.getenv('GCLOUD_PROJECT'),
        'FIRESTORE_EMULATOR_HOST': os.getenv('FIRESTORE_EMULATOR_HOST')
    }
    
    for key, value in env_vars.items():
        if value:
            print(f"   ✓ {key}: {value[:50]}..." if len(str(value)) > 50 else f"   ✓ {key}: {value}")
        else:
            print(f"   ✗ {key}: Not set")
    
    # Step 2: Test Firestore connection
    print("\n2. Testing Firestore connection...")
    try:
        db = firestore.Client()
        print("   ✓ Firestore client created successfully")
        
        # Test write
        test_doc_ref = db.collection('test').document('connection_test')
        test_doc_ref.set({'test': True, 'timestamp': firestore.SERVER_TIMESTAMP})
        print("   ✓ Test write successful")
        
        # Test read
        test_doc = test_doc_ref.get()
        if test_doc.exists:
            print("   ✓ Test read successful")
        
    except Exception as e:
        print(f"   ✗ Firestore connection failed: {type(e).__name__}: {e}")
        traceback.print_exc()
        return
    
    # Step 3: Check jokes collection
    print("\n3. Checking jokes collection...")
    try:
        # Check if collection exists and has documents
        jokes_ref = db.collection('jokes')
        
        # Try different approaches to count
        print("   - Attempting to count jokes...")
        
        # Method 1: Stream with limit
        limited_jokes = list(jokes_ref.limit(10).stream())
        print(f"   ✓ Found at least {len(limited_jokes)} jokes")
        
        # Check structure of first joke
        if limited_jokes:
            first_joke = limited_jokes[0].to_dict()
            print(f"   ✓ First joke structure: {list(first_joke.keys())}")
            print(f"   ✓ First joke status: {first_joke.get('status', 'No status field')}")
        
    except Exception as e:
        print(f"   ✗ Error checking jokes collection: {type(e).__name__}: {e}")
        traceback.print_exc()
    
    # Step 4: Test CommunityFeatures initialization
    print("\n4. Testing CommunityFeatures initialization...")
    try:
        # Initialize without Redis/Neo4j
        community = CommunityFeatures(
            redis_client=None,
            knowledge_graph=None,
            db=db
        )
        print("   ✓ CommunityFeatures initialized successfully")
        print(f"   ✓ Database reference is: {'set' if community.db else 'None'}")
        
    except Exception as e:
        print(f"   ✗ CommunityFeatures initialization failed: {type(e).__name__}: {e}")
        traceback.print_exc()
        return
    
    # Step 5: Test get_random_joke with detailed error catching
    print("\n5. Testing get_random_joke method...")
    try:
        # Test the actual method
        result = community.get_random_joke(user_id_for_cache="debug_user")
        
        print(f"   Result success: {result.get('success')}")
        print(f"   Result message: {result.get('message')}")
        
        if result.get('success') and result.get('joke'):
            joke = result['joke']
            print(f"   ✓ Successfully retrieved joke ID: {joke.get('id')}")
            print(f"   ✓ Joke category: {joke.get('category')}")
        
    except Exception as e:
        print(f"   ✗ get_random_joke failed with exception: {type(e).__name__}: {e}")
        traceback.print_exc()
    
    # Step 6: Test direct Firestore query as used in get_random_joke
    print("\n6. Testing direct Firestore queries...")
    try:
        # Test Strategy 1: Random offset
        print("   - Testing strategy 1 (random offset)...")
        jokes_query = db.collection('jokes').limit(50).offset(0)
        strategy1_docs = list(jokes_query.stream())
        print(f"     ✓ Strategy 1 returned {len(strategy1_docs)} documents")
        
        # Test Strategy 2: Simple limit
        print("   - Testing strategy 2 (simple limit)...")
        jokes_query = db.collection('jokes').limit(100)
        strategy2_docs = list(jokes_query.stream())
        print(f"     ✓ Strategy 2 returned {len(strategy2_docs)} documents")
        
        # Test filtering by status
        print("   - Testing status filtering...")
        approved_query = db.collection('jokes').where('status', '==', 'approved').limit(10)
        approved_docs = list(approved_query.stream())
        print(f"     ✓ Found {len(approved_docs)} approved jokes")
        
    except Exception as e:
        print(f"   ✗ Direct query failed: {type(e).__name__}: {e}")
        traceback.print_exc()
    
    print("\n=== Debug Complete ===")


if __name__ == "__main__":
    debug_joke_feature()