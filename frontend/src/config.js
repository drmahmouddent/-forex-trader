// API Configuration
// Update this URL after deploying backend to Cloud Run

const config = {
  // Replace with your Cloud Run URL after deployment
  API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',
  WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api/ws',
}

export default config
