import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, Request, File, UploadFile, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.connection import init_db, SessionLocal
from database.repository import Repository
from database.models import Venue, TimeSlot, ImportHistory, AuditLog, AppSettings, Student
from database.backup_manager import BackupManager
from engine.column_mapper import ColumnMapper
from engine.data_importer import DataImporter
from engine.group_allocator import GroupAllocator
from engine.venue_optimizer import VenueOptimizer
from services.export_service import ExportService

app = FastAPI(title="NexusAllocate Pro Web", version="2.0.0")

# Initialize Database tables
init_db()

# Mount Static & Templates
static_dir = BASE_DIR / "static"
static_dir.mkdir(exist_ok=True)
templates_dir = BASE_DIR / "templates"
templates_dir.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
templates = Jinja2Templates(directory=str(templates_dir))

# Temporary uploaded files store
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

temp_import_cache: Dict[str, Any] = {}

# --- HTML Page Endpoint ---
@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

# --- Dashboard API ---
@app.get("/api/dashboard")
def get_dashboard():
    session = SessionLocal()
    try:
        data = Repository.get_dashboard_summary(session)
        # Format recent imports dates for JSON
        formatted_imports = []
        for imp in data.get("recent_imports", []):
            formatted_imports.append({
                "id": imp.id,
                "file_name": imp.file_name,
                "record_count": imp.record_count,
                "imported_at": imp.imported_at.strftime("%Y-%m-%d %H:%M:%S") if imp.imported_at else ""
            })
        data["recent_imports"] = formatted_imports
        return JSONResponse(content=data)
    finally:
        session.close()

# --- Student Database API ---
@app.get("/api/students")
def get_students(
    search: Optional[str] = None,
    department_id: Optional[int] = None,
    group_name: Optional[str] = None,
    venue_id: Optional[int] = None,
    gender: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    session = SessionLocal()
    try:
        students, total = Repository.get_students(
            session=session,
            search_query=search,
            department_id=department_id,
            group_name=group_name,
            venue_id=venue_id,
            gender=gender,
            limit=limit,
            offset=offset
        )
        student_list = []
        for s in students:
            student_list.append({
                "id": s.id,
                "usn": s.usn,
                "full_name": s.full_name,
                "gender": s.gender,
                "department": s.department.name if s.department else "Unassigned",
                "program": s.program.name if s.program else "",
                "group_name": s.group_name or "Unassigned",
                "venue": s.venue.name if s.venue else "Unassigned",
                "time_slot": s.time_slot.slot_name if s.time_slot else "Unassigned",
                "status": s.status
            })
        return JSONResponse(content={"students": student_list, "total": total, "limit": limit, "offset": offset})
    finally:
        session.close()

# --- File Import APIs ---
@app.post("/api/import/upload")
async def upload_import_file(file: UploadFile = File(...)):
    if not (file.filename.endswith(".xlsx") or file.filename.endswith(".xls") or file.filename.endswith(".csv")):
        raise HTTPException(status_code=400, detail="Invalid file type. Only Excel or CSV files are supported.")
    
    file_path = UPLOAD_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    contents = await file.read()
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Analyze headers using ColumnMapper
    importer = DataImporter()
    raw_headers = importer.extract_headers(str(file_path))
    mappings, confidence_scores = ColumnMapper.map_headers(raw_headers)

    cache_id = file_path.name
    temp_import_cache[cache_id] = {
        "file_path": str(file_path),
        "file_name": file.filename,
        "raw_headers": raw_headers,
        "mappings": mappings
    }

    return JSONResponse(content={
        "cache_id": cache_id,
        "file_name": file.filename,
        "raw_headers": raw_headers,
        "suggested_mappings": mappings,
        "confidence_scores": confidence_scores,
        "canonical_fields": ColumnMapper.CANONICAL_FIELDS
    })

class CommitImportRequest(BaseModel):
    cache_id: str
    mappings: Dict[str, str]

@app.post("/api/import/commit")
def commit_import(req: CommitImportRequest):
    if req.cache_id not in temp_import_cache:
        raise HTTPException(status_code=404, detail="Import session expired or invalid cache ID.")
    
    data = temp_import_cache[req.cache_id]
    file_path = data["file_path"]
    file_name = data["file_name"]

    # Parse and validate with custom header mappings
    importer = DataImporter()
    records, errors, warnings = importer.process_file(file_path, req.mappings)

    if errors:
        return JSONResponse(content={
            "success": False,
            "errors": errors,
            "warnings": warnings,
            "imported_count": 0
        })

    # Save to Database
    session = SessionLocal()
    try:
        imported_count, new_count, updated_count = importer.save_records_to_db(session, records, file_name)
        return JSONResponse(content={
            "success": True,
            "imported_count": imported_count,
            "new_count": new_count,
            "updated_count": updated_count,
            "warnings": warnings
        })
    finally:
        session.close()

# --- Group Allocation API ---
@app.post("/api/group/allocate")
def run_group_allocation():
    session = SessionLocal()
    try:
        allocator = GroupAllocator(session)
        result = allocator.allocate_groups()
        return JSONResponse(content={
            "success": result.success,
            "group_a_count": result.group_a_count,
            "group_b_count": result.group_b_count,
            "newly_allocated": result.newly_allocated,
            "existing_preserved": result.existing_preserved,
            "execution_time_seconds": result.execution_time_seconds,
            "details": result.details
        })
    finally:
        session.close()

# --- Venue & TimeSlot Management APIs ---
@app.get("/api/venues")
def get_venues_and_slots():
    session = SessionLocal()
    try:
        venues = session.query(Venue).filter(Venue.is_active == True).all()
        slots = session.query(TimeSlot).all()

        venue_list = []
        for v in venues:
            filled = session.query(Student).filter(Student.venue_id == v.id, Student.is_deleted == False).count()
            venue_list.append({
                "id": v.id,
                "name": v.name,
                "capacity": v.capacity,
                "location": v.location or "",
                "filled": filled
            })
        
        slot_list = [{
            "id": s.id,
            "slot_name": s.slot_name,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "day_number": s.day_number
        } for s in slots]

        total_students = session.query(Student).filter(Student.is_deleted == False).count()
        total_capacity = sum(v["capacity"] for v in venue_list) * (len(slot_list) or 1)

        return JSONResponse(content={
            "venues": venue_list,
            "slots": slot_list,
            "total_students": total_students,
            "total_capacity": total_capacity
        })
    finally:
        session.close()

class VenueCreateRequest(BaseModel):
    name: str
    capacity: int
    location: Optional[str] = ""

@app.post("/api/venues/add")
def add_venue(req: VenueCreateRequest):
    session = SessionLocal()
    try:
        v = Repository.get_or_create_venue(session, req.name, req.capacity, req.location)
        session.commit()
        return JSONResponse(content={"success": True, "id": v.id, "name": v.name, "capacity": v.capacity})
    finally:
        session.close()

@app.delete("/api/venues/{venue_id}")
def delete_venue(venue_id: int):
    session = SessionLocal()
    try:
        ok, msg = Repository.delete_venue(session, venue_id)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return JSONResponse(content={"success": True, "message": msg})
    finally:
        session.close()

class SlotCreateRequest(BaseModel):
    slot_name: str
    start_time: str
    end_time: str
    day_number: int = 1

@app.post("/api/slots/add")
def add_slot(req: SlotCreateRequest):
    session = SessionLocal()
    try:
        ts = Repository.get_or_create_time_slot(session, req.slot_name, req.start_time, req.end_time, req.day_number)
        session.commit()
        return JSONResponse(content={"success": True, "id": ts.id, "slot_name": ts.slot_name})
    finally:
        session.close()

@app.delete("/api/slots/{slot_id}")
def delete_slot(slot_id: int):
    session = SessionLocal()
    try:
        ok, msg = Repository.delete_time_slot(session, slot_id)
        if not ok:
            raise HTTPException(status_code=400, detail=msg)
        return JSONResponse(content={"success": True, "message": msg})
    finally:
        session.close()

@app.post("/api/venues/allocate")
def run_venue_allocation():
    session = SessionLocal()
    try:
        optimizer = VenueOptimizer(session)
        result = optimizer.allocate_venues()
        return JSONResponse(content={
            "success": result.success,
            "allocated_count": result.allocated_count,
            "unallocated_count": result.unallocated_count,
            "execution_time_seconds": result.execution_time_seconds,
            "solver_name": result.solver_name,
            "details": result.details
        })
    finally:
        session.close()

# --- Backup & Rollback APIs ---
class RestoreBackupRequest(BaseModel):
    backup_id: int

@app.get("/api/backups")
def get_backups():
    manager = BackupManager()
    backups = manager.list_backups()
    formatted = []
    for b in backups:
        filepath = Path(b["file_path"])
        size_bytes = filepath.stat().st_size if filepath.exists() else 0
        dt = b["created_at"]
        formatted.append({
            "id": b["id"],
            "filename": b["filename"],
            "file_path": str(b["file_path"]),
            "size_bytes": size_bytes,
            "created_at": dt.strftime("%Y-%m-%d %H:%M:%S") if isinstance(dt, datetime) else str(dt),
            "exists": b["exists"]
        })
    return JSONResponse(content={"backups": formatted})

@app.post("/api/backups/create")
def create_backup(description: str = Form("Manual Snapshot")):
    try:
        manager = BackupManager()
        rec = manager.create_backup("MANUAL_WEB_SNAPSHOT", description=description)
        return JSONResponse(content={"success": True, "message": f"Successfully created backup '{rec.filename}'"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backups/restore")
def restore_backup(req: RestoreBackupRequest):
    try:
        manager = BackupManager()
        ok = manager.restore_backup(req.backup_id)
        return JSONResponse(content={"success": True, "message": "Database successfully restored to snapshot."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Export Services APIs ---
@app.get("/api/export/excel")
def export_excel():
    session = SessionLocal()
    try:
        file_path = ExportService.generate_master_excel(session)
        return FileResponse(file_path, filename=Path(file_path).name, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    finally:
        session.close()

@app.get("/api/export/csv")
def export_csv(group: Optional[str] = None):
    session = SessionLocal()
    try:
        file_path = ExportService.generate_group_csv(session, group_name=group)
        return FileResponse(file_path, filename=Path(file_path).name, media_type="text/csv")
    finally:
        session.close()

@app.get("/api/export/pdf")
def export_pdf(group: Optional[str] = None):
    session = SessionLocal()
    try:
        file_path = ExportService.generate_pdf_attendance(session, group_name=group)
        return FileResponse(file_path, filename=Path(file_path).name, media_type="application/pdf")
    finally:
        session.close()

# --- Audit Logs API ---
@app.get("/api/logs")
def get_logs(limit: int = 100):
    session = SessionLocal()
    try:
        logs = session.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).all()
        return JSONResponse(content=[{
            "id": l.id,
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "timestamp": l.created_at.strftime("%Y-%m-%d %H:%M:%S") if l.created_at else "",
            "details": l.details
        } for l in logs])
    finally:
        session.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_app:app", host="0.0.0.0", port=8000, reload=True)
