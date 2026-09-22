#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"

echo "🚀 Deploying Chat Agent Queue to Google Cloud Project: $PROJECT_ID in region: $REGION"

# 1. Enable necessary APIs
echo "📋 Enabling Google Cloud APIs..."
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# 2. Load environment variables from .env file
echo "🔧 Loading environment variables from .env file..."
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    exit 1
fi

# Source the .env file
export $(grep -v '^#' .env | xargs)

# 3. Deploy to Cloud Run using Cloud Build
echo "🏗️ Submitting Cloud Build job to deploy to Cloud Run..."
gcloud builds submit \
  --project=$PROJECT_ID \
  --config cloudbuild.yaml \
  --substitutions=\
_SUPABASE_URL=$SUPABASE_URL,\
_SUPABASE_KEY=$SUPABASE_KEY,\
_SUPABASE_SERVICE_ROLE_KEY=$SUPABASE_SERVICE_ROLE_KEY,\
_UNIPILE_API_DNS=$UNIPILE_API_DNS,\
_UNIPILE_API_KEY=$UNIPILE_API_KEY,\
_OPENAI_API_KEY=$OPENAI_API_KEY,\
_OPENAI_MODEL=$OPENAI_MODEL,\
_DEFAULT_MIN_DELAY_MINUTES=$DEFAULT_MIN_DELAY_MINUTES,\
_DEFAULT_MAX_DELAY_MINUTES=$DEFAULT_MAX_DELAY_MINUTES,\
_MAX_RETRY_ATTEMPTS=$MAX_RETRY_ATTEMPTS,\
_LOG_LEVEL=$LOG_LEVEL

echo "✅ Deployment initiated. Check Cloud Build and Cloud Run for status."
echo "🌐 Once deployed, your service will be available at:"
echo "   https://chat-agent-queue-[hash]-uc.a.run.app"
echo ""
echo "📝 Next steps:"
echo "   1. Update your environment variables in this script with real values"
echo "   2. Configure your Unipile webhook to point to the deployed URL"
echo "   3. Test the system with the dashboard at /dashboard"
