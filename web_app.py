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
    
    # Analyze headers using DataImporter.inspect_file
    mapping, unmapped, missing_required, total_rows = DataImporter.inspect_file(file_path)

    raw_headers = list(mapping.keys()) + unmapped

    cache_id = file_path.name
    temp_import_cache[cache_id] = {
        "file_path": str(file_path),
        "file_name": file.filename,
        "raw_headers": raw_headers,
        "mappings": mapping
    }

    from engine.column_mapper import INTERNAL_FIELDS
    canonical_fields = list(INTERNAL_FIELDS.keys())

    return JSONResponse(content={
        "cache_id": cache_id,
        "file_name": file.filename,
        "raw_headers": raw_headers,
        "suggested_mappings": mapping,
        "missing_required": missing_required,
        "canonical_fields": canonical_fields
    })

class CommitImportRequest(BaseModel):
    cache_id: str
    mappings: Dict[str, str]

@app.post("/api/import/commit")
def commit_import(req: CommitImportRequest):
    if req.cache_id not in temp_import_cache:
        raise HTTPException(status_code=404, detail="Import session expired or invalid cache ID.")
    
    data = temp_import_cache[req.cache_id]
    file_path = Path(data["file_path"])

    session = SessionLocal()
    try:
        # Stack uploads cumulatively into cohort (do NOT delete previous uploads)
        res = DataImporter.import_excel(file_path, req.mappings)

        total_rows = res.get("total_rows", 0)
        new_students = res.get("new_students", 0)
        updated_students = res.get("updated_students", 0)

        return JSONResponse(content={
            "success": True,
            "imported_count": total_rows,
            "new_count": new_students,
            "updated_count": updated_students,
            "warnings": res.get("warnings", [])
        })
    except Exception as e:
        return JSONResponse(content={
            "success": False,
            "errors": [str(e)],
            "warnings": [],
            "imported_count": 0
        })
    finally:
        session.close()

# --- Group Allocation API ---
@app.post("/api/group/allocate")
def run_group_allocation():
    session = SessionLocal()
    try:
        # Reset existing group and venue assignments for active students so the newly uploaded file gets freshly stratified
        session.query(Student).filter(Student.is_deleted == False).update(
            {Student.group_name: None, Student.venue_id: None, Student.time_slot_id: None},
            synchronize_session=False
        )
        session.commit()

        res = GroupAllocator.allocate_groups(auto_backup=False)

        group_a = session.query(Student).filter(Student.group_name == "Group A", Student.is_deleted == False).count()
        group_b = session.query(Student).filter(Student.group_name == "Group B", Student.is_deleted == False).count()

        return JSONResponse(content={
            "success": True,
            "group_a_count": group_a,
            "group_b_count": group_b,
            "newly_allocated": res.newly_allocated_groups,
            "existing_preserved": res.skipped_existing,
            "execution_time_seconds": getattr(res, 'execution_time_seconds', 0.5),
            "details": res.warnings
        })
    except Exception as e:
        return JSONResponse(content={"success": False, "detail": str(e)}, status_code=500)
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

class SlotConfig(BaseModel):
    slot_name: str
    start_time: str = "09:00 AM"
    end_time: str = "11:00 AM"

class VenueConfig(BaseModel):
    name: str
    capacity: int

class VenueAllocationRequest(BaseModel):
    target_group: Optional[str] = None
    slots: Optional[List[SlotConfig]] = None
    venues: Optional[List[VenueConfig]] = None

@app.post("/api/venues/allocate")
def run_venue_allocation(req: Optional[VenueAllocationRequest] = None):
    session = SessionLocal()
    try:
        grp = req.target_group if req and req.target_group and req.target_group != "All" else None

        # 1. Nullify foreign key references on target students first to prevent FK constraint failures
        filter_query = session.query(Student).filter(Student.is_deleted == False)
        if grp:
            filter_query = filter_query.filter(Student.group_name == grp)
        filter_query.update({Student.venue_id: None, Student.time_slot_id: None}, synchronize_session=False)
        session.commit()

        if req:
            # Strictly deactivate/clear previous venues & slots so allocation is 100% scoped to user inputs
            if req.slots and len(req.slots) > 0:
                # Nullify time_slot_id for ALL students before clearing time_slots table
                session.query(Student).update({Student.time_slot_id: None}, synchronize_session=False)
                session.query(TimeSlot).delete(synchronize_session=False)
                session.commit()

                for idx, s in enumerate(req.slots, 1):
                    Repository.get_or_create_time_slot(session, s.slot_name, s.start_time, s.end_time, day_number=idx)
            
            if req.venues and len(req.venues) > 0:
                session.query(Venue).update({Venue.is_active: False}, synchronize_session=False)
                for v in req.venues:
                    v_obj = Repository.get_or_create_venue(session, v.name, v.capacity)
                    v_obj.is_active = True
                    v_obj.capacity = v.capacity

            session.commit()

        res = VenueOptimizer.optimize_allocations(target_group=grp, auto_backup=False)
        return JSONResponse(content={
            "success": True,
            "allocated_count": res.newly_allocated_venues,
            "unallocated_count": max(0, res.total_processed - res.newly_allocated_venues),
            "execution_time_seconds": getattr(res, 'execution_time_seconds', 0.5),
            "solver_name": "PuLP / Proportional MILP Solver",
            "details": res.warnings
        })
    except Exception as e:
        return JSONResponse(content={"success": False, "detail": str(e)}, status_code=500)
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
def export_excel(group: Optional[str] = None):
    session = SessionLocal()
    try:
        target_grp = group if group and group.strip() and group.lower() != "master" and group.lower() != "all" else None
        file_path = ExportService.generate_master_excel(session, group_name=target_grp)
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
