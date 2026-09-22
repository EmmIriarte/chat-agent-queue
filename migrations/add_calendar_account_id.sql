-- Migration: Add calendar account support
-- Date: 2025-10-15
-- Purpose: Add calendar_account_id to support separate Unipile accounts for LinkedIn vs Outlook/Google

-- Add calendar_account_id column (Outlook/Google Unipile account ID)
ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS calendar_account_id VARCHAR(255);

-- Add calendar_id column (cached calendar ID from Unipile Calendar API)
ALTER TABLE conversations 
ADD COLUMN IF NOT EXISTS calendar_id VARCHAR(255);

-- Add index for calendar account lookups
CREATE INDEX IF NOT EXISTS idx_conversations_calendar_account 
ON conversations(calendar_account_id);

-- Add comments for clarity
COMMENT ON COLUMN conversations.unipile_account_id IS 'LinkedIn Unipile account ID (used for messaging)';
COMMENT ON COLUMN conversations.calendar_account_id IS 'Outlook/Google Unipile account ID (used for calendar operations) - OPTIONAL';
COMMENT ON COLUMN conversations.calendar_id IS 'Cached calendar ID from Unipile Calendar API - discovered on first use';

-- Note: These are SEPARATE account IDs in Unipile:
-- - unipile_account_id = LinkedIn account (for sending messages)
-- - calendar_account_id = Outlook/Google account (for creating calendar events)
-- Frontend must link these accounts and pass both when creating conversations



