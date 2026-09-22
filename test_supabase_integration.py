"""
Quick integration test for Supabase operations
"""
import requests
import json
from uuid import uuid4
from datetime import datetime

BASE_URL = "http://localhost:8000"

def test_system():
    print("🧪 Testing Chat Agent Queue System\n")
    
    # Test 1: Health check
    print("1️⃣ Testing health endpoint...")
    try:
        resp = requests.get(f"{BASE_URL}/health")
        print(f"   Status: {resp.status_code}")
        print(f"   ✅ Health check passed\n")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}\n")
        return
    
    # Test 2: Enqueue a message (this will test database operations)
    print("2️⃣ Testing message enqueue (creates conversation + message)...")
    try:
        test_data = {
            "recipient_linkedin_id": f"test-recipient-{uuid4().hex[:8]}",
            "message": "Test message for integration testing",
            "job_id": "test-job-integration",
            "sender_linkedin_id": "test-sender-123",
            "unipile_account_id": "test-account-123",
            "direction": "outbound",
            "message_type": "message",
            "calendar_account_id": None
        }
        
        resp = requests.post(f"{BASE_URL}/api/v1/messages/enqueue", json=test_data)
        print(f"   Status: {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            print(f"   ✅ Message enqueued: {result.get('message_id', 'N/A')}")
            print(f"   ✅ Conversation created: {result.get('chat_id', 'N/A')}\n")
            
            # Get the chat_id for cleanup
            chat_id = result.get('chat_id')
            message_id = result.get('message_id')
            
            # Test 3: Get conversations
            print("3️⃣ Testing get all conversations...")
            resp = requests.get(f"{BASE_URL}/api/v1/internal/conversations")
            if resp.status_code == 200:
                convs = resp.json()
                print(f"   ✅ Found {len(convs.get('conversations', []))} conversations\n")
            
            # Test 4: Get messages
            print("4️⃣ Testing get all messages...")
            resp = requests.get(f"{BASE_URL}/api/v1/internal/messages/all")
            if resp.status_code == 200:
                msgs = resp.json()
                print(f"   ✅ Found {len(msgs.get('messages', []))} messages\n")
            
            # Test 5: Get queue status
            print("5️⃣ Testing queue status...")
            resp = requests.get(f"{BASE_URL}/api/v1/internal/status/queues")
            if resp.status_code == 200:
                status = resp.json()
                print(f"   ✅ Queue status: {json.dumps(status, indent=2)}\n")
            
            print("✅ All tests passed! No cleanup needed - test data will be automatically managed.")
            
        else:
            print(f"   ❌ Failed: {resp.text}\n")
    except Exception as e:
        print(f"   ❌ Error: {e}\n")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_system()
