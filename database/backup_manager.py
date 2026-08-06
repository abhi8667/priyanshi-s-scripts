import shutil
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from config import DB_PATH, BACKUP_DIR
from database.connection import SessionLocal
from database.models import BackupHistory, Student, AuditLog
from core.exceptions import BackupError

class BackupManager:
    """Manages automatic timestamped SQLite backups, checksum verification, and 1-click rollback."""

    @staticmethod
    def _compute_checksum(file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @classmethod
    def create_backup(cls, trigger_action: str, description: Optional[str] = None) -> BackupHistory:
        """Creates an atomic timestamped backup using SQLite online backup API."""
        if not DB_PATH.exists():
            raise BackupError(f"Database file does not exist at {DB_PATH}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_filename = f"backup_{timestamp}.db"
        dest_path = BACKUP_DIR / backup_filename

        try:
            # Use SQLite backup API to ensure safety even if DB is actively open
            src_conn = sqlite3.connect(DB_PATH)
            dst_conn = sqlite3.connect(dest_path)
            with dst_conn:
                src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()

            checksum = cls._compute_checksum(dest_path)

            # Record in database
            session: Session = SessionLocal()
            try:
                student_count = session.query(Student).filter(Student.is_deleted == False).count()
                backup_record = BackupHistory(
                    filename=backup_filename,
                    file_path=str(dest_path),
                    checksum=checksum,
                    trigger_action=trigger_action,
                    student_count=student_count,
                    created_at=datetime.utcnow()
                )
                session.add(backup_record)
                
                # Audit log
                audit = AuditLog(
                    action="DATABASE_BACKUP_CREATED",
                    entity_type="Backup",
                    details=f"Backup created: {backup_filename} | Action: {trigger_action} | Records: {student_count}"
                )
                session.add(audit)
                session.commit()
                session.refresh(backup_record)
                return backup_record
            finally:
                session.close()

        except Exception as e:
            if dest_path.exists():
                dest_path.unlink()
            raise BackupError(f"Failed to create database backup: {str(e)}")

    @classmethod
    def list_backups(cls) -> List[Dict[str, Any]]:
        """Returns all backup history records sorted newest first."""
        session: Session = SessionLocal()
        try:
            records = session.query(BackupHistory).order_by(BackupHistory.created_at.desc()).all()
            return [
                {
                    "id": r.id,
                    "filename": r.filename,
                    "file_path": r.file_path,
                    "checksum": r.checksum,
                    "trigger_action": r.trigger_action,
                    "student_count": r.student_count,
                    "created_at": r.created_at,
                    "exists": Path(r.file_path).exists()
                }
                for r in records
            ]
        finally:
            session.close()

    @classmethod
    def restore_backup(cls, backup_id: int) -> bool:
        """Restores the database to a chosen backup after checksum verification."""
        session: Session = SessionLocal()
        try:
            backup = session.query(BackupHistory).filter(BackupHistory.id == backup_id).first()
            if not backup:
                raise BackupError(f"Backup record with ID {backup_id} not found.")

            backup_file = Path(backup.file_path)
            if not backup_file.exists():
                raise BackupError(f"Backup file missing on disk: {backup.file_path}")

            # Verify checksum before restoring
            current_checksum = cls._compute_checksum(backup_file)
            if current_checksum != backup.checksum:
                raise BackupError("Backup file checksum mismatch! The backup file may be corrupted.")

            session.close()

            # Create a safety pre-rollback snapshot of current DB state
            cls.create_backup(trigger_action="PRE_ROLLBACK_AUTO_SAVE")

            # Restore file atomically
            src_conn = sqlite3.connect(backup_file)
            dst_conn = sqlite3.connect(DB_PATH)
            with dst_conn:
                src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()

            # Log post-restore audit event
            new_session = SessionLocal()
            audit = AuditLog(
                action="DATABASE_RESTORED",
                entity_type="Backup",
                entity_id=str(backup_id),
                details=f"Database restored to backup {backup.filename} (Timestamp: {backup.created_at})"
            )
            new_session.add(audit)
            new_session.commit()
            new_session.close()

            return True
        except Exception as e:
            raise BackupError(f"Rollback failed: {str(e)}")
