# Airbot Deployment Guide

## 1) Backend (Railway)

This repo already includes Railway config in [backend/railway.json](backend/railway.json).

### Create Railway service
1. In Railway, create a new project from your GitHub repo.
2. Set **Root Directory** to `backend`.
3. Railway will use `Dockerfile` build + `uvicorn` start command from `railway.json`.

### Required Railway environment variables
Set these in Railway service variables:

- `SECRET_KEY` = strong random value
- `ALGORITHM` = `HS256`
- `ACCESS_TOKEN_EXPIRE_MINUTES` = `1440`
- `LLM_PROVIDER` = `cloud`
- `GROQ_API_KEY` = your key
- `GROQ_MODEL_TEST_CASE` = `llama-3.3-70b-versatile`
- `GROQ_MODEL_GENERAL_CHAT` = `llama-3.1-8b-instant`
- `GOOGLE_CLIENT_ID` = your Google OAuth client id
- `GOOGLE_CLIENT_SECRET` = your Google OAuth client secret
- `BACKEND_URL` = your Railway public URL (for example `https://your-backend.up.railway.app`)
- `FRONTEND_URL` = your frontend public URL (for example `https://your-frontend.netlify.app`)

### Health check
- Health endpoint: `/health/`

## 2) Google OAuth setup
In Google Cloud Console OAuth client settings, add:

### Authorized JavaScript origins
- your frontend URL
- `http://localhost:5500` (for local testing)

### Authorized redirect URIs
- `https://<your-backend-domain>/auth/callback`
- `http://localhost:8000/auth/callback` (for local testing)

## 3) Frontend (static host: Netlify/Vercel/GitHub Pages)

The frontend now supports runtime backend URL via `frontend/js/config.js`.

Edit [frontend/js/config.js](frontend/js/config.js):

```js
window.AIRBOT_API_BASE_URL = 'https://<your-backend-domain>';
```

Then deploy the `frontend` folder as a static site.

## 4) Local fallback behavior
- Localhost frontend automatically uses `http://localhost:8000`.
- Non-local deployments use the value from `frontend/js/config.js`.

## 5) Post-deploy smoke tests
1. Open frontend URL.
2. Click **Sign In** (Google OAuth should redirect back to frontend success page).
3. Test `/chat/` prompt in UI.
4. Test test-case generation and Excel download flow.

## 6) Security follow-up (important)
If any real API keys/secrets were committed to Git, rotate them before production use.
