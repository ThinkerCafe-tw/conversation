"""
Fix production joke feature issues
"""

import os
import logging
from dotenv import load_dotenv
from google.cloud import firestore
from datetime import datetime
import sys

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_production_jokes():
    """Fix production joke issues"""
    try:
        # Initialize Firestore
        db = firestore.Client()
        logger.info("Connected to Firestore")
        
        # 1. Check current joke count
        jokes_ref = db.collection('jokes')
        existing_jokes = list(jokes_ref.limit(100).stream())
        logger.info(f"Current joke count: {len(existing_jokes)}")
        
        # 2. Check joke structure and fix if needed
        jokes_needing_fix = []
        for doc in existing_jokes:
            joke_data = doc.to_dict()
            
            # Check required fields
            required_fields = ['text', 'status', 'category']
            missing_fields = [field for field in required_fields if field not in joke_data]
            
            if missing_fields:
                jokes_needing_fix.append((doc.id, missing_fields))
        
        if jokes_needing_fix:
            logger.info(f"Found {len(jokes_needing_fix)} jokes needing fixes")
            
            # Fix jokes with missing fields
            for joke_id, missing_fields in jokes_needing_fix[:10]:  # Fix up to 10 at a time
                updates = {}
                if 'status' in missing_fields:
                    updates['status'] = 'approved'
                if 'category' in missing_fields:
                    updates['category'] = '綜合'
                
                if updates:
                    db.collection('jokes').document(joke_id).update(updates)
                    logger.info(f"Fixed joke {joke_id}: added {list(updates.keys())}")
        
        # 3. Ensure at least some jokes exist
        if len(existing_jokes) < 5:
            logger.info("Adding emergency jokes...")
            emergency_jokes = [
                {
                    'text': '為什麼程式設計師不喜歡戶外活動？因為外面沒有 Wi-Fi！',
                    'category': '程式設計',
                    'user_id': '系統_緊急',
                    'status': 'approved',
                    'timestamp': datetime.now(),
                    'likes': 0,
                    'views': 0
                },
                {
                    'text': '我的床是一個時光機，我躺下去一下子就到了八小時後。',
                    'category': '日常生活',
                    'user_id': '系統_緊急',
                    'status': 'approved',
                    'timestamp': datetime.now(),
                    'likes': 0,
                    'views': 0
                },
                {
                    'text': '為什麼鍵盤上的字母不是按照順序排列？因為這樣打字太簡單了，生活需要挑戰。',
                    'category': '冷笑話',
                    'user_id': '系統_緊急',
                    'status': 'approved',
                    'timestamp': datetime.now(),
                    'likes': 0,
                    'views': 0
                }
            ]
            
            for joke in emergency_jokes:
                db.collection('jokes').add(joke)
                logger.info(f"Added emergency joke: {joke['text'][:30]}...")
        
        # 4. Create or update jokes_stats
        stats_ref = db.collection('jokes_stats').document('summary')
        stats_ref.set({
            'total_jokes': len(existing_jokes),
            'last_fixed': datetime.now(),
            'status': 'healthy'
        }, merge=True)
        
        logger.info("✅ Production joke fixes complete")
        
        # 5. Test the fix
        from community_features import CommunityFeatures
        community = CommunityFeatures(None, None, db)
        result = community.get_random_joke("test_fix")
        
        if result['success']:
            logger.info("✅ Joke feature is now working!")
            logger.info(f"Test joke: {result['message'][:100]}...")
        else:
            logger.error(f"❌ Joke feature still failing: {result['message']}")
            
    except Exception as e:
        logger.error(f"Fix failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    fix_production_jokes()