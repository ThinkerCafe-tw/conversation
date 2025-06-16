"""
Health check script for joke feature
Run this to quickly diagnose joke feature issues
"""

import os
import logging
from dotenv import load_dotenv
from google.cloud import firestore
from datetime import datetime

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_joke_health():
    """Comprehensive health check for joke feature"""
    
    health_status = {
        'firestore_connection': False,
        'jokes_collection_exists': False,
        'jokes_count': 0,
        'approved_jokes_count': 0,
        'has_required_fields': False,
        'sample_joke': None,
        'overall_status': 'UNHEALTHY'
    }
    
    try:
        # 1. Check Firestore connection
        print("🔍 Checking Firestore connection...")
        db = firestore.Client()
        
        # Test write/read
        test_ref = db.collection('health_check').document('joke_feature')
        test_ref.set({'checked_at': datetime.now(), 'feature': 'jokes'})
        test_doc = test_ref.get()
        
        if test_doc.exists:
            health_status['firestore_connection'] = True
            print("✅ Firestore connection: OK")
        
        # 2. Check jokes collection
        print("\n🔍 Checking jokes collection...")
        jokes_ref = db.collection('jokes')
        
        # Get all jokes (with limit for safety)
        all_jokes = list(jokes_ref.limit(1000).stream())
        health_status['jokes_count'] = len(all_jokes)
        
        if all_jokes:
            health_status['jokes_collection_exists'] = True
            print(f"✅ Jokes collection exists with {len(all_jokes)} jokes")
            
            # 3. Check approved jokes
            approved_count = 0
            jokes_with_all_fields = 0
            required_fields = {'text', 'status', 'category'}
            
            for doc in all_jokes:
                joke_data = doc.to_dict()
                
                # Count approved
                if joke_data.get('status') == 'approved':
                    approved_count += 1
                
                # Check fields
                if required_fields.issubset(joke_data.keys()):
                    jokes_with_all_fields += 1
                
                # Store sample
                if not health_status['sample_joke'] and joke_data.get('status') == 'approved':
                    health_status['sample_joke'] = {
                        'id': doc.id,
                        'text': joke_data.get('text', '')[:50] + '...',
                        'category': joke_data.get('category', 'N/A'),
                        'fields': list(joke_data.keys())
                    }
            
            health_status['approved_jokes_count'] = approved_count
            health_status['has_required_fields'] = jokes_with_all_fields > 0
            
            print(f"📊 Approved jokes: {approved_count}")
            print(f"📊 Jokes with required fields: {jokes_with_all_fields}")
            
        else:
            print("❌ No jokes found in collection")
        
        # 4. Determine overall status
        if (health_status['firestore_connection'] and 
            health_status['jokes_collection_exists'] and 
            health_status['jokes_count'] > 0):
            
            if health_status['approved_jokes_count'] > 0:
                health_status['overall_status'] = 'HEALTHY'
            else:
                health_status['overall_status'] = 'DEGRADED'
        
        # 5. Print summary
        print("\n" + "="*50)
        print("📋 JOKE FEATURE HEALTH CHECK SUMMARY")
        print("="*50)
        
        status_emoji = {
            'HEALTHY': '✅',
            'DEGRADED': '⚠️',
            'UNHEALTHY': '❌'
        }
        
        print(f"\n{status_emoji[health_status['overall_status']]} Overall Status: {health_status['overall_status']}")
        print(f"\nDetails:")
        print(f"  - Firestore Connected: {'✅' if health_status['firestore_connection'] else '❌'}")
        print(f"  - Jokes Collection: {'✅' if health_status['jokes_collection_exists'] else '❌'}")
        print(f"  - Total Jokes: {health_status['jokes_count']}")
        print(f"  - Approved Jokes: {health_status['approved_jokes_count']}")
        print(f"  - Has Required Fields: {'✅' if health_status['has_required_fields'] else '❌'}")
        
        if health_status['sample_joke']:
            print(f"\n📝 Sample Joke:")
            print(f"  - ID: {health_status['sample_joke']['id']}")
            print(f"  - Text: {health_status['sample_joke']['text']}")
            print(f"  - Category: {health_status['sample_joke']['category']}")
            print(f"  - Fields: {', '.join(health_status['sample_joke']['fields'])}")
        
        # 6. Recommendations
        print("\n💡 Recommendations:")
        if health_status['overall_status'] == 'UNHEALTHY':
            if not health_status['firestore_connection']:
                print("  ❗ Fix Firestore connection (check credentials)")
            elif health_status['jokes_count'] == 0:
                print("  ❗ Run seed_jokes_content.py to populate jokes")
        elif health_status['overall_status'] == 'DEGRADED':
            if health_status['approved_jokes_count'] == 0:
                print("  ⚠️ No approved jokes - run fix_joke_production.py")
        else:
            print("  ✅ Everything looks good!")
        
        return health_status
        
    except Exception as e:
        print(f"\n❌ Health check failed with error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return health_status


if __name__ == "__main__":
    health = check_joke_health()
    
    # Exit with appropriate code
    if health['overall_status'] == 'HEALTHY':
        exit(0)
    elif health['overall_status'] == 'DEGRADED':
        exit(1)
    else:
        exit(2)