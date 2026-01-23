# MOSTRO Deployment Guide

## Quick Deploy Options

### Option 1: Render (Easiest - One Click Deploy)

1. **Push to GitHub** (if not already):
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin YOUR_GITHUB_REPO_URL
   git push -u origin main
   ```

2. **Deploy on Render**:
   - Go to https://render.com
   - Click "New" → "Blueprint"
   - Connect your GitHub repo
   - Render will auto-detect `render.yaml` and deploy all services
   - Add environment variables in Render dashboard:
     - `MONGODB_URI`: Your MongoDB connection string
     - `GEMINI_API_KEY`: Your Gemini API key

3. **Done!** Render will provide URLs for all services.

---

### Option 2: Vercel (Frontend) + Render (Backend)

**Frontend on Vercel:**
1. Go to https://vercel.com
2. Import your GitHub repo
3. Set root directory to `frontend`
4. Add environment variable:
   - `VITE_API_URL`: Your Render backend URL (after deploying backend)
5. Deploy

**Backend on Render:**
1. Go to https://render.com
2. New → Web Service
3. Connect repo, select `backend` folder
4. Build: `npm install`
5. Start: `npm start`
6. Add environment variables

**Agent Service on Render:**
1. New → Web Service
2. Select `agent-service` folder
3. Runtime: Python
4. Build: `pip install -r requirements.txt`
5. Start: `uvicorn main:app --host 0.0.0.0 --port 8000`
6. Add `GEMINI_API_KEY`

---

### Option 3: Railway (All Services)

1. Go to https://railway.app
2. New Project → Deploy from GitHub
3. Add three services:
   - Backend (Node.js)
   - Agent Service (Python)
   - Frontend (Static Site)
4. Railway auto-detects Dockerfiles
5. Add environment variables in each service
6. Deploy

---

### Option 4: Docker Compose (Self-Hosted)

Create `docker-compose.yml` in root:

```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "5000:5000"
    environment:
      - MONGODB_URI=${MONGODB_URI}
      - AGENT_SERVICE_URL=http://agent-service:8000
      - NODE_ENV=production
  
  agent-service:
    build: ./agent-service
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
  
  frontend:
    build: ./frontend
    ports:
      - "80:80"
    environment:
      - VITE_API_URL=http://backend:5000
```

Run: `docker-compose up -d`

---

## Environment Variables Needed

### Backend
- `MONGODB_URI`: mongodb+srv://...
- `AGENT_SERVICE_URL`: URL of agent service
- `NODE_ENV`: production
- `PORT`: 5000

### Agent Service
- `GEMINI_API_KEY`: Your API key

### Frontend
- `VITE_API_URL`: URL of backend service

---

## Post-Deployment Checklist

- [ ] Update CORS settings in backend if needed
- [ ] Test all API endpoints
- [ ] Verify MongoDB connection
- [ ] Check agent service connectivity
- [ ] Test frontend → backend → agent flow
- [ ] Set up custom domain (optional)
- [ ] Enable HTTPS (most platforms do this automatically)

---

## Recommended: Render Blueprint Deploy

The `render.yaml` file is already configured. Just:
1. Push to GitHub
2. Connect to Render
3. Add secrets
4. Deploy!

All services will be connected automatically.
