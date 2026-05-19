#!/bin/bash

# Forex Trader Deployment Script
# This script deploys the frontend to Firebase Hosting and backend to Google Cloud Run

set -e

echo "=========================================="
echo "  Forex Trader Deployment Script"
echo "=========================================="

# Check if Firebase CLI is installed
if ! command -v firebase &> /dev/null; then
    echo "Error: Firebase CLI not found. Install it with:"
    echo "  npm install -g firebase-tools"
    exit 1
fi

# Check if gcloud CLI is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: Google Cloud SDK not found. Install it from:"
    echo "  https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Step 1: Build frontend
echo ""
echo "Step 1: Building frontend..."
cd frontend
npm install
npm run build
cd ..
echo "Frontend built successfully!"

# Step 2: Deploy backend to Cloud Run
echo ""
echo "Step 2: Deploying backend to Google Cloud Run..."
gcloud run deploy forex-backend \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 2 \
    --set-env-vars "LOG_LEVEL=INFO"

# Get the Cloud Run URL
BACKEND_URL=$(gcloud run services describe forex-backend --region us-central1 --format='value(status.url)')
echo "Backend deployed to: $BACKEND_URL"

# Step 3: Update frontend with backend URL
echo ""
echo "Step 3: Updating frontend API URL..."
echo "Please update the API_URL in your frontend pages to:"
echo "  $BACKEND_URL/api"

# Step 4: Deploy frontend to Firebase Hosting
echo ""
echo "Step 4: Deploying frontend to Firebase Hosting..."
firebase deploy --only hosting

echo ""
echo "=========================================="
echo "  Deployment Complete!"
echo "=========================================="
echo ""
echo "Your app is live at:"
echo "  https://YOUR_FIREBASE_PROJECT_ID.web.app"
echo ""
echo "Backend API at:"
echo "  $BACKEND_URL"
echo ""
echo "IMPORTANT: Update API_URL in frontend pages to:"
echo "  $BACKEND_URL/api"
echo ""
