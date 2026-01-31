# Brand DNA Frontend Integration Plan

## Overview
The backend has been upgraded to generate a rich "Brand DNA" profile during onboarding. This plan outlines the steps to update the frontend to display these new fields.

## Current State Analysis

### Backend Data Structure (from pipeline.py)
The `brand_dna` object is created in the onboarding pipeline with this structure:

```python
self.result.brand_dna = {
    "heritage": getattr(market_research, 'brand_heritage', ""),           # Brand Heritage & History
    "cultural_impact": getattr(market_research, 'cultural_impact', ""),   # Cultural Impact
    "advertising_strategy": getattr(market_research, 'advertising_strategy', ""),  # Advertising Strategy
    "citations": getattr(market_research, 'citations', []),               # Source citations
    "core_identity": {
        "mission": self.result.brand_data.get("mission", []),
        "values": self.result.brand_data.get("values", []),
        "voice": self.result.brand_data.get("voice", {})
    },
    "strategic_context": {
        "market_position": self.result.market_data.get("market_position", ""),
        "opportunities": self.result.market_data.get("opportunities", []),
        "threats": self.result.market_data.get("threats", [])
    }
}
```

### Data Flow Issue Identified
**CRITICAL**: The `brand_dna` data is generated in the pipeline but is **NOT being persisted** to the database:

1. `OnboardingPipeline.run()` creates `self.result.brand_dna`
2. `save_onboarding_result()` in knowledge_base.py only saves: `brand_data`, `market_data`, `audiences_data`, `offerings_data`, `context_data`
3. **Missing**: `brand_dna` is not saved!

### Frontend Current State
The Brand view in `DashboardPage.jsx` currently displays:
- Brand Identity (name, tagline, description, voice)
- Market Position (industry, position, competitors)
- Target Audiences (segments with pain points)
- Products & Services

**Missing**: Brand DNA section entirely

## Implementation Plan

### Phase 1: Backend Updates

#### 1.1 Update KnowledgeBase Model
**File**: `backend/app/models/knowledge_base.py`

Add a new column to store brand_dna:
```python
# Brand DNA Data (JSONB)
# Structure:
# {
#     "heritage": "Brand history and founding story...",
#     "cultural_impact": "Cultural influence and partnerships...",
#     "advertising_strategy": "Marketing approach and famous campaigns...",
#     "citations": ["Source 1", "Source 2"],
#     "core_identity": { ... },
#     "strategic_context": { ... }
# }
brand_dna = Column(JSON, default=dict, nullable=False)
```

#### 1.2 Update KnowledgeBaseRepository
**File**: `backend/app/repositories/knowledge_base.py`

Update `save_onboarding_result()` to include brand_dna:
```python
async def save_onboarding_result(
    self,
    organization_id: str,
    brand_data: Dict[str, Any],
    market_data: Dict[str, Any],
    audiences_data: Dict[str, Any],
    offerings_data: Dict[str, Any],
    context_data: Dict[str, Any],
    brand_dna: Dict[str, Any] = None,  # NEW PARAMETER
) -> Optional[KnowledgeBase]:
```

#### 1.3 Update Onboarding Pipeline
**File**: `backend/app/services/onboarding/pipeline.py`

Ensure `brand_dna` is passed to the save function in `run_onboarding_task()` in `backend/app/api/onboarding.py`.

#### 1.4 Update API Response Schema (Optional)
**File**: `backend/app/schemas/onboarding.py`

Consider adding BrandDNA schema for type safety.

#### 1.5 Update to_presentation_format()
**File**: `backend/app/models/knowledge_base.py`

Include brand_dna in the presentation format for frontend consumption.

#### 1.6 Update API Endpoint
**File**: `backend/app/api/organizations.py`

Update `KnowledgeBaseResponse` to include `brand_dna` field.

### Phase 2: Frontend Updates

#### 2.1 Update DashboardPage.jsx Brand View
**File**: `frontend/src/pages/DashboardPage.jsx`

Add a new "Brand DNA" section card in the `renderBrandView()` function:

```jsx
{/* Brand DNA */}
{brandData.brand_dna && (
    <div className="brand-section-card brand-dna-card">
        <h3>Brand DNA</h3>
        
        {brandData.brand_dna.heritage && (
            <div className="brand-dna-section">
                <h4>Brand Heritage & History</h4>
                <p>{brandData.brand_dna.heritage}</p>
            </div>
        )}
        
        {brandData.brand_dna.cultural_impact && (
            <div className="brand-dna-section">
                <h4>Cultural Impact</h4>
                <p>{brandData.brand_dna.cultural_impact}</p>
            </div>
        )}
        
        {brandData.brand_dna.advertising_strategy && (
            <div className="brand-dna-section">
                <h4>Advertising Strategy</h4>
                <p>{brandData.brand_dna.advertising_strategy}</p>
            </div>
        )}
        
        {brandData.brand_dna.citations?.length > 0 && (
            <div className="brand-dna-citations">
                <h4>Sources</h4>
                <ul>
                    {brandData.brand_dna.citations.map((citation, i) => (
                        <li key={i}>{citation}</li>
                    ))}
                </ul>
            </div>
        )}
    </div>
)}
```

#### 2.2 Add CSS Styles
**File**: `frontend/src/pages/DashboardPage.css`

Add styles for the Brand DNA display:

```css
/* Brand DNA specific styles */
.brand-dna-card {
    grid-column: 1 / -1; /* Full width */
}

.brand-dna-section {
    margin-bottom: var(--spacing-lg);
}

.brand-dna-section h4 {
    font-size: 0.9rem;
    color: var(--color-text-primary);
    margin: var(--spacing-md) 0 var(--spacing-sm) 0;
    font-weight: 600;
}

.brand-dna-section p {
    line-height: 1.6;
    color: var(--color-text-secondary);
}

.brand-dna-citations {
    margin-top: var(--spacing-lg);
    padding-top: var(--spacing-md);
    border-top: 1px solid var(--color-border);
}

.brand-dna-citations h4 {
    font-size: 0.85rem;
    color: var(--color-text-muted);
    margin-bottom: var(--spacing-sm);
}

.brand-dna-citations ul {
    list-style: none;
    padding: 0;
    margin: 0;
}

.brand-dna-citations li {
    font-size: 0.8rem;
    color: var(--color-text-muted);
    margin-bottom: var(--spacing-xs);
    padding-left: var(--spacing-md);
    position: relative;
}

.brand-dna-citations li::before {
    content: "•";
    position: absolute;
    left: 0;
    color: var(--color-accent);
}
```

## Files to Modify

### Backend
1. `backend/app/models/knowledge_base.py` - Add brand_dna column
2. `backend/app/repositories/knowledge_base.py` - Update save_onboarding_result()
3. `backend/app/api/onboarding.py` - Pass brand_dna to save function
4. `backend/app/api/organizations.py` - Include brand_dna in response

### Frontend
1. `frontend/src/pages/DashboardPage.jsx` - Add Brand DNA section
2. `frontend/src/pages/DashboardPage.css` - Add Brand DNA styles

## Testing Strategy

1. Run the onboarding pipeline for a test organization
2. Verify brand_dna is saved in the database
3. Check the API response includes brand_dna
4. Verify the frontend displays the Brand DNA section correctly
5. Test with missing data (graceful degradation)

## Migration Notes

Existing organizations will have empty `brand_dna` fields. The frontend should handle this gracefully by not displaying the section if data is missing.
