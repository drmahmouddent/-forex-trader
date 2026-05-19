# Forex Trader - Deployment Instructions

## Your App Info
- **Firebase Project:** forex-trader-db449
- **Frontend URL:** https://forex-trader-db449.web.app
- **Email:** mahmoudabdelall18@gmail.com

## Step 1: Deploy Backend to Google Cloud Run

### Option A: Using Google Cloud Console (Easiest)

1. Go to https://console.cloud.google.com/run
2. Make sure project `forex-trader-db449` is selected
3. Click **"Create Service"**
4. Choose **"Continuously deploy from a repository"**
5. Connect your GitHub repo or upload files

### Option B: Using Google Cloud Shell

1. Go to https://console.cloud.google.com
2. Click the **Cloud Shell** icon (top right, looks like `>_`)
3. Run these commands:

```bash
# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# Set project
gcloud config set project forex-trader-db449

# Create a storage bucket for source code
gsutil mb gs://forex-trader-db449-source

# Upload source code
cd /tmp
# You'll need to upload the forex-trader folder here

# Deploy
gcloud run deploy forex-backend \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 512Mi
```

### Option C: Install gcloud CLI on Your PC

1. Download from: https://cloud.google.com/sdk/docs/install
2. Run the installer
3. Open a NEW terminal and run:

```bash
gcloud auth login
gcloud config set project forex-trader-db449
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

cd D:\openclaude-workspace\forex-trader
gcloud run deploy forex-backend --source . --region us-central1 --allow-unauthenticated
```

## Step 2: Update Frontend with Backend URL

After backend deploys, you'll get a URL like:
`https://forex-backend-xxxxx-uc.a.run.app`

1. Edit `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=https://forex-backend-xxxxx-uc.a.run.app/api
NEXT_PUBLIC_WS_URL=wss://forex-backend-xxxxx-uc.a.run.app/api/ws
```

2. Rebuild and redeploy frontend:
```bash
cd frontend
npm run build
cd ..
firebase deploy --only hosting
```

## Step 3: Setup MT5 Bridge (Your Windows PC)

1. Open MetaTrader 5 and login to your trading account

2. Open terminal in `mt5-bridge` folder and run:
```bash
pip install -r requirements.txt
python bridge.py
```

3. Download ngrok from https://ngrok.com/download

4. In another terminal:
```bash
ngrok http 5000
```

5. Copy the ngrok URL (e.g., `https://abc123.ngrok.io`)

6. Update Cloud Run environment:
```bash
gcloud run services update forex-backend \
    --region us-central1 \
    --set-env-vars MT5_BRIDGE_URL=https://abc123.ngrok.io
```

## Step 4: Start Trading!

1. Open https://forex-trader-db449.web.app
2. Make sure MT5 bridge is running on your PC
3. Click "Start Bot" on the dashboard

## Troubleshooting

- **Frontend shows no data:** Check backend URL in `.env.local`
- **MT5 not connecting:** Make sure MT5 is running and bridge is started
- **Trades not executing:** Check ngrok URL is updated in Cloud Run

## Support

Your app is at: https://forex-trader-db449.web.app
