"""FastAPI service for receiving upload jobs via HTTP."""
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ..core.settings import settings
from ..core.logging_config import get_logger, setup_root_logger
from ..core.exceptions import ConfigError
from ..services.file_utils import build_s3_key
from .queue import Job, job_queue
from ..agents.orchestration_agent.wrapper import OrchestratorAgent

logger = get_logger(__name__)


class JobRequest(BaseModel):
    """Request model for creating a job."""
    path: str = Field(..., description="File path (absolute or relative)")
    scope: str = Field(..., pattern="^(mba|policy)$", description="Upload scope")


class JobResponse(BaseModel):
    """Response model for job creation."""
    status: str
    message: str
    job: Optional[dict] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    queue_stats: dict


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.
    
    Returns:
        Configured FastAPI app
    """
    # Initialize logging
    setup_root_logger()
    
    # Create FastAPI app
    app = FastAPI(
        title="HMA Ingestion API",
        description="API for submitting file upload jobs",
        version="0.1.0"
    )
    
    # Create orchestrator agent instance
    orchestrator_agent = None
    
    def get_orchestrator():
        nonlocal orchestrator_agent
        if orchestrator_agent is None:
            orchestrator_agent = OrchestratorAgent()
        return orchestrator_agent
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """Check service health and queue status."""
        stats = job_queue.stats()
        return HealthResponse(
            status="healthy",
            queue_stats=stats
        )
    
    @app.post("/jobs", response_model=JobResponse)
    async def create_job(request: JobRequest):
        """
        Create a new upload job.
        
        Args:
            request: Job creation request
            
        Returns:
            Job creation response
        """
        try:
            # Resolve file path
            file_path = Path(request.path).resolve()
            
            # Validate file exists
            if not file_path.exists():
                raise HTTPException(status_code=404, detail=f"File not found: {request.path}")
            
            if not file_path.is_file():
                raise HTTPException(status_code=400, detail=f"Not a file: {request.path}")
            
            # Get bucket and prefix for scope
            try:
                bucket = settings.get_bucket(request.scope)
                prefix = settings.get_prefix(request.scope)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            
            # Build S3 key
            s3_key = build_s3_key(request.scope, file_path, prefix)
            
            # Create job
            job = Job(
                path=file_path,
                scope=request.scope,
                s3_key=s3_key,
                bucket=bucket
            )
            
            # Enqueue job
            job_queue.put(job)
            logger.info(f"API: Enqueued job for {file_path.name}")
            
            return JobResponse(
                status="success",
                message=f"Job enqueued for {file_path.name}",
                job={
                    "file": str(file_path),
                    "scope": request.scope,
                    "bucket": bucket,
                    "key": s3_key
                }
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"API error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/stats")
    async def get_stats():
        """Get queue statistics."""
        return job_queue.stats()
    
    @app.post("/orchestrate")
    async def orchestrate(payload: dict):
        """
        Orchestrate a user query through the Orchestrator Agent.
        Payload shape:
          { "query": "What's my deductible for 2025? member_id=123 dob=1990-05-15" }
        Returns:
          { "summary": "<final answer>" }
        """
        try:
            agent = get_orchestrator()
            return await agent.run(payload)
        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            return {"summary": f"Error processing request: {str(e)}"}
    
    @app.post("/verify")
    async def verify_member_api(payload: dict):
        """
        Verify member identity.
        Payload shape:
          { "member_id": "M1001", "dob": "2005-05-23", "name": "optional" }
        Returns:
          { "valid": true/false, "member_id": "...", "name": "..." }
        """
        try:
            from ..agents.member_verification_agent.tools import verify_member
            return await verify_member(payload)
        except Exception as e:
            logger.error(f"Verification error: {e}", exc_info=True)
            return {"error": f"Verification failed: {str(e)}"}
    
    @app.post("/intent")
    async def identify_intent(payload: dict):
        """
        Identify intent from user query.
        Payload shape:
          { "query": "What's my deductible for 2025?" }
        Returns:
          { "intent": "get_deductible_oop", "params": {...} }
        """
        try:
            from ..agents.intent_identification_agent.tools import identify_intent_and_params
            query = payload.get("query", "")
            return await identify_intent_and_params(query)
        except Exception as e:
            logger.error(f"Intent identification error: {e}", exc_info=True)
            return {"error": f"Intent identification failed: {str(e)}"}
    
    @app.post("/benefits")
    async def get_benefits(payload: dict):
        """
        Get benefit accumulator information.
        Payload shape:
          { "member_id": "M1001", "service": "Massage Therapy", "plan_year": 2025 }
        Returns:
          { "status": "success", "remaining": 3, "used": 2, ... }
        """
        try:
            from ..agents.benefit_accumulator_agent.tools import get_benefit_details
            return await get_benefit_details(payload)
        except Exception as e:
            logger.error(f"Benefits error: {e}", exc_info=True)
            return {"error": f"Benefits retrieval failed: {str(e)}"}
    
    @app.post("/deductible")
    async def get_deductible(payload: dict):
        """
        Get deductible and out-of-pocket information.
        Payload shape:
          { "member_id": "M1001", "plan_year": 2025 }
        Returns:
          { "status": "success", "individual_deductible": {...}, "family_deductible": {...} }
        """
        try:
            from ..agents.deductible_oop_agent.tools import get_deductible_oop
            return await get_deductible_oop(payload)
        except Exception as e:
            logger.error(f"Deductible error: {e}", exc_info=True)
            return {"error": f"Deductible retrieval failed: {str(e)}"}
    
    return app


# Create app instance for uvicorn
app = create_app()


def run_server():
    """Run the API server using uvicorn."""
    import uvicorn
    
    setup_root_logger()
    logger.info("Starting HMA Ingestion API server...")
    
    # Create app
    app = create_app()
    
    # Run server
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    run_server()