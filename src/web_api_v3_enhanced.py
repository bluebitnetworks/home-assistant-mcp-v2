#!/usr/bin/env python3
"""
Home Assistant MCP - Enhanced REST API Interface with WebSocket Support.

This module provides a FastAPI-based REST & WebSocket API for the Home Assistant MCP,
allowing web interfaces to interact with the MCP functionality in real-time.
"""

import os
import sys
import logging
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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
from src.main import load_config
from src.claude_integration.mcp import HomeAssistantMCP

# ----- WebSocket Connection Manager -----

class ConnectionManager:
    """Manages WebSocket connections and broadcasts."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.subscription_topics: Dict[WebSocket, List[str]] = {}
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.subscription_topics[websocket] = []
        logger.info(f"New WebSocket connection. Total active: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.subscription_topics:
            del self.subscription_topics[websocket]
        logger.info(f"WebSocket disconnected. Total active: {len(self.active_connections)}")
    
    async def subscribe(self, websocket: WebSocket, topic: str):
        """Subscribe a connection to a topic."""
        if websocket in self.subscription_topics:
            if topic not in self.subscription_topics[websocket]:
                self.subscription_topics[websocket].append(topic)
                await websocket.send_json({
                    "type": "subscription_success",
                    "topic": topic,
                    "message": f"Subscribed to {topic}"
                })
                logger.info(f"Client subscribed to {topic}")
            else:
                await websocket.send_json({
                    "type": "subscription_info",
                    "topic": topic,
                    "message": f"Already subscribed to {topic}"
                })
    
    async def unsubscribe(self, websocket: WebSocket, topic: str):
        """Unsubscribe a connection from a topic."""
        if websocket in self.subscription_topics and topic in self.subscription_topics[websocket]:
            self.subscription_topics[websocket].remove(topic)
            await websocket.send_json({
                "type": "unsubscription_success",
                "topic": topic,
                "message": f"Unsubscribed from {topic}"
            })
            logger.info(f"Client unsubscribed from {topic}")
    
    async def broadcast_to_topic(self, topic: str, message: Dict[str, Any]):
        """Broadcast a message to all subscribers of a topic."""
        message["timestamp"] = datetime.now().isoformat()
        
        count = 0
        for connection, topics in self.subscription_topics.items():
            if topic in topics:
                try:
                    await connection.send_json({
                        "type": "message",
                        "topic": topic,
                        "data": message
                    })
                    count += 1
                except Exception as e:
                    logger.error(f"Error sending to WebSocket: {str(e)}")
        
        logger.debug(f"Broadcast message to {count} subscribers of {topic}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected clients."""
        message["timestamp"] = datetime.now().isoformat()
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json({
                    "type": "broadcast",
                    "data": message
                })
            except Exception as e:
                logger.error(f"Error sending to WebSocket: {str(e)}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)

# ----- Initialize API Components -----

# Initialize the MCP interface
config = load_config()
mcp = HomeAssistantMCP(config)

# Create WebSocket manager
manager = ConnectionManager()

# Create FastAPI app with detailed docs
app = FastAPI(
    title="Home Assistant MCP API",
    description="""
    REST and WebSocket API for interacting with Home Assistant via the MCP.
    
    ## Features
    
    * **Entity Control**: Get and control Home Assistant entities
    * **Dashboards**: Create and validate dashboards
    * **Automations**: Manage automations, including suggestions
    * **Config**: Test and validate configurations
    * **WebSockets**: Real-time updates and event subscriptions
    
    ## Authentication
    
    Authentication is optional and can be enabled in the configuration.
    When enabled, use the `X-API-Key` header with your API key.
    """,
    version="0.1.0",
    docs_url=None,  # We'll create custom docs endpoint
    redoc_url="/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple API key authentication
API_KEY = config.get("api", {}).get("key", "")
API_KEY_ENABLED = bool(API_KEY)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: str = Depends(api_key_header)):
    """Validate API key if enabled."""
    if not API_KEY_ENABLED:
        return True
    
    if api_key and api_key == API_KEY:
        return True
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )

# ----- Pydantic Models -----

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

class WebSocketMessage(BaseModel):
    action: str
    topic: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

# ----- Helper Functions -----

async def process_entity_state_changes():
    """
    Background task to monitor entity state changes and broadcast via WebSocket.
    """
    last_states = {}
    
    while True:
        try:
            # Get current entity states
            states = await mcp.api.get_states()
            
            # Check for changes
            for state in states:
                entity_id = state.get("entity_id")
                if not entity_id:
                    continue
                
                # If we have this entity in our last states
                if entity_id in last_states:
                    last_state = last_states[entity_id]
                    
                    # If state or attributes changed
                    if (last_state.get("state") != state.get("state") or
                            last_state.get("attributes") != state.get("attributes")):
                        
                        # Broadcast the change
                        await manager.broadcast_to_topic(
                            f"entity:{entity_id}", 
                            {
                                "entity_id": entity_id,
                                "state": state.get("state"),
                                "attributes": state.get("attributes"),
                                "last_changed": state.get("last_changed"),
                                "last_updated": state.get("last_updated"),
                            }
                        )
                        
                        # Also broadcast to general entity updates topic
                        await manager.broadcast_to_topic(
                            "entities:updated",
                            {
                                "entity_id": entity_id,
                                "state": state.get("state"),
                                "attributes": state.get("attributes"),
                                "last_changed": state.get("last_changed"),
                                "last_updated": state.get("last_updated"),
                            }
                        )
                
                # Update last known state
                last_states[entity_id] = state
                
            # Wait before checking again
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"Error in entity state monitor: {str(e)}")
            await asyncio.sleep(5)  # Wait longer if there was an error

# ----- API Routes -----

@app.get("/", dependencies=[Depends(get_api_key)])
async def root():
    """API root endpoint with basic information."""
    return {
        "message": "Home Assistant MCP API",
        "version": "0.1.0",
        "endpoints": [
            "/api/entities",
            "/api/dashboards", 
            "/api/automations",
            "/api/config",
            "/ws"
        ],
        "docs": "/docs",
        "redoc": "/redoc",
        "auth_required": API_KEY_ENABLED,
    }

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Custom Swagger UI."""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Home Assistant MCP API",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Check Home Assistant connection
    is_valid, error = await mcp.api.validate_connection()
    
    if is_valid:
        return {
            "status": "healthy",
            "home_assistant": "connected",
            "timestamp": datetime.now().isoformat()
        }
    else:
        return {
            "status": "unhealthy",
            "home_assistant": "disconnected",
            "error": error,
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/schemas", dependencies=[Depends(get_api_key)])
async def get_schemas():
    """Get the MCP schemas."""
    return mcp.get_schemas()

# Entity Control Endpoints
@app.post("/api/entities", dependencies=[Depends(get_api_key)])
async def entity_control(request: EntityControlRequest, background_tasks: BackgroundTasks):
    """Control Home Assistant entities and view their states."""
    try:
        result = await asyncio.to_thread(
            mcp.process_request, 
            "home_assistant_entity_control", 
            request.dict(exclude_none=True)
        )
        
        # If controlling an entity, emit WebSocket event
        if request.action == "control_entity" and request.entity_id:
            background_tasks.add_task(
                manager.broadcast_to_topic,
                "entities:controlled",
                {
                    "entity_id": request.entity_id,
                    "action": request.control_action,
                    "parameters": request.parameters,
                    "result": result
                }
            )
        
        return result
    except Exception as e:
        logger.error(f"Error in entity control: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing request: {str(e)}"
        )

# Dashboard Endpoints
@app.post("/api/dashboards", dependencies=[Depends(get_api_key)])
async def dashboard_control(request: DashboardRequest, background_tasks: BackgroundTasks):
    """Create and validate Home Assistant dashboards."""
    try:
        result = await asyncio.to_thread(
            mcp.process_request, 
            "home_assistant_dashboard", 
            request.dict(exclude_none=True)
        )
        
        # Emit WebSocket event
        if request.action == "create_dashboard":
            background_tasks.add_task(
                manager.broadcast_to_topic,
                "dashboards:updated",
                {
                    "action": "created",
                    "title": request.title,
                    "result": result
                }
            )
        
        return result
    except Exception as e:
        logger.error(f"Error in dashboard control: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing request: {str(e)}"
        )

# Automation Endpoints
@app.post("/api/automations", dependencies=[Depends(get_api_key)])
async def automation_control(request: AutomationRequest, background_tasks: BackgroundTasks):
    """Manage Home Assistant automations."""
    try:
        result = await asyncio.to_thread(
            mcp.process_request, 
            "home_assistant_automation", 
            request.dict(exclude_none=True)
        )
        
        # Emit WebSocket event for automation changes
        if request.action in ["create_automation", "update_automation", "delete_automation"]:
            background_tasks.add_task(
                manager.broadcast_to_topic,
                "automations:updated",
                {
                    "action": request.action,
                    "automation_id": request.automation_id,
                    "result": result
                }
            )
        
        return result
    except Exception as e:
        logger.error(f"Error in automation control: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing request: {str(e)}"
        )

# Config Endpoints
@app.post("/api/config", dependencies=[Depends(get_api_key)])
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

# WebSocket Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                # Parse message
                message = json.loads(data)
                action = message.get("action", "")
                
                if action == "ping":
                    # Simple ping-pong for connection testing
                    await websocket.send_json({
                        "type": "pong", 
                        "timestamp": datetime.now().isoformat()
                    })
                
                elif action == "subscribe":
                    # Subscribe to a topic
                    topic = message.get("topic", "")
                    if topic:
                        await manager.subscribe(websocket, topic)
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Missing topic for subscription"
                        })
                
                elif action == "unsubscribe":
                    # Unsubscribe from a topic
                    topic = message.get("topic", "")
                    if topic:
                        await manager.unsubscribe(websocket, topic)
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Missing topic for unsubscription"
                        })
                
                elif action == "get_entity":
                    # Get entity state
                    entity_id = message.get("entity_id", "")
                    if entity_id:
                        state = await mcp.api.get_entity_state(entity_id)
                        await websocket.send_json({
                            "type": "entity_state",
                            "entity_id": entity_id,
                            "data": state
                        })
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Missing entity_id"
                        })
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown action: {action}"
                    })
                
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON message"
                })
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {str(e)}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"Error processing message: {str(e)}"
                })
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        manager.disconnect(websocket)

# ----- Startup and Shutdown Events -----

@app.on_event("startup")
async def startup_event():
    """Run when the API server starts."""
    logger.info("Starting Home Assistant MCP REST & WebSocket API")
    
    # Start the entity state monitor in the background
    asyncio.create_task(process_entity_state_changes())

@app.on_event("shutdown")
async def shutdown_event():
    """Run when the API server shuts down."""
    logger.info("Shutting down Home Assistant MCP REST & WebSocket API")
    await mcp.api.close()

# ----- Server -----

def run_server(host="0.0.0.0", port=8080, reload=False):
    """Run the FastAPI server."""
    logger.info(f"Starting Home Assistant MCP REST & WebSocket API on {host}:{port}")
    uvicorn.run(
        "web_api_v3_enhanced:app",
        host=host,
        port=port,
        reload=reload,
    )

if __name__ == "__main__":
    run_server()
