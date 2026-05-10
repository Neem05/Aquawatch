#!/bin/bash

# Build and deploy to Cloud Run
PROJECT_ID="cloud-project-74451"
SERVICE_NAME="aquawatch-api"
REGION="us-central1"

# Get endpoint ID from Vertex AI
ENDPOINT_ID=$(cat ../vertex_ai/endpoint_id.txt)

echo "🚀 Deploying AquaWatch API to Cloud Run..."
echo "Endpoint ID: $ENDPOINT_ID"

# Build container
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 3 \
  --allow-unauthenticated \
  --set-env-vars "PROJECT_ID=$PROJECT_ID,ENDPOINT_ID=$ENDPOINT_ID,LOCATION=$REGION"

echo "✅ Deployment complete!"
echo "📡 API URL: https://$SERVICE_NAME-xxx-uc.a.run.app"