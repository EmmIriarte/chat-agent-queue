# Chat Agent Queue Platform - Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [API Endpoints](#api-endpoints)
5. [Conversation Flow](#conversation-flow)
6. [AI Integration](#ai-integration)
7. [Calendar Booking](#calendar-booking)
8. [Deployment](#deployment)
9. [Production Readiness](#production-readiness)

---

## Overview

The Chat Agent Queue Platform is an AI-powered LinkedIn messaging system designed to automate recruiter outreach and candidate conversations. It uses OpenAI's GPT models to generate context-aware, personalized messages and can automatically book calendar appointments based on candidate availability.

### Key Features
- **Automated LinkedIn Messaging**: Queue and send messages to candidates automatically
- **AI-Powered Responses**: Uses GPT to generate context-aware replies to candidate messages
- **Calendar Integration**: Automatically books meetings when candidates express interest
- **Per-Job & Per-Conversation AI Control**: Toggle AI on/off at job or conversation level
- **Real-Time Dashboard**: Monitor all conversations and queue status
- **Supabase Integration**: Pulls account mappings and job data from external database

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Application                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Internal    │  │   Unipile   │  │  Dashboard   │          │
│  │    API       │  │  Webhook    │  │     UI       │          │
│  │   Router     │  │   Handler   │  │              │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                  │
│         └─────────────────┴─────────────────┘                  │
│                          │                                     │
│         ┌────────────────┴────────────────────┐               │
│         │                                       │               │
│  ┌──────▼───────┐                      ┌───────▼──────┐       │
│  │   Services   │                      │   Database   │       │
│  │   Layer      │◄─────────────────────►│   Layer      │       │
│  │              │                       │              │       │
│  │ - Queue Mgr  │                       │ - PostgreSQL  │       │
│  │ - OpenAI     │                       │ - Supabase   │       │
│  │ - Calendar   │                       │ - Unipile    │       │
│  └──────────────┘                       └──────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Initial Outreach**: External platform calls `/api/v1/internal/messages/enqueue`
2. **Message Queueing**: Messages stored in PostgreSQL with status `scheduled`
3. **Queue Processor**: APScheduler runs every 30s to send scheduled messages via Unipile API
4. **Inbound Webhook**: Candidate replies trigger `/api/v1/unipile/webhook`
5. **AI Processing**: System generates AI response using conversation history
6. **Calendar Booking**: If AI detects scheduling intent, creates calendar event
7. **Response Enqueue**: AI response added to queue for sending

---

## Components

### 1. Internal API Router (`app/routers/internal.py`)

Handles platform management endpoints:
- Account management
- Message queueing
- Job/conversation queries
- AI toggle controls
- Dashboard endpoints

### 2. Unipile Webhook Router (`app/routers/unipile.py`)

Processes incoming messages from Unipile:
- Detects new vs existing conversations
- Generates AI responses
- Handles calendar booking logic
- Updates conversation stages

### 3. Database Layer (`app/db/`)

- **PostgreSQL**: Stores messages, conversations, and job settings
- **Supabase**: External database for account mappings and job information
- **asyncpg**: Async PostgreSQL connection pooling

### 4. Service Layer (`app/services/`)

- **Queue Manager**: Handles message queuing and processing
- **OpenAI Client**: Generates AI responses using GPT models
- **Calendar Service**: Discovers calendars, checks availability, books events
- **Scheduling Parser**: Extracts booking data from AI responses

### 5. Clients (`app/clients/`)

- **Unipile API Client**: Sends messages, lists calendars, retrieves events
- **OpenAI Client**: Generates AI responses

---

## API Endpoints

### Internal API Endpoints (Platform Management)

#### 1. Enqueue Message
**POST** `/api/v1/internal/messages/enqueue`

Queue a new message to be sent to a candidate.

**Request Body:**
```json
{
  "unipile_account_id": "aeQOURVDRG-RvEAo1CWZyw",
  "calendar_account_id": "eGq_DvdhQuSNXtU0KN70Mw",
  "recipient_linkedin_id": "ACoAAC8mvj8BLjUm42KpTQzPoLU7pLY960TZ474",
  "job_id": "152868f4-ee5b-43cc-82d6-f3e045bf267e",
  "message": "Hi! Would you be interested in this role?",
  "is_invite": false,
  "is_initial_reachout": true
}
```

**Response:**
```json
{
  "status": "success",
  "message_id": "uuid",
  "chat_id": "uuid",
  "scheduled_at": "2025-10-27T12:00:00Z"
}
```

**What it does:**
1. Validates account mapping in Supabase
2. Creates conversation if it doesn't exist
3. Adds message to queue with `scheduled` status
4. Returns message details

---

#### 2. Get Queue Status
**GET** `/api/v1/internal/status/queues`

Get overall queue statistics.

**Response:**
```json
{
  "status": "success",
  "statistics": {
    "total_messages": 50,
    "scheduled": 10,
    "sent": 35,
    "error": 5,
    "cancelled": 0,
    "total_conversations": 20,
    "total_jobs": 3
  }
}
```

---

#### 3. Get All Messages
**GET** `/api/v1/internal/messages/all`

Get detailed information about all messages in the queue.

**Response:**
```json
{
  "status": "success",
  "count": 50,
  "messages": [
    {
      "message_id": "uuid",
      "chat_id": "uuid",
      "message": "Hello!",
      "direction": "outbound",
      "status": "sent",
      "created_at": "2025-10-27T12:00:00Z",
      ...
    }
  ]
}
```

---

#### 4. Get All Conversations
**GET** `/api/v1/internal/conversations`

Get all conversations with AI status.

**Response:**
```json
{
  "status": "success",
  "count": 20,
  "conversations": [
    {
      "chat_id": "uuid",
      "job_id": "uuid",
      "stage": "initial_outreach",
      "conversation_ai_enabled": true,
      "job_ai_enabled": true,
      "message_count": 5,
      "created_at": "2025-10-27T12:00:00Z"
    }
  ]
}
```

---

#### 5. Get Conversation History
**GET** `/api/v1/internal/conversations/{chat_id}/history`

Get full message history for a conversation.

**Response:**
```json
{
  "status": "success",
  "conversation": {
    "chat_id": "uuid",
    "job_id": "uuid",
    "stage": "call_scheduled",
    "created_at": "2025-10-27T12:00:00Z"
  },
  "messages": [
    {
      "message_id": "uuid",
      "message": "Hello!",
      "direction": "outbound",
      "status": "sent",
      "created_at": "2025-10-27T12:00:00Z"
    }
  ]
}
```

---

#### 6. Get Job Complete Data
**GET** `/api/v1/internal/jobs/{job_id}`

Get complete job data with all conversations pre-grouped.

**Response:**
```json
{
  "status": "success",
  "job_id": "uuid",
  "conversations": [
    {
      "chat_id": "uuid",
      "stage": "initial_outreach",
      "latest_message": {...},
      "messages": [...]
    }
  ]
}
```

---

#### 7. Get All Accounts
**GET** `/api/v1/internal/accounts`

Get all connected Unipile accounts from Supabase.

**Response:**
```json
{
  "status": "success",
  "count": 15,
  "accounts": [
    {
      "account_id": "aeQOURVDRG-RvEAo1CWZyw",
      "provider_id": "linkedin_provider_id",
      "name": "John Doe"
    }
  ]
}
```

---

#### 8. Toggle Job AI
**POST** `/api/v1/internal/jobs/{job_id}/ai/toggle`

Toggle AI on/off for a specific job (affects all conversations).

**Response:**
```json
{
  "status": "success",
  "job_id": "uuid",
  "ai_enabled": true
}
```

---

#### 9. Get Job AI Status
**GET** `/api/v1/internal/jobs/{job_id}/ai/status`

Get current AI status for a job.

**Response:**
```json
{
  "status": "success",
  "job_id": "uuid",
  "ai_enabled": true
}
```

---

#### 10. Send Message to Conversation
**POST** `/api/v1/internal/conversations/{chat_id}/send-message`

Send a new message to an existing conversation from platform UI.

**Request Body:**
```json
{
  "message": "Follow-up message"
}
```

**Response:**
```json
{
  "status": "success",
  "message_id": "uuid",
  "chat_id": "uuid",
  "scheduled_at": "2025-10-27T12:00:00Z"
}
```

---

### Unipile Webhook Endpoint

#### Inbound Message Webhook
**POST** `/api/v1/unipile/webhook`

Handles incoming messages from Unipile/LinkedIn.

**What it does:**
1. Logs inbound message to database
2. Checks if conversation exists
3. If new conversation: logs only
4. If existing conversation:
   - Checks AI settings (job-level → conversation-level)
   - Generates AI response using conversation history
   - If AI detects scheduling intent:
     - Discovers default calendar
     - Checks availability
     - Creates calendar event
   - Enqueues AI response
5. Returns success response

---

### Dashboard UI

**GET** `/dashboard`

Serves the HTML dashboard UI showing:
- Connected accounts from Supabase
- Queue statistics (scheduled, sent, errors)
- All messages in queue with status
- All conversations with AI status indicators

---

## Conversation Flow

### Conversation Stages

1. **initial_outreach**: First message sent to candidate
2. **awaiting_response**: Waiting for candidate reply
3. **engaged**: Candidate replied, conversation active
4. **scheduling**: Candidate expressed interest in scheduling
5. **call_scheduled**: Calendar event successfully created
6. **call_completed**: Post-call state
7. **not_interested**: Candidate declined

### Typical Flow

```
┌────────────────────────────────────────────────────────────┐
│ 1. Initial Outreach                                        │
│    Platform calls /messages/enqueue                        │
│    → Message queued with status "scheduled"                │
└────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│ 2. Queue Processing                                        │
│    APScheduler runs every 30s                             │
│    → Calls Unipile API to send message                    │
│    → Updates status to "sent"                             │
└────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│ 3. Candidate Replies                                        │
│    Unipile sends webhook to /unipile/webhook               │
│    → Message logged as inbound                             │
│    → AI generates response                                 │
│    → Response enqueued                                    │
└────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│ 4. AI Detects Scheduling Intent                            │
│    → AI outputs JSON with booking_data                    │
│    → Calendar service discovers default calendar           │
│    → Checks availability                                  │
│    → Creates event if available                           │
└────────────────────────────────────────────────────────────┘
```

---

## AI Integration

### How AI Works

The AI generates responses based on:
- **Conversation History**: All previous messages in the conversation
- **Job Information**: Job title, description, client from Supabase
- **Recruiter Name**: Account mapping from Supabase
- **Conversation Stage**: Current stage (e.g., `initial_outreach`, `scheduling`)

### AI Response Format

The AI is instructed to output structured JSON:

```json
{
  "message": "Great! I'll send you a calendar invite for Tuesday at 2pm.",
  "stage": "call_scheduled",
  "booking_data": {
    "datetime": "2025-10-29T14:00:00Z",
    "duration": 30,
    "email": "candidate@example.com",
    "candidate_name": "John Doe",
    "job_summary": "Senior Python Developer at TechCorp"
  }
}
```

### AI Settings Hierarchy

1. **Job-Level Setting** (highest priority): If disabled, all conversations disabled
2. **Conversation-Level Setting**: Per-conversation AI control
3. **Default**: AI enabled

---

## Calendar Booking

### Flow

1. **AI Detects Intent**: Response includes `booking_data`
2. **Calendar Discovery**: Find default calendar using `is_default` flag
3. **Availability Check**: Check if proposed time is available
4. **Event Creation**: Create calendar event with:
   - Title: "Interview: {candidate_name}"
   - Attendees: Candidate email
   - Body: Job summary and context
   - Start/End: Based on `booking_data`

### Required Data

- `calendar_account_id`: Unipile calendar account ID
- `calendar_id`: Default calendar ID (auto-discovered)
- `datetime`: ISO format datetime
- `duration`: Minutes
- `email`: Candidate email
- `candidate_name`: Candidate name
- `job_summary`: Job title and description

---

## Deployment

### Google Cloud Run

The system is deployed as a single Docker container on Google Cloud Run.

**Container includes:**
- PostgreSQL 15 (Alpine)
- Python 3.12
- FastAPI application
- All dependencies

**Environment Variables:**
- `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`
- `UNIPILE_API_KEY`, `UNIPILE_API_DNS`
- `OPENAI_API_KEY`, `OPENAI_MODEL`
- PostgreSQL credentials

**Deployment Script:**
```bash
./deploy-gcp.sh
```

This script:
1. Builds Docker image for `linux/amd64`
2. Pushes to Google Container Registry
3. Deploys to Cloud Run
4. Sets environment variables

**Service URL:**
```
https://chat-agent-queue-1094852692091.us-central1.run.app
```

---

## Production Readiness

### ✅ Completed Features

- [x] LinkedIn message queueing and sending
- [x] Inbound message handling
- [x] AI response generation
- [x] Calendar integration (discovery, availability, booking)
- [x] Job and conversation AI controls
- [x] Real-time dashboard UI
- [x] Database persistence
- [x] Google Cloud Run deployment
- [x] Error handling and logging
- [x] Webhook security validation

### ⚠️ Needs Work for Production

#### 1. Security
- [ ] **API Authentication**: Add API keys or OAuth for internal endpoints
- [ ] **Webhook Validation**: Verify Unipile webhook signatures
- [ ] **Rate Limiting**: Implement rate limiting on public endpoints
- [ ] **HTTPS Enforcement**: Ensure all traffic uses HTTPS
- [ ] **Environment Variable Encryption**: Use Google Secret Manager

#### 2. Error Handling & Resilience
- [ ] **Retry Logic**: Add exponential backoff for API calls
- [ ] **Dead Letter Queue**: Store failed messages for manual review
- [ ] **Circuit Breakers**: Prevent cascade failures
- [ ] **Alerting**: Set up Cloud Monitoring alerts
- [ ] **Graceful Degradation**: Handle API outages gracefully

#### 3. Scalability
- [ ] **Database Connection Pooling**: Optimize PostgreSQL connections
- [ ] **Horizontal Scaling**: Support multiple Cloud Run instances
- [ ] **Message Queue**: Consider using Cloud Pub/Sub for better scalability
- [ ] **Caching**: Add Redis for frequently accessed data
- [ ] **Load Testing**: Test with high message volumes

#### 4. Monitoring & Observability
- [ ] **Structured Logging**: Add correlation IDs to all logs
- [ ] **Metrics**: Track message send rates, AI response times, errors
- [ ] **Dashboards**: Create custom dashboards in Cloud Monitoring
- [ ] **Distributed Tracing**: Add OpenTelemetry instrumentation
- [ ] **Health Checks**: More comprehensive health endpoints

#### 5. Data Management
- [ ] **Backup Strategy**: Automated PostgreSQL backups
- [ ] **Data Retention**: Implement message/conversation retention policies
- [ ] **GDPR Compliance**: Add data export/deletion endpoints
- [ ] **Audit Logging**: Track all AI-generated messages and decisions
- [ ] **Data Validation**: Stricter input validation on all endpoints

#### 6. Testing
- [ ] **Unit Tests**: Test all service functions
- [ ] **Integration Tests**: Test API endpoints end-to-end
- [ ] **Mock Unipile**: Create test fixtures for Unipile responses
- [ ] **AI Response Testing**: Validate AI output quality
- [ ] **Calendar Integration Tests**: Test booking flow

#### 7. UI/UX Improvements
- [ ] **Message Search**: Add search functionality to dashboard
- [ ] **Filters**: Filter conversations by status, job, AI enabled
- [ ] **Pagination**: Handle large message/conversation lists
- [ ] **Real-time Updates**: WebSocket for live updates
- [ ] **Export**: Export conversation data to CSV/PDF

#### 8. Configuration Management
- [ ] **Feature Flags**: Toggle features without redeployment
- [ ] **A/B Testing**: Test different AI prompts
- [ ] **Custom AI Prompts**: Allow per-job custom prompts
- [ ] **Scheduling Policies**: Configurable delay ranges per job
- [ ] **Business Hours**: Enforce scheduling within business hours

#### 9. Compliance & Ethics
- [ ] **Message Review**: Allow human review before sending AI responses
- [ ] **Consent Tracking**: Track candidate opt-outs
- [ ] **Spam Prevention**: Detect and prevent spam patterns
- [ ] **Fairness Testing**: Ensure AI doesn't bias by demographics
- [ ] **Rate Limits per Candidate**: Prevent message flooding

#### 10. Documentation
- [ ] **API Swagger UI**: Auto-generated API documentation
- [ ] **Runbook**: Step-by-step troubleshooting guide
- [ ] **Architecture Diagrams**: Visual architecture documentation
- [ ] **User Guide**: End-user documentation for recruiters
- [ ] **Developer Guide**: Onboarding guide for new developers

#### 11. Performance Optimization
- [ ] **Database Indexes**: Optimize query performance
- [ ] **API Response Caching**: Cache Supabase queries
- [ ] **Batch Operations**: Batch multiple message sends
- [ ] **Async Processing**: Offload heavy operations to background tasks
- [ ] **CDN**: Serve static assets via CDN

#### 12. Multi-tenancy
- [ ] **Organization Isolation**: Support multiple organizations
- [ ] **Role-Based Access Control**: Different permission levels
- [ ] **Billing Integration**: Track usage per organization
- [ ] **Resource Quotas**: Limit resources per organization

---

## Getting Started

### Prerequisites
- Google Cloud Project
- Supabase account
- Unipile account
- OpenAI API key

### Setup
1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your credentials
3. Run `./deploy-gcp.sh` to deploy to Cloud Run
4. Configure Unipile webhook to point to your service URL
5. Access dashboard at `/dashboard`

### Testing
1. Send initial outreach using `/messages/enqueue`
2. Monitor queue status at `/status/queues`
3. Simulate candidate response via webhook
4. Check dashboard for AI responses and booking status

---

## Support

For issues or questions:
- Check logs in Cloud Run
- Use `/api/v1/internal/test-env` to verify environment variables
- Use `/api/v1/internal/test-supabase` to verify Supabase connection
- Review dashboard at `/dashboard` for system status

---

**Last Updated:** October 27, 2025
**Version:** 1.0.0

