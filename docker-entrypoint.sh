#!/bin/sh
set -e

echo "🚀 Starting FastAPI application with Supabase backend..."

# Switch to non-root user for the application
# Pass all environment variables to the appuser session
su - appuser -c "cd /app && \
export SUPABASE_URL=\"$SUPABASE_URL\" && \
export SUPABASE_KEY=\"$SUPABASE_KEY\" && \
export SUPABASE_SERVICE_ROLE_KEY=\"$SUPABASE_SERVICE_ROLE_KEY\" && \
export ENVIRONMENT=\"$ENVIRONMENT\" && \
export UNIPILE_API_DNS=\"$UNIPILE_API_DNS\" && \
export UNIPILE_API_KEY=\"$UNIPILE_API_KEY\" && \
export OPENAI_API_KEY=\"$OPENAI_API_KEY\" && \
export OPENAI_MODEL=\"$OPENAI_MODEL\" && \
export DEFAULT_MIN_DELAY_MINUTES=\"$DEFAULT_MIN_DELAY_MINUTES\" && \
export DEFAULT_MAX_DELAY_MINUTES=\"$DEFAULT_MAX_DELAY_MINUTES\" && \
export MAX_RETRY_ATTEMPTS=\"$MAX_RETRY_ATTEMPTS\" && \
export LOG_LEVEL=\"$LOG_LEVEL\" && \
/opt/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"
