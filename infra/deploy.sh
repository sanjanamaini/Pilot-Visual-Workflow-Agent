#!/bin/bash
set -euo pipefail

# Pilot — One-command deployment script
# Usage: ./deploy.sh <PROJECT_ID> [REGION]

PROJECT_ID="${1:?Usage: ./deploy.sh <PROJECT_ID> [REGION]}"
REGION="${2:-us-central1}"

echo "🚀 Deploying Pilot to project: $PROJECT_ID (region: $REGION)"

# Enable required APIs
echo "📦 Enabling Google Cloud APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  firestore.googleapis.com \
  cloudbuild.googleapis.com \
  --project="$PROJECT_ID"

# Create Artifact Registry repo (if not exists)
echo "📦 Setting up Artifact Registry..."
gcloud artifacts repositories create pilot \
  --repository-format=docker \
  --location="$REGION" \
  --project="$PROJECT_ID" 2>/dev/null || true

# Build and push
echo "🔨 Building Docker image..."
cd "$(dirname "$0")/../backend"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/pilot/backend:latest"
gcloud builds submit --tag="$IMAGE" --project="$PROJECT_ID"

# Deploy to Cloud Run
echo "🌐 Deploying to Cloud Run..."
gcloud run deploy pilot-backend \
  --image="$IMAGE" \
  --region="$REGION" \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="GOOGLE_API_KEY=$(gcloud secrets versions access latest --secret=pilot-gemini-key --project=$PROJECT_ID 2>/dev/null || echo 'SET_ME')" \
  --project="$PROJECT_ID"

echo ""
echo "✅ Pilot deployed!"
echo "🔗 Backend URL:"
gcloud run services describe pilot-backend --region="$REGION" --project="$PROJECT_ID" --format='get(status.url)'
