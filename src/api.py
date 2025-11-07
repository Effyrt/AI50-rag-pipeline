"""
FastAPI application for PE Dashboard
Provides RAG and Structured pipeline endpoints
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Optional
import json
from pathlib import Path
from datetime import datetime

# Import pipelines
from rag_pipeline import RAGPipeline  
from structured_pipeline import load_payload

# Initialize FastAPI
app = FastAPI(
    title="PE Dashboard API",
    description="Forbes AI 50 Private Equity Dashboard System",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG pipeline (singleton)
rag_pipeline = None

def get_rag_pipeline():
    """Get or create RAG pipeline instance"""
    global rag_pipeline
    if rag_pipeline is None:
        rag_pipeline = RAGPipeline()
    return rag_pipeline


# ============================================================
# Request/Response Models
# ============================================================

class DashboardRequest(BaseModel):
    company_name: str
    top_k: int = 20

class DashboardResponse(BaseModel):
    company_name: str
    pipeline: str
    dashboard: str
    generated_at: str
    retrieved_chunks: Optional[int] = None


# ============================================================
# Health Check & Info Endpoints
# ============================================================

@app.get("/")
def read_root():
    """API health check and information"""
    return {
        "message": "PE Dashboard API is running",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "rag_dashboard": "/dashboard/rag - Generate RAG dashboard",
            "structured_dashboard": "/dashboard/structured - Generate structured dashboard"
        }
    }


# ============================================================
# RAG Pipeline Endpoints (YOUR WORK!)
# ============================================================

@app.post("/dashboard/rag", response_model=DashboardResponse)
def generate_rag_dashboard(request: DashboardRequest):
    """
    Generate PE dashboard using RAG pipeline (UNSTRUCTURED)
    
    Args:
        request: DashboardRequest with company_name and top_k
    
    Returns:
        Generated dashboard in markdown format
    """
    try:
        rag = get_rag_pipeline()
        
        # Generate dashboard
        dashboard = rag.generate_dashboard(
            company_name=request.company_name,
            top_k=request.top_k
        )
        
        return DashboardResponse(
            company_name=request.company_name,
            pipeline="RAG (Unstructured)",
            dashboard=dashboard,
            generated_at=datetime.now().isoformat(),
            retrieved_chunks=request.top_k
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Dashboard generation error: {str(e)}"
        )


# ============================================================
# Structured Pipeline Endpoints
# ============================================================

@app.post("/dashboard/structured", response_model=DashboardResponse)
def generate_structured_dashboard(request: DashboardRequest):
    """
    Generate PE dashboard using structured pipeline
    
    Args:
        request: DashboardRequest with company_name
    
    Returns:
        Generated dashboard in markdown format
    """
    try:
        # Try to load structured payload
        payload = load_payload(request.company_name)
        
        # TODO: member A will implement the actual structured dashboard generation
        # For now, return a placeholder
        
        dashboard = f"""# {request.company_name} Dashboard
*Generated: {datetime.now().isoformat()}*
*Pipeline: Structured*

"""
        
        return DashboardResponse(
            company_name=request.company_name,
            pipeline="Structured",
            dashboard=dashboard,
            generated_at=datetime.now().isoformat()
        )
        
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Structured data not found for {request.company_name}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )


# ============================================================
# Utility Endpoints
# ============================================================

@app.get("/test")
def test_endpoint():
    """Simple test endpoint to verify API is working"""
    return {
        "status": "success",
        "message": "API is working correctly!",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("Starting PE Dashboard API Server")
    print("="*60)
    print("\nRAG Pipeline: Ready ✓")
    print("\nAPI Documentation: http://localhost:8000/docs")
    print("="*60 + "\n")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)