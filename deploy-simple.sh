#!/bin/bash

# Simple deployment script using Docker and Google Cloud Console
# This script builds and tags the image for Google Container Registry

set -e

echo "🚀 Deploying Chat Agent Queue to Google Cloud"

# Get project ID (you'll need to set this manually if gcloud is broken)
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"your-project-id"}
echo "📋 Using Project ID: $PROJECT_ID"

# Build the image
echo "🏗️ Building Docker image..."
docker build -f Dockerfile.gcp -t chat-agent-queue .

# Tag for Google Container Registry
echo "🏷️ Tagging image for GCR..."
docker tag chat-agent-queue gcr.io/$PROJECT_ID/chat-agent-queue

echo "✅ Image built and tagged successfully!"
echo ""
echo "📝 Next steps:"
echo "1. Configure Docker to use gcloud as a credential helper:"
echo "   gcloud auth configure-docker"
echo ""
echo "2. Push the image to Google Container Registry:"
echo "   docker push gcr.io/$PROJECT_ID/chat-agent-queue"
echo ""
echo "3. Deploy to Cloud Run using the Google Cloud Console:"
echo "   https://console.cloud.google.com/run"
echo ""
echo "   Or use this gcloud command (if gcloud is working):"
echo "   gcloud run deploy chat-agent-queue \\"
echo "     --image gcr.io/$PROJECT_ID/chat-agent-queue \\"
echo "     --region us-central1 \\"
echo "     --platform managed \\"
echo "     --allow-unauthenticated \\"
echo "     --port 8000 \\"
echo "     --memory 4Gi \\"
echo "     --cpu 2 \\"
echo "     --max-instances 10 \\"
echo "     --timeout 3600"
echo ""
echo "4. Set environment variables in Cloud Run console or via gcloud"


