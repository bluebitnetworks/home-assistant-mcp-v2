#!/usr/bin/env python3
"""
Home Assistant MCP - REST API Interface.

This module provides a FastAPI-based REST API for the Home Assistant MCP,
allowing web interfaces to interact with the MCP functionality.
"""

import os
import sys
import logging
import asyncio
import uvicorn
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add root directory to path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Import Home Assistant MCP components
try:
    # Try relative imports first (for development)
    from .main import load_config
    from .claude_integration.mcp import HomeAssistantMCP
except ImportError:
    # Fall back to absolute imports (for production/Railway)
    from src.main import load_config
    from src.claude_integration.mcp import HomeAssistantMCP

# Initialize the MCP interface
config = load_config()
mcp = HomeAssistantMCP(config)

# Create FastAPI app
app = FastAPI(
    title="Home Assistant MCP API",
    description="REST API for interacting with Home Assistant via the MCP",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGINS", "*").split(",")],  # Use env var or default to all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Key middleware
@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    # Skip API key check for root endpoint
    if request.url.path == "/":
        return await call_next(request)
        
    api_key = os.getenv("API_KEY")
    # Only check if API_KEY is set
    if api_key and api_key != "":
        request_api_key = request.headers.get("X-API-Key")
        if not request_api_key or request_api_key != api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid or missing API key"}
            )
    return await call_next(request)

# ------ Pydantic Models ------

class EntityControlRequest(BaseModel):
    action: str
    entity_id: Optional[str] = None
    control_action: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None

class DashboardRequest(BaseModel):
    action: str
    title: Optional[str] = None
    views: Optional[List[Dict[str, Any]]] = None
    yaml_content: Optional[str] = None
    output_path: Optional[str] = None

class AutomationRequest(BaseModel):
    action: str
    automation_id: Optional[str] = None
    entity_id: Optional[str] = None
    automation_yaml: Optional[str] = None
    days: Optional[int] = None

class ConfigRequest(BaseModel):
    action: str
    config_type: str
    config_yaml: Optional[str] = None

# ------ API Routes ------

@app.get("/")
async def root():
    """API root endpoint with basic information."""
    return {
        "message": "Home Assistant MCP API",
        "version": "0.1.0",
        "endpoints": [
            "/api/entities",
            "/api/dashboards", 
            "/api/automations",
            "/api/config"
        ]
    }

@app.get("/api/schemas")
async def get_schemas():
    """Get the MCP schemas."""
    return mcp.get_schemas()

# Entity Control Endpoints
@app.post("/api/entities")
async def entity_control(request: EntityControlRequest):
    """Control Home Assistant entities and view their states."""
    try:
        result = await asyncio.to_thread(
            mcp.process_request, 
            "home_assistant_entity_control", 
            request.dict(exclude_none=True)
        )
        return result
    except Exception as e:
        logger.error(f"Error in entity control: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing request: {str(e)}"
        )

# Dashboard Endpoints
@app.post("/api/dashboards")
async def dashboard_control(request: DashboardRequest):
    """Create and validate Home Assistant dashboards."""
    try:
        result = await asyncio.to_thread(
            mcp.process_request, 
            "home_assistant_dashboard", 
            request.dict(exclude_none=True)
        )
        return result
    except Exception as e:
        logger.error(f"Error in dashboard control: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing request: {str(e)}"
        )

# Automation Endpoints
@app.post("/api/automations")
async def automation_control(request: AutomationRequest):
    """Manage Home Assistant automations."""
    try:
        result = await asyncio.to_thread(
            mcp.process_request, 
            "home_assistant_automation", 
            request.dict(exclude_none=True)
        )
        return result
    except Exception as e:
        logger.error(f"Error in automation control: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing request: {str(e)}"
        )

# Config Endpoints
@app.post("/api/config")
async def config_control(request: ConfigRequest):
    """Test and validate Home Assistant configurations."""
    try:
        result = await asyncio.to_thread(
            mcp.process_request, 
            "home_assistant_config", 
            request.dict(exclude_none=True)
        )
        return result
    except Exception as e:
        logger.error(f"Error in config control: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing request: {str(e)}"
        )

# ------ Server ------

def run_server():
    """Run the FastAPI server."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8080))
    reload = os.getenv("DEBUG", "False").lower() == "true"
    
    logger.info(f"Starting Home Assistant MCP REST API on {host}:{port}")
    # Use module name format for uvicorn
    module_name = "src.web_api_v3:app"
    
    # Check if we're running as a module
    if __name__ != "__main__":
        module_name = "web_api_v3:app"
    
    uvicorn.run(
        module_name,
        host=host,
        port=port,
        reload=reload,
    )

if __name__ == "__main__":
    run_server()
