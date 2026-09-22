#!/bin/bash

# GCP Deployment Script for Chat Agent Queue System
# This script sets up the entire infrastructure and deploys the application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting GCP Deployment for Chat Agent Queue System${NC}"

# Check if gcloud is installed and authenticated
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}❌ You are not authenticated with gcloud. Please run 'gcloud auth login' first.${NC}"
    exit 1
fi

# Get current project
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ No project selected. Please run 'gcloud config set project YOUR_PROJECT_ID'${NC}"
    exit 1
fi

echo -e "${GREEN}📋 Using project: ${PROJECT_ID}${NC}"

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required Google Cloud APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Create Cloud SQL instance
echo -e "${YELLOW}🗄️  Creating Cloud SQL PostgreSQL instance...${NC}"
gcloud sql instances create chat-agent-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --storage-type=SSD \
    --storage-size=10GB \
    --backup-start-time=03:00 \
    --enable-ip-alias \
    --authorized-networks=0.0.0.0/0

# Create database
echo -e "${YELLOW}📊 Creating database...${NC}"
gcloud sql databases create chat_agent_queue --instance=chat-agent-db

# Create database user
echo -e "${YELLOW}👤 Creating database user...${NC}"
DB_PASSWORD=$(openssl rand -base64 32)
gcloud sql users create postgres \
    --instance=chat-agent-db \
    --password="$DB_PASSWORD"

# Store password in Secret Manager
echo -e "${YELLOW}🔐 Storing database password in Secret Manager...${NC}"
echo -n "$DB_PASSWORD" | gcloud secrets create postgres-password --data-file=-

# Get Cloud SQL connection name
CONNECTION_NAME=$(gcloud sql instances describe chat-agent-db --format="value(connectionName)")

# Update cloudbuild.yaml with actual values
echo -e "${YELLOW}📝 Updating deployment configuration...${NC}"
sed -i.bak "s/your-cloud-sql-connection-name/$CONNECTION_NAME/g" cloudbuild.yaml

# Build and deploy
echo -e "${YELLOW}🏗️  Building and deploying application...${NC}"
gcloud builds submit --config cloudbuild.yaml

# Get the service URL
SERVICE_URL=$(gcloud run services describe chat-agent-queue --region=us-central1 --format="value(status.url)")

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 Service URL: ${SERVICE_URL}${NC}"
echo -e "${GREEN}📊 Database connection: ${CONNECTION_NAME}${NC}"
echo -e "${GREEN}🔑 Database password stored in Secret Manager${NC}"

echo -e "${YELLOW}📋 Next steps:${NC}"
echo -e "1. Update your environment variables in the Cloud Run service"
echo -e "2. Test the health endpoint: ${SERVICE_URL}/health"
echo -e "3. Test the dashboard: ${SERVICE_URL}/dashboard/"
echo -e "4. Configure your webhook URLs in Unipile"

echo -e "${GREEN}🎉 Your Chat Agent Queue System is now running on Google Cloud!${NC}"


