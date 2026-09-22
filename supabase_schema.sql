-- SQL script to create tables in Supabase
-- Run this in your Supabase SQL Editor

-- Step 1: Create function to update conversation timestamp
CREATE OR REPLACE FUNCTION update_conversation_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    UPDATE conversations 
    SET updated_at = NOW() 
    WHERE chat_id = NEW.chat_id;
    RETURN NEW;
END;
$$;

-- Step 2: Create conversations table FIRST (referenced by foreign key)
CREATE TABLE IF NOT EXISTS conversations (
    chat_id uuid NOT NULL,
    sender_linkedin_id character varying(255) NOT NULL,
    recipient_linkedin_id character varying(255) NOT NULL,
    unipile_account_id character varying(255) NOT NULL,
    calendar_account_id character varying(255),
    calendar_id character varying(255),
    job_id character varying(255) NOT NULL,
    stage character varying(50) DEFAULT 'initial_outreach'::character varying NOT NULL,
    ai_enabled boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT conversations_pkey PRIMARY KEY (chat_id),
    CONSTRAINT unique_conversation UNIQUE (sender_linkedin_id, recipient_linkedin_id)
);

-- Step 3: Create messages table AFTER conversations exists (order matters for foreign key)
CREATE TABLE IF NOT EXISTS messages (
    message_id uuid NOT NULL,
    chat_id uuid NOT NULL,
    sender_linkedin_id character varying(255) NOT NULL,
    recipient_linkedin_id character varying(255) NOT NULL,
    unipile_account_id character varying(255) NOT NULL,
    job_id character varying(255) NOT NULL,
    message text NOT NULL,
    direction character varying(20) NOT NULL,
    message_type character varying(20) DEFAULT 'message'::character varying NOT NULL,
    is_initial_reachout boolean DEFAULT false NOT NULL,
    status character varying(20),
    scheduled_at timestamp without time zone,
    retry_count integer DEFAULT 0,
    error_message text,
    conversation_stage character varying(50),
    has_attachment boolean DEFAULT false,
    attachment_info text,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    sent_at timestamp without time zone,
    CONSTRAINT messages_pkey PRIMARY KEY (message_id),
    CONSTRAINT messages_direction_check CHECK (((direction)::text = ANY ((ARRAY['outbound'::character varying, 'inbound'::character varying])::text[]))),
    CONSTRAINT messages_message_type_check CHECK (((message_type)::text = ANY ((ARRAY['message'::character varying, 'invite'::character varying])::text[]))),
    CONSTRAINT messages_status_check CHECK (((status)::text = ANY ((ARRAY['scheduled'::character varying, 'sending'::character varying, 'sent'::character varying, 'cancelled'::character varying, 'error'::character varying, 'history'::character varying])::text[]))),
    CONSTRAINT messages_chat_id_fkey FOREIGN KEY (chat_id) REFERENCES conversations(chat_id) ON DELETE CASCADE
);

-- Step 4: Create job_settings table
CREATE TABLE IF NOT EXISTS job_settings (
    job_id character varying(255) NOT NULL,
    ai_enabled boolean DEFAULT true NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    CONSTRAINT job_settings_pkey PRIMARY KEY (job_id)
);

-- Step 5: Create indexes for conversations
CREATE INDEX IF NOT EXISTS idx_conversations_account ON conversations (unipile_account_id);
CREATE INDEX IF NOT EXISTS idx_conversations_job ON conversations (job_id);
CREATE INDEX IF NOT EXISTS idx_conversations_sender_recipient ON conversations (sender_linkedin_id, recipient_linkedin_id);

-- Step 6: Create indexes for messages
CREATE INDEX IF NOT EXISTS idx_messages_account ON messages (unipile_account_id);
CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages (chat_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages (created_at);
CREATE INDEX IF NOT EXISTS idx_messages_direction ON messages (direction);
CREATE INDEX IF NOT EXISTS idx_messages_job ON messages (job_id);
CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages (recipient_linkedin_id);
CREATE INDEX IF NOT EXISTS idx_messages_scheduled ON messages (scheduled_at) WHERE scheduled_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages (sender_linkedin_id);
CREATE INDEX IF NOT EXISTS idx_messages_status ON messages (status) WHERE status IS NOT NULL;

-- Step 7: Create trigger to update conversation timestamp (requires tables to exist)
DROP TRIGGER IF EXISTS trigger_update_conversation_timestamp ON messages;
CREATE TRIGGER trigger_update_conversation_timestamp 
    AFTER INSERT ON messages 
    FOR EACH ROW 
    EXECUTE FUNCTION update_conversation_timestamp();

-- Step 8: Create views
CREATE OR REPLACE VIEW active_queue AS
 SELECT m.message_id,
    m.chat_id,
    m.sender_linkedin_id,
    m.recipient_linkedin_id,
    m.unipile_account_id,
    m.job_id,
    m.message,
    m.direction,
    m.message_type,
    m.is_initial_reachout,
    m.status,
    m.scheduled_at,
    m.retry_count,
    m.error_message,
    m.conversation_stage,
    m.has_attachment,
    m.attachment_info,
    m.created_at,
    m.sent_at,
    c.stage AS current_conversation_stage
   FROM messages m
     JOIN conversations c ON m.chat_id = c.chat_id
  WHERE m.status IN ('scheduled', 'sending')
  ORDER BY m.scheduled_at;

CREATE OR REPLACE VIEW conversation_messages AS
 SELECT m.message_id,
    m.chat_id,
    m.sender_linkedin_id,
    m.recipient_linkedin_id,
    m.unipile_account_id,
    m.job_id,
    m.message,
    m.direction,
    m.message_type,
    m.is_initial_reachout,
    m.status,
    m.scheduled_at,
    m.retry_count,
    m.error_message,
    m.conversation_stage,
    m.has_attachment,
    m.attachment_info,
    m.created_at,
    m.sent_at,
    c.stage AS current_conversation_stage
   FROM messages m
     JOIN conversations c ON m.chat_id = c.chat_id
  ORDER BY m.created_at;

CREATE OR REPLACE VIEW conversation_summary AS
 SELECT c.chat_id,
    c.sender_linkedin_id,
    c.recipient_linkedin_id,
    c.unipile_account_id,
    c.job_id,
    c.stage,
    c.created_at,
    c.updated_at,
    count(m.message_id) AS message_count,
    max(m.created_at) AS last_message_at,
    ( SELECT m2.message
           FROM messages m2
          WHERE m2.chat_id = c.chat_id
          ORDER BY m2.created_at DESC
         LIMIT 1) AS last_message_preview
   FROM conversations c
     LEFT JOIN messages m ON c.chat_id = m.chat_id
  GROUP BY c.chat_id
  ORDER BY max(m.created_at) DESC NULLS LAST;

