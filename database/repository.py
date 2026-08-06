from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func
from database.connection import SessionLocal
from database.models import (
    Student, Department, Program, Venue, TimeSlot,
    ImportHistory, AuditLog, AppSettings
)
from core.domain_models import StudentRecord, Gender, StudentStatus

class Repository:
    """Encapsulates all database query and transaction logic."""

    @staticmethod
    def get_or_create_department(session: Session, name: str, code: Optional[str] = None) -> Department:
        clean_name = name.strip()
        dept = session.query(Department).filter(func.lower(Department.name) == clean_name.lower()).first()
        if not dept:
            dept_code = code or clean_name[:4].upper()
            dept = Department(name=clean_name, code=dept_code)
            session.add(dept)
            session.flush()
        return dept

    @staticmethod
    def get_or_create_program(session: Session, name: str, code: Optional[str] = None) -> Program:
        clean_name = name.strip()
        prog = session.query(Program).filter(func.lower(Program.name) == clean_name.lower()).first()
        if not prog:
            prog_code = code or clean_name[:4].upper()
            prog = Program(name=clean_name, code=prog_code)
            session.add(prog)
            session.flush()
        return prog

    @staticmethod
    def get_or_create_venue(session: Session, name: str, capacity: int, location: Optional[str] = None) -> Venue:
        clean_name = name.strip()
        venue = session.query(Venue).filter(func.lower(Venue.name) == clean_name.lower()).first()
        if not venue:
            venue = Venue(name=clean_name, capacity=capacity, location=location)
            session.add(venue)
            session.flush()
        else:
            if capacity != venue.capacity:
                venue.capacity = capacity
                session.flush()
        return venue

    @staticmethod
    def get_or_create_time_slot(session: Session, slot_name: str, start_time: str, end_time: str, day_number: int = 1) -> TimeSlot:
        clean_slot = slot_name.strip()
        ts = session.query(TimeSlot).filter(
            func.lower(TimeSlot.slot_name) == clean_slot.lower(),
            TimeSlot.day_number == day_number
        ).first()
        if not ts:
            ts = TimeSlot(slot_name=clean_slot, start_time=start_time, end_time=end_time, day_number=day_number)
            session.add(ts)
            session.flush()
        return ts

    @classmethod
    def get_students(
        cls,
        session: Session,
        search_query: Optional[str] = None,
        department_id: Optional[int] = None,
        program_id: Optional[int] = None,
        group_name: Optional[str] = None,
        venue_id: Optional[int] = None,
        time_slot_id: Optional[int] = None,
        gender: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> Tuple[List[Student], int]:
        """Queries students with filters, full text search across USN/ID/Name, and pagination."""
        query = session.query(Student).options(
            joinedload(Student.department),
            joinedload(Student.program),
            joinedload(Student.venue),
            joinedload(Student.time_slot)
        ).filter(Student.is_deleted == False)

        if search_query and search_query.strip():
            term = f"%{search_query.strip()}%"
            query = query.filter(
                or_(
                    Student.usn.ilike(term),
                    Student.student_id.ilike(term),
                    Student.student_number.ilike(term),
                    Student.full_name.ilike(term)
                )
            )

        if department_id:
            query = query.filter(Student.department_id == department_id)
        if program_id:
            query = query.filter(Student.program_id == program_id)
        if group_name:
            query = query.filter(Student.group_name == group_name)
        if venue_id:
            query = query.filter(Student.venue_id == venue_id)
        if time_slot_id:
            query = query.filter(Student.time_slot_id == time_slot_id)
        if gender and gender != "All":
            query = query.filter(Student.gender == gender)
        if status and status != "All":
            query = query.filter(Student.status == status)

        total_count = query.count()

        query = query.order_by(Student.usn.asc())

        if offset is not None:
            query = query.offset(offset)
        if limit is not None:
            query = query.limit(limit)

        return query.all(), total_count

    @classmethod
    def get_dashboard_summary(cls, session: Session) -> Dict[str, Any]:
        """Generates summary statistics for the dashboard cards and charts."""
        total_students = session.query(Student).filter(Student.is_deleted == False).count()
        allocated_groups = session.query(Student).filter(Student.is_deleted == False, Student.group_name.isnot(None)).count()
        allocated_venues = session.query(Student).filter(Student.is_deleted == False, Student.venue_id.isnot(None)).count()
        pending_allocation = session.query(Student).filter(Student.is_deleted == False, Student.group_name.is_(None)).count()

        group_counts = session.query(
            Student.group_name, func.count(Student.id)
        ).filter(Student.is_deleted == False).group_by(Student.group_name).all()

        gender_counts = session.query(
            Student.gender, func.count(Student.id)
        ).filter(Student.is_deleted == False).group_by(Student.gender).all()

        dept_counts = session.query(
            Department.name, func.count(Student.id)
        ).join(Student, Student.department_id == Department.id).filter(
            Student.is_deleted == False
        ).group_by(Department.name).all()

        venues = session.query(Venue).filter(Venue.is_active == True).all()
        venue_stats = []
        for v in venues:
            filled = session.query(Student).filter(Student.venue_id == v.id, Student.is_deleted == False).count()
            venue_stats.append({
                "id": v.id,
                "name": v.name,
                "capacity": v.capacity,
                "filled": filled,
                "remaining": max(0, v.capacity - filled)
            })

        recent_imports = session.query(ImportHistory).order_by(ImportHistory.imported_at.desc()).limit(10).all()

        return {
            "total_students": total_students,
            "allocated_groups": allocated_groups,
            "allocated_venues": allocated_venues,
            "pending_allocation": pending_allocation,
            "group_distribution": {g or "Unassigned": cnt for g, cnt in group_counts},
            "gender_distribution": {gen or "Unknown": cnt for gen, cnt in gender_counts},
            "department_distribution": {d: cnt for d, cnt in dept_counts},
            "venue_utilization": venue_stats,
            "recent_imports": recent_imports
        }

    @classmethod
    def delete_import_history(cls, session: Session, import_id: int) -> Tuple[bool, str]:
        """Deletes an import history record from SQLite and records an audit log."""
        imp = session.query(ImportHistory).filter(ImportHistory.id == import_id).first()
        if not imp:
            return False, "Import record not found."

        file_name = imp.file_name
        session.delete(imp)

        audit = AuditLog(
            action="IMPORT_FILE_DELETED",
            entity_type="ImportHistory",
            entity_id=str(import_id),
            details=f"Deleted import history record for file '{file_name}'."
        )
        session.add(audit)
        session.commit()
        return True, f"Successfully deleted import file record '{file_name}'."
