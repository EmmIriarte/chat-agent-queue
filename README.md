# Chat Agent Queue System

A queue-based messaging system for managing LinkedIn conversations via Unipile with AI-generated responses.

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Python 3.11+ (for local development without Docker)

### Running with Docker (Recommended)

1. **Clone and navigate to the project**
   ```bash
   cd chat_agent_qeue
   ```

2. **Create environment file**
   ```bash
   cp env.example .env
   ```
   Edit `.env` and add your API keys:
   - `UNIPILE_API_KEY`
   - `OPENAI_API_KEY`
   - `EXTERNAL_DATABASE_URL` (when ready)

3. **Start the services**
   ```bash
   docker-compose up --build
   ```

4. **Access the application**
   - API: http://localhost:8000
   - API Docs (Swagger): http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

### Running Locally (Without Docker)

1. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up PostgreSQL**
   - Install PostgreSQL locally
   - Create database: `chat_queue_db`
   - Update `DATABASE_URL` in `.env`

4. **Run the application**
   ```bash
   python -m app.main
   # or
   uvicorn app.main:app --reload --port 8000
   ```

## 📡 Webhook Configuration

Configure Unipile to send webhooks to:
```
POST http://your-domain.com/api/v1/webhook/message-received
```

### Supported Events

The webhook can detect and process these LinkedIn message events:

- ✅ **On new message** - New messages received or sent
- ✅ **On message read** - Messages marked as read
- ✅ **On message reaction** - Emoji reactions to messages  
- ✅ **On message edit** - Messages that were edited
- ✅ **On message delete** - Messages that were deleted
- ✅ **On message delivered** - Messages marked as delivered

**Note:** Currently, only `message_received` events are processed for conversation tracking and auto-responses. Other events are logged but ignored.

For local testing with ngrok:
```bash
ngrok http 8000
```
Then use the ngrok URL: `https://your-subdomain.ngrok.io/api/v1/webhook/message-received`

## 🧪 Testing the Webhook

You can test the webhook endpoint using curl:

```bash
curl -X POST http://localhost:8000/api/v1/webhook/message-received \
  -H "Content-Type: application/json" \
  -d '{
    "account_id": "test_account",
    "account_type": "LINKEDIN",
    "account_info": {
      "type": "LINKEDIN",
      "feature": "classic",
      "user_id": "ACoAAAcDMMQBODyLwZrRcgYhrkCafURGqva0U4E"
    },
    "event": "message_received",
    "chat_id": "test_chat",
    "timestamp": "2025-10-13T10:00:00.000Z",
    "webhook_name": "Test Webhook",
    "message_id": "test_msg_123",
    "message": "Hello! This is a test message.",
    "sender": {
      "attendee_id": "sender_123",
      "attendee_name": "Test Sender",
      "attendee_provider_id": "LinkedInID456",
      "attendee_profile_url": "https://linkedin.com/in/test"
    },
    "attendees": [
      {
        "attendee_id": "recipient_123",
        "attendee_name": "Test Recipient",
        "attendee_provider_id": "ACoAAAcDMMQBODyLwZrRcgYhrkCafURGqva0U4E",
        "attendee_profile_url": "https://linkedin.com/in/test2"
      }
    ]
  }'
```

## 🎨 **Web Dashboard**

Access the **real-time queue monitoring dashboard** at:

```
http://localhost:8000/dashboard/
```

**Features:**
- 📊 **Live Statistics** - Total messages, scheduled, sent, errors
- 📬 **Message List** - View all queued messages with details
- ⏱️ **Auto-Refresh** - Updates every 5 seconds
- ➕ **Quick Test Form** - Submit test messages directly from UI
- ❌ **Cancel Messages** - One-click cancellation for scheduled messages
- 🎨 **Modern UI** - Beautiful, responsive design

**Perfect For:**
- ✅ Validating the implementation
- ✅ Real-time queue monitoring
- ✅ Testing batch enqueue
- ✅ Debugging message issues

## 📚 API Endpoints

### Health & Status
- `GET /` - Root endpoint
- `GET /health` - Health check

### Dashboard UI
- `GET /dashboard/` - Real-time queue monitoring dashboard

### Unipile Integration
- `POST /api/v1/unipile/webhook/message-received` - Receive Unipile webhooks

### Supabase Database
- `GET /api/v1/supabase/test` - Test Supabase connection
- `GET /api/v1/supabase/account/{unipile_account_id}` - Get account mapping
- `GET /api/v1/supabase/job/{job_id}` - Get job information

### Internal System
- `POST /api/v1/internal/messages/enqueue` - Enqueue single message
- `POST /api/v1/internal/messages/enqueue/batch` - Enqueue multiple messages (supports mixed invites/messages)
- `GET /api/v1/internal/messages/all` - Get detailed list of all messages in queue
- `DELETE /api/v1/internal/messages/{message_id}/cancel` - Cancel scheduled message
- `GET /api/v1/internal/status/queues` - Monitor queue status (summary)
- `GET /api/v1/internal/ai/prompt` - Get current AI prompt template
- `PUT /api/v1/internal/ai/prompt` - Update AI prompt template
- `PUT /api/v1/internal/policies/scheduling` - Update scheduling policy (Coming Soon)
- `GET /api/v1/internal/policies/scheduling` - Get scheduling policy (Coming Soon)

## 🚀 **Using the Batch Enqueue Endpoint**

Send multiple LinkedIn messages and invites in one request:

```bash
curl -X POST http://localhost:8000/api/v1/internal/messages/enqueue/batch \
  -H "Content-Type: application/json" \
  -d '{
    "jobs": [
      {
        "unipile_account_id": "your-unipile-account-id",
        "recipient_linkedin_id": "ACoAAC8mvj8BLjUm42KpTQzPoLU7pLY960TZ474",
        "job_id": "job123",
        "message": "Hi! I have an exciting opportunity for you...",
        "is_invite": true,
        "is_initial_reachout": true
      },
      {
        "unipile_account_id": "your-unipile-account-id",
        "recipient_linkedin_id": "ACoAAC8mvj8BLjUm42KpTQzPoLU7pLY960TZ475",
        "job_id": "job124",
        "message": "Following up on our conversation...",
        "is_invite": false,
        "is_initial_reachout": false
      }
    ]
  }'
```

**Features:**
- ✅ **Batch Processing** - Send multiple jobs in one request
- ✅ **Mixed Types** - Combine invites (`is_invite: true`) and messages (`is_invite: false`) 
- ✅ **Duplicate Prevention** - Automatically prevents duplicate initial outreach
- ✅ **Random Delays** - Each message scheduled with 2-10 min random delay (LinkedIn spam avoidance)
- ✅ **Automatic Retry** - Failed messages retry up to 3 times
- ✅ **Background Processing** - Messages sent automatically by background worker

## 📁 Project Structure

```
chat_agent_qeue/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── config.py        # Settings and configuration
│   ├── schemas.py       # Pydantic models
│   ├── database.py      # Supabase client
│   ├── clients/         # External API clients
│   │   ├── __init__.py
│   │   └── unipile.py   # Unipile API client (invites/messages)
│   ├── services/        # Business logic services
│   │   ├── __init__.py
│   │   ├── queue.py     # In-memory message queue manager
│   │   └── worker.py    # APScheduler background worker
│   └── routers/         # API route modules
│       ├── __init__.py
│       ├── health.py    # Health check routes
│       ├── unipile.py   # Unipile webhook routes
│       ├── supabase.py  # Supabase query routes
│       └── internal.py  # Internal system routes (batch enqueue)
├── ARCHITECTURE.md      # Complete system architecture
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker image definition
├── docker-compose.yml  # Docker services orchestration
└── env.example         # Environment variables template
```

## 🔧 Development

### View Logs
```bash
# Docker
docker-compose logs -f app

# Local
# Logs output to console
```

### Stop Services
```bash
docker-compose down
```

### Restart Services
```bash
docker-compose restart app
```

## 📖 Documentation

- [Architecture Document](./ARCHITECTURE.md) - Complete system design and data structures
- API Docs (Swagger): http://localhost:8000/docs (when running)

## 🛠 Tech Stack

- **Backend**: FastAPI (Python 3.11)
- **Database**: PostgreSQL 15
- **Scheduler**: APScheduler
- **LLM**: OpenAI GPT-4
- **Messaging Platform**: Unipile (LinkedIn)
- **Deployment**: Docker

## ⚠️ Current Status

**Phase 1: Webhook Listener** ✅
- Basic FastAPI server
- Webhook endpoint receiving Unipile messages
- Message direction detection (inbound/outbound)
- Conversation pair identification

**Phase 2: Coming Next** 🚧
- Database models and migrations
- Message queueing system
- Scheduler implementation
- LLM integration for auto-responses
- External DB connection for account/job info

