"""
MAESTRO Agent Service - FastAPI Server
MSME Inventory Intelligence System - Multi-Agent Decision Engine

UNIFIED 6-AGENT PIPELINE:
1. Router/Context-Summarization Agent - Extract structured business context
2. External Risk Scout Agent - Bounded risk modifiers [-0.2, +0.3]
3. Risk Assessment Agent [DETERMINISTIC] - Weighted composite (0.35+0.35+0.30)
4. Policy Agent [DETERMINISTIC] - Buffer policy (warehouse>buffer, cash only reduces)
5. Warehouse Capacity Agent [DETERMINISTIC] - Hard constraints (≥0.75 → split)
6. Decision Orchestrator Agent - Final explainable recommendation

PIPELINE MODES:
- /process-inventory-decision   → Pure deterministic (NO LLM)
- /process-unified              → Unified 6-agent pipeline (HYBRID: LLM + deterministic)
- /process                      → Session-based full pipeline

HARD CONSTRAINT PRIORITY:
- Warehouse capacity ALWAYS overrides buffer intent
- Cash risk can REDUCE buffer, never increase it
- External modifiers bounded to [-0.2, +0.3]
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn
from datetime import datetime
import uuid

from config import Config
from questions import get_all_questions, get_question
from orchestrator import (
    run_full_pipeline,
    run_quick_analysis,
    generate_mock_response,
    run_maestro_pipeline
)

# Initialize FastAPI app
app = FastAPI(
    title="MAESTRO Agent Service",
    description="MSME Inventory Intelligence System - AI-powered inventory optimization",
    version="2.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session storage (use Redis in production)
sessions: Dict[str, Dict[str, Any]] = {}

# Pydantic models
class StartSessionRequest(BaseModel):
    user_id: Optional[str] = None

class StartSessionResponse(BaseModel):
    session_id: str
    message: str
    first_question: dict

class UserResponseRequest(BaseModel):
    session_id: str
    answer: str

class UserResponseResponse(BaseModel):
    session_id: str
    message: str
    next_question: Optional[dict]
    is_complete: bool
    progress: float

class ProcessRequest(BaseModel):
    session_id: str


# =============================================================================
# DETERMINISTIC PIPELINE REQUEST MODEL
# =============================================================================

class InventoryDecisionRequest(BaseModel):
    """
    Request model for deterministic inventory decision endpoint.
    
    Fields:
        demand_type: Type of demand pattern ("steady", "seasonal", "volatile")
        seasonal_event: Whether a seasonal event is expected (holiday, festival)
        supplier_delay: Level of supplier delays ("none", "minor", "frequent", "major")
        external_disruption: Whether external disruptions exist (strikes, weather)
        current_stock: Current inventory level (units) - OPTIONAL if business_state provided
        max_capacity: Maximum warehouse capacity (units) - OPTIONAL if business_state provided
        cash_flow: Cash flow status ("healthy", "tight", "critical")
        business_state: Live business state from MongoDB (optional, for data-driven decisions)
    """
    demand_type: str
    seasonal_event: bool
    supplier_delay: str
    external_disruption: bool
    current_stock: Optional[int] = None
    max_capacity: Optional[int] = None
    cash_flow: str
    business_id: Optional[str] = None
    business_state: Optional[Dict[str, Any]] = None

class AgentOutputResponse(BaseModel):
    session_id: str
    status: str
    results: Optional[Dict[str, Any]]
    summary: Optional[Dict[str, Any]]


# =============================================================================
# UNIFIED PIPELINE REQUEST MODEL
# =============================================================================

class UnifiedPipelineRequest(BaseModel):
    """
    Request model for the unified 6-agent pipeline.
    
    Supports two input formats:
    1. Onboarding answers (q1-q10 from session)
    2. Structured business context (from API callers)
    
    Optional flag to control pipeline mode:
    - use_deterministic_core: If True (default), uses rule-based logic for
      risk assessment, policy, and warehouse stages. LLM only for understanding.
      If False, uses LLM for all stages (slower, less predictable).
    """
    # Option 1: Onboarding answers
    answers: Optional[Dict[str, str]] = None
    
    # Option 2: Structured inputs (for direct API calls)
    business_type: Optional[str] = None
    products: Optional[str] = None
    demand_pattern: Optional[str] = None  # steady, seasonal, volatile
    seasonal_event: Optional[bool] = None
    supplier_reliability: Optional[str] = None  # reliable, occasional_delays, frequent_delays
    delay_duration: Optional[str] = None  # days, weeks
    storage_situation: Optional[str] = None  # comfortable, tight, critical
    cash_flow_status: Optional[str] = None  # healthy, tight, critical
    has_inventory_system: Optional[bool] = None
    primary_goal: Optional[str] = None
    
    # Pipeline mode flag
    use_deterministic_core: bool = True


# API Endpoints

@app.get("/favicon.ico")
async def favicon():
    """Return empty favicon to prevent 404 errors"""
    return Response(content=b"", media_type="image/x-icon")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "MAESTRO Agent Service",
        "description": "MSME Inventory Intelligence System",
        "status": "running",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "llm_configured": bool(Config.GOOGLE_API_KEY),
        "timestamp": datetime.utcnow().isoformat()
    }


# =============================================================================
# DETERMINISTIC INVENTORY DECISION ENDPOINT
# =============================================================================

@app.post("/process-inventory-decision")
async def process_inventory_decision(request: InventoryDecisionRequest):
    """
    Process inventory decision using deterministic rule-based pipeline.
    
    This endpoint runs the MAESTRO decision engine WITHOUT LLM calls.
    It converts business inputs into risk signals and produces a 
    structured inventory recommendation.
    
    NOW ENHANCED: Accepts live business_state from MongoDB for
    data-driven decisions using REAL operational data.
    
    Request Body:
        - demand_type: "steady" | "seasonal" | "volatile"
        - seasonal_event: true | false
        - supplier_delay: "none" | "minor" | "frequent" | "major"
        - external_disruption: true | false
        - current_stock: integer (units) - OPTIONAL if business_state provided
        - max_capacity: integer (units) - OPTIONAL if business_state provided
        - cash_flow: "healthy" | "tight" | "critical"
        - business_state: Live business state from MongoDB (optional)
    
    Response:
        - success: boolean
        - final_decision: {reorder_timing, order_strategy, risk_level}
        - explanation: Human-readable recommendation
        - confidence: float (0.0-1.0)
        - risk_profile: Detailed risk breakdown
        - data_source: "live" | "payload" indicating data origin
    
    Example:
        POST /process-inventory-decision
        {
            "demand_type": "seasonal",
            "seasonal_event": true,
            "supplier_delay": "frequent",
            "external_disruption": false,
            "current_stock": 60,
            "max_capacity": 100,
            "cash_flow": "tight",
            "business_state": { ... }
        }
    """
    try:
        # Convert Pydantic model to dictionary for pipeline
        input_context = {
            "demand_type": request.demand_type,
            "seasonal_event": request.seasonal_event,
            "supplier_delay": request.supplier_delay,
            "external_disruption": request.external_disruption,
            "current_stock": request.current_stock,
            "max_capacity": request.max_capacity,
            "cash_flow": request.cash_flow,
            "business_state": request.business_state,
        }
        
        # Run the deterministic MAESTRO pipeline
        result = run_maestro_pipeline(input_context)
        
        # Return successful result
        return result
        
    except Exception as e:
        # Log error for debugging (in production, use proper logging)
        print(f"❌ Error in /process-inventory-decision: {str(e)}")
        
        # Return safe error response
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your inventory decision. Please try again."
        )


# =============================================================================
# UNIFIED 6-AGENT PIPELINE ENDPOINT
# =============================================================================

@app.post("/process-unified")
async def process_unified_pipeline(request: UnifiedPipelineRequest):
    """
    Process inventory decision through the UNIFIED 6-agent MAESTRO pipeline.
    
    This endpoint runs the complete pipeline:
    1. Router Agent [LLM] → structured business context
    2. Signal Conversion [DETERMINISTIC] → numeric internal risk signals
    3. External Risk Scout [LLM] → bounded modifiers [-0.2, +0.3]
    4. Risk Assessment [DETERMINISTIC] → composite risk + level
    5. Policy Agent [DETERMINISTIC] → buffer policy
    6. Warehouse Agent [DETERMINISTIC] → feasibility & execution mode
    7. Decision Orchestrator [LLM] → final JSON output
    
    HARD CONSTRAINT PRIORITY:
    - Warehouse capacity (≥0.75) → SPLIT_DELIVERIES (non-negotiable)
    - Cash risk (≥0.7) → reduce buffer by one level (never increase)
    
    Request Body Options:
        Option 1 - Onboarding Answers:
            {
                "answers": {
                    "q1": "...", "q2": "...", ..., "q10": "..."
                },
                "use_deterministic_core": true
            }
        
        Option 2 - Structured Inputs:
            {
                "business_type": "retail",
                "products": "clothing",
                "demand_pattern": "seasonal",
                "seasonal_event": true,
                "supplier_reliability": "occasional_delays",
                "delay_duration": "weeks",
                "storage_situation": "tight",
                "cash_flow_status": "healthy",
                "has_inventory_system": false,
                "primary_goal": "prevent stockouts",
                "use_deterministic_core": true
            }
    
    Response:
        {
            "success": true,
            "pipeline": "full",
            "raw_answers": {...},
            "stages": {
                "context_summary": {...},
                "internal_risks": {...},
                "external_risks": {...},
                "risk_assessment": {...},
                "buffer_policy": {...},
                "warehouse_assessment": {...},
                "final_output": {...}
            },
            "result": {
                "final_decision": {...},
                "what_we_understood": {...},
                "detected_risks": [...],
                "why_this_decision": "...",
                "immediate_actions": [...]
            }
        }
    """
    try:
        # Prepare user_responses from either format
        if request.answers:
            # Option 1: Direct onboarding answers
            user_responses = request.answers
        else:
            # Option 2: Convert structured inputs to q1-q10 format
            user_responses = _convert_structured_to_answers(request)
        
        # Run the unified pipeline
        result = run_full_pipeline(
            user_responses=user_responses,
            use_deterministic_core=request.use_deterministic_core
        )
        
        return result
        
    except Exception as e:
        print(f"❌ Error in /process-unified: {str(e)}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline error: {str(e)}"
        )


def _convert_structured_to_answers(request: UnifiedPipelineRequest) -> Dict[str, str]:
    """
    Convert structured API inputs to q1-q10 onboarding answer format.
    This ensures compatibility with the Router Agent's expected input.
    """
    return {
        "q1": request.products or request.business_type or "general goods",
        "q2": request.demand_pattern or "steady",
        "q3": "yes" if request.seasonal_event else "no",
        "q4": request.supplier_reliability or "reliable",
        "q5": request.delay_duration or "days",
        "q6": "",  # External disruptions - inferred
        "q7": request.storage_situation or "comfortable",
        "q8": request.cash_flow_status or "healthy",
        "q9": "yes" if request.has_inventory_system else "no",
        "q10": request.primary_goal or "optimize inventory"
    }


@app.get("/questions")
async def get_questions():
    """Get all inventory intake questions"""
    return {
        "questions": get_all_questions(),
        "total": len(get_all_questions())
    }

@app.post("/start-session", response_model=StartSessionResponse)
async def start_session(request: StartSessionRequest):
    """Start a new inventory assessment session"""
    session_id = str(uuid.uuid4())
    
    # Initialize session
    sessions[session_id] = {
        "user_id": request.user_id or f"msme_{session_id[:8]}",
        "created_at": datetime.utcnow().isoformat(),
        "current_question": 1,
        "answers": {},
        "status": "onboarding"
    }
    
    first_question = get_question(1)
    
    return StartSessionResponse(
        session_id=session_id,
        message="Welcome to MAESTRO! Let's understand your inventory challenges.",
        first_question=first_question
    )

@app.post("/respond", response_model=UserResponseResponse)
async def submit_response(request: UserResponseRequest):
    """Submit user response to current question"""
    session = sessions.get(request.session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    current_q = session["current_question"]
    question = get_question(current_q)
    
    if not question:
        raise HTTPException(status_code=400, detail="Invalid question state")
    
    # Store the answer
    session["answers"][question["key"]] = request.answer
    
    # Move to next question
    total_questions = len(get_all_questions())
    session["current_question"] = current_q + 1
    
    # Check if onboarding is complete
    is_complete = current_q >= total_questions
    
    if is_complete:
        session["status"] = "ready_to_process"
        next_question = None
        message = "Great! I now have a complete picture of your inventory situation. Let me run this through our AI agents to generate your personalized recommendation..."
    else:
        next_question = get_question(current_q + 1)
        message = "Got it!"
    
    progress = (current_q / total_questions) * 100
    
    return UserResponseResponse(
        session_id=request.session_id,
        message=message,
        next_question=next_question,
        is_complete=is_complete,
        progress=progress
    )

@app.post("/process", response_model=AgentOutputResponse)
async def process_with_agents(request: ProcessRequest):
    """Process user data through the 5-agent inventory pipeline"""
    session = sessions.get(request.session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["status"] != "ready_to_process":
        raise HTTPException(
            status_code=400, 
            detail=f"Session not ready for processing. Current status: {session['status']}"
        )
    
    session["status"] = "processing"
    
    try:
        # Run the full 5-agent MAESTRO pipeline
        results = run_full_pipeline(session["answers"])
        
        session["status"] = "completed"
        session["results"] = results
        
        return AgentOutputResponse(
            session_id=request.session_id,
            status="completed",
            results=results,
            summary=results.get("summary")
        )
        
    except Exception as e:
        session["status"] = "error"
        session["error"] = str(e)
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session details and status"""
    session = sessions.get(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        **session
    }

@app.get("/session/{session_id}/results")
async def get_results(session_id: str):
    """Get inventory recommendation results for a session"""
    session = sessions.get(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Results not available. Current status: {session['status']}"
        )
    
    return {
        "session_id": session_id,
        "results": session.get("results"),
        "summary": session.get("results", {}).get("summary")
    }

@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    if session_id in sessions:
        del sessions[session_id]
        return {"message": "Session deleted successfully"}
    raise HTTPException(status_code=404, detail="Session not found")

# Run the server
if __name__ == "__main__":
    print("🚀 Starting MAESTRO Agent Service...")
    print("📦 MSME Inventory Intelligence System")
    print(f"📍 Server running at http://{Config.HOST}:{Config.PORT}")
    print(f"📚 API docs at http://{Config.HOST}:{Config.PORT}/docs")
    
    uvicorn.run(
        "main:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG
    )
