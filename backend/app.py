"""
Veraflux Backend - FastAPI Application Entry Point
Real-time Disaster Intelligence Platform

This module serves as the main entry point for Veraflux API service.
It provides RESTful endpoints for disaster data ingestion, processing,
verification, and visualization.

To run the server:
    uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000
"""

import asyncio
import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

# Add backend directory to Python path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import application modules
try:
    from config.settings import get_settings, is_development
    from storage.event_store import get_event_store
except ImportError:
    # Fallback for development without full config
    class MockSettings:
        def __init__(self):
            self.api = MockAPISettings()
    
    class MockAPISettings:
        def __init__(self):
            self.cors_origins = ["*"]
    
    def get_settings():
        return MockSettings()
    
    def is_development():
        return True
    
    def get_event_store():
        import sys
        import os
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)
        sys.path.append(parent_dir)
        
        from storage.event_store import InMemoryEventStore
        return InMemoryEventStore()


# Global application state
class AppState:
    """Application state manager for shared resources"""
    
    def __init__(self):
        self.settings = get_settings()
        # Initialize with None values - will be set in lifespan if available
        self.db_manager = None
        self.vector_store = None
        self.embedding_generator = None
        self.semantic_search = None
        self.event_repository = None


app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup: Initialize database connections and services
    print(f"Starting Veraflux API - {datetime.utcnow()}")
    
    try:
        # Try to initialize services if dependencies are available
        try:
            from storage.database import DatabaseManager, EventRepository
            app_state.db_manager = DatabaseManager(app_state.settings.database.database_url)
            app_state.db_manager.initialize()
            app_state.event_repository = EventRepository(app_state.db_manager)
            print("✅ Database initialized")
        except Exception as e:
            print(f"⚠️  Database initialization failed: {e}")
        
        try:
            from storage.vector_store import VectorStore, EmbeddingGenerator, SemanticSearchManager
            app_state.vector_store = VectorStore(
                app_state.settings.vector_store.vector_db_url,
                app_state.settings.vector_store.embedding_dimension
            )
            await app_state.vector_store.initialize()
            
            app_state.embedding_generator = EmbeddingGenerator(
                app_state.settings.vector_store.embedding_model
            )
            await app_state.embedding_generator.initialize()
            
            app_state.semantic_search = SemanticSearchManager(
                app_state.vector_store,
                app_state.embedding_generator
            )
            print("✅ Vector store initialized")
        except Exception as e:
            print(f"⚠️  Vector store initialization failed: {e}")
        
        print("✅ Veraflux API started successfully")
        
    except Exception as e:
        print(f"❌ Failed to initialize services: {e}")
        # Don't raise - allow app to start with limited functionality
    
    yield
    
    # Shutdown: Clean up resources
    print("Shutting down Veraflux API...")


# Create FastAPI application with production configuration
app = FastAPI(
    title="Veraflux",
    description="Real-time Disaster Intelligence Platform API",
    version="1.0.0",
    docs_url="/docs" if is_development() else None,
    redoc_url="/redoc" if is_development() else None,
    lifespan=lifespan
)

# Configure CORS for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_state.settings.api.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# Middleware for request logging and error handling
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests and response times"""
    start_time = datetime.utcnow()
    
    try:
        response = await call_next(request)
        process_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Log request details (in production, use proper logging)
        if is_development():
            print(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
        
        response.headers["X-Process-Time"] = str(process_time)
        return response
        
    except Exception as e:
        print(f"Request error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "timestamp": datetime.utcnow().isoformat()}
        )


# API Endpoints

@app.get("/", response_model=Dict[str, Any])
async def root():
    """
    Root endpoint providing API information and health status.
    
    Returns:
        Dict containing API metadata and basic health information.
    """
    return {
        "service": "Veraflux",
        "description": "Real-time Disaster Intelligence Platform",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "health": "/health",
            "events": "/events",
            "docs": "/docs" if is_development() else "Documentation not available in production"
        }
    }


@app.get("/health", response_model=Dict[str, Any])
async def health_check():
    """
    Comprehensive health check endpoint.
    
    Monitors the status of all critical system components including
    database connectivity, vector store availability, and overall system health.
    
    Returns:
        Dict containing detailed health status of all system components.
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "components": {}
    }
    
    try:
        # Check database connectivity
        if app_state.db_manager:
            health_status["components"]["database"] = {
                "status": "healthy",
                "message": "Database connection established"
            }
        else:
            health_status["components"]["database"] = {
                "status": "unhealthy",
                "message": "Database not initialized"
            }
            health_status["status"] = "degraded"
        
        # Check vector store
        if app_state.vector_store:
            health_status["components"]["vector_store"] = {
                "status": "healthy",
                "message": "Vector store operational"
            }
        else:
            health_status["components"]["vector_store"] = {
                "status": "unhealthy",
                "message": "Vector store not initialized"
            }
            health_status["status"] = "degraded"
        
        # Check embedding service
        if app_state.embedding_generator:
            health_status["components"]["embedding_service"] = {
                "status": "healthy",
                "message": "Embedding service ready"
            }
        else:
            health_status["components"]["embedding_service"] = {
                "status": "unhealthy",
                "message": "Embedding service not initialized"
            }
            health_status["status"] = "degraded"
        
        # Overall status determination
        unhealthy_components = [
            name for name, comp in health_status["components"].items()
            if comp["status"] == "unhealthy"
        ]
        
        if unhealthy_components:
            health_status["status"] = "unhealthy" if len(unhealthy_components) > 1 else "degraded"
        
        return health_status
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "components": health_status.get("components", {})
        }


@app.get("/version", response_model=Dict[str, str])
async def get_version():
    """
    Version information endpoint.
    
    Returns:
        Dict containing version and build information.
    """
    return {
        "api_version": "1.0.0",
        "build_timestamp": datetime.utcnow().isoformat(),
        "environment": "development"  # Simplified for now
    }


# Exception handlers for production-ready error responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with generic error response"""
    print(f"Unhandled exception: {exc}")  # Log the full exception for debugging
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat(),
            "path": str(request.url.path)
        }
    )


# Events endpoints
@app.get("/events", response_model=List[Dict[str, Any]])
async def get_events(
    source: Optional[str] = None,
    event_type: Optional[str] = None,
    state: Optional[str] = None,
    limit: int = 50
):
    """
    Get all ingested events with optional filtering
    
    Args:
        source: Filter by source name (e.g., "National Disaster Management Authority")
        event_type: Filter by event type (e.g., "flood", "earthquake")
        state: Filter by Indian state (e.g., "maharashtra", "kerala")
        limit: Maximum number of events to return (default: 50)
        
    Returns:
        List of event dictionaries matching the criteria
    """
    try:
        # Get event store with fallback
        event_store = None
        try:
            from storage.event_store import get_event_store
            event_store = get_event_store()
        except ImportError:
            # Fallback for standalone execution - use the same global store as RSS ingestor
            try:
                from ingestion.rss_ingestor import get_memory_store
                event_store = get_memory_store()
                print(f"Using memory store from RSS ingestor: {type(event_store)}")
            except ImportError:
                # Final fallback - create a simple store
                class SimpleEventStore:
                    def __init__(self):
                        self.events = []
                    
                    def get_all_events(self):
                        return self.events
                    
                    def add_events(self, events):
                        self.events.extend(events)
                        return len(events)
                
                event_store = SimpleEventStore()
        
        # Debug logging
        print(f"Event store type: {type(event_store)}")
        print(f"Event count: {event_store.get_event_count()}")
        
        # Start with all events
        events = event_store.get_all_events()
        
        # Apply filters
        if source:
            events = [e for e in events if e.source_name == source]
        
        if event_type:
            events = [e for e in events if e.event_type.value == event_type]
        
        if state:
            events = [e for e in events if e.location and e.location.address and state.lower() in e.location.address.lower()]
        
        # Apply limit
        events = events[:limit]
        
        # Convert to simple dictionaries
        return [{"id": e.id, "title": e.title, "text": e.text, "event_type": e.event_type.value, 
                "severity": e.severity, "source_name": e.source_name, "timestamp": e.timestamp.isoformat(),
                "location": e.location.to_dict() if e.location else None,
                "verified": e.verified, "confidence": e.confidence, "tags": e.tags} for e in events]
        
    except Exception as e:
        print(f"Error in get_events: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to retrieve events: {str(e)}"}
        )


@app.post("/ingest/rss")
async def trigger_rss_ingestion():
    """
    Trigger RSS ingestion manually
    
    Returns:
        Dict with ingestion results
    """
    try:
        from ingestion.rss_ingestor import IndiaRSSIngestor
        
        # Create and run RSS ingestor
        ingestor = IndiaRSSIngestor()
        events = await ingestor.ingest()
        
        return {
            "status": "success",
            "message": f"RSS ingestion completed",
            "events_processed": len(events),
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"RSS ingestion failed: {str(e)}"}
        )


# Development server startup
if __name__ == "__main__":
    import uvicorn
    
    # Run the development server
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
