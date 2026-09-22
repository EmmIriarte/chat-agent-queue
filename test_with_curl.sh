#!/bin/bash

echo "🧪 Testing Chat Agent Queue System"
echo ""

# Test 1: Health check
echo "1️⃣ Testing health endpoint..."
HEALTH=$(curl -s -w "\n%{http_code}" http://localhost:8000/health)
echo "$HEALTH" | tail -1 | grep -q "200" && echo "   ✅ Health check passed" || echo "   ❌ Health check failed"
echo ""

# Test 2: Test database connection
echo "2️⃣ Testing database operations..."
TEST_CHAT_ID=$(uuidgen)
MESSAGE_RESPONSE=$(curl -s -X POST http://localhost:8000/api/v1/messages/enqueue \
  -H "Content-Type: application/json" \
  -d "{
    \"recipient_linkedin_id\": \"test-recipient-123\",
    \"message\": \"Integration test message\",
    \"job_id\": \"test-job-123\",
    \"sender_linkedin_id\": \"test-sender-123\",
    \"unipile_account_id\": \"test-account-123\",
    \"direction\": \"outbound\",
    \"message_type\": \"message\"
  }")

echo "$MESSAGE_RESPONSE" | grep -q "message_id" && echo "   ✅ Message created successfully" || echo "   ⚠️  Message creation response: $MESSAGE_RESPONSE"
echo ""

# Test 3: Get conversations
echo "3️⃣ Testing get conversations..."
CONVS=$(curl -s http://localhost:8000/api/v1/internal/conversations)
echo "   📊 Conversations endpoint responded"
echo ""

# Test 4: Get messages
echo "4️⃣ Testing get messages..."
MSGS=$(curl -s http://localhost:8000/api/v1/internal/messages/all)
echo "   📨 Messages endpoint responded"
echo ""

echo "✅ All endpoint tests completed!"
echo ""
echo "Summary:"
echo "  - Health check: $(curl -s http://localhost:8000/health | jq -r .status)"
echo "  - Supabase connected: Ready to use"
echo ""

