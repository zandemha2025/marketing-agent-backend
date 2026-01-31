# Production Deployment Checklist

**Application:** Marketing Agent v2.0.0  
**Last Updated:** 2026-01-30  
**Target Platforms:** Railway (Backend), Vercel (Frontend)

---

## Table of Contents

1. [Pre-Deployment Requirements](#1-pre-deployment-requirements)
2. [Environment Configuration](#2-environment-configuration)
3. [Infrastructure Setup](#3-infrastructure-setup)
4. [Database Setup](#4-database-setup)
5. [Backend Deployment](#5-backend-deployment)
6. [Frontend Deployment](#6-frontend-deployment)
7. [Post-Deployment Verification](#7-post-deployment-verification)
8. [Monitoring & Alerting](#8-monitoring--alerting)
9. [Rollback Procedures](#9-rollback-procedures)

---

## 1. Pre-Deployment Requirements

### 1.1 Code Readiness

```
[ ] All tests passing (backend + frontend)
[ ] Security audit completed and critical issues resolved
[ ] Code reviewed and approved
[ ] Version tagged in git (e.g., v2.0.0)
[ ] CHANGELOG updated
[ ] No console.log/print statements in production code
```

### 1.2 Required Accounts & Access

| Service | Purpose | Required |
|---------|---------|----------|
| Railway | Backend hosting | ✅ |
| Vercel | Frontend hosting | ✅ |
| PostgreSQL | Database (Railway addon) | ✅ |
| OpenRouter | LLM API access | ✅ |
| Firecrawl | Web scraping | ✅ |
| Perplexity | Research API | ✅ |
| Segmind | Image generation | Optional |
| ElevenLabs | Voice generation | Optional |
| AWS S3 | Asset storage | Optional |
| Convex | Real-time sync | Optional |

### 1.3 API Keys to Obtain

```bash
# Required
OPENROUTER_API_KEY=     # https://openrouter.ai/keys
FIRECRAWL_API_KEY=      # https://firecrawl.dev/
PERPLEXITY_API_KEY=     # https://perplexity.ai/settings/api

# Optional (for full functionality)
SEGMIND_API_KEY=        # https://segmind.com/
ELEVENLABS_API_KEY=     # https://elevenlabs.io/
AWS_ACCESS_KEY_ID=      # AWS Console
AWS_SECRET_ACCESS_KEY=  # AWS Console
CONVEX_DEPLOY_KEY=      # Convex Dashboard
```

---

## 2. Environment Configuration

### 2.1 Backend Environment Variables

Create these in Railway dashboard under Variables:

```bash
# Application
APP_NAME="Marketing Agent"
DEBUG=false
ENVIRONMENT=production

# Database (auto-populated by Railway PostgreSQL addon)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Security - CRITICAL
SECRET_KEY=<generate-with-command-below>

# API Keys
OPENROUTER_API_KEY=<your-key>
FIRECRAWL_API_KEY=<your-key>
PERPLEXITY_API_KEY=<your-key>
SEGMIND_API_KEY=<your-key>
ELEVENLABS_API_KEY=<your-key>

# AWS S3 (if using)
AWS_ACCESS_KEY_ID=<your-key>
AWS_SECRET_ACCESS_KEY=<your-secret>
AWS_REGION=us-east-1
S3_BUCKET_NAME=<your-bucket>

# CORS - Update with your actual domains
CORS_ORIGINS=https://your-app.vercel.app,https://your-custom-domain.com

# Convex (if using)
CONVEX_URL=https://your-deployment.convex.cloud
CONVEX_DEPLOY_KEY=<your-key>
```

**Generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2.2 Frontend Environment Variables

Create in Vercel dashboard under Environment Variables:

```bash
# API URL - Point to your Railway backend
VITE_API_URL=https://your-backend.railway.app
```

### 2.3 Environment Variable Checklist

```
[ ] SECRET_KEY is unique, 32+ characters
[ ] DEBUG=false
[ ] ENVIRONMENT=production
[ ] DATABASE_URL points to production PostgreSQL
[ ] All required API keys set
[ ] CORS_ORIGINS contains only production domains
[ ] No development URLs in production config
```

---

## 3. Infrastructure Setup

### 3.1 Railway Setup (Backend)

1. **Create New Project**
   ```
   [ ] Log into Railway dashboard
   [ ] Click "New Project"
   [ ] Select "Deploy from GitHub repo"
   [ ] Connect your repository
   [ ] Select the backend directory as root
   ```

2. **Add PostgreSQL**
   ```
   [ ] Click "New" → "Database" → "PostgreSQL"
   [ ] Note: DATABASE_URL is auto-injected
   ```

3. **Configure Service**
   ```
   [ ] Set root directory to "backend"
   [ ] Verify railway.toml is detected
   [ ] Add all environment variables
   [ ] Set custom domain (optional)
   ```

4. **Resource Allocation**
   ```
   [ ] Minimum: 512MB RAM, 0.5 vCPU
   [ ] Recommended: 1GB RAM, 1 vCPU
   [ ] Enable auto-scaling if available
   ```

### 3.2 Vercel Setup (Frontend)

1. **Import Project**
   ```
   [ ] Log into Vercel dashboard
   [ ] Click "Add New" → "Project"
   [ ] Import from GitHub
   [ ] Select repository
   ```

2. **Configure Build**
   ```
   [ ] Framework Preset: Vite
   [ ] Root Directory: frontend
   [ ] Build Command: npm run build
   [ ] Output Directory: dist
   ```

3. **Environment Variables**
   ```
   [ ] Add VITE_API_URL pointing to Railway backend
   [ ] Set for Production environment
   ```

4. **Domain Configuration**
   ```
   [ ] Add custom domain (optional)
   [ ] Configure SSL (automatic)
   ```

### 3.3 S3 Setup (Optional - Asset Storage)

```
[ ] Create S3 bucket with unique name
[ ] Configure bucket policy for public read (if needed)
[ ] Set up CORS configuration
[ ] Create IAM user with S3 access
[ ] Note access key and secret
[ ] Configure CloudFront CDN (optional)
```

**S3 CORS Configuration:**
```json
[
    {
        "AllowedHeaders": ["*"],
        "AllowedMethods": ["GET", "PUT", "POST"],
        "AllowedOrigins": ["https://your-app.vercel.app"],
        "ExposeHeaders": ["ETag"]
    }
]
```

---

## 4. Database Setup

### 4.1 Initial Setup

```
[ ] PostgreSQL addon created in Railway
[ ] DATABASE_URL environment variable set
[ ] SSL connection enabled (default on Railway)
```

### 4.2 Database Migrations

The application auto-creates tables on startup. For manual migration:

```bash
# Connect to Railway PostgreSQL
railway connect postgres

# Or use connection string
psql $DATABASE_URL
```

### 4.3 Database Verification

```sql
-- Check tables exist
\dt

-- Expected tables:
-- users
-- organizations
-- campaigns
-- knowledge_bases
-- conversations
-- assets
-- deliverables
-- scheduled_posts
-- trends
```

### 4.4 Backup Configuration

```
[ ] Enable automatic backups in Railway
[ ] Set backup retention period (7+ days recommended)
[ ] Test backup restoration procedure
[ ] Document backup/restore process
```

---

## 5. Backend Deployment

### 5.1 Pre-Deployment Checks

```bash
# Local testing
cd backend
python -m pytest tests/ -v

# Check for security issues
pip-audit

# Verify requirements
pip install -r requirements.txt --dry-run
```

### 5.2 Deployment Steps

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Release v2.0.0"
   git tag v2.0.0
   git push origin main --tags
   ```

2. **Railway Auto-Deploy**
   ```
   [ ] Verify Railway detected the push
   [ ] Monitor build logs
   [ ] Check for build errors
   ```

3. **Verify Deployment**
   ```
   [ ] Check deployment status in Railway
   [ ] View deployment logs
   [ ] Verify health endpoint responds
   ```

### 5.3 Railway Configuration File

Verify [`backend/railway.toml`](backend/railway.toml):
```toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### 5.4 Health Check Verification

```bash
curl https://your-backend.railway.app/health

# Expected response:
{
  "status": "healthy",
  "version": "2.0.0",
  "environment": "production",
  "checks": {
    "database": {"status": "connected", "type": "postgresql"},
    "openrouter_api_key": "set",
    ...
  }
}
```

---

## 6. Frontend Deployment

### 6.1 Pre-Deployment Checks

```bash
cd frontend

# Install dependencies
npm ci

# Build locally to verify
npm run build

# Run E2E tests (optional)
npm run test:e2e
```

### 6.2 Deployment Steps

1. **Push to GitHub** (same as backend if monorepo)

2. **Vercel Auto-Deploy**
   ```
   [ ] Verify Vercel detected the push
   [ ] Monitor build logs
   [ ] Check for build errors
   ```

3. **Verify Deployment**
   ```
   [ ] Check deployment status in Vercel
   [ ] Visit production URL
   [ ] Check browser console for errors
   ```

### 6.3 Vercel Configuration

Verify [`frontend/vercel.json`](frontend/vercel.json):
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite"
}
```

### 6.4 Frontend Verification

```
[ ] Homepage loads correctly
[ ] Login page accessible
[ ] API calls reach backend (check Network tab)
[ ] No CORS errors in console
[ ] Assets load correctly
```

---

## 7. Post-Deployment Verification

### 7.1 Smoke Tests

Run these tests immediately after deployment:

```
[ ] Health endpoint returns 200
[ ] Login page loads
[ ] User can register new account
[ ] User can log in
[ ] Dashboard loads after login
[ ] Onboarding flow works
[ ] Campaign creation works
[ ] Chat functionality works
[ ] Asset generation works (if API keys set)
```

### 7.2 API Endpoint Tests

```bash
# Health check
curl -X GET https://your-backend.railway.app/health

# Auth endpoints
curl -X POST https://your-backend.railway.app/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123","name":"Test User"}'

# Protected endpoint (should fail without token)
curl -X GET https://your-backend.railway.app/api/users/me
# Expected: 401 Unauthorized
```

### 7.3 Performance Baseline

```
[ ] Homepage load time < 3s
[ ] API response time < 500ms (simple endpoints)
[ ] No memory leaks observed
[ ] Database queries optimized
```

### 7.4 Security Verification

```
[ ] HTTPS enforced (HTTP redirects to HTTPS)
[ ] API docs disabled (/docs returns 404)
[ ] CORS blocks unauthorized origins
[ ] Auth required for protected endpoints
[ ] No sensitive data in error responses
```

---

## 8. Monitoring & Alerting

### 8.1 Railway Monitoring

```
[ ] Enable metrics in Railway dashboard
[ ] Set up alerts for:
    - High CPU usage (>80%)
    - High memory usage (>80%)
    - Service restarts
    - Failed health checks
```

### 8.2 Vercel Analytics

```
[ ] Enable Vercel Analytics
[ ] Monitor Core Web Vitals
[ ] Set up error tracking
```

### 8.3 External Monitoring (Recommended)

```
[ ] Set up uptime monitoring (UptimeRobot, Pingdom)
[ ] Configure status page
[ ] Set up error tracking (Sentry)
[ ] Configure log aggregation
```

### 8.4 Alert Contacts

```
[ ] Primary on-call: _______________
[ ] Secondary on-call: _______________
[ ] Escalation path documented
[ ] PagerDuty/Opsgenie configured (optional)
```

---

## 9. Rollback Procedures

### 9.1 Backend Rollback (Railway)

1. **Quick Rollback**
   ```
   [ ] Go to Railway dashboard
   [ ] Select service
   [ ] Click "Deployments"
   [ ] Find last working deployment
   [ ] Click "Redeploy"
   ```

2. **Git Rollback**
   ```bash
   git revert HEAD
   git push origin main
   # Railway will auto-deploy
   ```

### 9.2 Frontend Rollback (Vercel)

1. **Quick Rollback**
   ```
   [ ] Go to Vercel dashboard
   [ ] Select project
   [ ] Click "Deployments"
   [ ] Find last working deployment
   [ ] Click "..." → "Promote to Production"
   ```

### 9.3 Database Rollback

```
[ ] Restore from backup (Railway dashboard)
[ ] Or run migration rollback scripts
[ ] Verify data integrity after restore
```

### 9.4 Rollback Checklist

```
[ ] Identify the issue
[ ] Notify stakeholders
[ ] Execute rollback
[ ] Verify rollback successful
[ ] Document incident
[ ] Plan fix for next deployment
```

---

## Quick Reference

### Useful Commands

```bash
# Generate secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Test backend locally
cd backend && uvicorn app.main:app --reload

# Test frontend locally
cd frontend && npm run dev

# Build frontend
cd frontend && npm run build

# Run backend tests
cd backend && python -m pytest tests/ -v

# Check Railway logs
railway logs

# Connect to Railway PostgreSQL
railway connect postgres
```

### Important URLs

| Environment | Backend | Frontend |
|-------------|---------|----------|
| Production | https://your-backend.railway.app | https://your-app.vercel.app |
| Staging | https://staging-backend.railway.app | https://staging.your-app.vercel.app |

### Emergency Contacts

| Role | Name | Contact |
|------|------|---------|
| DevOps Lead | TBD | TBD |
| Backend Lead | TBD | TBD |
| Frontend Lead | TBD | TBD |

---

## Deployment Sign-Off

| Step | Completed | Verified By | Date |
|------|-----------|-------------|------|
| Pre-deployment checks | [ ] | | |
| Environment configuration | [ ] | | |
| Backend deployment | [ ] | | |
| Frontend deployment | [ ] | | |
| Smoke tests | [ ] | | |
| Security verification | [ ] | | |
| Monitoring setup | [ ] | | |

**Deployment Approved By:** _______________  
**Date:** _______________

---

*This checklist should be reviewed and updated before each production deployment.*
