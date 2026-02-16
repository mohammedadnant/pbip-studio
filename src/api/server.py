"""
FastAPI Backend Server
Provides REST API for Power BI migration operations
"""

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.schema import FabricDatabase
from services.indexer import IndexingService
from services.query_service import QueryService
from services.migration_service import MigrationService

# Initialize FastAPI app
app = FastAPI(title="Power BI Migration Toolkit API", version="1.0.0")

# Enable CORS for local Qt WebEngine (restricted to localhost only for security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)

# Initialize database and services
# Use default AppData location (None = get_database_path())
try:
    db = FabricDatabase()
    print("Initializing database schema...")
    db.initialize_schema()
    print(f"✓ Database ready at: {db.get_database_location()}")
except Exception as e:
    print(f"✗ CRITICAL: Database initialization failed: {e}")
    print("  The application may not function correctly.")
    # Create db object anyway to prevent crashes, but it won't work
    db = None

indexer = IndexingService(db) if db else None
query_service = QueryService(db) if db else None
migration_service = MigrationService(db) if db else None


# Pydantic models for API
class WorkspaceResponse(BaseModel):
    workspace_id: str
    workspace_name: str
    tool_id: str
    last_scanned: Optional[str] = None
    scan_status: Optional[str] = None
    dataset_count: int = 0
    table_count: int = 0
    migration_needed_count: int = 0


class DatasetResponse(BaseModel):
    dataset_id: str
    dataset_name: str
    workspace_name: str
    table_count: int
    migration_needed_count: int


class MigrationRequest(BaseModel):
    source_id: int
    new_source_type: str
    new_connection: Dict


# API Endpoints
@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "running", "app": "Power BI Migration Toolkit"}


@app.get("/api/workspaces", response_model=List[WorkspaceResponse])
async def get_workspaces(tool_id: Optional[str] = None):
    """Get all workspaces"""
    workspaces = query_service.get_workspaces(tool_id=tool_id)
    return workspaces


@app.get("/api/datasets", response_model=List[DatasetResponse])
async def search_datasets(
    search: Optional[str] = None,
    workspace_id: Optional[str] = None,
    requires_migration: Optional[bool] = None
):
    """Search datasets with filters"""
    datasets = query_service.search_datasets(
        search_term=search,
        workspace_id=workspace_id,
        requires_migration=requires_migration
    )
    return datasets


@app.get("/api/datasets/{dataset_id}")
async def get_dataset(dataset_id: str):
    """Get dataset details"""
    dataset = query_service.get_dataset_details(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@app.get("/api/datasets/{dataset_id}/tables")
async def get_dataset_tables(dataset_id: str):
    """Get tables for a dataset"""
    tables = query_service.get_dataset_tables(dataset_id)
    return tables


@app.get("/api/data-sources/migration-needed")
async def get_migration_needed_sources():
    """Get data sources that need migration"""
    sources = query_service.get_migration_needed_sources()
    return sources


@app.post("/api/migrate-source")
async def migrate_source(request: MigrationRequest):
    """Migrate a data source"""
    try:
        success = migration_service.update_data_source(
            source_id=request.source_id,
            new_connection=request.new_connection
        )
        
        if success:
            migration_service.log_migration(
                source_id=request.source_id,
                migration_type=f"to_{request.new_source_type}",
                old_connection="",
                new_connection=str(request.new_connection),
                changes={"new_source_type": request.new_source_type},
                status="success"
            )
            return {"status": "success", "message": "Migration completed"}
        else:
            raise HTTPException(status_code=400, detail="Migration failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/index-export")
async def index_export(export_path: str, tool_id: str = "powerbi", clear_existing: bool = False):
    """Index an export folder"""
    try:
        path = Path(export_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Export path not found")
        
        # Clear existing data if requested
        if clear_existing:
            db.clear_all_data()
        
        stats = indexer.index_export_folder(path, tool_id=tool_id)
        return {"status": "success", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Get overall statistics"""
    stats = query_service.get_overall_stats()
    return stats


@app.get("/api/assessment-summary")
async def get_assessment_summary():
    """Get comprehensive assessment summary for management dashboard"""
    try:
        summary = query_service.get_assessment_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/clear-database")
async def clear_database():
    """Clear all data from database"""
    try:
        db.clear_all_data()
        return {"status": "success", "message": "Database cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
