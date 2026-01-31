# Marketing Agent v2 - Getting Started

This guide will help you get the Marketing Agent platform up and running for testing.

## Prerequisites

- **Node.js** >= 18.0.0
- **Python** >= 3.9
- **npm** or **yarn**
- **pip**

## Quick Start

### Option 1: Using the startup script (recommended)

```bash
chmod +x start-dev.sh
./start-dev.sh
```

This will:
1. Create a Python virtual environment
2. Install all Python dependencies
3. Install all Node.js dependencies
4. Start both backend and frontend servers

### Option 2: Manual Setup

#### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start the frontend
npm run dev
```

## Accessing the Application

Once both services are running:

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3000 |
| **Backend API** | http://localhost:8000 |
| **API Docs** | http://localhost:8000/docs |
| **Health Check** | http://localhost:8000/health |

## Environment Configuration

### Backend (.env)

The backend is pre-configured with API keys for:
- **OpenRouter** - LLM access (Claude, GPT-4)
- **Firecrawl** - Web scraping
- **Perplexity** - Research/search
- **Segmind** - Image generation
- **ElevenLabs** - Voice generation
- **xAI** - Video analysis

### Frontend (.env.development)

Pre-configured to proxy API calls to the backend on port 8000.

## First Login

1. Navigate to http://localhost:3000
2. Register a new account (or use existing test credentials)
3. Complete the onboarding flow with your company domain
4. Start creating campaigns!

## Key Features to Test

### 1. AI Chat (Dashboard → Chat)
- Chat with the AI about your marketing needs
- Launch campaigns through conversation

### 2. Campaign Studio (Dashboard → Campaigns)
- Create new campaigns
- Execute campaign workflow
- View generated assets

### 3. Kata Lab (Sidebar → Kata Lab)
- AI video creation studio
- Synthetic influencer generation
- Product compositing

### 4. TrendMaster (Dashboard → TrendMaster)
- Discover trending topics
- Create content from trends

### 5. Content Calendar (Dashboard → Calendar)
- Schedule social media posts
- Drag-and-drop rescheduling

### 6. Kanban Board (Dashboard → Workflow)
- Manage marketing tasks
- Track campaign progress

### 7. Analytics (Dashboard → Analytics)
- View performance metrics
- Campaign analytics

### 8. Image Editor (Dashboard → Image Editor)
- AI-powered image editing
- Conversational interface

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│                    (React + Vite + Tailwind)                 │
│                       Port: 3000                             │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP/WebSocket
                            │ /api/* proxied
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                         Backend                              │
│                  (FastAPI + SQLAlchemy)                      │
│                       Port: 8000                             │
├─────────────────────────────────────────────────────────────┤
│  Services:                                                   │
│  • AI/LLM (OpenRouter, Anthropic)                           │
│  • Content Generation                                        │
│  • Campaign Orchestration                                    │
│  • CDP (Customer Data Platform)                             │
│  • Analytics & Attribution                                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                        Database                              │
│               SQLite (dev) / PostgreSQL (prod)              │
└─────────────────────────────────────────────────────────────┘
```

## Troubleshooting

### Backend won't start

1. Check Python version: `python3 --version`
2. Ensure virtual environment is activated
3. Check for missing dependencies: `pip install -r requirements.txt`
4. Check the `.env` file exists in `/backend`

### Frontend won't build

1. Check Node version: `node --version`
2. Clear npm cache: `npm cache clean --force`
3. Delete node_modules and reinstall:
   ```bash
   rm -rf node_modules
   npm install
   ```

### API Connection Failed

1. Ensure backend is running on port 8000
2. Check CORS settings in backend config
3. Verify frontend environment points to correct API URL

### Database Issues

The database auto-creates on first startup. To reset:
```bash
rm backend/data.db
# Restart the backend
```

## Development Tips

- **Hot Reload**: Both frontend and backend support hot reload
- **API Docs**: Use http://localhost:8000/docs for interactive API testing
- **Debug Mode**: Set `DEBUG=true` in backend `.env` for verbose logging

## Production Deployment

For production deployment on Railway:
1. Set `ENVIRONMENT=production`
2. Configure PostgreSQL database URL
3. Set a secure `SECRET_KEY`
4. Update `CORS_ORIGINS` with your domain

See `backend/railway.toml` for deployment configuration.
