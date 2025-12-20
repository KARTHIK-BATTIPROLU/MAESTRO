"""
MAESTRO Agent Service - FastAPI Server
MSME Inventory Intelligence System - Multi-Agent Decision Engine

5-AGENT PIPELINE:
1. Router/Intake Agent - Extract structured signals
2. Research Agent - External risk modifiers
3. Warehouse Agent - Feasibility constraints
4. Decision Agent - Correlated recommendation
5. Orchestrator Agent - Final user output

DETERMINISTIC PIPELINE:
- Pure rule-based inventory decisions
- No LLM required for core decisions
- POST /process-inventory-decision
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
    version="1.0.0"
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
        current_stock: Current inventory level (units)
        max_capacity: Maximum warehouse capacity (units)
        cash_flow: Cash flow status ("healthy", "tight", "critical")
    """
    demand_type: str
    seasonal_event: bool
    supplier_delay: str
    external_disruption: bool
    current_stock: int
    max_capacity: int
    cash_flow: str

class AgentOutputResponse(BaseModel):
    session_id: str
    status: str
    results: Optional[Dict[str, Any]]
    summary: Optional[Dict[str, Any]]

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
    
    Request Body:
        - demand_type: "steady" | "seasonal" | "volatile"
        - seasonal_event: true | false
        - supplier_delay: "none" | "minor" | "frequent" | "major"
        - external_disruption: true | false
        - current_stock: integer (units)
        - max_capacity: integer (units)
        - cash_flow: "healthy" | "tight" | "critical"
    
    Response:
        - success: boolean
        - final_decision: {reorder_timing, order_strategy, risk_level}
        - explanation: Human-readable recommendation
        - confidence: float (0.0-1.0)
        - risk_profile: Detailed risk breakdown
    
    Example:
        POST /process-inventory-decision
        {
            "demand_type": "seasonal",
            "seasonal_event": true,
            "supplier_delay": "frequent",
            "external_disruption": false,
            "current_stock": 60,
            "max_capacity": 100,
            "cash_flow": "tight"
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
            "cash_flow": request.cash_flow
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
