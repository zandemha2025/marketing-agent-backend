# Marketing Agent Platform - Complete Implementation Plan

## Overview

This plan covers everything needed to reach 100% implementation:
- **Critical Items** (4) - Must fix immediately
- **High Priority Items** (4) - Important for quality
- **Not Built Items** (7) - Features to add

**Total Estimated Effort:** 10-13 days

---

# PHASE 1: CRITICAL ITEMS (2-3 days)

## 1.1 Fix Kata Frontend Endpoints

**Problem:** Kata components use hardcoded fetch calls instead of the api.js service.

**Files to Modify:**

### A. `/frontend/src/components/kata/SyntheticInfluencerCreator.jsx`

**Current (Broken):**
```javascript
// Line 112 - hardcoded endpoint
const response = await fetch('/api/kata/synthetic-influencer', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
});
```

**Fix:**
```javascript
// Import api service at top
import api from '../../../services/api';

// Replace fetch with api service call
const handleGenerate = async () => {
  try {
    setIsGenerating(true);

    const payload = {
      name: influencerData.name,
      appearance: influencerData.appearance,
      voice: influencerData.voice,
      style: influencerData.style,
      script: influencerData.script,
      reference_images: influencerData.referenceImages.map(img => img.name)
    };

    const result = await api.createSyntheticInfluencer(payload);
    onJobCreated(result);
  } catch (error) {
    console.error('Failed to create synthetic influencer:', error);
    setError(error.message);
  } finally {
    setIsGenerating(false);
  }
};
```

### B. `/frontend/src/components/kata/VideoCompositor.jsx`

**Current (Broken):**
```javascript
// Lines 91, 99, 107 - hardcoded endpoints
const endpoints = {
  merge: '/api/kata/merge-videos',
  product: '/api/kata/composite-product',
  ugc: '/api/kata/ugc-style'
};
const response = await fetch(endpoints[mode], {...});
```

**Fix:**
```javascript
import api from '../../../services/api';

const handleComposite = async () => {
  try {
    setIsProcessing(true);

    let result;
    switch (mode) {
      case 'merge':
        result = await api.mergeVideos({
          video1_url: files.video1?.url,
          video2_url: files.video2?.url,
          transition: settings.transition
        });
        break;
      case 'product':
        result = await api.compositeProduct({
          video_url: files.background?.url,
          product_image_url: files.product?.url,
          placement: settings.placement,
          scale: settings.scale
        });
        break;
      case 'ugc':
        result = await api.applyUGCStyle({
          video_url: files.source?.url,
          style: settings.ugcStyle
        });
        break;
    }

    onJobCreated(result);
  } catch (error) {
    setError(error.message);
  } finally {
    setIsProcessing(false);
  }
};
```

### C. `/frontend/src/pages/KataLabPage.jsx`

**Current (Broken):**
```javascript
// Line 43 - hardcoded endpoint, no cleanup
const pollJob = async (jobId) => {
  const response = await fetch(`/api/kata/jobs/${jobId}`);
  // ...
  setTimeout(() => pollJob(jobId), 2000); // Memory leak!
};
```

**Fix:**
```javascript
import api from '../services/api';

// Add ref for cleanup
const pollingRef = useRef(null);

const pollJob = async (jobId) => {
  try {
    const job = await api.getKataJobStatus(jobId);
    setCurrentJob(job);

    if (job.status === 'complete') {
      const result = await api.getKataJobResult(jobId);
      setGeneratedContent(result);
    } else if (job.status === 'failed') {
      setError(job.error || 'Job failed');
    } else {
      // Continue polling
      pollingRef.current = setTimeout(() => pollJob(jobId), 2000);
    }
  } catch (error) {
    setError(error.message);
  }
};

// Cleanup on unmount
useEffect(() => {
  return () => {
    if (pollingRef.current) {
      clearTimeout(pollingRef.current);
    }
  };
}, []);
```

### D. `/frontend/src/services/api.js`

**Add Kata API methods:**
```javascript
// ============ KATA ENGINE ============

async createSyntheticInfluencer(data) {
  return this.request('/kata/synthetic-influencer', {
    method: 'POST',
    body: JSON.stringify(data)
  });
},

async compositeProduct(data) {
  return this.request('/kata/composite-product', {
    method: 'POST',
    body: JSON.stringify(data)
  });
},

async mergeVideos(data) {
  return this.request('/kata/merge-videos', {
    method: 'POST',
    body: JSON.stringify(data)
  });
},

async applyUGCStyle(data) {
  return this.request('/kata/ugc-style', {
    method: 'POST',
    body: JSON.stringify(data)
  });
},

async generateVoice(data) {
  return this.request('/kata/generate-voice', {
    method: 'POST',
    body: JSON.stringify(data)
  });
},

async getKataJobStatus(jobId) {
  return this.request(`/kata/jobs/${jobId}`);
},

async getKataJobResult(jobId) {
  return this.request(`/kata/jobs/${jobId}/result`);
},

async listKataJobs(status = null) {
  const params = status ? `?status=${status}` : '';
  return this.request(`/kata/jobs${params}`);
},
```

---

## 1.2 Fix KataLabPage Memory Leak

**Problem:** Polling interval never cleared on unmount.

**File:** `/frontend/src/pages/KataLabPage.jsx`

**Solution:** Already covered above in 1.1C - add `pollingRef` and cleanup in `useEffect`.

---

## 1.3 Remove Mock Data from TrendMaster

**Problem:** Component has hardcoded MOCK_TRENDS array.

**File:** `/frontend/src/components/trends/TrendMaster.jsx`

**Current (Lines 31-118):**
```javascript
const MOCK_TRENDS = [
  {
    id: 't1',
    title: 'AI-Generated Content Goes Mainstream',
    // ... hardcoded data
  },
  // ... 5 more hardcoded trends
];
```

**Fix:**
```javascript
// Remove entire MOCK_TRENDS constant

// Update component to require real data
const TrendMaster = ({
  trends = [],  // Remove default mock
  onRefresh,
  onCreateCampaign,
  onAnalyzeTrend,
  loading = false,
  error = null
}) => {
  // Remove the fallback logic
  // const displayTrends = customTrends?.length > 0 ? customTrends : MOCK_TRENDS;

  // Just use trends directly
  const [filteredTrends, setFilteredTrends] = useState(trends);

  useEffect(() => {
    let filtered = trends;

    if (selectedCategory !== 'all') {
      filtered = filtered.filter(t => t.category === selectedCategory);
    }

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(t =>
        t.title.toLowerCase().includes(query) ||
        t.description.toLowerCase().includes(query)
      );
    }

    setFilteredTrends(filtered);
  }, [trends, selectedCategory, searchQuery]);

  // Show empty state if no trends
  if (!loading && trends.length === 0) {
    return (
      <div className="trend-master-empty">
        <h3>No trends found</h3>
        <p>Click refresh to scan for market trends</p>
        <button onClick={onRefresh}>Scan for Trends</button>
      </div>
    );
  }

  // ... rest of component
};
```

---

## 1.4 Implement User Authentication

**Problem:** No real authentication - just placeholder.

### Backend Changes

**File:** `/backend/app/api/auth.py` (NEW FILE)

```python
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from typing import Optional
import jwt
import bcrypt
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.database import get_db
from app.repositories.user import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer()

SECRET_KEY = settings.jwt_secret_key or "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    organization_id: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    organization_id: str
    role: str

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = Depends(get_db)
):
    payload = verify_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_repo = UserRepository(db)
    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

@router.post("/register", response_model=Token)
async def register(user_data: UserCreate, db = Depends(get_db)):
    user_repo = UserRepository(db)

    # Check if user exists
    existing = await user_repo.get_by_email(user_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password
    password_hash = bcrypt.hashpw(
        user_data.password.encode('utf-8'),
        bcrypt.gensalt()
    ).decode('utf-8')

    # Create user
    user = await user_repo.create(
        email=user_data.email,
        name=user_data.name,
        password_hash=password_hash,
        organization_id=user_data.organization_id,
        role="editor"
    )

    # Generate token
    access_token = create_access_token({"sub": user.id, "org": user.organization_id})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "organization_id": user.organization_id,
            "role": user.role
        }
    }

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db = Depends(get_db)):
    user_repo = UserRepository(db)

    user = await user_repo.get_by_email(credentials.email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password
    if not bcrypt.checkpw(
        credentials.password.encode('utf-8'),
        user.password_hash.encode('utf-8')
    ):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Generate token
    access_token = create_access_token({"sub": user.id, "org": user.organization_id})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "organization_id": user.organization_id,
            "role": user.role
        }
    }

@router.get("/me", response_model=UserResponse)
async def get_me(current_user = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "organization_id": current_user.organization_id,
        "role": current_user.role
    }
```

**File:** `/backend/app/main.py` - Add auth router

```python
from app.api.auth import router as auth_router

# Add to router includes
app.include_router(auth_router, prefix="/api")
```

**File:** `/backend/app/repositories/user.py` - Add methods

```python
async def get_by_email(self, email: str) -> Optional[User]:
    result = await self.db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()
```

### Frontend Changes

**File:** `/frontend/src/services/api.js` - Add auth methods

```javascript
// ============ AUTHENTICATION ============

async register(email, password, name, organizationId) {
  return this.request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, name, organization_id: organizationId })
  });
},

async login(email, password) {
  const result = await this.request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password })
  });

  // Store token
  if (result.access_token) {
    localStorage.setItem('auth_token', result.access_token);
    localStorage.setItem('user', JSON.stringify(result.user));
  }

  return result;
},

async getMe() {
  return this.request('/auth/me');
},

logout() {
  localStorage.removeItem('auth_token');
  localStorage.removeItem('user');
  localStorage.removeItem('organizationId');
},

getAuthToken() {
  return localStorage.getItem('auth_token');
},

getCurrentUser() {
  const user = localStorage.getItem('user');
  return user ? JSON.parse(user) : null;
},

// Update request method to include auth header
async request(endpoint, options = {}) {
  const token = this.getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // ... rest of request method
}
```

**File:** `/frontend/src/pages/LoginPage.jsx` (NEW FILE)

```jsx
import React, { useState } from 'react';
import api from '../services/api';
import './LoginPage.css';

const LoginPage = ({ onLogin }) => {
  const [mode, setMode] = useState('login'); // 'login' or 'register'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      let result;
      if (mode === 'login') {
        result = await api.login(email, password);
      } else {
        // For registration, we need an org - create one or join existing
        result = await api.register(email, password, name, null);
      }

      onLogin(result.user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <h1>Marketing Agent</h1>

        <div className="mode-toggle">
          <button
            className={mode === 'login' ? 'active' : ''}
            onClick={() => setMode('login')}
          >
            Login
          </button>
          <button
            className={mode === 'register' ? 'active' : ''}
            onClick={() => setMode('register')}
          >
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {mode === 'register' && (
            <div className="form-group">
              <label>Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </div>
          )}

          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && <div className="error">{error}</div>}

          <button type="submit" disabled={loading}>
            {loading ? 'Please wait...' : mode === 'login' ? 'Login' : 'Register'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginPage;
```

**File:** `/frontend/src/App.jsx` - Update routing

```jsx
import LoginPage from './pages/LoginPage';

function App() {
  const [currentPage, setCurrentPage] = useState('login');
  const [user, setUser] = useState(null);
  const [organizationId, setOrganizationId] = useState(null);

  useEffect(() => {
    // Check for existing auth
    const token = api.getAuthToken();
    const savedUser = api.getCurrentUser();
    const savedOrgId = localStorage.getItem('organizationId');

    if (token && savedUser) {
      setUser(savedUser);
      if (savedOrgId) {
        setOrganizationId(savedOrgId);
        setCurrentPage('dashboard');
      } else {
        setCurrentPage('onboarding');
      }
    }
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
    if (userData.organization_id) {
      setOrganizationId(userData.organization_id);
      setCurrentPage('dashboard');
    } else {
      setCurrentPage('onboarding');
    }
  };

  const handleLogout = () => {
    api.logout();
    setUser(null);
    setOrganizationId(null);
    setCurrentPage('login');
  };

  return (
    <div className="app">
      {currentPage === 'login' && (
        <LoginPage onLogin={handleLogin} />
      )}
      {currentPage === 'onboarding' && (
        <OnboardingPage
          user={user}
          onComplete={(orgId) => {
            setOrganizationId(orgId);
            setCurrentPage('dashboard');
          }}
        />
      )}
      {currentPage === 'dashboard' && (
        <DashboardPage
          organizationId={organizationId}
          user={user}
          onLogout={handleLogout}
          navigateTo={setCurrentPage}
        />
      )}
      {/* ... other pages */}
    </div>
  );
}
```

---

# PHASE 2: HIGH PRIORITY ITEMS (3-4 days)

## 2.1 Fix Deliverables Refine Endpoint

**Problem:** `/deliverables/refine` calls LLM but doesn't save to database.

**File:** `/backend/app/api/deliverables.py`

**Current:**
```python
@router.post("/refine")
async def refine_content(request: RefineRequest, db = Depends(get_db)):
    # Calls LLM but doesn't save
    refined = await openrouter.complete(prompt)
    return {"refined_text": refined}
```

**Fix:**
```python
class RefineRequest(BaseModel):
    deliverable_id: Optional[str] = None  # Add this field
    text: str
    action: str
    type: str

@router.post("/refine")
async def refine_content(request: RefineRequest, db = Depends(get_db)):
    openrouter = OpenRouterService(settings.openrouter_api_key)

    action_prompts = {
        "shorten": "Make this text more concise while keeping the key message:",
        "expand": "Expand this text with more detail and examples:",
        "tone_casual": "Rewrite this in a more casual, conversational tone:",
        "tone_professional": "Rewrite this in a more professional, formal tone:",
        "fix_grammar": "Fix any grammar or spelling errors in this text:"
    }

    prompt = f"{action_prompts.get(request.action, 'Improve this text:')}\n\n{request.text}"

    refined = await openrouter.complete(
        prompt=prompt,
        system_prompt=f"You are a professional copywriter specializing in {request.type} content."
    )

    # Save if deliverable_id provided
    if request.deliverable_id:
        result = await db.execute(
            select(Deliverable).where(Deliverable.id == request.deliverable_id)
        )
        deliverable = result.scalar_one_or_none()

        if deliverable:
            deliverable.content = refined
            deliverable.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(deliverable)

            return {
                "refined_text": refined,
                "deliverable": {
                    "id": deliverable.id,
                    "title": deliverable.title,
                    "content": deliverable.content,
                    "updated_at": deliverable.updated_at.isoformat()
                }
            }

    return {"refined_text": refined}
```

---

## 2.2 Implement File Upload to Storage

**Problem:** No S3 or cloud storage integration.

### Backend Changes

**File:** `/backend/app/services/storage.py` (NEW FILE)

```python
import boto3
from botocore.exceptions import ClientError
import uuid
from typing import Optional
import mimetypes

from app.core.config import settings

class StorageService:
    def __init__(self):
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region
        )
        self.bucket = settings.aws_s3_bucket
        self.cdn_url = settings.cdn_url or f"https://{self.bucket}.s3.amazonaws.com"

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        folder: str = "uploads",
        content_type: Optional[str] = None
    ) -> str:
        """Upload file to S3 and return public URL."""

        # Generate unique filename
        ext = filename.split('.')[-1] if '.' in filename else ''
        unique_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex
        key = f"{folder}/{unique_name}"

        # Detect content type
        if not content_type:
            content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=file_content,
                ContentType=content_type,
                ACL='public-read'
            )

            return f"{self.cdn_url}/{key}"
        except ClientError as e:
            raise Exception(f"Failed to upload file: {str(e)}")

    async def delete_file(self, url: str) -> bool:
        """Delete file from S3."""
        try:
            # Extract key from URL
            key = url.replace(f"{self.cdn_url}/", "")
            self.s3.delete_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate presigned URL for direct upload."""
        return self.s3.generate_presigned_url(
            'put_object',
            Params={'Bucket': self.bucket, 'Key': key},
            ExpiresIn=expires_in
        )
```

**File:** `/backend/app/api/uploads.py` (NEW FILE)

```python
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from typing import List

from app.services.storage import StorageService
from app.core.database import get_db

router = APIRouter(prefix="/uploads", tags=["uploads"])

storage = StorageService()

@router.post("/image")
async def upload_image(file: UploadFile = File(...)):
    """Upload an image file."""

    # Validate file type
    allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if file.content_type not in allowed_types:
        raise HTTPException(400, "Invalid file type. Allowed: JPEG, PNG, GIF, WebP")

    # Validate file size (max 10MB)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "File too large. Max 10MB")

    url = await storage.upload_file(
        file_content=content,
        filename=file.filename,
        folder="images",
        content_type=file.content_type
    )

    return {"url": url, "filename": file.filename, "size": len(content)}

@router.post("/video")
async def upload_video(file: UploadFile = File(...)):
    """Upload a video file."""

    allowed_types = ['video/mp4', 'video/quicktime', 'video/webm']
    if file.content_type not in allowed_types:
        raise HTTPException(400, "Invalid file type. Allowed: MP4, MOV, WebM")

    # Validate file size (max 100MB)
    content = await file.read()
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(400, "File too large. Max 100MB")

    url = await storage.upload_file(
        file_content=content,
        filename=file.filename,
        folder="videos",
        content_type=file.content_type
    )

    return {"url": url, "filename": file.filename, "size": len(content)}

@router.post("/document")
async def upload_document(file: UploadFile = File(...)):
    """Upload a document file."""

    allowed_types = ['application/pdf', 'application/msword',
                     'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
    if file.content_type not in allowed_types:
        raise HTTPException(400, "Invalid file type. Allowed: PDF, DOC, DOCX")

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(400, "File too large. Max 20MB")

    url = await storage.upload_file(
        file_content=content,
        filename=file.filename,
        folder="documents",
        content_type=file.content_type
    )

    return {"url": url, "filename": file.filename, "size": len(content)}

@router.delete("")
async def delete_file(url: str):
    """Delete a file by URL."""
    success = await storage.delete_file(url)
    if not success:
        raise HTTPException(404, "File not found")
    return {"success": True}
```

**File:** `/backend/app/core/config.py` - Add settings

```python
# AWS Settings
aws_access_key_id: Optional[str] = None
aws_secret_access_key: Optional[str] = None
aws_region: str = "us-east-1"
aws_s3_bucket: str = "marketing-agent-uploads"
cdn_url: Optional[str] = None
```

### Frontend Changes

**File:** `/frontend/src/services/api.js` - Add upload methods

```javascript
// ============ FILE UPLOADS ============

async uploadImage(file) {
  const formData = new FormData();
  formData.append('file', file);

  return this.request('/uploads/image', {
    method: 'POST',
    headers: {}, // Let browser set Content-Type for FormData
    body: formData
  });
},

async uploadVideo(file) {
  const formData = new FormData();
  formData.append('file', file);

  return this.request('/uploads/video', {
    method: 'POST',
    headers: {},
    body: formData
  });
},

async deleteFile(url) {
  return this.request(`/uploads?url=${encodeURIComponent(url)}`, {
    method: 'DELETE'
  });
},
```

---

## 2.3 Complete Image Editor File Handling

**Problem:** ConversationalImageEditor has placeholder file upload.

**File:** `/frontend/src/components/image-editor/ConversationalImageEditor.jsx`

**Fix the file upload handler:**

```jsx
import api from '../../services/api';

const handleFileUpload = async (file) => {
  if (!file) return;

  setIsUploading(true);
  setError(null);

  try {
    // Upload to storage
    const uploadResult = await api.uploadImage(file);

    // Create or update session with the uploaded image
    if (!sessionId) {
      const session = await api.createImageEditSession({
        organization_id: organizationId,
        title: file.name,
        original_image_url: uploadResult.url,
        current_image_url: uploadResult.url
      });
      setSessionId(session.id);
    } else {
      await api.updateImageEditSession(sessionId, {
        current_image_url: uploadResult.url
      });
    }

    setCurrentImage(uploadResult.url);
    setVersions([...versions, { url: uploadResult.url, timestamp: new Date() }]);

    addMessage('assistant', `I've loaded your image "${file.name}". What would you like me to do with it?`);
  } catch (err) {
    setError(`Failed to upload: ${err.message}`);
    addMessage('assistant', `Sorry, I couldn't upload the image. ${err.message}`);
  } finally {
    setIsUploading(false);
  }
};

const handleDrop = async (e) => {
  e.preventDefault();
  setIsDragging(false);

  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) {
    await handleFileUpload(file);
  }
};

const handleFileSelect = async (e) => {
  const file = e.target.files[0];
  if (file) {
    await handleFileUpload(file);
  }
};
```

---

## 2.4 Fix ScriptBuilder to Use Real API

**Problem:** Falls back to local generation instead of using API.

**File:** `/frontend/src/components/kata/ScriptBuilder.jsx`

**Remove the fallback, require real API:**

```jsx
const generateScript = async () => {
  setIsGenerating(true);
  setError(null);

  try {
    // Always use real API
    const response = await api.generateScript({
      format: selectedFormat,
      answers: answers,
      tone: answers.tone || 'professional',
      duration: answers.duration || '60'
    });

    setGeneratedScript(response.script);
    setCurrentStep('result');
  } catch (err) {
    // Show error instead of falling back to local generation
    setError(`Failed to generate script: ${err.message}. Please try again.`);
    console.error('Script generation failed:', err);
  } finally {
    setIsGenerating(false);
  }
};
```

**Add backend endpoint if missing:**

**File:** `/backend/app/api/kata.py`

```python
@router.post("/generate-script")
async def generate_script(request: dict, db = Depends(get_db)):
    """Generate a video script using AI."""

    openrouter = OpenRouterService(settings.openrouter_api_key)

    format_prompts = {
        'testimonial': "Create a customer testimonial video script",
        'explainer': "Create an explainer video script",
        'product': "Create a product showcase video script",
        'story': "Create a brand story video script"
    }

    prompt = f"""
    {format_prompts.get(request.get('format', 'explainer'))}

    Details:
    - Duration: {request.get('duration', '60')} seconds
    - Tone: {request.get('tone', 'professional')}
    - Topic: {request.get('answers', {}).get('topic', 'Product overview')}
    - Key points: {request.get('answers', {}).get('key_points', '')}
    - Target audience: {request.get('answers', {}).get('audience', 'General')}
    - Call to action: {request.get('answers', {}).get('cta', '')}

    Generate a complete video script with:
    1. Hook/Opening (5-10 seconds)
    2. Main content (body)
    3. Call to action (5-10 seconds)

    Include speaker directions and visual suggestions in [brackets].
    """

    script = await openrouter.complete(
        prompt=prompt,
        system_prompt="You are an expert video scriptwriter for marketing content."
    )

    return {"script": script, "format": request.get('format'), "duration": request.get('duration')}
```

---

# PHASE 3: NOT BUILT ITEMS (5-6 days)

## 3.1 Social Media Publishing

**Files to Create:**

### Backend

**File:** `/backend/app/services/social/__init__.py`

```python
from .twitter import TwitterService
from .instagram import InstagramService
from .linkedin import LinkedInService
from .facebook import FacebookService

__all__ = ['TwitterService', 'InstagramService', 'LinkedInService', 'FacebookService']
```

**File:** `/backend/app/services/social/twitter.py`

```python
import tweepy
from typing import Optional

class TwitterService:
    def __init__(self, api_key: str, api_secret: str, access_token: str, access_secret: str):
        auth = tweepy.OAuthHandler(api_key, api_secret)
        auth.set_access_token(access_token, access_secret)
        self.api = tweepy.API(auth)
        self.client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_secret
        )

    async def post(self, text: str, image_url: Optional[str] = None) -> dict:
        """Post a tweet, optionally with an image."""
        try:
            if image_url:
                # Download image and upload to Twitter
                import requests
                response = requests.get(image_url)
                media = self.api.media_upload(filename='image.jpg', file=response.content)
                result = self.client.create_tweet(text=text, media_ids=[media.media_id])
            else:
                result = self.client.create_tweet(text=text)

            return {
                "success": True,
                "post_id": result.data['id'],
                "url": f"https://twitter.com/i/status/{result.data['id']}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def delete(self, post_id: str) -> bool:
        """Delete a tweet."""
        try:
            self.client.delete_tweet(post_id)
            return True
        except:
            return False
```

**File:** `/backend/app/services/social/linkedin.py`

```python
import requests
from typing import Optional

class LinkedInService:
    def __init__(self, access_token: str, organization_id: str = None):
        self.access_token = access_token
        self.organization_id = organization_id
        self.base_url = "https://api.linkedin.com/v2"

    async def post(self, text: str, image_url: Optional[str] = None) -> dict:
        """Post to LinkedIn."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }

        # Get user URN
        me_response = requests.get(f"{self.base_url}/me", headers=headers)
        user_urn = f"urn:li:person:{me_response.json()['id']}"

        post_data = {
            "author": user_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }

        if image_url:
            # Handle image upload to LinkedIn
            # (LinkedIn requires registering upload, then uploading binary)
            pass

        response = requests.post(
            f"{self.base_url}/ugcPosts",
            headers=headers,
            json=post_data
        )

        if response.status_code == 201:
            return {
                "success": True,
                "post_id": response.json().get('id'),
                "url": None  # LinkedIn doesn't return direct URL
            }
        else:
            return {"success": False, "error": response.text}
```

**File:** `/backend/app/api/scheduled_posts.py` - Update publish endpoint

```python
from app.services.social import TwitterService, LinkedInService, InstagramService, FacebookService

@router.post("/{post_id}/publish")
async def publish_post(post_id: str, db = Depends(get_db)):
    """Publish a scheduled post immediately."""

    result = await db.execute(
        select(ScheduledPost).where(ScheduledPost.id == post_id)
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(404, "Post not found")

    # Get organization's social credentials
    org_result = await db.execute(
        select(Organization).where(Organization.id == post.organization_id)
    )
    org = org_result.scalar_one_or_none()
    social_creds = org.settings.get('social_credentials', {})

    publish_result = None

    try:
        if post.platform == 'twitter':
            creds = social_creds.get('twitter', {})
            twitter = TwitterService(
                api_key=creds.get('api_key'),
                api_secret=creds.get('api_secret'),
                access_token=creds.get('access_token'),
                access_secret=creds.get('access_secret')
            )
            publish_result = await twitter.post(post.content, post.image_url)

        elif post.platform == 'linkedin':
            creds = social_creds.get('linkedin', {})
            linkedin = LinkedInService(access_token=creds.get('access_token'))
            publish_result = await linkedin.post(post.content, post.image_url)

        elif post.platform == 'instagram':
            # Instagram requires Business API
            creds = social_creds.get('instagram', {})
            instagram = InstagramService(access_token=creds.get('access_token'))
            publish_result = await instagram.post(post.content, post.image_url)

        elif post.platform == 'facebook':
            creds = social_creds.get('facebook', {})
            facebook = FacebookService(
                page_id=creds.get('page_id'),
                access_token=creds.get('access_token')
            )
            publish_result = await facebook.post(post.content, post.image_url)

        if publish_result and publish_result.get('success'):
            post.status = 'published'
            post.published_at = datetime.utcnow()
            post.platform_post_id = publish_result.get('post_id')
            post.platform_url = publish_result.get('url')
            await db.commit()

            return {
                "success": True,
                "post": post,
                "platform_result": publish_result
            }
        else:
            post.status = 'failed'
            post.error_message = publish_result.get('error', 'Unknown error')
            await db.commit()

            raise HTTPException(500, f"Failed to publish: {publish_result.get('error')}")

    except Exception as e:
        post.status = 'failed'
        post.error_message = str(e)
        await db.commit()
        raise HTTPException(500, f"Failed to publish: {str(e)}")
```

---

## 3.2 Analytics Dashboard

**File:** `/backend/app/api/analytics.py` (NEW FILE)

```python
from fastapi import APIRouter, Depends, Query
from datetime import datetime, timedelta
from sqlalchemy import select, func

from app.core.database import get_db
from app.models import Campaign, Asset, ScheduledPost, Task, Deliverable

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/overview/{organization_id}")
async def get_overview(organization_id: str, db = Depends(get_db)):
    """Get analytics overview for organization."""

    # Campaign stats
    campaigns = await db.execute(
        select(func.count(Campaign.id), Campaign.status)
        .where(Campaign.organization_id == organization_id)
        .group_by(Campaign.status)
    )
    campaign_stats = {row[1]: row[0] for row in campaigns.fetchall()}

    # Asset stats
    assets = await db.execute(
        select(func.count(Asset.id))
        .join(Campaign)
        .where(Campaign.organization_id == organization_id)
    )
    total_assets = assets.scalar() or 0

    # Task stats
    tasks = await db.execute(
        select(func.count(Task.id), Task.status)
        .where(Task.organization_id == organization_id)
        .group_by(Task.status)
    )
    task_stats = {row[1]: row[0] for row in tasks.fetchall()}

    # Scheduled posts stats
    posts = await db.execute(
        select(func.count(ScheduledPost.id), ScheduledPost.status)
        .where(ScheduledPost.organization_id == organization_id)
        .group_by(ScheduledPost.status)
    )
    post_stats = {row[1]: row[0] for row in posts.fetchall()}

    # Recent activity (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)

    recent_campaigns = await db.execute(
        select(func.count(Campaign.id))
        .where(
            Campaign.organization_id == organization_id,
            Campaign.created_at >= week_ago
        )
    )

    recent_deliverables = await db.execute(
        select(func.count(Deliverable.id))
        .join(Campaign)
        .where(
            Campaign.organization_id == organization_id,
            Deliverable.created_at >= week_ago
        )
    )

    return {
        "campaigns": {
            "total": sum(campaign_stats.values()),
            "by_status": campaign_stats,
            "created_this_week": recent_campaigns.scalar() or 0
        },
        "assets": {
            "total": total_assets
        },
        "tasks": {
            "total": sum(task_stats.values()),
            "by_status": task_stats,
            "completion_rate": round(
                task_stats.get('done', 0) / max(sum(task_stats.values()), 1) * 100, 1
            )
        },
        "scheduled_posts": {
            "total": sum(post_stats.values()),
            "by_status": post_stats
        },
        "activity": {
            "campaigns_this_week": recent_campaigns.scalar() or 0,
            "deliverables_this_week": recent_deliverables.scalar() or 0
        }
    }

@router.get("/campaigns/{organization_id}")
async def get_campaign_analytics(
    organization_id: str,
    start_date: datetime = Query(None),
    end_date: datetime = Query(None),
    db = Depends(get_db)
):
    """Get detailed campaign analytics."""

    query = select(Campaign).where(Campaign.organization_id == organization_id)

    if start_date:
        query = query.where(Campaign.created_at >= start_date)
    if end_date:
        query = query.where(Campaign.created_at <= end_date)

    result = await db.execute(query)
    campaigns = result.scalars().all()

    analytics = []
    for campaign in campaigns:
        # Get asset count
        assets_result = await db.execute(
            select(func.count(Asset.id)).where(Asset.campaign_id == campaign.id)
        )

        # Get deliverable count
        deliverables_result = await db.execute(
            select(func.count(Deliverable.id)).where(Deliverable.campaign_id == campaign.id)
        )

        analytics.append({
            "id": campaign.id,
            "name": campaign.name,
            "status": campaign.status,
            "created_at": campaign.created_at.isoformat(),
            "asset_count": assets_result.scalar() or 0,
            "deliverable_count": deliverables_result.scalar() or 0,
            "has_brief": campaign.brief_data is not None,
            "concept_selected": campaign.selected_concept_index is not None
        })

    return {"campaigns": analytics}
```

### Frontend Component

**File:** `/frontend/src/components/analytics/AnalyticsDashboard.jsx`

```jsx
import React, { useState, useEffect } from 'react';
import api from '../../services/api';
import './AnalyticsDashboard.css';

const AnalyticsDashboard = ({ organizationId }) => {
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, [organizationId]);

  const loadAnalytics = async () => {
    try {
      const data = await api.getAnalyticsOverview(organizationId);
      setOverview(data);
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="loading">Loading analytics...</div>;
  if (!overview) return <div className="error">Failed to load analytics</div>;

  return (
    <div className="analytics-dashboard">
      <h2>Analytics Overview</h2>

      <div className="stats-grid">
        <div className="stat-card">
          <h3>Campaigns</h3>
          <div className="stat-value">{overview.campaigns.total}</div>
          <div className="stat-detail">
            {overview.campaigns.created_this_week} this week
          </div>
        </div>

        <div className="stat-card">
          <h3>Assets</h3>
          <div className="stat-value">{overview.assets.total}</div>
        </div>

        <div className="stat-card">
          <h3>Tasks</h3>
          <div className="stat-value">{overview.tasks.total}</div>
          <div className="stat-detail">
            {overview.tasks.completion_rate}% complete
          </div>
        </div>

        <div className="stat-card">
          <h3>Scheduled Posts</h3>
          <div className="stat-value">{overview.scheduled_posts.total}</div>
          <div className="stat-detail">
            {overview.scheduled_posts.by_status?.published || 0} published
          </div>
        </div>
      </div>

      <div className="status-breakdown">
        <h3>Campaign Status</h3>
        <div className="status-bars">
          {Object.entries(overview.campaigns.by_status || {}).map(([status, count]) => (
            <div key={status} className="status-bar">
              <span className="status-label">{status}</span>
              <div className="bar-container">
                <div
                  className={`bar bar-${status}`}
                  style={{ width: `${(count / overview.campaigns.total) * 100}%` }}
                />
              </div>
              <span className="status-count">{count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;
```

---

## 3.3 User Management

**File:** `/backend/app/api/users.py` (NEW FILE)

```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import List, Optional

from app.core.database import get_db
from app.repositories.user import UserRepository
from app.api.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserInvite(BaseModel):
    email: EmailStr
    name: str
    role: str = "editor"

@router.get("/")
async def list_users(
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """List all users in the organization."""
    if current_user.role != "admin":
        raise HTTPException(403, "Admin access required")

    user_repo = UserRepository(db)
    users = await user_repo.get_by_organization(current_user.organization_id)

    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat()
        }
        for u in users
    ]

@router.post("/invite")
async def invite_user(
    invite: UserInvite,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Invite a new user to the organization."""
    if current_user.role != "admin":
        raise HTTPException(403, "Admin access required")

    user_repo = UserRepository(db)

    # Check if user already exists
    existing = await user_repo.get_by_email(invite.email)
    if existing:
        raise HTTPException(400, "User already exists")

    # Create user with temporary password
    import secrets
    temp_password = secrets.token_urlsafe(12)

    user = await user_repo.create(
        email=invite.email,
        name=invite.name,
        password_hash=None,  # Will be set on first login
        organization_id=current_user.organization_id,
        role=invite.role
    )

    # TODO: Send invitation email with temp_password

    return {
        "id": user.id,
        "email": user.email,
        "message": "Invitation sent"
    }

@router.patch("/{user_id}")
async def update_user(
    user_id: str,
    update: UserUpdate,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Update a user's details."""
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(403, "Not authorized")

    user_repo = UserRepository(db)
    user = await user_repo.get(user_id)

    if not user:
        raise HTTPException(404, "User not found")

    if user.organization_id != current_user.organization_id:
        raise HTTPException(403, "Not authorized")

    # Only admins can change roles
    if update.role and current_user.role != "admin":
        raise HTTPException(403, "Admin access required to change roles")

    updated = await user_repo.update(user_id, update.dict(exclude_unset=True))

    return {
        "id": updated.id,
        "email": updated.email,
        "name": updated.name,
        "role": updated.role,
        "is_active": updated.is_active
    }

@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """Deactivate a user."""
    if current_user.role != "admin":
        raise HTTPException(403, "Admin access required")

    if current_user.id == user_id:
        raise HTTPException(400, "Cannot delete yourself")

    user_repo = UserRepository(db)
    user = await user_repo.get(user_id)

    if not user or user.organization_id != current_user.organization_id:
        raise HTTPException(404, "User not found")

    await user_repo.update(user_id, {"is_active": False})

    return {"success": True}
```

---

## 3.4 Real Video Generation (Kata Integration) - HALFTIME APPROACH

**Based on research:** Halftime (XAI Hackathon winner) uses Grok for context-aware video compositing. Their approach:
1. **Scene Analysis:** Grok analyzes video narrative, lighting, setting, and objects
2. **Insertion Zone Detection:** AI identifies valid placement areas (walls, hands, surfaces)
3. **Context-Aware Rendering:** Generates assets that match scene lighting/physics
4. **Dynamic Compositing:** Real-time insertion without disrupting content flow

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    KATA ENGINE (Halftime-Style)                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   SCENE      │    │  INSERTION   │    │   ASSET      │       │
│  │  ANALYZER    │───▶│    ZONE      │───▶│  RENDERER    │       │
│  │  (Grok API)  │    │  DETECTOR    │    │ (SegMind+)   │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                   │                │
│         ▼                   ▼                   ▼                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │  Narrative   │    │  Position    │    │  Lighting    │       │
│  │  Context     │    │  Coordinates │    │  Matched     │       │
│  │  Mood/Tone   │    │  Mask/Alpha  │    │  Product     │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│                                                                  │
│         └─────────────────┬─────────────────┘                   │
│                           ▼                                      │
│                  ┌──────────────┐                                │
│                  │  COMPOSITOR  │                                │
│                  │  (FFmpeg +   │                                │
│                  │   SegMind)   │                                │
│                  └──────────────┘                                │
│                           │                                      │
│                           ▼                                      │
│                  ┌──────────────┐                                │
│                  │ FINAL VIDEO  │                                │
│                  │ with Product │                                │
│                  │  Placement   │                                │
│                  └──────────────┘                                │
└─────────────────────────────────────────────────────────────────┘
```

### Service Implementation

**File:** `/backend/app/services/kata/scene_analyzer.py` (NEW - Grok Integration)

```python
import httpx
from typing import Dict, List, Optional
import base64

class GrokSceneAnalyzer:
    """
    Analyzes video frames using Grok's multimodal capabilities.
    Based on Halftime's approach from XAI hackathon.
    """

    def __init__(self, xai_api_key: str):
        self.api_key = xai_api_key
        self.base_url = "https://api.x.ai/v1"
        self.model = "grok-2-vision-latest"  # or grok-4 when available

    async def analyze_frame(self, frame_url: str) -> Dict:
        """
        Analyze a single video frame for:
        - Scene context (narrative, setting, mood)
        - Lighting conditions
        - Valid insertion zones
        - Object positions
        """

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": """You are a video scene analyzer for product placement.
                            Analyze the image and return JSON with:
                            {
                                "scene_context": {
                                    "setting": "description of location",
                                    "mood": "emotional tone",
                                    "narrative_moment": "what's happening"
                                },
                                "lighting": {
                                    "direction": "left/right/front/back/ambient",
                                    "intensity": "low/medium/high",
                                    "color_temperature": "warm/neutral/cool",
                                    "shadows": "soft/hard/none"
                                },
                                "insertion_zones": [
                                    {
                                        "type": "hand/surface/wall/screen/clothing",
                                        "position": {"x": 0-100, "y": 0-100},
                                        "size": {"width": 0-100, "height": 0-100},
                                        "confidence": 0-1,
                                        "natural_fit": "why this zone works"
                                    }
                                ],
                                "objects_detected": ["list", "of", "objects"],
                                "people": [
                                    {
                                        "position": "location in frame",
                                        "action": "what they're doing",
                                        "hand_positions": "if visible"
                                    }
                                ]
                            }"""
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "image_url",
                                    "image_url": {"url": frame_url}
                                },
                                {
                                    "type": "text",
                                    "text": "Analyze this video frame for product placement opportunities. Identify the best insertion zones where a product could naturally fit into the scene."
                                }
                            ]
                        }
                    ],
                    "response_format": {"type": "json_object"}
                },
                timeout=30.0
            )

            result = response.json()
            return result["choices"][0]["message"]["content"]

    async def analyze_video_segment(
        self,
        frames: List[str],
        product_type: str
    ) -> Dict:
        """
        Analyze multiple frames to find the best insertion opportunity.
        """

        analyses = []
        for frame_url in frames:
            analysis = await self.analyze_frame(frame_url)
            analyses.append(analysis)

        # Find best insertion point across all frames
        best_zone = None
        best_confidence = 0
        best_frame_idx = 0

        for idx, analysis in enumerate(analyses):
            if isinstance(analysis, str):
                import json
                analysis = json.loads(analysis)

            for zone in analysis.get("insertion_zones", []):
                if zone.get("confidence", 0) > best_confidence:
                    # Check if zone matches product type
                    if self._zone_matches_product(zone, product_type):
                        best_confidence = zone["confidence"]
                        best_zone = zone
                        best_frame_idx = idx

        return {
            "best_frame_index": best_frame_idx,
            "insertion_zone": best_zone,
            "lighting": analyses[best_frame_idx].get("lighting") if analyses else None,
            "scene_context": analyses[best_frame_idx].get("scene_context") if analyses else None,
            "all_analyses": analyses
        }

    def _zone_matches_product(self, zone: Dict, product_type: str) -> bool:
        """Check if zone type is appropriate for the product."""
        zone_product_mapping = {
            "hand": ["beverage", "phone", "small_item", "food"],
            "surface": ["any"],
            "wall": ["poster", "logo", "billboard"],
            "screen": ["digital", "ad", "logo"],
            "clothing": ["logo", "brand"]
        }

        zone_type = zone.get("type", "surface")
        allowed_products = zone_product_mapping.get(zone_type, ["any"])

        return "any" in allowed_products or product_type in allowed_products
```

**File:** `/backend/app/services/kata/video_compositor.py` (Enhanced)

```python
import subprocess
import tempfile
import os
from typing import Dict, Optional
import httpx

class HalftimeCompositor:
    """
    Video compositor inspired by Halftime's approach.
    Uses scene analysis to place products naturally in video.
    """

    def __init__(self, segmind_api_key: str, xai_api_key: str):
        self.segmind_key = segmind_api_key
        self.scene_analyzer = GrokSceneAnalyzer(xai_api_key)

    async def composite_product(
        self,
        video_url: str,
        product_image_url: str,
        product_type: str = "beverage",
        style_match: bool = True
    ) -> Dict:
        """
        Insert product into video using Halftime-style context-aware compositing.

        Process:
        1. Extract key frames from video
        2. Analyze frames with Grok to find insertion zones
        3. Match product lighting/style to scene
        4. Composite product into video
        5. Apply seamless blending
        """

        # Step 1: Extract frames for analysis
        frames = await self._extract_key_frames(video_url, num_frames=5)

        # Step 2: Analyze with Grok
        analysis = await self.scene_analyzer.analyze_video_segment(
            frames=frames,
            product_type=product_type
        )

        if not analysis.get("insertion_zone"):
            return {
                "success": False,
                "error": "No suitable insertion zone found",
                "analysis": analysis
            }

        # Step 3: Style-match the product image
        if style_match:
            styled_product = await self._style_match_product(
                product_image_url=product_image_url,
                lighting=analysis["lighting"],
                scene_context=analysis["scene_context"]
            )
        else:
            styled_product = product_image_url

        # Step 4: Composite into video
        output_url = await self._composite_with_ffmpeg(
            video_url=video_url,
            product_url=styled_product,
            insertion_zone=analysis["insertion_zone"],
            start_frame=analysis["best_frame_index"]
        )

        return {
            "success": True,
            "video_url": output_url,
            "insertion_zone": analysis["insertion_zone"],
            "scene_analysis": analysis["scene_context"]
        }

    async def _extract_key_frames(
        self,
        video_url: str,
        num_frames: int = 5
    ) -> list:
        """Extract evenly-spaced frames from video for analysis."""

        # Download video to temp file
        async with httpx.AsyncClient() as client:
            response = await client.get(video_url)

            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
                f.write(response.content)
                video_path = f.name

        try:
            # Get video duration
            result = subprocess.run([
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                video_path
            ], capture_output=True, text=True)

            duration = float(result.stdout.strip())
            interval = duration / (num_frames + 1)

            # Extract frames
            frames = []
            for i in range(1, num_frames + 1):
                timestamp = interval * i
                frame_path = f"/tmp/frame_{i}.jpg"

                subprocess.run([
                    "ffmpeg", "-y",
                    "-ss", str(timestamp),
                    "-i", video_path,
                    "-vframes", "1",
                    "-q:v", "2",
                    frame_path
                ], capture_output=True)

                # Upload frame and get URL (or use base64)
                # For now, return local path - in production, upload to S3
                frames.append(frame_path)

            return frames

        finally:
            os.unlink(video_path)

    async def _style_match_product(
        self,
        product_image_url: str,
        lighting: Dict,
        scene_context: Dict
    ) -> str:
        """
        Use SegMind to adjust product image to match scene lighting.
        """

        # Build adjustment prompt based on scene analysis
        adjustments = []

        if lighting:
            if lighting.get("color_temperature") == "warm":
                adjustments.append("add warm golden tones")
            elif lighting.get("color_temperature") == "cool":
                adjustments.append("add cool blue tones")

            if lighting.get("direction") == "left":
                adjustments.append("add shadow on right side")
            elif lighting.get("direction") == "right":
                adjustments.append("add shadow on left side")

            if lighting.get("intensity") == "low":
                adjustments.append("reduce brightness slightly")

        if not adjustments:
            return product_image_url

        # Use SegMind for image adjustment
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.segmind.com/v1/sdxl-img2img",
                headers={"x-api-key": self.segmind_key},
                json={
                    "image": product_image_url,
                    "prompt": f"same product, {', '.join(adjustments)}, photorealistic",
                    "negative_prompt": "distorted, different product, cartoon",
                    "strength": 0.3,  # Low strength to preserve product
                    "num_inference_steps": 25
                },
                timeout=60.0
            )

            if response.status_code == 200:
                # Return URL of adjusted image
                result = response.json()
                return result.get("image_url", product_image_url)

        return product_image_url

    async def _composite_with_ffmpeg(
        self,
        video_url: str,
        product_url: str,
        insertion_zone: Dict,
        start_frame: int
    ) -> str:
        """
        Composite product into video using FFmpeg.
        """

        # Download video and product
        async with httpx.AsyncClient() as client:
            video_resp = await client.get(video_url)
            product_resp = await client.get(product_url)

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as vf:
            vf.write(video_resp.content)
            video_path = vf.name

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as pf:
            pf.write(product_resp.content)
            product_path = pf.name

        output_path = tempfile.mktemp(suffix=".mp4")

        try:
            # Get video dimensions
            probe = subprocess.run([
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0",
                video_path
            ], capture_output=True, text=True)

            width, height = map(int, probe.stdout.strip().split(','))

            # Calculate overlay position from insertion zone
            zone = insertion_zone
            x = int(zone["position"]["x"] / 100 * width)
            y = int(zone["position"]["y"] / 100 * height)
            w = int(zone["size"]["width"] / 100 * width)
            h = int(zone["size"]["height"] / 100 * height)

            # Composite with FFmpeg
            subprocess.run([
                "ffmpeg", "-y",
                "-i", video_path,
                "-i", product_path,
                "-filter_complex",
                f"[1:v]scale={w}:{h}[product];[0:v][product]overlay={x}:{y}:enable='gte(n,{start_frame})'",
                "-c:a", "copy",
                output_path
            ], capture_output=True)

            # Upload to storage and return URL
            # For now, return local path
            return output_path

        finally:
            os.unlink(video_path)
            os.unlink(product_path)
```

**File:** `/backend/app/services/kata/video_generator.py` (Updated with Halftime approach)

```python
import httpx
import asyncio
from typing import Optional, Dict
from .scene_analyzer import GrokSceneAnalyzer
from .video_compositor import HalftimeCompositor

class VideoGenerator:
    """
    Kata Engine video generator using Halftime-style approach.
    Integrates:
    - Grok for scene analysis
    - SegMind for image generation/adjustment
    - ElevenLabs for voice synthesis
    - FFmpeg for video compositing
    """

    def __init__(
        self,
        xai_api_key: str,
        segmind_api_key: str,
        elevenlabs_api_key: str
    ):
        self.scene_analyzer = GrokSceneAnalyzer(xai_api_key)
        self.compositor = HalftimeCompositor(segmind_api_key, xai_api_key)
        self.elevenlabs_key = elevenlabs_api_key

    async def generate_synthetic_influencer(
        self,
        name: str,
        appearance: Dict,
        voice: Dict,
        script: str,
        style: str = "ugc",
        reference_images: list = None
    ) -> Dict:
        """
        Generate a synthetic influencer video.

        Pipeline:
        1. Generate/use reference face image (SegMind)
        2. Generate voice audio (ElevenLabs)
        3. Generate talking head video (SadTalker via Replicate)
        4. Apply UGC styling
        """

        # Step 1: Face image
        if reference_images and len(reference_images) > 0:
            face_url = reference_images[0]
        else:
            face_url = await self._generate_face(appearance)

        # Step 2: Voice synthesis
        audio_url = await self._generate_voice(script, voice)

        # Step 3: Talking head
        video_url = await self._generate_talking_head(face_url, audio_url)

        # Step 4: Apply UGC style
        final_url = await self._apply_ugc_style(video_url, style)

        return {
            "success": True,
            "video_url": final_url,
            "audio_url": audio_url,
            "face_url": face_url,
            "influencer_name": name
        }

    async def composite_product_placement(
        self,
        video_url: str,
        product_image_url: str,
        product_type: str = "beverage"
    ) -> Dict:
        """
        Insert product into video using Halftime-style context-aware placement.
        """
        return await self.compositor.composite_product(
            video_url=video_url,
            product_image_url=product_image_url,
            product_type=product_type,
            style_match=True
        )

    async def _generate_face(self, appearance: Dict) -> str:
        """Generate face image using SegMind."""

        prompt = f"""photorealistic portrait, {appearance.get('age', 'young')} {appearance.get('gender', 'person')},
        {appearance.get('ethnicity', '')}, {appearance.get('hair', '')},
        {appearance.get('style', 'professional')}, neutral background,
        looking at camera, high quality, 4k"""

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.segmind.com/v1/sdxl1.0-txt2img",
                headers={"x-api-key": self.compositor.segmind_key},
                json={
                    "prompt": prompt,
                    "negative_prompt": "cartoon, anime, illustration, painting, distorted",
                    "samples": 1,
                    "scheduler": "UniPC",
                    "num_inference_steps": 30,
                    "guidance_scale": 7.5,
                    "seed": -1,
                    "img_width": 768,
                    "img_height": 768
                },
                timeout=60.0
            )

            result = response.json()
            return result.get("image")

    async def _generate_voice(self, text: str, voice_config: Dict) -> str:
        """Generate voice audio using ElevenLabs."""

        voice_id = voice_config.get("voice_id", "21m00Tcm4TlvDq8ikWAM")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                headers={
                    "xi-api-key": self.elevenlabs_key,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": voice_config.get("stability", 0.5),
                        "similarity_boost": voice_config.get("similarity", 0.75)
                    }
                },
                timeout=60.0
            )

            # Save audio and return URL
            # In production, upload to S3
            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(response.content)
                return f.name

    async def _generate_talking_head(
        self,
        face_url: str,
        audio_url: str
    ) -> str:
        """Generate talking head video using SadTalker."""

        import replicate

        output = replicate.run(
            "cjwbw/sadtalker:3aa3dac9353cc4d6bd62a8f95957bd844003b401ca4e4a9b33baa574c549d376",
            input={
                "source_image": face_url,
                "driven_audio": audio_url,
                "preprocess": "crop",
                "still_mode": False,
                "expression_scale": 1.0
            }
        )

        return output

    async def _apply_ugc_style(self, video_url: str, style: str) -> str:
        """Apply UGC-style effects to video."""

        style_filters = {
            "tiktok": "[0:v]crop=ih*9/16:ih,scale=1080:1920,eq=saturation=1.2:contrast=1.1[v]",
            "instagram": "[0:v]crop=min(iw\\,ih):min(iw\\,ih),scale=1080:1080,eq=saturation=1.1[v]",
            "youtube": "[0:v]scale=1920:1080,eq=contrast=1.05[v]",
            "raw": "[0:v]copy[v]"
        }

        import subprocess
        import tempfile

        filter_chain = style_filters.get(style, style_filters["raw"])
        output_path = tempfile.mktemp(suffix=".mp4")

        subprocess.run([
            "ffmpeg", "-y",
            "-i", video_url,
            "-filter_complex", filter_chain,
            "-map", "[v]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-c:a", "aac",
            output_path
        ], capture_output=True)

        return output_path
```

**Update:** `/backend/app/api/kata.py` - Full Halftime-style endpoints

```python
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, List, Optional
import uuid
import asyncio

from app.core.config import settings
from app.services.kata.video_generator import VideoGenerator
from app.services.kata.scene_analyzer import GrokSceneAnalyzer

router = APIRouter(prefix="/kata", tags=["kata"])

# Initialize services
video_gen = VideoGenerator(
    xai_api_key=settings.xai_api_key,
    segmind_api_key=settings.segmind_api_key,
    elevenlabs_api_key=settings.elevenlabs_api_key
)

scene_analyzer = GrokSceneAnalyzer(settings.xai_api_key)

# Job storage (use Redis in production)
_jobs: Dict[str, Dict] = {}

class SyntheticInfluencerRequest(BaseModel):
    name: str
    appearance: Dict
    voice: Dict
    script: str
    style: str = "ugc"
    reference_images: List[str] = []

class ProductPlacementRequest(BaseModel):
    video_url: str
    product_image_url: str
    product_type: str = "beverage"

class SceneAnalysisRequest(BaseModel):
    video_url: str
    num_frames: int = 5

@router.post("/synthetic-influencer")
async def create_synthetic_influencer(
    request: SyntheticInfluencerRequest,
    background_tasks: BackgroundTasks
):
    """Generate synthetic influencer video using Halftime-style pipeline."""

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Initializing..."
    }

    async def process():
        try:
            _jobs[job_id]["status"] = "in_progress"
            _jobs[job_id]["message"] = "Generating face image..."
            _jobs[job_id]["progress"] = 10

            result = await video_gen.generate_synthetic_influencer(
                name=request.name,
                appearance=request.appearance,
                voice=request.voice,
                script=request.script,
                style=request.style,
                reference_images=request.reference_images
            )

            _jobs[job_id]["status"] = "complete"
            _jobs[job_id]["progress"] = 100
            _jobs[job_id]["result"] = result

        except Exception as e:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(e)

    background_tasks.add_task(lambda: asyncio.run(process()))

    return {"job_id": job_id, "status": "pending"}

@router.post("/composite-product")
async def composite_product(
    request: ProductPlacementRequest,
    background_tasks: BackgroundTasks
):
    """
    Insert product into video using Halftime-style context-aware compositing.
    Uses Grok for scene analysis and SegMind for style matching.
    """

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "pending",
        "progress": 0,
        "message": "Analyzing scene..."
    }

    async def process():
        try:
            _jobs[job_id]["status"] = "in_progress"

            _jobs[job_id]["message"] = "Analyzing video with Grok..."
            _jobs[job_id]["progress"] = 20

            result = await video_gen.composite_product_placement(
                video_url=request.video_url,
                product_image_url=request.product_image_url,
                product_type=request.product_type
            )

            _jobs[job_id]["status"] = "complete"
            _jobs[job_id]["progress"] = 100
            _jobs[job_id]["result"] = result

        except Exception as e:
            _jobs[job_id]["status"] = "failed"
            _jobs[job_id]["error"] = str(e)

    background_tasks.add_task(lambda: asyncio.run(process()))

    return {"job_id": job_id, "status": "pending"}

@router.post("/analyze-scene")
async def analyze_scene(request: SceneAnalysisRequest):
    """
    Analyze video for insertion zones using Grok.
    Returns potential product placement opportunities.
    """

    frames = await video_gen.compositor._extract_key_frames(
        request.video_url,
        request.num_frames
    )

    analysis = await scene_analyzer.analyze_video_segment(
        frames=frames,
        product_type="any"
    )

    return {
        "analysis": analysis,
        "insertion_zones": analysis.get("insertion_zone"),
        "scene_context": analysis.get("scene_context"),
        "recommendation": _generate_placement_recommendation(analysis)
    }

def _generate_placement_recommendation(analysis: Dict) -> str:
    """Generate human-readable recommendation from analysis."""

    zone = analysis.get("insertion_zone")
    if not zone:
        return "No suitable insertion zones found in this video."

    context = analysis.get("scene_context", {})

    return f"""
    Best placement opportunity found:
    - Zone type: {zone.get('type')}
    - Position: {zone.get('position')}
    - Confidence: {zone.get('confidence', 0) * 100:.0f}%
    - Scene: {context.get('setting', 'Unknown')}
    - Mood: {context.get('mood', 'Unknown')}
    - Recommendation: {zone.get('natural_fit', 'Place product naturally in this zone')}
    """

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get job status and progress."""

    if job_id not in _jobs:
        raise HTTPException(404, "Job not found")

    return _jobs[job_id]

@router.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str):
    """Get completed job result."""

    if job_id not in _jobs:
        raise HTTPException(404, "Job not found")

    job = _jobs[job_id]

    if job["status"] != "complete":
        raise HTTPException(400, f"Job not complete. Status: {job['status']}")

    return job.get("result")
```

### Environment Variables for Kata

```env
# XAI/Grok (for scene analysis - Halftime style)
XAI_API_KEY=your-xai-api-key

# SegMind (for image generation and style matching)
SEGMIND_API_KEY=your-segmind-api-key

# ElevenLabs (for voice synthesis)
ELEVENLABS_API_KEY=your-elevenlabs-api-key

# Replicate (for video generation models)
REPLICATE_API_KEY=your-replicate-api-key
```

---

## 3.5 Email & Newsletter Generation

**Problem:** No system to create marketing emails or newsletters from campaign content.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    EMAIL GENERATION PIPELINE                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │   BRAND DNA  │    │   CAMPAIGN   │    │   TEMPLATE   │       │
│  │   Colors     │ +  │   Content    │ +  │   Selection  │       │
│  │   Fonts      │    │   Goals      │    │   or Custom  │       │
│  │   Voice      │    │   CTA        │    │              │       │
│  └──────────────┘    └──────────────┘    └──────────────┘       │
│         │                   │                   │                │
│         └───────────────────┼───────────────────┘                │
│                             ▼                                    │
│                  ┌──────────────────┐                            │
│                  │   AI GENERATOR   │                            │
│                  │   (OpenRouter)   │                            │
│                  └────────┬─────────┘                            │
│                           │                                      │
│                           ▼                                      │
│         ┌─────────────────────────────────────┐                  │
│         │         REACT EMAIL / MJML          │                  │
│         │     Template Compilation Engine     │                  │
│         └─────────────────────────────────────┘                  │
│                           │                                      │
│              ┌────────────┼────────────┐                         │
│              ▼            ▼            ▼                         │
│         ┌────────┐  ┌────────┐  ┌────────┐                      │
│         │  HTML  │  │  MJML  │  │  JSON  │                      │
│         │ Output │  │ Source │  │ Config │                      │
│         └────────┘  └────────┘  └────────┘                      │
│                           │                                      │
│                           ▼                                      │
│         ┌─────────────────────────────────────┐                  │
│         │      ESP INTEGRATION (Optional)     │                  │
│         │  SendGrid | Mailchimp | Resend      │                  │
│         └─────────────────────────────────────┘                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Backend Implementation

**File:** `/backend/app/services/email_generator.py`

```python
from typing import Dict, List, Optional
import httpx
from jinja2 import Environment, BaseLoader

from app.services.openrouter import OpenRouterService

class EmailGenerator:
    """
    Generates marketing emails and newsletters using AI + templates.
    Applies brand DNA for consistent styling.
    """

    def __init__(self, openrouter: OpenRouterService):
        self.openrouter = openrouter
        self.jinja = Environment(loader=BaseLoader())

    async def generate_email(
        self,
        email_type: str,
        campaign: Dict,
        brand_dna: Dict,
        custom_prompt: Optional[str] = None
    ) -> Dict:
        """
        Generate a marketing email based on campaign and brand.

        Args:
            email_type: 'promotional', 'newsletter', 'welcome', 'announcement', 'nurture'
            campaign: Campaign data including goals, audience, content
            brand_dna: Brand colors, fonts, voice, tone
            custom_prompt: Optional custom instructions

        Returns:
            Dict with subject, preheader, html, mjml, and plaintext versions
        """

        type_prompts = {
            "promotional": "Create a promotional email that drives conversions",
            "newsletter": "Create an engaging newsletter with multiple content sections",
            "welcome": "Create a warm welcome email for new subscribers",
            "announcement": "Create an announcement email for news or updates",
            "nurture": "Create a nurturing email that builds relationship"
        }

        prompt = f"""
        {type_prompts.get(email_type, type_prompts['promotional'])}

        BRAND DNA:
        - Brand name: {brand_dna.get('name', 'Brand')}
        - Voice: {brand_dna.get('voice', 'Professional')}
        - Tone: {brand_dna.get('tone', 'Friendly')}
        - Key messaging: {brand_dna.get('key_messaging', '')}

        CAMPAIGN CONTEXT:
        - Name: {campaign.get('name', '')}
        - Goal: {campaign.get('goal', '')}
        - Target audience: {campaign.get('target_audience', '')}
        - Key message: {campaign.get('brief_data', {}).get('key_message', '')}
        - Call to action: {campaign.get('cta', 'Learn More')}

        {custom_prompt or ''}

        Generate JSON with:
        {{
            "subject": "Email subject line (compelling, under 60 chars)",
            "preheader": "Preview text (under 100 chars)",
            "headline": "Main headline",
            "body_sections": [
                {{"type": "intro", "content": "Opening paragraph"}},
                {{"type": "feature", "title": "Feature title", "content": "Feature description"}},
                {{"type": "cta", "text": "Button text", "url_placeholder": "[CTA_URL]"}}
            ],
            "footer_text": "Footer content",
            "unsubscribe_text": "Unsubscribe link text"
        }}
        """

        result = await self.openrouter.complete(
            prompt=prompt,
            system_prompt="You are an expert email marketer. Generate compelling email content that matches the brand voice.",
            response_format="json"
        )

        # Parse result and generate MJML
        content = result if isinstance(result, dict) else eval(result)
        mjml = self._generate_mjml(content, brand_dna)
        html = await self._compile_mjml(mjml)

        return {
            "content": content,
            "mjml": mjml,
            "html": html,
            "plaintext": self._generate_plaintext(content),
            "email_type": email_type
        }

    def _generate_mjml(self, content: Dict, brand_dna: Dict) -> str:
        """Generate MJML template from content and brand DNA."""

        colors = brand_dna.get('colors', {})
        primary_color = colors.get('primary', '#1a73e8')
        secondary_color = colors.get('secondary', '#ffffff')
        text_color = colors.get('text', '#333333')

        fonts = brand_dna.get('fonts', {})
        heading_font = fonts.get('heading', 'Arial, sans-serif')
        body_font = fonts.get('body', 'Arial, sans-serif')

        mjml = f"""
        <mjml>
          <mj-head>
            <mj-attributes>
              <mj-all font-family="{body_font}" />
              <mj-text color="{text_color}" />
              <mj-button background-color="{primary_color}" />
            </mj-attributes>
            <mj-style>
              h1 {{ font-family: {heading_font}; }}
            </mj-style>
          </mj-head>
          <mj-body background-color="#f4f4f4">
            <mj-section background-color="{secondary_color}" padding="20px">
              <mj-column>
                <mj-text font-size="28px" font-weight="bold" align="center">
                  {content.get('headline', '')}
                </mj-text>
              </mj-column>
            </mj-section>
        """

        # Add body sections
        for section in content.get('body_sections', []):
            if section.get('type') == 'intro':
                mjml += f"""
            <mj-section background-color="{secondary_color}" padding="20px">
              <mj-column>
                <mj-text font-size="16px" line-height="1.5">
                  {section.get('content', '')}
                </mj-text>
              </mj-column>
            </mj-section>
                """
            elif section.get('type') == 'feature':
                mjml += f"""
            <mj-section background-color="{secondary_color}" padding="20px">
              <mj-column>
                <mj-text font-size="20px" font-weight="bold">
                  {section.get('title', '')}
                </mj-text>
                <mj-text font-size="16px" line-height="1.5">
                  {section.get('content', '')}
                </mj-text>
              </mj-column>
            </mj-section>
                """
            elif section.get('type') == 'cta':
                mjml += f"""
            <mj-section background-color="{secondary_color}" padding="20px">
              <mj-column>
                <mj-button href="{section.get('url_placeholder', '#')}"
                           font-size="16px" padding="15px 30px">
                  {section.get('text', 'Learn More')}
                </mj-button>
              </mj-column>
            </mj-section>
                """

        # Footer
        mjml += f"""
            <mj-section background-color="#333333" padding="20px">
              <mj-column>
                <mj-text color="#ffffff" font-size="12px" align="center">
                  {content.get('footer_text', '')}
                </mj-text>
                <mj-text color="#888888" font-size="10px" align="center">
                  {content.get('unsubscribe_text', 'Unsubscribe from these emails')}
                </mj-text>
              </mj-column>
            </mj-section>
          </mj-body>
        </mjml>
        """

        return mjml

    async def _compile_mjml(self, mjml: str) -> str:
        """Compile MJML to HTML using mjml-api or local compiler."""

        # Option 1: Use MJML API
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.mjml.io/v1/render",
                json={"mjml": mjml},
                headers={"Authorization": f"Basic {self.mjml_api_key}"},
                timeout=30.0
            )
            if response.status_code == 200:
                return response.json().get("html", "")

        # Option 2: Fallback to basic HTML conversion
        return self._basic_html_fallback(mjml)

    def _generate_plaintext(self, content: Dict) -> str:
        """Generate plaintext version of email."""

        lines = [
            content.get('headline', ''),
            '',
        ]

        for section in content.get('body_sections', []):
            if section.get('type') == 'intro':
                lines.append(section.get('content', ''))
                lines.append('')
            elif section.get('type') == 'feature':
                lines.append(f"** {section.get('title', '')} **")
                lines.append(section.get('content', ''))
                lines.append('')
            elif section.get('type') == 'cta':
                lines.append(f">>> {section.get('text', '')} <<<")
                lines.append('')

        lines.append('---')
        lines.append(content.get('footer_text', ''))
        lines.append(content.get('unsubscribe_text', ''))

        return '\n'.join(lines)
```

**File:** `/backend/app/api/emails.py`

```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List

from app.core.database import get_db
from app.core.config import settings
from app.services.email_generator import EmailGenerator
from app.services.openrouter import OpenRouterService

router = APIRouter(prefix="/emails", tags=["emails"])

class EmailGenerateRequest(BaseModel):
    campaign_id: str
    email_type: str = "promotional"  # promotional, newsletter, welcome, announcement, nurture
    custom_prompt: Optional[str] = None

class EmailPreviewRequest(BaseModel):
    mjml: str

@router.post("/generate")
async def generate_email(request: EmailGenerateRequest, db = Depends(get_db)):
    """Generate a marketing email based on campaign and brand."""

    # Get campaign and organization
    campaign = await db.get(Campaign, request.campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    org = await db.get(Organization, campaign.organization_id)
    kb = await db.get(KnowledgeBase, org.id)

    # Initialize services
    openrouter = OpenRouterService(settings.openrouter_api_key)
    email_gen = EmailGenerator(openrouter)

    # Generate email
    result = await email_gen.generate_email(
        email_type=request.email_type,
        campaign={
            "name": campaign.name,
            "goal": campaign.brief_data.get("goal") if campaign.brief_data else "",
            "target_audience": campaign.brief_data.get("target_audience") if campaign.brief_data else "",
            "brief_data": campaign.brief_data,
            "cta": campaign.brief_data.get("cta") if campaign.brief_data else "Learn More"
        },
        brand_dna=kb.brand_dna if kb else {},
        custom_prompt=request.custom_prompt
    )

    # Save as deliverable
    deliverable = Deliverable(
        campaign_id=campaign.id,
        title=f"Email: {result['content'].get('subject', 'Marketing Email')}",
        type="email",
        content=result,
        status="draft"
    )
    db.add(deliverable)
    await db.commit()

    return {
        "deliverable_id": deliverable.id,
        **result
    }

@router.post("/preview")
async def preview_mjml(request: EmailPreviewRequest):
    """Convert MJML to HTML preview."""

    openrouter = OpenRouterService(settings.openrouter_api_key)
    email_gen = EmailGenerator(openrouter)

    html = await email_gen._compile_mjml(request.mjml)

    return {"html": html}

@router.get("/templates")
async def list_templates():
    """List available email templates."""

    return {
        "templates": [
            {"id": "promotional", "name": "Promotional", "description": "Sales and promotional content"},
            {"id": "newsletter", "name": "Newsletter", "description": "Multi-section newsletter"},
            {"id": "welcome", "name": "Welcome", "description": "New subscriber welcome"},
            {"id": "announcement", "name": "Announcement", "description": "News and updates"},
            {"id": "nurture", "name": "Nurture", "description": "Relationship building"}
        ]
    }
```

---

## 3.6 Landing Page & Website Generation

**Problem:** No system to create landing pages or full websites from campaign content.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│               LANDING PAGE / WEBSITE GENERATOR                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUT SOURCES                                                   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │   BRAND DNA  │ │   CAMPAIGN   │ │ USER PROMPT  │             │
│  │   Colors     │ │   Content    │ │ "I want a    │             │
│  │   Fonts      │ │   Assets     │ │  landing pg  │             │
│  │   Logo URL   │ │   Images     │ │  for..."     │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│                                                                  │
│                       ┌──────────────┐                          │
│                       │   PLANNER    │                          │
│                       │  (Grok/GPT)  │                          │
│                       │  - Sections  │                          │
│                       │  - Layout    │                          │
│                       │  - Copy      │                          │
│                       └──────────────┘                          │
│                              │                                   │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│       ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│       │  SIMPLE  │    │  REACT/  │    │   FULL   │             │
│       │   HTML   │    │  NEXT.JS │    │   SITE   │             │
│       │ +Tailwind│    │  EXPORT  │    │  (v0.dev)│             │
│       └──────────┘    └──────────┘    └──────────┘             │
│                                                                  │
│  OUTPUT:                                                         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  • Downloadable HTML/CSS/JS bundle                         │ │
│  │  • Next.js project scaffold                                │ │
│  │  • Hosted preview URL                                      │ │
│  │  • Component library export                                │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Implementation Approach

**Option A: Simple HTML + Tailwind (Built-in)**
- AI generates structured content
- Apply brand colors via CSS variables
- Output static HTML files
- Best for: Quick landing pages, email captures

**Option B: React/Next.js Export (Advanced)**
- AI generates React components
- Use shadcn/ui for polished UI
- Export as Next.js project
- Best for: Marketing sites, multi-page sites

**Option C: v0.dev Integration (Premium)**
- Send prompt to v0.dev API (if available)
- Get production-ready Next.js code
- Higher quality, more complex layouts
- Best for: Complex landing pages, full websites

### Backend Implementation

**File:** `/backend/app/services/landing_page_generator.py`

```python
from typing import Dict, List, Optional
import json

from app.services.openrouter import OpenRouterService

class LandingPageGenerator:
    """
    Generates landing pages and websites with brand-consistent design.
    """

    def __init__(self, openrouter: OpenRouterService):
        self.openrouter = openrouter

    async def generate_landing_page(
        self,
        page_type: str,
        campaign: Dict,
        brand_dna: Dict,
        custom_prompt: Optional[str] = None,
        output_format: str = "html"  # html, react, nextjs
    ) -> Dict:
        """
        Generate a landing page based on campaign and brand.

        Args:
            page_type: 'product', 'signup', 'event', 'download', 'coming_soon'
            campaign: Campaign data
            brand_dna: Brand styling information
            output_format: 'html', 'react', 'nextjs'

        Returns:
            Dict with generated code and preview URL
        """

        # Step 1: Plan the page structure
        plan = await self._plan_page_structure(page_type, campaign, brand_dna, custom_prompt)

        # Step 2: Generate the code
        if output_format == "html":
            code = await self._generate_html_tailwind(plan, brand_dna)
        elif output_format == "react":
            code = await self._generate_react(plan, brand_dna)
        elif output_format == "nextjs":
            code = await self._generate_nextjs(plan, brand_dna)

        return {
            "plan": plan,
            "code": code,
            "output_format": output_format,
            "brand_applied": True
        }

    async def _plan_page_structure(
        self,
        page_type: str,
        campaign: Dict,
        brand_dna: Dict,
        custom_prompt: Optional[str]
    ) -> Dict:
        """Use AI to plan page sections and content."""

        type_guidance = {
            "product": "Create a product landing page with hero, features, testimonials, and CTA",
            "signup": "Create a signup/lead capture page with compelling value proposition",
            "event": "Create an event landing page with details, speakers, agenda, and registration",
            "download": "Create a download/lead magnet page with preview and form",
            "coming_soon": "Create a coming soon page with teaser and email capture"
        }

        prompt = f"""
        {type_guidance.get(page_type, type_guidance['product'])}

        BRAND:
        - Name: {brand_dna.get('name', 'Brand')}
        - Tagline: {brand_dna.get('tagline', '')}
        - Voice: {brand_dna.get('voice', 'Professional')}

        CAMPAIGN:
        - Name: {campaign.get('name', '')}
        - Goal: {campaign.get('goal', '')}
        - Key message: {campaign.get('brief_data', {}).get('key_message', '')}
        - Target audience: {campaign.get('target_audience', '')}

        {custom_prompt or ''}

        Generate a JSON structure for the landing page:
        {{
            "meta": {{
                "title": "Page title for browser tab",
                "description": "Meta description for SEO"
            }},
            "sections": [
                {{
                    "type": "hero",
                    "headline": "Main headline",
                    "subheadline": "Supporting text",
                    "cta_text": "Button text",
                    "cta_url": "#signup",
                    "background_style": "gradient|image|solid"
                }},
                {{
                    "type": "features",
                    "headline": "Section headline",
                    "items": [
                        {{"icon": "icon-name", "title": "Feature 1", "description": "Description"}},
                        {{"icon": "icon-name", "title": "Feature 2", "description": "Description"}},
                        {{"icon": "icon-name", "title": "Feature 3", "description": "Description"}}
                    ]
                }},
                {{
                    "type": "testimonials",
                    "headline": "What customers say",
                    "items": [
                        {{"quote": "Testimonial text", "author": "Name", "role": "Title"}}
                    ]
                }},
                {{
                    "type": "cta",
                    "headline": "Ready to get started?",
                    "subheadline": "Supporting text",
                    "cta_text": "Get Started",
                    "cta_url": "#"
                }},
                {{
                    "type": "footer",
                    "links": [
                        {{"text": "Privacy", "url": "/privacy"}},
                        {{"text": "Terms", "url": "/terms"}}
                    ],
                    "copyright": "© 2026 Brand Name"
                }}
            ]
        }}
        """

        result = await self.openrouter.complete(
            prompt=prompt,
            system_prompt="You are an expert landing page designer. Create compelling, conversion-focused page structures.",
            response_format="json"
        )

        return result if isinstance(result, dict) else json.loads(result)

    async def _generate_html_tailwind(self, plan: Dict, brand_dna: Dict) -> Dict:
        """Generate HTML with Tailwind CSS."""

        colors = brand_dna.get('colors', {})
        primary = colors.get('primary', '#1a73e8')
        secondary = colors.get('secondary', '#ffffff')

        # Build HTML sections
        html_sections = []

        for section in plan.get('sections', []):
            section_html = await self._render_section_html(section, brand_dna)
            html_sections.append(section_html)

        # Full HTML document
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{plan.get('meta', {}).get('title', 'Landing Page')}</title>
    <meta name="description" content="{plan.get('meta', {}).get('description', '')}">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {{
            theme: {{
                extend: {{
                    colors: {{
                        primary: '{primary}',
                        secondary: '{secondary}'
                    }}
                }}
            }}
        }}
    </script>
    <style>
        :root {{
            --primary: {primary};
            --secondary: {secondary};
        }}
    </style>
</head>
<body class="bg-white text-gray-900">
    {''.join(html_sections)}
</body>
</html>
        """

        return {
            "html": html,
            "files": {
                "index.html": html
            }
        }

    async def _render_section_html(self, section: Dict, brand_dna: Dict) -> str:
        """Render a single section to HTML."""

        section_type = section.get('type')

        if section_type == 'hero':
            return f"""
    <section class="bg-gradient-to-r from-primary to-blue-600 text-white py-20 px-4">
        <div class="max-w-4xl mx-auto text-center">
            <h1 class="text-5xl font-bold mb-6">{section.get('headline', '')}</h1>
            <p class="text-xl mb-8 opacity-90">{section.get('subheadline', '')}</p>
            <a href="{section.get('cta_url', '#')}"
               class="bg-white text-primary px-8 py-4 rounded-lg font-semibold hover:bg-opacity-90 transition">
                {section.get('cta_text', 'Get Started')}
            </a>
        </div>
    </section>
            """

        elif section_type == 'features':
            items_html = ""
            for item in section.get('items', []):
                items_html += f"""
                <div class="text-center p-6">
                    <div class="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mx-auto mb-4">
                        <span class="text-primary text-2xl">★</span>
                    </div>
                    <h3 class="text-xl font-semibold mb-2">{item.get('title', '')}</h3>
                    <p class="text-gray-600">{item.get('description', '')}</p>
                </div>
                """

            return f"""
    <section class="py-20 px-4 bg-gray-50">
        <div class="max-w-6xl mx-auto">
            <h2 class="text-3xl font-bold text-center mb-12">{section.get('headline', '')}</h2>
            <div class="grid md:grid-cols-3 gap-8">
                {items_html}
            </div>
        </div>
    </section>
            """

        elif section_type == 'testimonials':
            items_html = ""
            for item in section.get('items', []):
                items_html += f"""
                <div class="bg-white p-6 rounded-lg shadow-md">
                    <p class="text-gray-600 italic mb-4">"{item.get('quote', '')}"</p>
                    <div class="font-semibold">{item.get('author', '')}</div>
                    <div class="text-sm text-gray-500">{item.get('role', '')}</div>
                </div>
                """

            return f"""
    <section class="py-20 px-4">
        <div class="max-w-6xl mx-auto">
            <h2 class="text-3xl font-bold text-center mb-12">{section.get('headline', '')}</h2>
            <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                {items_html}
            </div>
        </div>
    </section>
            """

        elif section_type == 'cta':
            return f"""
    <section class="py-20 px-4 bg-primary text-white">
        <div class="max-w-4xl mx-auto text-center">
            <h2 class="text-3xl font-bold mb-4">{section.get('headline', '')}</h2>
            <p class="text-xl mb-8 opacity-90">{section.get('subheadline', '')}</p>
            <a href="{section.get('cta_url', '#')}"
               class="bg-white text-primary px-8 py-4 rounded-lg font-semibold hover:bg-opacity-90 transition">
                {section.get('cta_text', 'Get Started')}
            </a>
        </div>
    </section>
            """

        elif section_type == 'footer':
            links_html = ""
            for link in section.get('links', []):
                links_html += f'<a href="{link.get("url", "#")}" class="hover:text-white transition">{link.get("text", "")}</a>'

            return f"""
    <footer class="py-12 px-4 bg-gray-900 text-gray-400">
        <div class="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center">
            <div class="mb-4 md:mb-0">{section.get('copyright', '')}</div>
            <div class="flex space-x-6">
                {links_html}
            </div>
        </div>
    </footer>
            """

        return ""

    async def _generate_react(self, plan: Dict, brand_dna: Dict) -> Dict:
        """Generate React components with Tailwind."""

        prompt = f"""
        Generate a complete React landing page component using:
        - Tailwind CSS for styling
        - Modern React patterns (functional components, hooks)
        - Accessible HTML structure

        Brand colors:
        - Primary: {brand_dna.get('colors', {}).get('primary', '#1a73e8')}
        - Secondary: {brand_dna.get('colors', {}).get('secondary', '#ffffff')}

        Page structure:
        {json.dumps(plan, indent=2)}

        Generate a single React component file that renders the entire landing page.
        Use inline Tailwind classes. Make it production-ready.
        """

        result = await self.openrouter.complete(
            prompt=prompt,
            system_prompt="You are an expert React developer. Generate clean, production-ready code."
        )

        return {
            "jsx": result,
            "files": {
                "LandingPage.jsx": result
            }
        }

    async def _generate_nextjs(self, plan: Dict, brand_dna: Dict) -> Dict:
        """Generate a Next.js project structure."""

        # Generate main page
        page_component = await self._generate_react(plan, brand_dna)

        # Create project structure
        files = {
            "package.json": json.dumps({
                "name": "landing-page",
                "version": "1.0.0",
                "scripts": {
                    "dev": "next dev",
                    "build": "next build",
                    "start": "next start"
                },
                "dependencies": {
                    "next": "^14.0.0",
                    "react": "^18.2.0",
                    "react-dom": "^18.2.0"
                },
                "devDependencies": {
                    "tailwindcss": "^3.4.0",
                    "autoprefixer": "^10.4.0",
                    "postcss": "^8.4.0"
                }
            }, indent=2),
            "app/page.jsx": page_component.get("jsx", ""),
            "app/layout.jsx": f"""
import './globals.css'

export const metadata = {{
  title: '{plan.get("meta", {}).get("title", "Landing Page")}',
  description: '{plan.get("meta", {}).get("description", "")}',
}}

export default function RootLayout({{ children }}) {{
  return (
    <html lang="en">
      <body>{{children}}</body>
    </html>
  )
}}
            """,
            "app/globals.css": f"""
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {{
  --primary: {brand_dna.get('colors', {}).get('primary', '#1a73e8')};
  --secondary: {brand_dna.get('colors', {}).get('secondary', '#ffffff')};
}}
            """,
            "tailwind.config.js": f"""
module.exports = {{
  content: ['./app/**/*.{{js,jsx}}'],
  theme: {{
    extend: {{
      colors: {{
        primary: '{brand_dna.get("colors", {}).get("primary", "#1a73e8")}',
        secondary: '{brand_dna.get("colors", {}).get("secondary", "#ffffff")}'
      }}
    }}
  }},
  plugins: []
}}
            """
        }

        return {
            "files": files,
            "instructions": """
To run this Next.js project:
1. Extract files to a new directory
2. Run: npm install
3. Run: npm run dev
4. Open http://localhost:3000
            """
        }
```

**File:** `/backend/app/api/landing_pages.py`

```python
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.config import settings
from app.services.landing_page_generator import LandingPageGenerator
from app.services.openrouter import OpenRouterService

router = APIRouter(prefix="/landing-pages", tags=["landing-pages"])

class GenerateRequest(BaseModel):
    campaign_id: str
    page_type: str = "product"  # product, signup, event, download, coming_soon
    output_format: str = "html"  # html, react, nextjs
    custom_prompt: Optional[str] = None

@router.post("/generate")
async def generate_landing_page(request: GenerateRequest, db = Depends(get_db)):
    """Generate a landing page from campaign data."""

    # Get campaign and organization
    campaign = await db.get(Campaign, request.campaign_id)
    if not campaign:
        raise HTTPException(404, "Campaign not found")

    org = await db.get(Organization, campaign.organization_id)
    kb = await db.get(KnowledgeBase, org.id)

    # Initialize generator
    openrouter = OpenRouterService(settings.openrouter_api_key)
    generator = LandingPageGenerator(openrouter)

    # Generate page
    result = await generator.generate_landing_page(
        page_type=request.page_type,
        campaign={
            "name": campaign.name,
            "goal": campaign.brief_data.get("goal") if campaign.brief_data else "",
            "target_audience": campaign.brief_data.get("target_audience") if campaign.brief_data else "",
            "brief_data": campaign.brief_data
        },
        brand_dna=kb.brand_dna if kb else {},
        custom_prompt=request.custom_prompt,
        output_format=request.output_format
    )

    # Save as deliverable
    deliverable = Deliverable(
        campaign_id=campaign.id,
        title=f"Landing Page: {result['plan'].get('meta', {}).get('title', 'Landing Page')}",
        type="landing_page",
        content=result,
        status="draft"
    )
    db.add(deliverable)
    await db.commit()

    return {
        "deliverable_id": deliverable.id,
        **result
    }

@router.get("/templates")
async def list_page_templates():
    """List available page templates."""

    return {
        "templates": [
            {"id": "product", "name": "Product", "description": "Product landing page with features and testimonials"},
            {"id": "signup", "name": "Signup", "description": "Lead capture page with value proposition"},
            {"id": "event", "name": "Event", "description": "Event page with agenda and registration"},
            {"id": "download", "name": "Download", "description": "Lead magnet download page"},
            {"id": "coming_soon", "name": "Coming Soon", "description": "Teaser page with email capture"}
        ],
        "output_formats": [
            {"id": "html", "name": "HTML + Tailwind", "description": "Simple static HTML file"},
            {"id": "react", "name": "React Component", "description": "React component with Tailwind"},
            {"id": "nextjs", "name": "Next.js Project", "description": "Full Next.js project scaffold"}
        ]
    }
```

### Frontend Integration

Add these components to the Dashboard:

**In Campaigns View - New Deliverable Types:**
```
┌────────────────────────────────────────────────────────────────────┐
│  CREATE DELIVERABLE                                                │
│                                                                     │
│  What would you like to create?                                    │
│                                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │ 📝 Social    │ │ 📧 Email     │ │ 🌐 Landing   │               │
│  │    Post      │ │              │ │    Page      │               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
│                                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │
│  │ 🎬 Video     │ │ 🖼️ Image     │ │ 📰 Blog      │               │
│  │    Script    │ │              │ │    Post      │               │
│  └──────────────┘ └──────────────┘ └──────────────┘               │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

**Email Generator Modal:**
```
┌────────────────────────────────────────────────────────────────────┐
│  GENERATE EMAIL                                       [✕ Close]    │
│                                                                     │
│  Email Type: [Promotional ▼]                                       │
│                                                                     │
│  Custom Instructions (optional):                                   │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ Focus on the limited-time offer and urgency...             │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [Generate Email]                                                  │
│                                                                     │
│  ─── PREVIEW ───────────────────────────────────────────────────   │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ Subject: 🎉 Last Chance: 40% Off Ends Tonight!            │   │
│  │                                                            │   │
│  │ [Email preview rendered here]                              │   │
│  │                                                            │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [Edit MJML]  [Download HTML]  [Save as Deliverable]              │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

**Landing Page Generator Modal:**
```
┌────────────────────────────────────────────────────────────────────┐
│  GENERATE LANDING PAGE                                [✕ Close]    │
│                                                                     │
│  Page Type: [Product Launch ▼]                                     │
│                                                                     │
│  Output Format:                                                     │
│  ○ HTML + Tailwind (Simple, ready to deploy)                       │
│  ○ React Component (For React projects)                            │
│  ○ Next.js Project (Full project scaffold)                         │
│                                                                     │
│  Custom Instructions (optional):                                   │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │ Add a comparison table and FAQ section...                  │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [Generate Page]                                                   │
│                                                                     │
│  ─── PREVIEW ───────────────────────────────────────────────────   │
│                                                                     │
│  [Desktop] [Tablet] [Mobile]                                       │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │                                                            │   │
│  │  [Live preview of generated landing page]                  │   │
│  │                                                            │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [Edit Code]  [Download ZIP]  [Deploy to Preview]                  │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## 3.7 Multi-User Collaboration (Future)

This is a larger feature that would include:
- Real-time presence (who's viewing what)
- Collaborative editing with conflict resolution
- Comments and mentions
- Activity feed
- Notifications

**Estimated effort:** 3-5 days additional

---

## 3.6 Billing/Subscriptions (Future)

Would integrate with Stripe:
- Subscription tiers (Free, Starter, Pro, Enterprise)
- Usage-based billing for API calls
- Invoice management
- Payment methods

**Estimated effort:** 2-3 days additional

---

# UX FLOWS: Where Features Appear & How Users Access Them

This section documents the complete user journey through the platform, showing where each feature lives, when it appears, and how users navigate between them.

## Application Flow Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MARKETING AGENT PLATFORM                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   [LOGIN PAGE]                                                               │
│        │                                                                     │
│        ▼                                                                     │
│   ┌─────────────┐     First time user?     ┌──────────────────┐             │
│   │   Has Org?  │──────── NO ─────────────▶│  ONBOARDING PAGE │             │
│   └─────────────┘                          │  (4 steps)       │             │
│        │ YES                               └────────┬─────────┘             │
│        ▼                                            │                        │
│   ┌─────────────────────────────────────────────────▼─────────────────────┐ │
│   │                        DASHBOARD PAGE                                  │ │
│   │  ┌─────────────────────────────────────────────────────────────────┐  │ │
│   │  │                      TOP NAVIGATION BAR                          │  │ │
│   │  │  [Logo] [Campaigns] [Assets] [Schedule] [Trends] [Kata] [Chat]  │  │ │
│   │  └─────────────────────────────────────────────────────────────────┘  │ │
│   │                                                                        │ │
│   │  ┌──────────────┬──────────────┬──────────────┬──────────────┐        │ │
│   │  │  CAMPAIGNS   │    ASSETS    │   SCHEDULE   │    TRENDS    │        │ │
│   │  │    VIEW      │     VIEW     │     VIEW     │     VIEW     │        │ │
│   │  └──────────────┴──────────────┴──────────────┴──────────────┘        │ │
│   │         │              │              │              │                  │ │
│   │         ▼              ▼              ▼              ▼                  │ │
│   │  ┌──────────────┬──────────────┬──────────────┬──────────────┐        │ │
│   │  │  WORKFLOW    │    IMAGE     │    TASKS     │    CHAT      │        │ │
│   │  │    VIEW      │   EDITOR     │    VIEW      │    VIEW      │        │ │
│   │  └──────────────┴──────────────┴──────────────┴──────────────┘        │ │
│   │                                                                        │ │
│   └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
│   ┌────────────────────────┐     ┌────────────────────────┐                 │
│   │  CAMPAIGN STUDIO PAGE  │     │     KATA LAB PAGE      │                 │
│   │  (Full campaign exec)  │     │  (Video generation)    │                 │
│   └────────────────────────┘     └────────────────────────┘                 │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. LOGIN PAGE

**URL:** `/login`
**When It Appears:** First visit, or after logout, or when auth token expires

### Layout
```
┌─────────────────────────────────────────────────┐
│                                                  │
│              MARKETING AGENT                     │
│              ────────────────                    │
│                                                  │
│         [ Login ]  [ Register ]                  │
│                                                  │
│         ┌─────────────────────┐                  │
│         │ Email               │                  │
│         └─────────────────────┘                  │
│                                                  │
│         ┌─────────────────────┐                  │
│         │ Password            │                  │
│         └─────────────────────┘                  │
│                                                  │
│         [    Login Button    ]                   │
│                                                  │
│         Forgot password?                         │
│                                                  │
└─────────────────────────────────────────────────┘
```

### Actions & Responses
| User Action | System Response | Navigation |
|------------|-----------------|------------|
| Enter email + password, click Login | Validate credentials via `/api/auth/login` | → Dashboard (if org exists) or → Onboarding |
| Click Register tab | Show registration form | Stay on page |
| Submit registration | Create user via `/api/auth/register` | → Onboarding |
| Invalid credentials | Show error message | Stay on page |
| Click Forgot Password | Open password reset modal | Stay on page |

---

## 2. ONBOARDING PAGE

**URL:** `/onboarding`
**When It Appears:** After login when user has no organization

### Flow Steps

```
Step 1: WELCOME        Step 2: BRAND URL       Step 3: ANALYZING       Step 4: COMPLETE
─────────────────      ──────────────────      ─────────────────       ────────────────

┌───────────────┐      ┌───────────────┐      ┌───────────────┐       ┌───────────────┐
│               │      │               │      │               │       │               │
│  Welcome!     │      │  Enter your   │      │  Analyzing    │       │  ✓ Ready!     │
│  Let's set    │  →   │  brand URL    │  →   │  your brand   │   →   │               │
│  up your      │      │               │      │               │       │  [Go to       │
│  workspace    │      │  [_________]  │      │  ████████░░   │       │   Dashboard]  │
│               │      │               │      │  67%          │       │               │
│  [Continue]   │      │  [Analyze]    │      │               │       │               │
│               │      │               │      │               │       │               │
└───────────────┘      └───────────────┘      └───────────────┘       └───────────────┘
```

### Actions & Responses
| Step | User Action | System Response | Navigation |
|------|-------------|-----------------|------------|
| 1 | Click Continue | Move to URL input step | → Step 2 |
| 2 | Enter URL, click Analyze | Start analysis via `/api/onboarding/init` | → Step 3 |
| 3 | (Automatic) | Poll `/api/onboarding/status/{job_id}` every 2s | → Step 4 when complete |
| 3 | Click Cancel | Cancel job, show retry option | Stay on Step 3 |
| 4 | Click Go to Dashboard | Save org ID, navigate | → Dashboard |
| Any | Error occurs | Show error with retry button | Stay on current step |

### What Happens During Analysis
1. **Firecrawl** crawls the provided URL
2. **Perplexity** researches the company/brand
3. System extracts: Brand DNA, competitors, target audience, voice & tone
4. Creates Organization + KnowledgeBase in database

---

## 3. DASHBOARD PAGE

**URL:** `/dashboard`
**When It Appears:** After login (if org exists) or after onboarding

### Main Layout

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ [≡] Marketing Agent          [🔔] [👤 User ▼]                                │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  TAB NAVIGATION:                                                              │
│  ┌─────────┬─────────┬──────────┬────────┬──────────┬────────┬──────────┐   │
│  │Campaigns│ Assets  │ Workflow │Schedule│  Trends  │  Kata  │   Chat   │   │
│  └─────────┴─────────┴──────────┴────────┴──────────┴────────┴──────────┘   │
│                                                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │                                                                        │   │
│  │                        ACTIVE VIEW CONTENT                             │   │
│  │                    (changes based on selected tab)                     │   │
│  │                                                                        │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐   │
│  │                     SLIDING DELIVERABLES PANEL                         │   │
│  │                  (slides up when deliverable selected)                 │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3.1 CAMPAIGNS VIEW (Default Dashboard View)

**Tab:** Campaigns
**When Active:** Default when entering dashboard

### Layout
```
┌────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  MY CAMPAIGNS                              [+ New Campaign]         │
│  ─────────────                                                      │
│                                                                     │
│  Filter: [All ▼]  [Draft ▼]  [In Progress ▼]  [Completed ▼]        │
│                                                                     │
│  ┌──────────────────────┐  ┌──────────────────────┐                │
│  │ 📊 Q1 Product Launch │  │ 📊 Holiday Campaign  │                │
│  │ Status: In Progress  │  │ Status: Draft        │                │
│  │ 5 deliverables       │  │ 0 deliverables       │                │
│  │ Created: Jan 15      │  │ Created: Jan 20      │                │
│  │ [Open] [Edit] [···]  │  │ [Open] [Edit] [···]  │                │
│  └──────────────────────┘  └──────────────────────┘                │
│                                                                     │
│  ┌──────────────────────┐                                          │
│  │ 📊 Social Media Q2   │                                          │
│  │ Status: Completed    │                                          │
│  │ 12 deliverables      │                                          │
│  │ Created: Dec 10      │                                          │
│  │ [Open] [Edit] [···]  │                                          │
│  └──────────────────────┘                                          │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Actions & Responses
| User Action | System Response | Navigation |
|-------------|-----------------|------------|
| Click "+ New Campaign" | Open campaign creation modal | Stay, show modal |
| Enter name + description, submit | Create via `/api/campaigns`, show in list | Stay, close modal |
| Click "Open" on campaign | Navigate to Campaign Studio | → Campaign Studio Page |
| Click "Edit" on campaign | Open edit modal | Stay, show modal |
| Click "···" menu | Show: Duplicate, Archive, Delete options | Stay, show dropdown |
| Click Delete | Confirm dialog → DELETE `/api/campaigns/{id}` | Stay, remove from list |
| Click status filter | Filter campaigns by status | Stay, update list |

---

## 3.2 ASSETS VIEW

**Tab:** Assets
**When Active:** Click "Assets" tab

### Layout
```
┌────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  ASSET LIBRARY                             [↑ Upload]  [+ Create]  │
│  ─────────────                                                      │
│                                                                     │
│  Campaign: [All Campaigns ▼]   Type: [All Types ▼]                 │
│                                                                     │
│  GRID VIEW:                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │
│  │ [Image]  │ │ [Image]  │ │ [Video]  │ │ [Doc]    │              │
│  │ Hero.png │ │ Banner   │ │ Promo.mp4│ │ Copy.docx│              │
│  │ v3       │ │ v1       │ │ v2       │ │ v1       │              │
│  │ 2 comments│ │          │ │ 5 comments│ │          │              │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │
│                                                                     │
│  ──── VERSION HISTORY (when asset selected) ────                    │
│  │ v3 - Current (Jan 20)                                           │
│  │ v2 - Jan 18 - "Updated colors"                                  │
│  │ v1 - Jan 15 - "Initial upload"                                  │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Actions & Responses
| User Action | System Response | Navigation |
|-------------|-----------------|------------|
| Click "Upload" | Open file picker | Stay, show picker |
| Select file | Upload via `/api/uploads/image`, create asset | Stay, add to grid |
| Click asset | Select asset, show version history | Stay, update panel |
| Click version | Load that version in detail view | Stay, update view |
| Click "Create" | Open creation options (AI Generate, Template) | Stay, show modal |
| Click "AI Generate" | Open image generation modal | → Image Editor |
| Double-click asset | Open in Image Editor | → Image Editor View |
| Right-click asset | Show context menu (Download, Share, Delete) | Stay |

---

## 3.3 WORKFLOW VIEW (Kanban)

**Tab:** Workflow
**When Active:** Click "Workflow" tab

### Layout
```
┌────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  WORKFLOW BOARD                            Campaign: [Q1 Launch ▼]  │
│  ─────────────                                                      │
│                                                                     │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐  │
│  │   IDEAS     │ │ IN PROGRESS │ │   REVIEW    │ │   APPROVED  │  │
│  ├─────────────┤ ├─────────────┤ ├─────────────┤ ├─────────────┤  │
│  │ ┌─────────┐ │ │ ┌─────────┐ │ │ ┌─────────┐ │ │ ┌─────────┐ │  │
│  │ │ Hero    │ │ │ │ Social  │ │ │ │ Email   │ │ │ │ Banner  │ │  │
│  │ │ Image   │ │ │ │ Post #1 │ │ │ │ Header  │ │ │ │ Ad v2   │ │  │
│  │ └─────────┘ │ │ └─────────┘ │ │ └─────────┘ │ │ └─────────┘ │  │
│  │ ┌─────────┐ │ │ ┌─────────┐ │ │             │ │             │  │
│  │ │ Video   │ │ │ │ Landing │ │ │             │ │             │  │
│  │ │ Script  │ │ │ │ Page    │ │ │             │ │             │  │
│  │ └─────────┘ │ │ └─────────┘ │ │             │ │             │  │
│  │             │ │             │ │             │ │             │  │
│  │ [+ Add]     │ │ [+ Add]     │ │ [+ Add]     │ │             │  │
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘  │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Actions & Responses
| User Action | System Response | Navigation |
|-------------|-----------------|------------|
| Drag card to another column | Update status via `/api/deliverables/{id}` | Stay, animate move |
| Click card | Open deliverable in sliding panel | Stay, show panel |
| Click "+ Add" | Create new deliverable in that column | Stay, add card |
| Click card "···" | Show menu: Edit, Duplicate, Delete | Stay |
| Drag to reorder within column | Update order | Stay |
| Change campaign filter | Load deliverables for selected campaign | Stay, update board |

---

## 3.4 SCHEDULE VIEW (Calendar)

**Tab:** Schedule
**When Active:** Click "Schedule" tab

### Layout
```
┌────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  CONTENT CALENDAR                                                   │
│  ────────────────                                                   │
│                                                                     │
│  [< Jan 2026 >]           [Day] [Week] [Month]       [+ Schedule]  │
│                                                                     │
│  ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┐                       │
│  │ SUN │ MON │ TUE │ WED │ THU │ FRI │ SAT │                       │
│  ├─────┼─────┼─────┼─────┼─────┼─────┼─────┤                       │
│  │     │     │     │ 1   │ 2   │ 3   │ 4   │                       │
│  │     │     │     │     │ 🐦  │     │     │                       │
│  ├─────┼─────┼─────┼─────┼─────┼─────┼─────┤                       │
│  │ 5   │ 6   │ 7   │ 8   │ 9   │ 10  │ 11  │                       │
│  │     │ 🔗in│     │ 🐦  │     │ 📘  │     │                       │
│  │     │     │     │ 📸  │     │     │     │                       │
│  ├─────┼─────┼─────┼─────┼─────┼─────┼─────┤                       │
│                                                                     │
│  Legend: 🐦 Twitter  📸 Instagram  🔗in LinkedIn  📘 Facebook      │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Actions & Responses
| User Action | System Response | Navigation |
|-------------|-----------------|------------|
| Click date | Show posts scheduled for that date | Stay, show sidebar |
| Click "+ Schedule" | Open scheduling modal | Stay, show modal |
| Select platform, time, content | Create via `/api/scheduled-posts` | Stay, add to calendar |
| Drag post to new date | Reschedule via PATCH `/api/scheduled-posts/{id}` | Stay, animate move |
| Click post icon | Open post detail panel | Stay, show panel |
| Click "Publish Now" in panel | Publish via `/api/scheduled-posts/{id}/publish` | Stay, update status |
| Click Week/Month toggle | Change calendar view | Stay, update view |

---

## 3.5 TRENDS VIEW

**Tab:** Trends
**When Active:** Click "Trends" tab

### Layout
```
┌────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  TREND MONITOR                                        [↻ Refresh]  │
│  ─────────────                                                      │
│                                                                     │
│  Categories: [All ▼]  Search: [________________]                    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 📈 AI-Generated Content Goes Mainstream        [High Impact] │   │
│  │ Marketing teams are increasingly adopting AI tools...        │   │
│  │ Relevance: ████████░░ 85%     Sources: 15     24h trend: +12%│   │
│  │ [Create Campaign] [Analyze] [Save]                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 📈 Short-Form Video Dominates Social           [High Impact] │   │
│  │ TikTok and Reels continue to see explosive growth...         │   │
│  │ Relevance: ███████░░░ 70%     Sources: 23     24h trend: +8% │   │
│  │ [Create Campaign] [Analyze] [Save]                           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Actions & Responses
| User Action | System Response | Navigation |
|-------------|-----------------|------------|
| Click "Refresh" | Fetch new trends via `/api/trends` | Stay, update list |
| Click "Create Campaign" | Create campaign seeded with trend data | → Campaign Studio |
| Click "Analyze" | Deep analysis with Perplexity | Stay, show analysis modal |
| Click "Save" | Save trend to saved items | Stay, show toast |
| Filter by category | Filter displayed trends | Stay, update list |
| Search | Filter by search term | Stay, update list |

---

## 3.6 KATA VIEW (from Dashboard)

**Tab:** Kata
**When Active:** Click "Kata" tab (opens Kata Lab Page)

**Note:** Clicking Kata tab navigates to full Kata Lab Page (see section 5)

---

## 3.7 CHAT VIEW

**Tab:** Chat
**When Active:** Click "Chat" tab OR Chat panel always visible on right

### Layout
```
┌────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  CHAT WITH AI AGENT                                                │
│  ─────────────────                                                  │
│                                                                     │
│  Conversations: [Q1 Launch Chat ▼]              [+ New Chat]       │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  🤖 Hi! I'm your marketing assistant. I can help you:       │   │
│  │     • Create campaign content                                │   │
│  │     • Analyze your brand performance                         │   │
│  │     • Generate ideas for social posts                        │   │
│  │     • Edit and refine deliverables                          │   │
│  │                                                              │   │
│  │  What would you like to work on today?                      │   │
│  │                                                              │   │
│  │  ────────────────────────────────────────────                │   │
│  │                                                              │   │
│  │  👤 Can you help me create social media posts for our       │   │
│  │     new product launch?                                      │   │
│  │                                                              │   │
│  │  🤖 I'd be happy to help with your product launch posts!    │   │
│  │     Let me ask a few questions...                           │   │
│  │     [typing indicator]                                       │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Type your message...                              [Send →]   │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Actions & Responses
| User Action | System Response | Navigation |
|-------------|-----------------|------------|
| Type message, press Enter/Send | Stream response via `/api/chat/message` | Stay, show streaming response |
| Click "+ New Chat" | Create conversation via `/api/chat/conversations` | Stay, clear chat |
| Select different conversation | Load history via `/api/chat/conversations/{id}/messages` | Stay, load messages |
| AI generates deliverable | Show in chat + add to deliverables panel | Stay |
| Click "Apply" on AI suggestion | Apply to current deliverable | Stay, update deliverable |

---

## 3.8 IMAGE EDITOR VIEW

**Tab:** N/A (accessed from Assets or Chat)
**When Active:** Double-click asset OR click "Edit Image" in chat

### Layout
```
┌────────────────────────────────────────────────────────────────────┐
│                                                                     │
│  CONVERSATIONAL IMAGE EDITOR                          [✕ Close]    │
│  ───────────────────────────                                       │
│                                                                     │
│  ┌───────────────────────────────┬─────────────────────────────┐   │
│  │                               │  CHAT                        │   │
│  │                               │                              │   │
│  │        [Current Image]        │  🤖 What would you like me   │   │
│  │                               │     to change about this     │   │
│  │                               │     image?                   │   │
│  │                               │                              │   │
│  │                               │  👤 Make the background      │   │
│  │                               │     darker and add a         │   │
│  │                               │     subtle vignette          │   │
│  │                               │                              │   │
│  │                               │  🤖 [Processing...]          │   │
│  │                               │                              │   │
│  ├───────────────────────────────┤  ────────────────────────    │   │
│  │ VERSION HISTORY               │  [Type edit instruction...]  │   │
│  │ v3 (current) | v2 | v1        │                              │   │
│  └───────────────────────────────┴─────────────────────────────┘   │
│                                                                     │
│  [↶ Undo] [↷ Redo] [⬇ Download] [✓ Save to Assets]                │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Actions & Responses
| User Action | System Response | Navigation |
|-------------|-----------------|------------|
| Drop image file | Upload via `/api/uploads/image`, create session | Stay, show image |
| Type edit instruction | Process via `/api/image-editor/edit` | Stay, show new version |
| Click version thumbnail | Switch to that version | Stay, update main view |
| Click Undo/Redo | Navigate version history | Stay, update image |
| Click "Save to Assets" | Create asset from current version | Stay, show toast |
| Click "Download" | Download current version | Browser download |
| Click Close | Return to previous view | → Assets or Dashboard |

---

## 4. CAMPAIGN STUDIO PAGE

**URL:** `/studio/{campaign_id}`
**When Active:** Click "Open" on a campaign card

### Layout

```
┌────────────────────────────────────────────────────────────────────┐
│ [← Back to Dashboard]      CAMPAIGN STUDIO: Q1 Product Launch      │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  EXECUTION PHASES                                                   │
│  ────────────────                                                   │
│                                                                     │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐            │
│  │ PHASE 1 │ → │ PHASE 2 │ → │ PHASE 3 │ → │ PHASE 4 │            │
│  │Research │   │Concepts │   │ Create  │   │ Review  │            │
│  │   ✓     │   │  ●      │   │         │   │         │            │
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘            │
│                                                                     │
│  CURRENT PHASE: Concept Generation                                  │
│  ─────────────────────────────────                                  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                                                               │  │
│  │  The AI is generating creative concepts for your campaign... │  │
│  │                                                               │  │
│  │  ████████████████████░░░░░░░░ 65%                            │  │
│  │                                                               │
│  │  Currently: Analyzing competitor campaigns                    │  │
│  │                                                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  CONCEPT OPTIONS (select one to continue):                    │  │
│  │                                                               │  │
│  │  ○ Concept A: "Innovation Forward"                            │  │
│  │    Bold, futuristic approach emphasizing cutting-edge tech    │  │
│  │                                                               │  │
│  │  ○ Concept B: "Human Connection"                              │  │
│  │    Warm, relatable stories featuring real customer impact     │  │
│  │                                                               │  │
│  │  ○ Concept C: "Performance Driven"                            │  │
│  │    Data-focused messaging highlighting results and ROI        │  │
│  │                                                               │  │
│  │                                    [Select & Continue]        │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Phases & Actions

| Phase | Description | User Action Required | System Response |
|-------|-------------|---------------------|-----------------|
| 1. Research | AI analyzes brand, market, competitors | None (automatic) | Progress updates via WebSocket |
| 2. Concepts | AI generates 3 creative concepts | Select one concept | Move to Phase 3 |
| 3. Create | AI generates deliverables | Review generated content | Move to Phase 4 |
| 4. Review | Human approval gate | Approve, edit, or reject each item | Complete campaign |

### Actions & Responses
| User Action | System Response | Navigation |
|-------------|-----------------|------------|
| Click "Start Campaign" | Begin execution via `/api/orchestrator/execute` | Stay, show progress |
| Select concept | Store selection, proceed to creation | Move to Phase 3 |
| Edit deliverable | Open in editor panel | Stay, show panel |
| Approve deliverable | Mark as approved, move to "Approved" column | Stay, update status |
| Reject deliverable | Mark for regeneration | Stay, regenerate |
| Click "Complete Campaign" | Finalize campaign status | → Dashboard |
| Click "← Back" | Return to dashboard | → Dashboard |

---

## 5. KATA LAB PAGE

**URL:** `/kata`
**When Active:** Click "Kata" tab or navigate directly

### Main Layout

```
┌────────────────────────────────────────────────────────────────────┐
│ [← Dashboard]               KATA LAB                               │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  CREATE                                                             │
│  ────────                                                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                │
│  │ 🧑 Synthetic │ │ 🎬 Video     │ │ 📝 Script    │                │
│  │  Influencer  │ │ Compositor   │ │  Builder     │                │
│  │              │ │              │ │              │                │
│  │ Create AI    │ │ Merge clips, │ │ Generate     │                │
│  │ spokesperson │ │ add products │ │ video scripts│                │
│  └──────────────┘ └──────────────┘ └──────────────┘                │
│                                                                     │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                     │
│  ACTIVE JOBS                                                        │
│  ───────────                                                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Job: Synthetic Influencer - "Sarah"     Status: In Progress  │  │
│  │ ████████████░░░░░░░░ 60%                                     │  │
│  │ Currently: Generating voice audio...                          │  │
│  │ [Cancel]                                                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  COMPLETED                                                          │
│  ─────────                                                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ "Product Demo Video"                         ✓ Complete      │  │
│  │ Created: Jan 28, 2026                    [Preview] [Download] │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Sub-Views

#### 5.1 Synthetic Influencer Creator
```
┌────────────────────────────────────────────────────────────────────┐
│  CREATE SYNTHETIC INFLUENCER                          [✕ Close]    │
│  ────────────────────────────                                      │
│                                                                     │
│  Step 1 of 4: APPEARANCE                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                                                              │   │
│  │  Name: [________________]                                    │   │
│  │                                                              │   │
│  │  Appearance:                                                 │   │
│  │  Age: [25-35 ▼]   Gender: [Female ▼]   Ethnicity: [____]    │   │
│  │  Hair: [____________]   Style: [Professional ▼]             │   │
│  │                                                              │   │
│  │  OR upload reference images:                                 │   │
│  │  [Drop images here or click to upload]                       │   │
│  │                                                              │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  [← Back]                                        [Next: Voice →]   │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

#### 5.2 Video Compositor (Halftime-Style)
```
┌────────────────────────────────────────────────────────────────────┐
│  VIDEO COMPOSITOR                                     [✕ Close]    │
│  ────────────────                                                   │
│                                                                     │
│  Mode: [Product Placement ▼]                                       │
│                                                                     │
│  ┌───────────────────────────┬─────────────────────────────────┐   │
│  │                           │  PRODUCT IMAGE                   │   │
│  │     SOURCE VIDEO          │  [Drop product image here]       │   │
│  │     [Drop video here]     │                                  │   │
│  │                           │  The AI will analyze your video  │   │
│  │                           │  and find the best placement     │   │
│  │                           │  opportunities using Grok.       │   │
│  │                           │                                  │   │
│  └───────────────────────────┴─────────────────────────────────┘   │
│                                                                     │
│  Options:                                                           │
│  ☑ Auto-match lighting    ☑ Scene-aware placement                  │
│  Product type: [Beverage ▼]                                        │
│                                                                     │
│  [Analyze Scene]                              [Generate Video]      │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Actions & Responses
| User Action | System Response | Navigation |
|-------------|-----------------|------------|
| Click "Synthetic Influencer" | Open creator wizard | Stay, show wizard |
| Complete wizard, click Generate | Create job via `/api/kata/synthetic-influencer` | Stay, show in Active Jobs |
| Click "Video Compositor" | Open compositor modal | Stay, show modal |
| Upload video + product | Analyze via `/api/kata/analyze-scene` | Stay, show analysis |
| Click "Generate Video" | Create job via `/api/kata/composite-product` | Stay, show in Active Jobs |
| Click "Preview" on completed | Open video preview modal | Stay, show preview |
| Click "Download" | Download video file | Browser download |
| Click "Cancel" on active job | Cancel job | Stay, remove from list |

---

## 6. SLIDING DELIVERABLES PANEL

**When Active:** Click any deliverable from Kanban, Calendar, or Campaign Studio

### Layout
```
┌────────────────────────────────────────────────────────────────────┐
│ DELIVERABLE: Hero Banner Image                    [✕ Close Panel] │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Status: [In Progress ▼]    Type: Image    Campaign: Q1 Launch    │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                                                               │  │
│  │                    [CONTENT PREVIEW]                          │  │
│  │                                                               │  │
│  │            Image, text preview, or video player               │  │
│  │                                                               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ACTIONS                                                            │
│  ────────                                                           │
│  [📝 Edit]  [🔄 Regenerate]  [✏️ Refine]  [📤 Export]              │
│                                                                     │
│  REFINEMENT OPTIONS                                                 │
│  ──────────────────                                                 │
│  [Shorten] [Expand] [More Casual] [More Professional] [Fix Grammar]│
│                                                                     │
│  HISTORY                                                            │
│  ────────                                                           │
│  • Jan 20, 3:45pm - Refined (shortened)                            │
│  • Jan 20, 2:30pm - Regenerated                                    │
│  • Jan 20, 1:00pm - Created                                        │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

### Actions & Responses
| User Action | System Response | Navigation |
|-------------|-----------------|------------|
| Click refinement option | Refine via `/api/deliverables/refine` | Stay, update content |
| Click "Edit" | Open in appropriate editor | → Image Editor or Text Editor |
| Click "Regenerate" | Request new generation | Stay, show loading |
| Click "Export" | Download or copy content | Browser action |
| Change status dropdown | Update via `/api/deliverables/{id}` | Stay, update status |
| Click "✕ Close" | Close panel | Stay, hide panel |

---

# Summary: Implementation Order

## Week 1: Critical + High Priority
| Day | Items |
|-----|-------|
| Day 1 | Fix Kata endpoints (1.1), Memory leak (1.2) |
| Day 2 | Remove mock data (1.3), Start auth (1.4) |
| Day 3 | Complete auth (1.4), Test all critical |
| Day 4 | Fix deliverables refine (2.1), File upload (2.2) |
| Day 5 | Complete image editor (2.3), Fix ScriptBuilder (2.4) |

## Week 2: Not Built Items
| Day | Items |
|-----|-------|
| Day 6 | Social publishing - Twitter, LinkedIn (3.1) |
| Day 7 | Social publishing - Instagram, Facebook (3.1) |
| Day 8 | Analytics dashboard (3.2) |
| Day 9 | User management (3.3) |
| Day 10 | Video generation integration (3.4) |

## Week 3: Polish & Testing
| Day | Items |
|-----|-------|
| Day 11-12 | Integration testing, bug fixes |
| Day 13 | Documentation, deployment prep |

---

# Environment Variables Needed

```env
# Authentication
JWT_SECRET_KEY=your-jwt-secret-key

# AWS S3
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
AWS_S3_BUCKET=marketing-agent-uploads

# Social Media
TWITTER_API_KEY=your-twitter-key
TWITTER_API_SECRET=your-twitter-secret
LINKEDIN_CLIENT_ID=your-linkedin-id
LINKEDIN_CLIENT_SECRET=your-linkedin-secret

# Video Generation
REPLICATE_API_KEY=your-replicate-key
RUNWAY_API_KEY=your-runway-key
ELEVENLABS_API_KEY=your-elevenlabs-key
```

---

# Testing Checklist

After implementation, verify:

- [ ] User can register and login
- [ ] Auth tokens work across all endpoints
- [ ] File uploads work to S3
- [ ] Kata components use api.js (no hardcoded URLs)
- [ ] No memory leaks in polling
- [ ] TrendMaster shows real data (no mock fallback)
- [ ] Deliverable refinement saves to database
- [ ] Image editor uploads real files
- [ ] Script builder fails gracefully without API
- [ ] Social publishing works for all platforms
- [ ] Analytics dashboard shows real data
- [ ] User management works for admins
- [ ] Video generation creates real videos
