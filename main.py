"""
AI Diagram Creator Service - Main Application

A stateless FastAPI service that generates infrastructure diagrams from natural language
descriptions using multi-agent LLM frameworks and the Python diagrams package.
"""

import base64
import os
from contextlib import asynccontextmanager
from typing import Any

import structlog
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.websockets import WebSocketDisconnect

from src.agents import (
    ArchitectAgent,
    BuilderAgent,
    CoordinatorAgent,
    DiagramContext,
    DiagramResponse,
    global_agent_registry,
)
from src.agents.streaming import global_agui_streamer
from src.api.security import get_api_key
from src.core.settings import settings
from src.diagram.engine import DiagramEngine
from utils.logging_config import configure_logging

# Configure logging as the first step
configure_logging()
logger = structlog.get_logger(__name__)

# Validate settings on startup
validation_errors = settings.validate_required_settings()
if validation_errors:
    for error in validation_errors:
        logger.error(f"Configuration error: {error}")
    if not settings.features.enable_llm_mocking:
        raise ValueError(
            "Configuration validation failed. Check your environment variables."
        )

# --- Rate Limiting Setup ---
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.security.max_requests_per_minute}/minute"],
)


# Pydantic models for request/response validation
class DiagramRequest(BaseModel):
    """Request model for diagram generation"""

    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Natural language description of the infrastructure",
    )
    session_id: str | None = Field(
        None,
        description="A unique ID for the generation session, used for progress streaming.",
    )
    output_format: str = Field(
        default="png", pattern="^(png|svg|pdf)$", description="Output image format"
    )
    title: str | None = Field(
        None, max_length=100, description="Optional diagram title"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "description": "Create a web application with load balancer, two web servers, and RDS database",
                "output_format": "png",
                "title": "Web Application Architecture",
                "session_id": "1234567890",
            }
        }
    }


class HealthResponse(BaseModel):
    status: str
    llm_available: bool
    agents: dict[str, Any]


class ServiceInfo(BaseModel):
    service_name: str
    version: str
    description: str
    features: dict[str, bool]


class ChatRequest(BaseModel):
    """Request model for assistant chat (bonus feature)"""

    message: str = Field(
        ..., min_length=1, max_length=1000, description="User message to the assistant"
    )
    context: str | None = Field(None, description="Previous conversation context")
    mode: str = Field(
        default="general",
        pattern="^(general|explanation|code|architecture)$",
        description="Chat mode",
    )


class ChatResponse(BaseModel):
    """Response model for assistant chat"""

    message: str = Field(..., description="Assistant response")
    suggested_actions: list[str] = Field(
        default_factory=list, description="Suggested follow-up actions"
    )
    followup_questions: list[str] = Field(
        default_factory=list, description="Follow-up questions"
    )


# Use centralized settings
config = settings

# Create shared diagram engine
diagram_engine = DiagramEngine()

# Initialize agents
# Agent Instances - Initialize in dependency order
architect_agent = ArchitectAgent()
builder_agent = BuilderAgent(diagram_engine)
coordinator_agent = CoordinatorAgent(architect_agent, builder_agent)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    logger.info("🚀 Starting AI Diagram Creator Service...")

    # Initialize agents (already done at module level)
    logger.info("Agents initialized successfully")

    yield

    logger.info("🛑 Shutting down AI Diagram Creator Service...")


# Create FastAPI application
app = FastAPI(
    title="AI Diagram Creator Service",
    description="An advanced, stateless Python API service that generates infrastructure diagrams from natural language descriptions using a multi-agent system.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if config.server.debug else None,
    redoc_url="/redoc" if config.server.debug else None,
)

# Add Rate Limiting Middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


# Add CORS middleware
cors_config = config.get_cors_config()
app.add_middleware(CORSMiddleware, **cors_config)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    logger.error(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500, content={"detail": "Internal server error", "status_code": 500}
    )


@app.post("/generate-diagram", response_model=DiagramResponse, tags=["Diagrams"])
async def generate_diagram_endpoint(
    request: DiagramRequest, api_key: str = Depends(get_api_key)
):
    """
    Generates a diagram from a natural language description using a multi-agent workflow.
    This endpoint is protected by API key authentication.
    """
    logger.info(
        "New diagram request received",
        description=request.description,
        session_id=request.session_id,
        api_key_used=api_key,
    )

    if not request.description:
        raise HTTPException(status_code=400, detail="Description cannot be empty.")

    logger.debug("Processing diagram generation request", session_id=request.session_id)

    session_id = (
        request.session_id
        or f"session_{base64.urlsafe_b64encode(os.urandom(6)).decode()}"
    )

    context = DiagramContext(
        original_description=request.description,
        output_format=request.output_format,
        session_id=session_id,
    )

    logger.info(f"Handing off to coordinator agent for session: {session_id}")
    try:
        # Delegate to coordinator agent with full debug visibility
        result = await coordinator_agent.generate_diagram(context)

        logger.info("=" * 80)
        logger.info("🔍 QA DEBUG: COORDINATOR RESPONSE")
        logger.info("=" * 80)
        logger.info(f"Success: {result.success}")
        if result.analysis:
            logger.info(f"Components found: {len(result.analysis.services)}")
        if result.execution_plan:
            logger.info(f"Tools executed: {len(result.execution_plan.tool_sequence)}")
        logger.info("=" * 80)

        return result

    except Exception as e:
        logger.error("=" * 80)
        logger.error("🔍 QA DEBUG: COORDINATOR FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {str(e)}")
        logger.error("=" * 80)

        raise HTTPException(
            status_code=500, detail=f"Diagram generation failed: {str(e)}"
        ) from e


@app.get("/agents/status", tags=["System"])
async def get_agents_status():
    """
    Returns the status of all registered agents in the system.
    """
    return await global_agent_registry.get_all_agents()


@app.websocket("/ws/diagram-progress/{session_id}")
async def websocket_progress_endpoint(websocket: WebSocket, session_id: str):
    """
    Provides real-time progress updates for a diagram generation session
    via AG-UI streaming.
    """
    logger.info(f"WebSocket connection established for session: {session_id}")
    await global_agui_streamer.subscribe(websocket, session_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed for session: {session_id}")
        await global_agui_streamer.unsubscribe(websocket)


# Health check endpoint
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Performs a health check of the service, including LLM availability.
    """
    agents_status = await global_agent_registry.get_all_agents()
    agent_health = {id: meta.dict() for id, meta in agents_status.items()}
    all_agents_active = all(
        agent.status == "active" for agent in agents_status.values()
    )

    return HealthResponse(
        status="healthy" if all_agents_active else "degraded",
        llm_available=bool(config.gemini.api_key),
        agents=agent_health,
    )


# Root endpoint
@app.get("/", response_model=ServiceInfo, tags=["System"])
async def root():
    """Returns basic information about the service."""
    return ServiceInfo(
        service_name="AI Diagram Creator Service",
        version="1.0.0",
        description="Generates infrastructure diagrams from natural language using a multi-agent system.",
        features={
            "multi_agent_workflow": True,
            "pydantic_ai": True,
            "a2a_protocol": True,
            "ag_ui_streaming": True,
            "react_frontend": True,
            "llm_powered_analysis": True,
            "streaming_progress": True,
            "qa_debug_mode": True,
        },
    )


# Development server
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    logger.info(f"🔍 QA DEBUG: Starting server on port {port}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="debug" if config.server.debug else "info",
    )
