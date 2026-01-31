# Frontend Bug Handoff Document

## Summary
The backend onboarding pipeline works correctly, but the frontend UI gets stuck on the "Initializing" screen and never transitions to show results, even when the backend reports `status: "complete"`.

---

## What Works ✅

### Backend (100% functional)
1. **Onboarding API** - All endpoints work correctly:
   - `POST /api/onboarding/start` - Creates org, starts pipeline
   - `GET /api/onboarding/status/{org_id}` - Returns correct status
   - `GET /api/onboarding/result/{org_id}` - Returns research data

2. **Pipeline execution** - Successfully runs through all stages:
   - Initializing → Crawling → Analyzing → Research → Synthesizing → Complete

3. **Database** - SQLite persistence works, data is saved correctly

### Proof the backend works:
```bash
# Status returns complete
curl http://localhost:8000/api/onboarding/status/83ddd1e1c35d
# Returns: {"status":"complete","progress":{"stage":"complete","progress":1.0,...}}

# Result returns data
curl http://localhost:8000/api/onboarding/result/83ddd1e1c35d
# Returns: {"organization_id":"83ddd1e1c35d","brand":{"name":"Stripe",...},...}
```

---

## What's Broken ❌

### Frontend Issue
The `OnboardingPage.jsx` gets stuck showing "Initializing" at 0% progress even when:
1. Backend returns `status: "complete"` with `progress: 1.0`
2. Backend returns valid result data

### Two Scenarios Where It Fails:

#### Scenario 1: New Onboarding (should work but doesn't update UI)
- User enters domain, clicks "Start Discovery"
- Backend creates org, runs pipeline, completes in ~1 second
- Frontend shows "Initializing 0%" and never updates
- Backend logs show status polling returns 200 OK with `status: "complete"`

#### Scenario 2: Already Onboarded Domain
- User enters domain that's already completed
- Backend returns 400: `"Organization already onboarded. Use /result endpoint to view data."`
- Frontend should show error OR redirect to results
- Instead, frontend stays stuck on "Initializing 0%"

---

## Relevant Code

### `/frontend/src/pages/OnboardingPage.jsx`

```javascript
// Lines 27-54: The polling logic
const pollStatus = useCallback(async (orgId) => {
    try {
        const status = await api.getOnboardingStatus(orgId);

        setProgress({
            stage: status.progress.stage,
            progress: status.progress.progress,
            message: status.progress.message,
        });

        if (status.status === 'complete') {
            // THIS SHOULD TRIGGER but UI doesn't update
            const resultData = await api.getOnboardingResult(orgId);
            setResult(resultData);
            setStage(STAGES.RESULT);  // <-- Should change to RESULT stage
        } else if (status.status === 'failed') {
            setError(status.progress.error || 'Onboarding failed');
            setStage(STAGES.ERROR);
        } else {
            // Keep polling
            setTimeout(() => pollStatus(orgId), 2000);
        }
    } catch (err) {
        console.error('Polling error:', err);
        setError(err.message);
        setStage(STAGES.ERROR);
    }
}, []);

// Lines 57-92: The start handler
const handleStartOnboarding = async (domain) => {
    setStage(STAGES.PROCESSING);  // Immediately shows processing screen

    try {
        const response = await api.startOnboarding(domain);
        setOrganizationId(response.organization_id);
        pollStatus(response.organization_id);  // Start polling

        // Also tries WebSocket (may be failing silently)
        try {
            api.connectOnboardingProgress(...)
        } catch (wsError) {
            console.warn('WebSocket not available, using polling');
        }
    } catch (err) {
        setError(err.message);
        setStage(STAGES.ERROR);  // <-- Should trigger on 400 error
    }
};
```

### `/frontend/src/services/api.js`

```javascript
// Lines 49-55: API methods look correct
async getOnboardingStatus(organizationId) {
    return this.request(`/onboarding/status/${organizationId}`);
}

async getOnboardingResult(organizationId) {
    return this.request(`/onboarding/result/${organizationId}`);
}
```

---

## Possible Causes to Investigate

1. **React State Not Updating**
   - `setStage(STAGES.RESULT)` may be called but component not re-rendering
   - Check if there's a key prop issue or stale closure problem

2. **Error Swallowed Silently**
   - The `getOnboardingResult()` call on line 39 might be throwing
   - Check if the result schema matches what `OnboardingResult` component expects

3. **WebSocket Interference**
   - WebSocket connection attempt (lines 73-87) might be interfering
   - WebSocket errors might be masking the polling completion

4. **Stage State Management**
   - Check if something else is resetting `stage` back to PROCESSING
   - Look for useEffect hooks that might override the state

5. **Progress Component Not Handling "complete" Stage**
   - `OnboardingProgress` component might not properly handle `stage: "complete"`
   - It displays based on progress.stage, not the parent's `stage` state

---

## Files to Check

1. `/frontend/src/pages/OnboardingPage.jsx` - Main page logic
2. `/frontend/src/components/onboarding/OnboardingProgress.jsx` - Progress display
3. `/frontend/src/components/onboarding/OnboardingResult.jsx` - Result display
4. `/frontend/src/services/api.js` - API client
5. `/frontend/src/App.jsx` - Router/parent component

---

## Quick Debug Steps

1. Add console.log in `pollStatus`:
```javascript
console.log('Status response:', status);
console.log('Current stage state:', stage);
```

2. Add console.log before `setStage(STAGES.RESULT)`:
```javascript
if (status.status === 'complete') {
    console.log('TRANSITIONING TO RESULT');
    const resultData = await api.getOnboardingResult(orgId);
    console.log('Result data:', resultData);
    setResult(resultData);
    setStage(STAGES.RESULT);
}
```

3. Check if `OnboardingResult` component renders at all by adding:
```javascript
// In OnboardingResult.jsx
console.log('OnboardingResult rendered with:', props);
```

---

## Environment

- Frontend: React + Vite on http://localhost:3000
- Backend: FastAPI on http://localhost:8000
- Database: SQLite (file-based at `/backend/data.db`)
- Vite proxies `/api` to backend

---

## How to Reproduce

1. Start backend: `cd backend && source .venv/bin/activate && uvicorn app.main:app --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:3000
4. Enter "stripe.com" (or any domain)
5. Click "Start Discovery"
6. Observe: UI stuck at "Initializing 0%"
7. Verify backend completed: `curl http://localhost:8000/api/onboarding/status/[org_id]`
