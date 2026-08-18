import pandas as pd
import hashlib
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
from pathlib import Path
from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from database.models import Student, Department, Program, ImportHistory, AuditLog
from database.repository import Repository
from engine.column_mapper import ColumnMapper
from core.domain_models import Gender, StudentStatus
from core.exceptions import ValidationError, InductionSystemError
from config import NEAR_DUPLICATE_THRESHOLD

class DataImporter:
    """Handles file parsing, fuzzy header mapping, validation, duplicate detection, and smart differential imports."""

    @classmethod
    def inspect_file(cls, file_path: Path) -> Tuple[Dict[str, str], List[str], List[str], int]:
        """Reads file headers and returns proposed column mappings and row count."""
        ext = file_path.suffix.lower()
        if ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path, nrows=5)
        elif ext == '.csv':
            df = pd.read_csv(file_path, nrows=5)
        else:
            raise ValidationError(f"Unsupported file format: {ext}. Please upload .xlsx, .xls, or .csv")

        total_rows = len(pd.read_excel(file_path)) if ext in ['.xlsx', '.xls'] else len(pd.read_csv(file_path))

        mapping, unmapped, missing_required = ColumnMapper.map_columns(list(df.columns))
        return mapping, unmapped, missing_required, total_rows

    @classmethod
    def import_excel(cls, file_path: Path, column_mapping: Dict[str, str]) -> Dict[str, Any]:
        """Executes the full import pipeline with validation, diffing, and audit logging."""
        ext = file_path.suffix.lower()
        if ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        elif ext == '.csv':
            df = pd.read_csv(file_path)
        else:
            raise ValidationError(f"Unsupported file format: {ext}")

        # Hash file to detect re-uploading identical file
        with open(file_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        session: Session = SessionLocal()
        try:
            # Check duplicate upload
            existing_import = session.query(ImportHistory).filter(ImportHistory.file_hash == file_hash).first()
            
            # Map columns in DataFrame
            df_renamed = df.rename(columns=column_mapping)
            
            if 'department' not in df_renamed.columns:
                if 'program' in df_renamed.columns:
                    df_renamed['department'] = df_renamed['program']
                else:
                    df_renamed['department'] = 'General'

            new_count = 0
            updated_count = 0
            duplicate_usn_count = 0
            warnings = []

            # Pre-load all existing students (including soft-deleted) by USN and Student ID to prevent duplicate records
            existing_students_map = {
                s.usn.strip().upper(): s for s in session.query(Student).filter(Student.usn.isnot(None)).all()
            }
            existing_student_ids_map = {
                s.student_id.strip().upper(): s for s in session.query(Student).filter(Student.student_id.isnot(None)).all()
            }

            # Create ImportHistory record first
            imp_record = ImportHistory(
                file_name=file_path.name,
                file_hash=file_hash,
                total_rows=len(df),
                new_records=0,
                updated_records=0,
                duplicate_records=0,
                imported_at=datetime.utcnow()
            )
            session.add(imp_record)
            session.flush()

            ts_tag = int(datetime.utcnow().timestamp()) % 10000

            for idx, row in df_renamed.iterrows():
                row_num = idx + 2  # Excel 1-based header offset
                raw_usn = str(row.get('usn', '')).strip() if pd.notna(row.get('usn')) else ""
                raw_stu_id = str(row.get('student_id', '')).strip() if pd.notna(row.get('student_id')) else ""
                raw_name = str(row.get('full_name', '')).strip() if pd.notna(row.get('full_name')) else ""
                raw_dept = str(row.get('department', '')).strip() if pd.notna(row.get('department')) else ""
                raw_prog = str(row.get('program', 'B.Tech')).strip() if pd.notna(row.get('program')) else "B.Tech"
                raw_gender = str(row.get('gender', 'Unknown')) if pd.notna(row.get('gender')) else "Unknown"
                raw_stu_num = str(row.get('student_number', '')).strip() if pd.notna(row.get('student_number')) else None

                # Sync USN and Student ID if one is provided (e.g. RVCE26B__1234)
                if not raw_usn and raw_stu_id:
                    raw_usn = raw_stu_id
                elif not raw_stu_id and raw_usn:
                    raw_stu_id = raw_usn

                # Automatic unique fallbacks if both USN and Student ID are missing
                if not raw_usn or raw_usn.lower() in ['nan', 'none', 'null']:
                    raw_usn = f"STU_{ts_tag}_{(idx+1):04d}"
                    raw_stu_id = raw_usn

                if not raw_name or raw_name.lower() in ['nan', 'none', 'null']:
                    raw_name = raw_usn

                if not raw_dept or raw_dept.lower() in ['nan', 'none', 'null']:
                    raw_dept = "General"

                clean_usn_key = raw_usn.upper()
                clean_id_key = raw_stu_id.upper()
                gender_enum = Gender.parse(raw_gender)

                dept_obj = Repository.get_or_create_department(session, raw_dept)
                prog_obj = Repository.get_or_create_program(session, raw_prog)

                # Deduplication check: Search by USN key or Student ID key
                matched_stu = existing_students_map.get(clean_usn_key) or existing_student_ids_map.get(clean_id_key)

                if matched_stu:
                    # Overwrite existing student record with LATEST information (keep latest only)
                    matched_stu.usn = raw_usn
                    matched_stu.student_id = raw_stu_id
                    matched_stu.full_name = raw_name
                    matched_stu.department_id = dept_obj.id
                    matched_stu.gender = gender_enum.value
                    matched_stu.status = StudentStatus.ACTIVE.value
                    matched_stu.is_deleted = False
                    matched_stu.import_history_id = imp_record.id
                    matched_stu.updated_at = datetime.utcnow()

                    existing_students_map[clean_usn_key] = matched_stu
                    existing_student_ids_map[clean_id_key] = matched_stu
                    updated_count += 1
                else:
                    new_stu = Student(
                        usn=raw_usn,
                        student_id=raw_stu_id,
                        student_number=raw_stu_num,
                        full_name=raw_name,
                        gender=gender_enum.value,
                        status=StudentStatus.ACTIVE.value,
                        department_id=dept_obj.id,
                        program_id=prog_obj.id,
                        import_history_id=imp_record.id,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(new_stu)
                    existing_students_map[clean_usn_key] = new_stu
                    existing_student_ids_map[clean_id_key] = new_stu
                    new_count += 1

            # Update final counts on ImportHistory
            imp_record.new_records = new_count
            imp_record.updated_records = updated_count
            imp_record.duplicate_records = duplicate_usn_count

            # Audit Log
            audit = AuditLog(
                action="EXCEL_IMPORT_SUCCESS",
                entity_type="Student",
                details=f"Imported file '{file_path.name}': {new_count} new students, {updated_count} updated, {duplicate_usn_count} duplicates/skipped."
            )
            session.add(audit)

            session.commit()

            return {
                "success": True,
                "file_name": file_path.name,
                "total_rows": len(df),
                "new_students": new_count,
                "updated_students": updated_count,
                "duplicate_skipped": duplicate_usn_count,
                "warnings": warnings,
                "is_reimport": existing_import is not None
            }

        except Exception as e:
            session.rollback()
            raise ValidationError(f"Import process failed: {str(e)}")
        finally:
            session.close()
